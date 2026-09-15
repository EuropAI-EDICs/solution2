"""Phase 6 — Data Space offers: Critic/HITL + pluggable EDC connector."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest


def test_publish_includes_validation_report(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("NLDT_DATASPACE_CONNECTOR", "mock")
    from services.lake.publish import publish_dataset

    ok = publish_dataset(
        lake_uri="lake://nldt-poc-lake/gold/utrecht/run/demo/out.json",
        access_class="open",
        dataset_id="demo-gold",
        license_="CC0-1.0",
    )
    assert ok["status"] == "ok"
    assert ok["validationReport"]["verdict"] == "pass"
    assert ok["validationReport"]["levels"]["V0"]["status"] == "pass"

    rejected = publish_dataset(
        lake_uri="lake://nldt-poc-lake/bronze/rijnland/peilen/x.json",
        access_class="restricted",
        force_hitl_approved=False,
    )
    assert rejected["status"] == "rejected"
    assert rejected["validationReport"]["verdict"] in ("fail", "needs_human")
    assert rejected["validationReport"]["levels"]["V4"]["status"] == "pending"


def test_restricted_publish_with_hitl(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    from services.lake.publish import publish_dataset

    result = publish_dataset(
        lake_uri="lake://nldt-poc-lake/bronze/rijnland/peilen/x.json",
        access_class="restricted",
        force_hitl_approved=True,
        dataset_id="peilen-restricted",
    )
    assert result["status"] == "ok"
    assert result["offer"]["hitlApproved"] is True
    assert result["validationReport"]["levels"]["V4"]["status"] == "pass"


def test_edc_manifest_connector(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("NLDT_EDC_MANIFEST_DIR", str(tmp_path / "edc"))
    monkeypatch.setenv("NLDT_DATASPACE_CONNECTOR", "edc-manifest")
    from services.lake.publish import publish_dataset

    result = publish_dataset(
        lake_uri="lake://nldt-poc-lake/gold/breda/run/t/out.json",
        access_class="open",
        dataset_id="breda-gold",
    )
    assert result["status"] == "ok"
    assert result["connector"]["backend"] == "edc-manifest"
    assert Path(result["connector"]["manifestPath"]).is_file()
    bundle = json.loads(Path(result["connector"]["manifestPath"]).read_text())
    assert bundle["asset"]["@id"] == result["offer"]["uid"]
    assert "contractDefinition" in bundle


def test_http_connector_falls_back_without_url(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("NLDT_EDC_MANIFEST_DIR", str(tmp_path / "edc"))
    monkeypatch.setenv("NLDT_DATASPACE_CONNECTOR", "http")
    monkeypatch.delenv("NLDT_EDC_MANAGEMENT_URL", raising=False)
    from services.lake.publish import publish_dataset

    result = publish_dataset(
        lake_uri="lake://nldt-poc-lake/gold/utrecht/run/t/out.json",
        access_class="open",
        dataset_id="utrecht-gold",
    )
    assert result["status"] == "ok"
    assert result["connector"]["backend"] == "http"
    assert result["connector"]["status"] == "manifest_only_no_url"


def test_lake_publish_offer_recipe_schema():
    from services.common.schema import load_recipe, validate_instance

    recipe = load_recipe("lake-publish-offer")
    validate_instance(recipe, "recipe.schema.json")
    assert recipe["riskLevel"] == "high"


def test_orchestrator_lake_publish_open(monkeypatch, tmp_path):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("NLDT_DATASPACE_CONNECTOR", "mock")
    from agents.orchestrator.graph import build_graph

    app = build_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "natural_language_request": "Publish open gold dataset",
            "recipe_id": "lake-publish-offer",
            "resolved_inputs": {
                "lakeUri": "lake://nldt-poc-lake/gold/utrecht/run/demo/out.json",
                "accessClass": "open",
                "datasetId": "demo-open",
                "license": "CC0-1.0",
            },
            "auto_approve_hitl": False,
            "register_pv": False,
            "export_3d": False,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert not result.get("error")
    assert result["validation_report"]["verdict"] == "pass"
    assert result["execution"]["outputs"]["result"]["status"] == "ok"


def test_orchestrator_lake_publish_restricted_needs_human(monkeypatch, tmp_path):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    from agents.orchestrator.graph import build_graph

    app = build_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "natural_language_request": "Publish restricted peilen",
            "recipe_id": "lake-publish-offer",
            "resolved_inputs": {
                "lakeUri": "lake://nldt-poc-lake/bronze/rijnland/peilen/x.json",
                "accessClass": "restricted",
            },
            "auto_approve_hitl": False,
            "register_pv": False,
            "export_3d": False,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert result["validation_report"]["verdict"] == "needs_human"
    assert result.get("execution") is None
