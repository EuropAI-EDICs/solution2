from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.catalog_adapter.app import app as catalog_app
from services.cookbook.app import app as cookbook_app
from services.process_adapter.app import app as process_app

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def catalog_client():
    return TestClient(catalog_app)


@pytest.fixture
def cookbook_client():
    return TestClient(cookbook_app)


@pytest.fixture
def process_client():
    return TestClient(process_app)


def test_catalog_landing(catalog_client):
    resp = catalog_client.get("/")
    assert resp.status_code == 200
    assert "Records" in resp.json()["title"]


def test_catalog_lists_recipe(catalog_client):
    resp = catalog_client.get("/records", params={"type": "recipe"})
    features = resp.json()["features"]
    assert any(f["id"] == "recipe-spatial-overlay-analysis" for f in features)


def test_catalog_recipe_link_points_to_cookbook(catalog_client):
    rec = catalog_client.get("/records/recipe-spatial-overlay-analysis").json()
    recipe_links = [l for l in rec["links"] if l["rel"] == "recipe"]
    assert len(recipe_links) == 1
    assert "spatial-overlay-analysis" in recipe_links[0]["href"]


def test_cookbook_serves_recipe(cookbook_client):
    resp = cookbook_client.get("/recipes/spatial-overlay-analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "spatial-overlay-analysis"
    assert len(data["steps"]) == 4


def test_process_list_and_execute(process_client):
    listing = process_client.get("/processes")
    assert listing.status_code == 200
    ids = {p["id"] for p in listing.json()["processes"]}
    assert "spatial-intersection" in ids

    layer_a = f"file://{EXAMPLES / 'layer-a.geojson'}"
    job = process_client.post(
        "/processes/fetch-features/execution",
        json={"inputs": {"source": layer_a}, "backend": "local"},
    )
    assert job.status_code == 200
    assert job.json()["status"] == "successful"
    assert "prov" in job.json()


def test_appstore_cookbook_cook_e2e(catalog_client, cookbook_client, process_client):
    """Full AppStore → Cookbook → Cook path over HTTP."""
    rec = catalog_client.get("/records/recipe-spatial-overlay-analysis").json()
    recipe_href = next(l["href"] for l in rec["links"] if l["rel"] == "recipe")
    recipe_id = recipe_href.rstrip("/").split("/")[-1]

    recipe = cookbook_client.get(f"/recipes/{recipe_id}").json()
    with (EXAMPLES / "aoi.geojson").open() as f:
        aoi = json.load(f)
    layer_a = f"file://{EXAMPLES / 'layer-a.geojson'}"
    layer_b = f"file://{EXAMPLES / 'layer-b.geojson'}"

    context: dict = {"recipe": {"inputs": {"aoi": aoi, "layerAUri": layer_a, "layerBUri": layer_b}}, "steps": {}}

    from services.common.templates import resolve_templates

    for step in recipe["steps"]:
        resolved = resolve_templates(step["inputs"], context)
        job = process_client.post(
            f"/processes/{step['processId']}/execution",
            json={"inputs": resolved, "backend": step.get("backend", "local")},
        ).json()
        mapped = {}
        for out_key, var_name in step.get("outputs", {}).items():
            val = job["outputs"].get(out_key, job["outputs"])
            mapped[out_key] = val
            mapped[var_name] = val
        context["steps"][step["id"]] = {"outputs": mapped}

    stats = context["steps"]["stats"]["outputs"]["statistics"]
    assert stats["totalAreaM2"] > 0
    assert "intersection" in context["steps"]["intersect"]["outputs"]
