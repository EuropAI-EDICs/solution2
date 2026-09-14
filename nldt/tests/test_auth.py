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


def test_services_guarded_in_static_mode(monkeypatch):
    from services.a2a.app import app as a2a_app
    from services.catalog_adapter.app import app as catalog_app
    from services.cookbook.app import app as cookbook_app
    from services.process_adapter.app import app as process_app

    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "svc-tok")
    cases = [
        (cookbook_app, "/recipes/spatial-overlay-analysis"),
        (process_app, "/processes"),
        (catalog_app, "/records"),
        (a2a_app, "/agent-card"),
    ]
    for app, path in cases:
        client = TestClient(app)
        assert client.get(path).status_code == 401, f"{app.title}: anonymous must be 401"
        ok = client.get(path, headers={"Authorization": "Bearer svc-tok"})
        assert ok.status_code == 200, f"{app.title}: valid token must pass ({ok.status_code})"


def test_services_open_by_default():
    from services.process_adapter.app import app as process_app

    client = TestClient(process_app)
    assert client.get("/processes").status_code == 200


def test_lowercase_bearer_scheme_accepted(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a")
    resp = guarded_client.get("/ping", headers={"Authorization": "bearer tok-a"})
    assert resp.status_code == 200


def test_non_ascii_token_gets_clean_401(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a")
    # raw bytes: a real ASGI server latin-1-decodes headers, so non-ASCII
    # token bytes do reach require_bearer as a non-ASCII str
    resp = guarded_client.get("/ping", headers={"Authorization": b"bearer t\xfey\xf6k"})
    assert resp.status_code == 401


def test_keycloak_missing_config_is_503_without_network(guarded_client, monkeypatch):
    for var in (
        "KEYCLOAK_URL",
        "KEYCLOAK_CLIENT_ID",
        "KEYCLOAK_CLIENT_SECRET",
        "KEYCLOAK_INTROSPECT_CLIENT_ID",
        "KEYCLOAK_INTROSPECT_CLIENT_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NLDT_AUTH_MODE", "keycloak")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "token introspection unavailable"


def test_introspection_result_is_cached(monkeypatch):
    import asyncio

    import services.common.auth as auth

    calls = {"n": 0}

    async def counting(token: str) -> bool:
        calls["n"] += 1
        return True

    monkeypatch.setattr(auth, "introspect_keycloak", counting)
    monkeypatch.delenv("NLDT_INTROSPECTION_CACHE_TTL", raising=False)
    auth.clear_introspection_cache()
    assert asyncio.run(auth.cached_introspect("t1")) is True
    assert asyncio.run(auth.cached_introspect("t1")) is True
    assert calls["n"] == 1
    auth.clear_introspection_cache()
