from __future__ import annotations

from fastapi.testclient import TestClient

from services.catalog_adapter.app import app as catalog_app
from services.cookbook.app import app as cookbook_app


def test_cookbook_serves_beleidskompas_recipe():
    client = TestClient(cookbook_app)
    resp = client.get("/recipes/beleidskompas-omgevingsanalyse")
    assert resp.status_code == 200
    data = resp.json()
    assert "beleidskompas" in data["tags"]
    assert data["steps"][0]["processId"] == "fetch-features"
    assert data["riskLevel"] == "low"


def test_catalog_search_finds_beleidskompas_assets():
    client = TestClient(catalog_app)
    resp = client.get("/records", params={"q": "beleidskompas"})
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()["features"]]
    assert "recipe-beleidskompas-omgevingsanalyse" in ids
    assert "recipe-breda-scan-qa" in ids


def test_scan_qa_recipe_tagged_for_beleidskompas():
    client = TestClient(catalog_app)
    rec = client.get("/records/recipe-breda-scan-qa").json()
    tags = rec["properties"]["tags"]
    assert "beleidskompas" in tags
    assert "policy-step:substantiation" in tags
    assert "legal" in tags
