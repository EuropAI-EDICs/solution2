# toolbox-sim/tests/test_identity.py
import base64
import json

from fastapi.testclient import TestClient

from app.identity import create_app

client = TestClient(create_app())


def _payload(token: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))


def test_health():
    assert client.get("/health").json() == {"status": "UP"}


def test_client_credentials_grant():
    r = client.post(
        "/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 300
    payload = _payload(body["access_token"])
    assert payload["sub"] == "nldt-agent"
    assert "/context-data/default/User" in payload["groups"]  # data_platform.list_scopes() leest deze
    assert r.headers["X-Sim-Provenance"].startswith("toolbox-sim/")


def test_unknown_secret_401():
    r = client.post(
        "/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "wrong"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_client"


def test_unknown_realm_404():
    r = client.post(
        "/realms/master/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    assert r.status_code == 404


def test_wrong_grant_type_401():
    r = client.post(
        "/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    assert r.status_code == 401
