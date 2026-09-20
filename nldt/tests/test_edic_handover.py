from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.edic_live_readiness import assess_live_path
from services.a2a.app import agent_card, app as a2a_app
from services.common.schema import (
    edic_entry_for_recipe,
    list_recipe_ids,
    load_edic_asset_map,
    load_recipe,
    validate_instance,
)
from services.cookbook.app import app as cookbook_app
from services.edic_compliance import HIGH_RISK_RECIPES, declaration_for_recipe
from services.marketplace_publish import marketplace_asset_payload, publish_recipe

NLDT = Path(__file__).resolve().parents[1]


def test_edic_asset_map_schema_and_recipe_coverage():
    payload = load_edic_asset_map()
    recipe_ids = set(list_recipe_ids())
    mapped = {
        a["id"].split(":", 1)[1]
        for a in payload["assets"]
        if a["kind"] == "recipe"
    }
    assert recipe_ids == mapped
    assert "edic-asset-map" not in recipe_ids
    for rid in recipe_ids:
        recipe = load_recipe(rid)
        entry = edic_entry_for_recipe(rid)
        assert entry is not None
        assert entry["riskLevel"] == recipe["riskLevel"]
        assert (NLDT.parent / entry["path"]).exists(), entry["path"]


def test_cookbook_skips_asset_map():
    client = TestClient(cookbook_app)
    listing = client.get("/recipes").json()["recipes"]
    ids = {r["id"] for r in listing}
    assert "edic-asset-map" not in ids
    assert "spatial-overlay-analysis" in ids
    assert client.get("/recipes/edic-asset-map").status_code == 404


def test_high_risk_declarations_exist_and_validate():
    decl_dir = NLDT / "edic" / "declarations"
    for rid in HIGH_RISK_RECIPES:
        path = decl_dir / f"{rid}.json"
        assert path.is_file(), path
        with path.open(encoding="utf-8") as f:
            decl = json.load(f)
        validate_instance(decl, "compliance-declaration.schema.json")
        generated = declaration_for_recipe(rid)
        assert decl["id"] == generated["id"]
        assert decl["hitl"]["required"] is True


def test_marketplace_payload_includes_trust_and_edic():
    recipe = load_recipe("spatial-overlay-analysis")
    report = {
        "id": "VR-overlay-1",
        "artifactId": "spatial-overlay-analysis",
        "artifactType": "recipe",
        "levels": {
            "V0": {"status": "pass"},
            "V1": {"status": "pass"},
            "V2": {"status": "pass"},
            "V3": {"status": "not_applicable"},
            "V4": {"status": "not_applicable"},
        },
        "verdict": "pass",
        "evaluatorRun": "nldt-critic#test",
        "evaluatedAt": "2026-09-20T12:00:00Z",
    }
    prov = {"activity": "nldt:ProcessExecution/spatial-overlay-analysis"}
    payload = marketplace_asset_payload(
        recipe, validation_report=report, provenance=prov
    )
    assert payload["validationReport"]["verdict"] == "pass"
    assert payload["provenance"]["activity"].startswith("nldt:")
    assert payload["edic"]["destination"] == "ldt-citiverse"
    result = publish_recipe(recipe, validation_report=report, provenance=prov)
    assert result["mock"] is True
    assert result["payload"]["edic"]["destination"] == "ldt-citiverse"


def test_a2a_agent_card_edic_identity(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_URL", "https://im-int.ldttoolbox.app")
    card = agent_card()
    assert card["provider"]["edic"] == "ldt-citiverse"
    assert card["authentication"]["identityManagement"] == "eu-ldt-toolbox-im"
    assert card["authentication"]["productionIdentity"] is True
    assert "localhost" not in card["authentication"]["identityProvider"]
    client = TestClient(a2a_app)
    resp = client.get("/agent-card")
    assert resp.status_code == 200
    assert resp.json()["name"] == "nldt-orchestrator"


def test_live_readiness_mock_by_default(monkeypatch):
    for key in (
        "UCS_BASE_URL",
        "MARKETPLACE_AGENT_URL",
        "NLDT_PV_BASE_URL",
        "KEYCLOAK_URL",
        "NLDT_DATA_PLATFORM_URL",
        "NLDT_NGSI_LD_URL",
        "NLDT_NLAIF_ROUTE",
        "NLDT_LLM_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MARKETPLACE_MOCK", "true")
    monkeypatch.setenv("NLDT_PV_MOCK", "true")
    monkeypatch.setenv("NLDT_DATA_PLATFORM_MOCK", "true")
    report = assess_live_path()
    assert report["referenceRecipe"] == "spatial-overlay-analysis"
    assert report["status"] == "mock"
    assert report["checks"]["llm_compute"]["optional"] is True


def test_live_readiness_live_when_toolbox_env_set(monkeypatch):
    monkeypatch.setenv("UCS_BASE_URL", "https://ucs-int.ldttoolbox.app")
    monkeypatch.setenv("MARKETPLACE_AGENT_URL", "https://marketplace-int.ldttoolbox.app")
    monkeypatch.setenv("MARKETPLACE_MOCK", "false")
    monkeypatch.setenv("NLDT_PV_BASE_URL", "https://pv-int.ldttoolbox.app")
    monkeypatch.setenv("NLDT_PV_MOCK", "false")
    monkeypatch.setenv("KEYCLOAK_URL", "https://im-int.ldttoolbox.app")
    report = assess_live_path()
    assert report["status"] == "live"
    assert report["checks"]["data_platform"]["optional"] is True


def test_every_asset_has_owner_acceptance_fallback():
    payload = load_edic_asset_map()
    for asset in payload["assets"]:
        assert asset["owner"]
        assert asset["acceptance"]
        assert asset["fallback"]
        assert asset["edic"] in {
            "ldt-citiverse",
            "impacts",
            "digital-commons",
            "alt-edic",
            "none",
        }
