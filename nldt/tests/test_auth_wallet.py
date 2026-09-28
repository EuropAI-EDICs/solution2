from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from services.auth_wallet.app import app


@pytest.fixture
def client():
    return TestClient(app)


MOCK_HUMAN = {"subject_type": "human", "presentation_id": "mock-user-1"}
MOCK_AGENT = {
    "subject_type": "agent",
    "presentation_id": "beleidskompas-svc",
    "credential_issuer": "Provincie Test",
}


def test_present_human_and_introspect(client):
    resp = client.post("/present", json={"presentation": MOCK_HUMAN})
    assert resp.status_code == 200
    body = resp.json()
    assert body["claims"]["subject_type"] == "human"
    assert body["claims"]["sub"] == "mock-user-1"
    assert body["claims"]["loa"] == "substantial"
    intro = client.post("/introspect", data={"token": body["token"]})
    assert intro.status_code == 200
    assert intro.json()["active"] is True
    assert intro.json()["sub"] == "mock-user-1"


def test_present_agent_and_introspect(client):
    resp = client.post("/present", json={"presentation": MOCK_AGENT})
    claims = resp.json()["claims"]
    assert claims["subject_type"] == "agent"
    assert claims["agentId"] == "beleidskompas-svc"
    assert "breda-scan-query" in claims["capabilities"]
    assert claims["assurance"] == "attested"
    assert client.post("/introspect", data={"token": resp.json()["token"]}).json()["active"] is True


def test_unknown_presentation_rejected(client):
    resp = client.post("/present", json={"presentation": {"subject_type": "human", "presentation_id": "nobody"}})
    assert resp.status_code == 401


def test_introspect_unknown_or_expired_token_inactive(client):
    assert client.post("/introspect", data={"token": "garbage"}).json()["active"] is False
    body = client.post("/present", json={"presentation": MOCK_AGENT}).json()
    from services.auth_wallet import app as aw

    key = hashlib.sha256(body["token"].encode()).hexdigest()  # store is SHA-256-keyed
    aw._TOKENS[key] = (0.0, aw._TOKENS[key][1])  # force expiry: expires_at -> 0.0
    assert client.post("/introspect", data={"token": body["token"]}).json()["active"] is False


# --- W6a: KeycloakBackend -------------------------------------------------------

import asyncio

INTRO_ACTIVE = {
    "active": True,
    "azp": "beleidskompas-svc",
    "realm_access": {"roles": ["nldt-capability.breda-scan-query", "unrelated-role"]},
    "resource_access": {"some-client": {"roles": ["nldt-capability.fetch-features"]}},
}


def _keycloak_backend(monkeypatch, intro=None):
    from services.auth_wallet.backend import KeycloakBackend

    async def fake_introspect(self, token):
        if isinstance(intro, Exception):
            raise intro
        return intro if intro is not None else INTRO_ACTIVE

    monkeypatch.setattr(KeycloakBackend, "introspect", fake_introspect)
    return KeycloakBackend()


AGENT_PRESENTATION = {
    "subject_type": "agent",
    "agentId": "beleidskompas-svc",
    "keycloak_token": "kc-token",
}


def test_keycloak_backend_maps_registry_and_roles(monkeypatch):
    backend = _keycloak_backend(monkeypatch)
    claims = asyncio.run(backend.verify(AGENT_PRESENTATION))
    assert claims["subject_type"] == "agent"
    assert claims["agentId"] == "beleidskompas-svc"
    assert claims["deployingOrg"] == "Provincie Test"
    assert claims["assurance"] == "attested"
    # effective capabilities = registry (6) ∩ Keycloak-granted roles (2)
    assert claims["capabilities"] == ["breda-scan-query", "fetch-features"]


def test_keycloak_backend_rejects_inactive_token(monkeypatch):
    backend = _keycloak_backend(monkeypatch, {"active": False, "azp": "beleidskompas-svc"})
    with pytest.raises(ValueError, match="not active"):
        asyncio.run(backend.verify(AGENT_PRESENTATION))


def test_keycloak_backend_rejects_party_mismatch(monkeypatch):
    backend = _keycloak_backend(monkeypatch, {**INTRO_ACTIVE, "azp": "other-agent"})
    with pytest.raises(ValueError, match="authorized party"):
        asyncio.run(backend.verify(AGENT_PRESENTATION))


def test_keycloak_backend_rejects_role_registry_drift(monkeypatch):
    backend = _keycloak_backend(
        monkeypatch, {"active": True, "azp": "beleidskompas-svc", "realm_access": {"roles": ["other"]}}
    )
    with pytest.raises(ValueError, match="drift"):
        asyncio.run(backend.verify(AGENT_PRESENTATION))


def test_keycloak_backend_rejects_human_presentations(monkeypatch):
    backend = _keycloak_backend(monkeypatch)
    with pytest.raises(ValueError, match="agent presentations only"):
        asyncio.run(backend.verify({"subject_type": "human", "presentation_id": "mock-user-1"}))


def test_keycloak_backend_rejects_unknown_agent(monkeypatch):
    backend = _keycloak_backend(monkeypatch, {"active": True, "azp": "ghost-svc"})
    with pytest.raises(ValueError, match="not in registry"):
        asyncio.run(
            backend.verify({"subject_type": "agent", "agentId": "ghost-svc", "keycloak_token": "t"})
        )


def test_present_keycloak_backend_401_and_503_mapping(client, monkeypatch):
    from services.auth_wallet import app as edge_app
    from services.auth_wallet.backend import KeycloakBackend

    backend = _keycloak_backend(monkeypatch, ValueError("rejected"))
    monkeypatch.setattr(edge_app, "_BACKEND", backend, raising=False)
    resp = client.post("/present", json={"presentation": AGENT_PRESENTATION})
    assert resp.status_code == 401

    backend = _keycloak_backend(monkeypatch, RuntimeError("KEYCLOAK_URL missing"))
    monkeypatch.setattr(edge_app, "_BACKEND", backend, raising=False)
    resp = client.post("/present", json={"presentation": AGENT_PRESENTATION})
    assert resp.status_code == 503


def test_keycloak_verifier_env_selection(monkeypatch):
    from services.auth_wallet.backend import MockBackend, KeycloakBackend, select_backend

    monkeypatch.delenv("NLDT_WALLET_VERIFIER", raising=False)
    assert isinstance(select_backend(), MockBackend)
    monkeypatch.setenv("NLDT_WALLET_VERIFIER", "keycloak")
    assert isinstance(select_backend(), KeycloakBackend)
    monkeypatch.setenv("NLDT_WALLET_VERIFIER", "bogus")
    with pytest.raises(RuntimeError, match="NLDT_WALLET_VERIFIER"):
        select_backend()
