from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from services.agent_wallet.app import app

    return TestClient(app)


class FakeResp:
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
