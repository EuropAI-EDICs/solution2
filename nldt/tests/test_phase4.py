from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.a2a.app import app as a2a_app
from services.context3d.app import app as context3d_app
from services.context3d.export_import import export_from_execution, import_context
from services.marketplace_publish import publish_recipe

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def context_client():
    return TestClient(context3d_app)


@pytest.fixture
def a2a_client():
    return TestClient(a2a_app)


def _sample_execution() -> dict:
    layer_a = f"file://{EXAMPLES / 'layer-a.geojson'}"
    layer_b = f"file://{EXAMPLES / 'layer-b.geojson'}"
    from services.process_adapter import jobs as job_store
    from services.process_adapter.handlers import execute_local

    a = execute_local("fetch-features", {"source": layer_a})["features"]
    b = execute_local("fetch-features", {"source": layer_b})["features"]
    inter = execute_local("spatial-intersection", {"layerA": a, "layerB": b})["result"]
    stats = execute_local("compute-area-statistics", {"features": inter})["statistics"]
    return {
        "recipeId": "spatial-overlay-analysis",
        "outputs": {"intersection": inter, "statistics": stats},
        "steps": [{"stepId": "intersect", "prov": {"activity": "test"}}],
    }


def test_export_web3d_context_schema():
    doc = export_from_execution(_sample_execution(), run_id="test01")
    assert doc["type"] == "Web3DContext"
    assert len(doc["layers"]) >= 1
    assert doc["bbox"][2] > doc["bbox"][0]


def test_import_web3d_context():
    doc = export_from_execution(_sample_execution(), run_id="test02")
    parsed = import_context(doc)
    assert parsed["layers"][0]["type"] == "geojson"
    assert parsed["inlineGeoJson"] is not None


def test_context3d_http_export(context_client):
    resp = context_client.post("/export", json={"execution": _sample_execution(), "runId": "http01"})
    assert resp.status_code == 200
    doc = resp.json()["document"]
    assert doc["type"] == "Web3DContext"


def test_context3d_http_import_roundtrip(context_client):
    doc = export_from_execution(_sample_execution(), run_id="round01")
    resp = context_client.post("/import", json={"document": doc})
    assert resp.status_code == 200
    assert resp.json()["id"] == doc["id"]


def test_marketplace_publish_mock():
    from services.common.schema import load_recipe

    recipe = load_recipe("spatial-overlay-analysis")
    result = publish_recipe(recipe)
    assert result["assetId"]
    assert result["mock"] is True


def test_a2a_agent_card(a2a_client):
    resp = a2a_client.get("/agent-card")
    assert resp.status_code == 200
    card = resp.json()
    assert card["name"] == "nldt-orchestrator"
    assert any(s["id"] == "execute-recipe" for s in card["skills"])


def test_a2a_execute_recipe_task(a2a_client, monkeypatch):
    from services.mcp_servers.client import ProcessClient
    from services.process_adapter import jobs as job_store

    class LocalProcessClient(ProcessClient):
        def execute(self, process_id, inputs, backend="local"):
            return job_store.create_job(process_id, inputs, backend=backend)

    monkeypatch.setenv("NLDT_OFFLINE", "1")
    monkeypatch.setattr("services.recipe_runner.ProcessClient", LocalProcessClient)
    layer_a = f"file://{EXAMPLES / 'layer-a.geojson'}"
    layer_b = f"file://{EXAMPLES / 'layer-b.geojson'}"
    with (EXAMPLES / "aoi.geojson").open() as f:
        aoi = json.load(f)
    resp = a2a_client.post(
        "/tasks",
        json={
            "skillId": "execute-recipe",
            "message": "spatial overlay",
            "recipeId": "spatial-overlay-analysis",
            "inputs": {"aoi": aoi, "layerAUri": layer_a, "layerBUri": layer_b},
            "autoApproveHitl": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "statistics" in data["result"]["execution"]["outputs"]


def test_telemetry_noop_without_otel():
    from services.common.telemetry import init_telemetry, span

    assert init_telemetry("test") is False
    with span("test.span"):
        pass
