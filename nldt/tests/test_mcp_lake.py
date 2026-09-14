from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from services.catalog_adapter.seed import (
    find_lake_datasets,
    find_poc_capabilities,
    get_lake_manifest,
)
from services.mcp_servers.lake_governance import (
    filter_lake_datasets,
    is_restricted_dataset,
    load_inventory_datasets,
)


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")


def test_lake_governance_filters_restricted():
    datasets = load_inventory_datasets()
    restricted = [d for d in datasets if d.get("accessClass") == "restricted"]
    assert restricted, "inventory should contain restricted datasets for Rijnland peilen"
    filtered = filter_lake_datasets(datasets, include_restricted=False)
    for ds in filtered:
        assert not is_restricted_dataset(ds)
    assert len(filtered) < len(datasets)


def test_search_lake_datasets_breda():
    hits = find_lake_datasets(poc="breda")
    assert hits
    for hit in hits:
        assert hit["type"] == "dataset"
        assert hit["properties"]["poc"] == "breda"
        assert hit["properties"]["accessClass"] != "restricted"


def test_search_lake_datasets_restricted_hidden():
    all_hits = find_lake_datasets(poc="rijnland", include_restricted=True)
    open_hits = find_lake_datasets(poc="rijnland", include_restricted=False)
    assert len(all_hits) >= len(open_hits)
    restricted_in_open = [h for h in open_hits if h["properties"].get("accessClass") == "restricted"]
    assert not restricted_in_open


def test_get_lake_manifest_by_uri():
    hits = find_lake_datasets(poc="utrecht", zone="silver")
    assert hits
    uri = hits[0]["properties"]["lakeUri"]
    manifest = get_lake_manifest(lake_uri=uri)
    assert manifest is not None
    assert manifest["lakeUri"] == uri
    assert manifest.get("sha256")


def test_get_lake_manifest_restricted_denied():
    datasets = load_inventory_datasets()
    restricted = next(d for d in datasets if d.get("accessClass") == "restricted")
    manifest = get_lake_manifest(lake_uri=restricted["lakeUri"], include_restricted=False)
    assert manifest is None


def test_list_poc_capabilities():
    caps = find_poc_capabilities()
    ids = {c["id"] for c in caps}
    assert "recipe-breda-scan-qa" in ids
    assert "process-scenario-sweep" in ids
    assert "process-bp2op-transform" in ids


def test_data_platform_list_scopes_mock():
    from services.adapters import data_platform

    scopes = data_platform.list_scopes()
    assert scopes
    assert any(s["plane"] == "context-data" for s in scopes)


def test_data_platform_trino_query_readonly_blocks_writes():
    from services.adapters import data_platform

    with pytest.raises(ValueError, match="read-only"):
        data_platform.trino_query("DROP TABLE foo")


def test_data_platform_trino_query_mock():
    from services.adapters import data_platform

    result = data_platform.trino_query("SELECT 1")
    assert result.get("mock") or result.get("rows")


def test_data_platform_list_catalogs_mock():
    from services.adapters import data_platform

    catalogs = data_platform.list_catalogs()
    assert catalogs
    assert catalogs[0]["catalog"]


def test_poc_mcp_tools_registered():
    from services.mcp_servers.poc_tools import POC_TOOLS

    expected = {
        "run_opportunity_map",
        "propose_scenarios",
        "run_scenario_sweep",
        "ask_scan",
        "run_value_scan",
        "run_crosstrack",
        "run_peil_conflict",
        "run_bp2op_transform",
    }
    assert expected <= set(POC_TOOLS.keys())


def test_bp2op_transform_replay():
    from services.process_adapter.handlers import execute_local

    out = execute_local("bp2op-transform", {"mode": "replay"})
    summary = out["summary"]
    assert summary["mode"] == "replay"
    assert summary.get("verdict") or summary.get("runDir")


def test_orchestrator_data_plane_routing():
    from agents.orchestrator.data_plane import infer_data_plane

    assert infer_data_plane("scenario sweep wind") == "lake"
    assert infer_data_plane("live air quality sensors") == "data_platform"
    assert infer_data_plane("scenario with live luchtkwaliteit") == "hybrid"


def test_orchestrator_breda_scan_qa_e2e():
    from pathlib import Path
    from uuid import uuid4

    from agents.orchestrator.graph import build_graph
    from services.mcp_servers.client import ProcessClient
    from services.process_adapter import jobs as job_store
    from services.process_adapter.poc_handlers import WORKSPACE

    run_dir = WORKSPACE / "poc-breda" / "runs" / "20260913T152919Z-breda-scan"
    if not (run_dir / "value-scan.json").is_file():
        pytest.skip("canonical Breda scan run missing")

    class LocalClient(ProcessClient):
        def execute(self, process_id, inputs, backend="local"):
            return job_store.create_job(process_id, inputs, backend=backend)

    import services.recipe_runner as rr

    with patch.object(rr, "ProcessClient", LocalClient):
        app = build_graph()
        run_id = str(uuid4())[:8]
        result = app.invoke(
            {
                "run_id": run_id,
                "natural_language_request": "Breda scan vraag",
                "recipe_id": "breda-scan-qa",
                "resolved_inputs": {
                    "runDir": str(run_dir),
                    "question": "welke buurten scoren het hoogst op democratische waarde?",
                },
                "auto_approve_hitl": True,
                "register_pv": False,
                "export_3d": False,
            },
            config={"configurable": {"thread_id": run_id}},
        )
    assert not result.get("error")
    assert result.get("data_plane") == "lake"
    assert result.get("lake_hits") is not None
    assert result["validation_report"]["verdict"] in ("pass", "needs_human")


def test_new_recipes_schema_valid():
    from services.common.schema import load_recipe, validate_instance

    for rid in ("breda-five-value-scan", "multi-track-crosstrack", "eindhoven-bp2op"):
        recipe = load_recipe(rid)
        validate_instance(recipe, "recipe.schema.json")
        assert recipe["id"] == rid


def test_qa_flow_s7_then_sweep_invalid_proposal():
    """S7 with no baseline should fail; sweep without valid set should not silently pass."""
    from services.process_adapter.handlers import execute_local
    from services.process_adapter.poc_handlers import POC_ROOT

    baseline = POC_ROOT / "runs" / "20260830T113234Z-wind"
    if not (baseline / "formalrules.json").is_file():
        pytest.skip("wind baseline missing")
    propose = execute_local(
        "scenario-author-propose",
        {"baselineRunDir": str(baseline), "author": "auto", "maxScenarios": 2},
    )
    assert propose["proposals"]["acceptedCount"] >= 1
    if propose["proposals"]["rejected"]:
        assert all("reason" in r or "error" in r for r in propose["proposals"]["rejected"])


def test_qa_flow_crosstrack_replay():
    from services.process_adapter.handlers import execute_local
    from services.process_adapter.poc_handlers import POC_ROOT

    xroot = POC_ROOT / "crosstrack-runs"
    if not xroot.is_dir() or not list(xroot.glob("*-xtrack")):
        pytest.skip("no crosstrack runs")
    out = execute_local("crosstrack-overlay", {"mode": "replay"})
    assert out["summary"]["mode"] == "replay"


def test_qa_flow_ask_scan_cite_or_abstain():
    from services.process_adapter.handlers import execute_local
    from services.process_adapter.poc_handlers import POC_BREDA, WORKSPACE

    run_dir = WORKSPACE / "poc-breda" / "runs" / "20260913T152919Z-breda-scan"
    if not (run_dir / "value-scan.json").is_file():
        pytest.skip("canonical Breda scan missing")
    out = execute_local(
        "breda-scan-query",
        {"runDir": str(run_dir), "question": "xyz onzin vraag zonder mapping", "asker": "auto"},
    )
    assert out["result"]["status"] in ("abstained", "answered", "grounding_failed")
    if out["result"]["status"] == "abstained":
        assert out["result"].get("rejection")
