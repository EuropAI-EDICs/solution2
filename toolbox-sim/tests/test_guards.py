# toolbox-sim/tests/test_guards.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.guards import add_provenance, require_bearer
from app.jwtutil import STATIC_TOKEN, mint_token

app = FastAPI()
add_provenance(app, "data-platform")


@app.get("/protected")
def protected(payload: dict = __import__("fastapi").Depends(require_bearer)):
    return {"sub": payload["sub"]}


client = TestClient(app)


def test_valid_jwt_accepted():
    r = client.get("/protected", headers={"Authorization": f"Bearer {mint_token('nldt-agent', [])}"})
    assert r.status_code == 200
    assert r.json()["sub"] == "nldt-agent"


def test_static_mesh_token_accepted():
    r = client.get("/protected", headers={"Authorization": f"Bearer {STATIC_TOKEN}"})
    assert r.status_code == 200
    assert r.json()["sub"] == "static-mesh"


def test_missing_or_bad_token_rejected_401():
    assert client.get("/protected").status_code == 401
    r = client.get("/protected", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_provenance_header_on_every_response():
    r = client.get("/protected")  # 401 — header moet er toch staan
    assert r.headers["X-Sim-Provenance"] == "toolbox-sim/data-platform"
