from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from services.common.auth import require_bearer
from services.common.schema import validate_instance

HUMAN_CLAIMS = {
    "subject_type": "human",
    "sub": "mock-user-1",
    "loa": "substantial",
    "org": "Provincie Test",
    "roles": ["policy-officer"],
    "exp": 9999999999,
}

AGENT_CLAIMS = {
    "subject_type": "agent",
    "agentId": "beleidskompas-svc",
    "deployingOrg": "Provincie Test",
    "capabilities": ["beleidskompas-omgevingsanalyse", "breda-scan-query"],
    "assurance": "attested",
    "exp": 9999999999,
}


@pytest.fixture
def claims_client():
    app = FastAPI(dependencies=[Depends(require_bearer)])

    @app.get("/who")
    async def who(request: Request):
        return {"claims": getattr(request.state, "wallet_claims", None)}

    return TestClient(app)


def test_claims_schema_accepts_both_subject_types():
    validate_instance(HUMAN_CLAIMS, "wallet-claims.schema.json")
    validate_instance(AGENT_CLAIMS, "wallet-claims.schema.json")


def test_claims_schema_rejects_wrong_shape():
    from jsonschema import ValidationError

    bad = {**HUMAN_CLAIMS, "subject_type": "agent"}  # agent without agent claims
    with pytest.raises(ValidationError):
        validate_instance(bad, "wallet-claims.schema.json")


def test_wallet_mode_requires_url(claims_client, monkeypatch):
    monkeypatch.delenv("NLDT_WALLET_INTROSPECT_URL", raising=False)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    resp = claims_client.get("/who", headers={"Authorization": "Bearer t"})
    assert resp.status_code == 503


def test_wallet_mode_accepts_active_token(claims_client, monkeypatch):
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        return {"active": True, **AGENT_CLAIMS}

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    resp = claims_client.get("/who", headers={"Authorization": "Bearer t"})
    assert resp.status_code == 200
    assert resp.json()["claims"]["agentId"] == "beleidskompas-svc"


def test_wallet_mode_rejects_inactive_token(claims_client, monkeypatch):
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        return {"active": False}

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    assert claims_client.get("/who", headers={"Authorization": "Bearer t"}).status_code == 401


def test_wallet_mode_rejects_invalid_claims(monkeypatch):
    """Active but malformed introspection payload fails loud (500), nothing stored."""
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        return {"active": True, "subject_type": "agent"}  # agent without agent claims

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    app = FastAPI(dependencies=[Depends(require_bearer)])

    @app.get("/who")
    async def who(request: Request):
        return {"claims": getattr(request.state, "wallet_claims", None)}

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/who", headers={"Authorization": "Bearer t"})
    assert resp.status_code == 500  # claims validator raised before request.state assignment
    assert resp.text == "Internal Server Error"
