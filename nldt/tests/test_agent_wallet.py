from __future__ import annotations

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from services.agent_wallet.app import app

    return TestClient(app)


class FakeResp:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"token": "tok-1", "expiresIn": 300, "claims": {}}


def test_token_capability_covered(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_WALLET_URL", "http://auth-edge.test")
    from services.agent_wallet import app as wallet_app

    captured = {}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return FakeResp()

    monkeypatch.setattr(wallet_app.httpx, "AsyncClient", FakeClient)
    resp = _client().post("/token", json={"capability": "breda-scan-query"})
    assert resp.status_code == 200
    assert resp.json() == {"token": "tok-1", "expiresIn": 300, "claims": {}}
    assert captured["url"] == "http://auth-edge.test/present"
    presentation = captured["json"]["presentation"]
    assert presentation["subject_type"] == "agent"
    assert presentation["presentation_id"] == "beleidskompas-svc"
    assert presentation["credential_issuer"] == "Provincie Test"


def test_token_capability_not_covered(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_WALLET_URL", "http://auth-edge.test")
    from services.agent_wallet import app as wallet_app

    class FakeClient:
        def __init__(self, timeout=None):
            raise AssertionError("outbound HTTP must not be called when capability not covered")

    monkeypatch.setattr(wallet_app.httpx, "AsyncClient", FakeClient)
    resp = _client().post("/token", json={"capability": "does-not-exist"})
    assert resp.status_code == 403
    assert "does-not-exist" in resp.json()["detail"]


def test_token_missing_wallet_url(monkeypatch):
    monkeypatch.delenv("NLDT_AUTH_WALLET_URL", raising=False)
    resp = _client().post("/token", json={"capability": "breda-scan-query"})
    assert resp.status_code == 503


def test_credentials_redacted():
    resp = _client().get("/credentials")
    assert resp.status_code == 200
    creds = resp.json()
    assert len(creds) == 1
    assert set(creds[0].keys()) == {
        "agentId",
        "deployingOrg",
        "assurance",
        "capabilities",
    }
    assert creds[0]["agentId"] == "beleidskompas-svc"
    assert creds[0]["assurance"] == "attested"
    assert "breda-scan-query" in creds[0]["capabilities"]


# --- W6a: keycloak backend mode -------------------------------------------------


def test_token_keycloak_mode_presentation(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_WALLET_URL", "http://auth-edge.test")
    monkeypatch.setenv("NLDT_AGENT_WALLET_BACKEND", "keycloak")
    monkeypatch.setenv("KEYCLOAK_URL", "http://kc.test")
    monkeypatch.setenv("NLDT_AGENT_BELEIDSKOMPAS_SVC_CLIENT_SECRET", "s3cr3t")
    from services.agent_wallet import app as wallet_app

    captured = {}

    async def fake_fetch(client_id: str, secret: str) -> str:
        captured["client_id"] = client_id
        captured["secret"] = secret
        return "kc-token-1"

    monkeypatch.setattr(wallet_app, "_fetch_client_token", fake_fetch)

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return FakeResp()

    monkeypatch.setattr(wallet_app.httpx, "AsyncClient", FakeClient)
    resp = _client().post("/token", json={"capability": "breda-scan-query"})
    assert resp.status_code == 200
    assert captured["client_id"] == "beleidskompas-svc"
    assert captured["secret"] == "s3cr3t"
    presentation = captured["json"]["presentation"]
    assert presentation["subject_type"] == "agent"
    assert presentation["agentId"] == "beleidskompas-svc"
    assert presentation["keycloak_token"] == "kc-token-1"
    assert "presentation_id" not in presentation  # mock shape must not leak


def test_token_keycloak_mode_missing_secret_fails_closed(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_WALLET_URL", "http://auth-edge.test")
    monkeypatch.setenv("NLDT_AGENT_WALLET_BACKEND", "keycloak")
    monkeypatch.setenv("KEYCLOAK_URL", "http://kc.test")
    monkeypatch.delenv("NLDT_AGENT_BELEIDSKOMPAS_SVC_CLIENT_SECRET", raising=False)
    from services.agent_wallet import app as wallet_app

    class Boom:
        def __init__(self, timeout=None):
            raise AssertionError("no outbound HTTP when the secret is missing")

    monkeypatch.setattr(wallet_app.httpx, "AsyncClient", Boom)
    resp = _client().post("/token", json={"capability": "breda-scan-query"})
    assert resp.status_code == 503
    assert "CLIENT_SECRET" in resp.json()["detail"]


def test_token_keycloak_mode_missing_keycloak_url_fails_closed(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_WALLET_URL", "http://auth-edge.test")
    monkeypatch.setenv("NLDT_AGENT_WALLET_BACKEND", "keycloak")
    monkeypatch.setenv("NLDT_AGENT_BELEIDSKOMPAS_SVC_CLIENT_SECRET", "s3cr3t")
    monkeypatch.delenv("KEYCLOAK_URL", raising=False)
    resp = _client().post("/token", json={"capability": "breda-scan-query"})
    assert resp.status_code == 503
