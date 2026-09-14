from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.catalog_adapter.app import app as catalog_app
from services.common.schema import validate_instance


@pytest.fixture
def client():
    return TestClient(catalog_app)


def test_application_record_valid_against_schema(client):
    rec = client.get("/records/application-beleidskompas").json()
    assert rec["type"] == "application"
    validate_instance(rec["properties"], "application.schema.json")


def test_catalog_lists_application_type(client):
    resp = client.get("/records", params={"type": "application"})
    ids = [f["id"] for f in resp.json()["features"]]
    assert ids == ["application-beleidskompas"]


def test_application_discoverable_by_query(client):
    resp = client.get("/records", params={"q": "beleidskompas"})
    ids = [f["id"] for f in resp.json()["features"]]
    assert "application-beleidskompas" in ids
    assert "recipe-beleidskompas-omgevingsanalyse" in ids


def test_application_links(client):
    rec = client.get("/records/application-beleidskompas").json()
    rels = {l["rel"]: l["href"] for l in rec["links"]}
    assert rels["launch"].startswith("https://")
    assert rels["docs"].startswith("https://")


def test_application_consumes_real_recipes(client):
    rec = client.get("/records/application-beleidskompas").json()
    for rid in rec["properties"]["consumesRecipes"]:
        assert client.get(f"/records/recipe-{rid}").status_code == 200


def test_seed_rejects_invalid_application(monkeypatch):
    from jsonschema import ValidationError

    from services.catalog_adapter import seed

    aid, title, descriptor, tags = seed.APPLICATIONS[0]
    bad = (aid, title, {**descriptor, "trustLevel": "banana"}, tags)
    monkeypatch.setattr(seed, "APPLICATIONS", [bad])
    with pytest.raises(ValidationError):
        seed.seed_records()
