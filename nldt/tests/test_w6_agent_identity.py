from __future__ import annotations

import json

from fastapi.testclient import TestClient

# W6a end-to-end (offline): agent virtual wallet (keycloak mode) -> auth edge
# (KeycloakBackend with faked RFC 7662 introspection) -> nLDT token ->
# process adapter trust gate -> PROV actor claims.
#
# The only faked boundary is Keycloak itself (token fetch + introspection);
# wallet, edge, schema validation, trust gate and process execution are real.


def test_w6a_end_to_end_token_gate_and_prov(tmp_path, monkeypatch):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"gates": {"crosstrack-overlay": {"agentAssurance": "attested"}}}))
    monkeypatch.setenv("NLDT_TRUST_POLICY_FILE", str(policy))
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")

    # --- auth edge with the Keycloak backend over faked introspection -------
    from services.auth_wallet import app as edge_app
    from services.auth_wallet.backend import KeycloakBackend

    intro = {
        "active": True,
        "azp": "beleidskompas-svc",
        "realm_access": {"roles": ["nldt-capability.breda-scan-query"]},
    }

    async def fake_introspect(self, token):
        return intro

    monkeypatch.setattr(KeycloakBackend, "introspect", fake_introspect)
    monkeypatch.setattr(edge_app, "_BACKEND", KeycloakBackend(), raising=False)
    edge = TestClient(edge_app.app)

    # --- agent wallet in keycloak mode, forwarding presentations to the edge -
    monkeypatch.setenv("NLDT_AUTH_WALLET_URL", "http://edge")
    monkeypatch.setenv("NLDT_AGENT_WALLET_BACKEND", "keycloak")
    monkeypatch.setenv("KEYCLOAK_URL", "http://kc.test")
    monkeypatch.setenv("NLDT_AGENT_BELEIDSKOMPAS_SVC_CLIENT_SECRET", "s3cr3t")
    from services.agent_wallet import app as wallet_app

    async def fake_fetch(client_id: str, secret: str) -> str:
        return "kc-token-1"

    monkeypatch.setattr(wallet_app, "_fetch_client_token", fake_fetch)

    class EdgeForwardingClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            return edge.request("POST", "/present", json=json)

    monkeypatch.setattr(wallet_app.httpx, "AsyncClient", EdgeForwardingClient)
    wallet = TestClient(wallet_app.app)

    def mint() -> dict:
        resp = wallet.post("/token", json={"capability": "breda-scan-query"})
        assert resp.status_code == 200, resp.text
        return resp.json()

    body = mint()
    claims = body["claims"]
    assert claims["agentId"] == "beleidskompas-svc"
    assert claims["deployingOrg"] == "Provincie Test"
    assert claims["assurance"] == "attested"
    # effective capabilities = registry ∩ Keycloak roles (drift drops the rest)
    assert claims["capabilities"] == ["breda-scan-query"]

    # --- bridge: the process adapter introspects tokens via the same edge ----
    import services.common.auth as auth

    async def introspect_via_edge(token: str) -> dict:
        return edge.post("/introspect", data={"token": token}).json()

    monkeypatch.setattr(auth, "introspect_wallet", introspect_via_edge)

    from services.process_adapter.app import app as process_app

    runner = TestClient(process_app)

    def execute(token: str):
        return runner.post(
            "/processes/crosstrack-overlay/execution",
            json={"inputs": {"question": "q"}, "backend": "local"},
            headers={"Authorization": f"Bearer {token}"},
        )

    # Keycloak granted only breda-scan-query: the crosstrack gate denies.
    denied = execute(body["token"])
    assert denied.status_code == 403
    assert denied.json()["detail"]["reason"] == "agent_capability_missing"

    # Grant the capability: the administration updates the registry (issuance
    # side) AND Keycloak backs it with a role — both are required (defense in
    # depth against capability drift). Then mint a fresh token and rerun.
    from pathlib import Path

    packaged = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "agent-clients.json").read_text(encoding="utf-8")
    )
    entry = dict(packaged["agents"][0])
    entry["capabilities"] = [*entry["capabilities"], "crosstrack-overlay"]
    registry_v2 = tmp_path / "agents-v2.json"
    registry_v2.write_text(json.dumps({"agents": [entry]}))
    monkeypatch.setenv("NLDT_AGENT_CREDENTIALS_FILE", str(registry_v2))
    intro["realm_access"]["roles"].append("nldt-capability.crosstrack-overlay")
    fresh = mint()
    assert fresh["claims"]["capabilities"] == ["breda-scan-query", "crosstrack-overlay"]
    ok = execute(fresh["token"])
    assert ok.status_code == 200, ok.text
    actor = ok.json()["actor"]
    assert actor["executor"]["agentId"] == "beleidskompas-svc"
    assert actor["executor"]["assurance"] == "attested"
    assert "active" not in actor["executor"]


def test_w6a_disabled_client_fails_closed(tmp_path, monkeypatch):
    """Revocation semantics: an inactive Keycloak token never mints an nLDT token."""
    from services.auth_wallet import app as edge_app
    from services.auth_wallet.backend import KeycloakBackend

    async def fake_introspect(self, token):
        return {"active": False, "azp": "beleidskompas-svc"}

    monkeypatch.setattr(KeycloakBackend, "introspect", fake_introspect)
    monkeypatch.setattr(edge_app, "_BACKEND", KeycloakBackend(), raising=False)
    edge = TestClient(edge_app.app)

    monkeypatch.setenv("NLDT_AUTH_WALLET_URL", "http://edge")
    monkeypatch.setenv("NLDT_AGENT_WALLET_BACKEND", "keycloak")
    monkeypatch.setenv("KEYCLOAK_URL", "http://kc.test")
    monkeypatch.setenv("NLDT_AGENT_BELEIDSKOMPAS_SVC_CLIENT_SECRET", "s3cr3t")
    from services.agent_wallet import app as wallet_app

    async def fake_fetch(client_id: str, secret: str) -> str:
        return "revoked-or-expired-token"

    monkeypatch.setattr(wallet_app, "_fetch_client_token", fake_fetch)

    class EdgeForwardingClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            return edge.request("POST", "/present", json=json)

    monkeypatch.setattr(wallet_app.httpx, "AsyncClient", EdgeForwardingClient)
    resp = TestClient(wallet_app.app).post("/token", json={"capability": "breda-scan-query"})
    assert resp.status_code == 502  # wallet maps the edge's 401 to "auth edge unavailable"
