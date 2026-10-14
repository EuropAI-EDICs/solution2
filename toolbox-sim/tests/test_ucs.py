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


def test_experiment_authoring_en_model_run():
    from app.algorithms import load_ground

    recipes = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "recipes.json").read_text())
    ground = load_ground(Path(__file__).resolve().parents[1] / "fixtures")
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    client = TestClient(create_app(PROCESSES, recipes=recipes, ground=ground))

    recipe_id = sorted(recipes)[0]
    r = client.post("/api/v1/experiments", headers=auth, json={"name": "scan-1", "recipeId": recipe_id})
    assert r.status_code == 201
    exp = r.json()
    assert exp["id"].startswith("exp-") and exp["recipeId"] == recipe_id and exp["runs"] == []

    run = client.post("/api/v1/experiments/trigger-process", headers=auth,
                      json={"processId": "urban-mobility", "inputs": {}, "experimentId": exp["id"]})
    assert run.status_code == 200 and run.json()["synthetic"] is True
    listed = client.get(f"/api/v1/experiments/{exp['id']}", headers=auth).json()
    assert len(listed["runs"]) == 1 and listed["runs"][0]["processId"] == "urban-mobility"

    unknown = client.post("/api/v1/experiments", headers=auth, json={"name": "x", "recipeId": "ontbreekt"})
    assert unknown.status_code == 404 and unknown.json()["error"] == "recipe-not-found"
