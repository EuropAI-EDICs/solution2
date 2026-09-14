from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.common.auth import require_bearer


@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    monkeypatch.delenv("NLDT_AUTH_MODE", raising=False)
    monkeypatch.delenv("NLDT_STATIC_TOKENS", raising=False)


@pytest.fixture
def guarded_client():
    app = FastAPI(dependencies=[Depends(require_bearer)])

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_mode_off_allows_anonymous(guarded_client):
    resp = guarded_client.get("/ping")
    assert resp.status_code == 200


def test_static_mode_requires_token(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a")
    assert guarded_client.get("/ping").status_code == 401


def test_static_mode_rejects_wrong_token(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_static_mode_accepts_known_token(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a,tok-b")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer tok-b"})
    assert resp.status_code == 200


def test_static_mode_fails_closed_without_tokens(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer anything"})
    assert resp.status_code == 401


def test_keycloak_mode_accepts_active_token(guarded_client, monkeypatch):
    import services.common.auth as auth

    async def fake_introspect(token: str) -> bool:
        return token == "kc-good"

    monkeypatch.setattr(auth, "introspect_keycloak", fake_introspect)
    monkeypatch.setenv("NLDT_AUTH_MODE", "keycloak")
    ok = guarded_client.get("/ping", headers={"Authorization": "Bearer kc-good"})
    bad = guarded_client.get("/ping", headers={"Authorization": "Bearer kc-bad"})
    assert ok.status_code == 200
    assert bad.status_code == 401


def test_keycloak_introspection_failure_is_503(guarded_client, monkeypatch):
    import services.common.auth as auth

    async def exploding(token: str) -> bool:
        raise RuntimeError("keycloak down")

    monkeypatch.setattr(auth, "introspect_keycloak", exploding)
    monkeypatch.setenv("NLDT_AUTH_MODE", "keycloak")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503


def test_unknown_mode_fails_closed(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "banana")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 500
