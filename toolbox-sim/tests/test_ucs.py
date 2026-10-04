# toolbox-sim/tests/test_ucs.py
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.jwtutil import mint_token
from app.ucs import create_app

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
PROCESSES = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ucs-processes.json").read_text())
client = TestClient(create_app(PROCESSES))


def test_trigger_known_process_replays_canonical_outputs():
    r = client.post("/api/v1/experiments/trigger-process", json={"processId": "utrecht-opportunity-map", "inputs": {}}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["provenance"] == f"sim-replay://canonical/{body['outputs']['runId']}"
    assert body["outputs"]["verdict"] == "pass"
    assert "headline" in body["outputs"]


def test_unknown_process_404_for_local_fallback():
    r = client.post("/api/v1/experiments/trigger-process", json={"processId": "nope", "inputs": {}}, headers=AUTH)
    assert r.status_code == 404
    assert r.json()["error"] == "process-not-found"


def test_requires_bearer():
    r = client.post("/api/v1/experiments/trigger-process", json={"processId": "utrecht-opportunity-map", "inputs": {}})
    assert r.status_code == 401
