from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.common.geo import area_statistics, intersect_feature_collections
from services.common.schema import load_recipe, validate_instance
from services.process_adapter.handlers import execute_local
from services.process_adapter.router import route_execute
from services.recipe_runner import run_recipe


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_recipe_schema_valid():
    recipe = load_recipe("spatial-overlay-analysis")
    assert recipe["id"] == "spatial-overlay-analysis"
    assert len(recipe["steps"]) == 4


def test_spatial_intersection_local():
    with (EXAMPLES / "layer-a.geojson").open() as f:
        a = json.load(f)
    with (EXAMPLES / "layer-b.geojson").open() as f:
        b = json.load(f)
    result = intersect_feature_collections(a, b)
    assert result["type"] == "FeatureCollection"
    stats = area_statistics(result)
    assert stats["totalAreaM2"] > 0


def test_process_execute_local():
    layer_a = f"file://{EXAMPLES / 'layer-a.geojson'}"
    layer_b = f"file://{EXAMPLES / 'layer-b.geojson'}"
    out_a = execute_local("fetch-features", {"source": layer_a})
    out_b = execute_local("fetch-features", {"source": layer_b})
    inter = execute_local(
        "spatial-intersection",
        {"layerA": out_a["features"], "layerB": out_b["features"]},
    )
    stats = execute_local("compute-area-statistics", {"features": inter["result"]})
    assert stats["statistics"]["totalAreaM2"] > 0


def test_route_execute_prov():
    job_id, outputs, prov = route_execute(
        "compute-area-statistics",
        {"features": {"type": "FeatureCollection", "features": []}},
    )
    assert job_id
    assert "statistics" in outputs
    assert prov["generated"].startswith("nldt:JobResult/")


def test_agent_plan_schema():
    plan = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "requestSummary": "test",
        "recipeId": "spatial-overlay-analysis",
        "resolvedInputs": {},
        "stepOrder": ["fetch-layer-a"],
        "effortBudget": {"maxSteps": 1},
        "plannedAt": "2026-08-31T12:00:00Z",
    }
    validate_instance(plan, "agent-plan.schema.json")


def test_recipe_runner_inprocess():
    layer_a = f"file://{EXAMPLES / 'layer-a.geojson'}"
    layer_b = f"file://{EXAMPLES / 'layer-b.geojson'}"
    with (EXAMPLES / "aoi.geojson").open() as f:
        aoi = json.load(f)

    from services.mcp_servers.client import ProcessClient
    from services.process_adapter import jobs as job_store

    class LocalClient(ProcessClient):
        def execute(self, process_id, inputs, backend="local"):
            job = job_store.create_job(process_id, inputs, backend=backend)
            return job

    result = run_recipe(
        "spatial-overlay-analysis",
        {"aoi": aoi, "layerAUri": layer_a, "layerBUri": layer_b},
        process_client=LocalClient(),
    )
    assert "intersection" in result["outputs"]
    assert "statistics" in result["outputs"]
    assert len(result["steps"]) == 4
