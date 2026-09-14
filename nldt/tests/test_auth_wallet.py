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
