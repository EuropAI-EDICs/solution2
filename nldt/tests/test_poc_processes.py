from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.common.schema import load_recipe, validate_instance
from services.process_adapter.handlers import (
    PROCESS_DEFINITIONS,
    describe_process,
    execute_local,
)
from services.process_adapter.poc_handlers import POC_PROCESS_DEFINITIONS, WORKSPACE
from services.catalog_adapter.seed import find_records
from services.recipe_runner import run_recipe
from services.mcp_servers.client import ProcessClient
from services.process_adapter import jobs as job_store


POC_IDS = set(POC_PROCESS_DEFINITIONS)


def test_poc_processes_registered():
    expected = {
        "breda-scan-query",
        "scenario-author-propose",
        "scenario-sweep",
        "opportunity-map-run",
        "crosstrack-overlay",
        "breda-scan-run",
        "breda-gebiedsafweging",
        "rijnland-peil-conflict",
        "rijnland-peil-whatif",
        "bp2op-transform",
        "minigim-gebiedscheck-run",
    }
    assert expected <= set(PROCESS_DEFINITIONS)
    for pid in expected:
        assert describe_process(pid)["id"] == pid


def test_poc_recipes_schema_valid():
    for rid in (
        "breda-scan-qa",
        "utrecht-scenario-sweep",
        "utrecht-opportunity-map",
        "utrecht-scenario-author",
        "rijnland-peil-conflict",
        "rijnland-peil-whatif",
        "breda-five-value-scan",
        "breda-gebiedsafweging",
        "multi-track-crosstrack",
        "eindhoven-bp2op",
        "minigim-gebiedscheck",
    ):
        recipe = load_recipe(rid)
        validate_instance(recipe, "recipe.schema.json")
        assert recipe["id"] == rid


def test_catalog_finds_poc_recipes():
    hits = find_records(q="scenario")
    ids = {r["id"] for r in hits}
    assert "recipe-utrecht-scenario-sweep" in ids or any(
        "scenario" in str(r.get("properties", {})).lower() for r in hits
    )
    poc_hits = find_records(q="poc-breda")
    assert any(r.get("type") == "recipe" for r in poc_hits) or any(
        "breda" in r.get("id", "") for r in poc_hits
    )


def test_opportunity_map_replay():
    out = execute_local(
        "opportunity-map-run",
        {"mode": "replay", "useCase": "wind"},
    )
    summary = out["summary"]
    assert summary["mode"] == "replay"
    assert "runDir" in summary
    assert Path(summary["runDir"]).is_dir()


def test_breda_scan_run_replay():
    out = execute_local("breda-scan-run", {"mode": "replay"})
    assert out["summary"]["mode"] == "replay"
    assert out["summary"]["hasValueScan"] is True


def test_breda_gebiedsafweging_offline_fixtures():
    out = execute_local("breda-gebiedsafweging", {"mode": "offline-fixtures"})
    summary = out["summary"]
    assert summary["mode"] == "offline-fixtures"
    assert summary["exitCode"] == 0
    assert summary["verdict"] == "needs_human"
    assert summary.get("nAccepted") == 2
    assert Path(summary["outDir"]).is_dir()
    assert (Path(summary["outDir"]) / "gebiedsafweging.html").is_file()


def test_minigim_gebiedscheck_replay():
    runs_root = WORKSPACE / "poc-minigim" / "runs"
    if not any(runs_root.glob("*-minigim-gebiedscheck/run_summary.json")):
        pytest.skip("geen minigim-gebiedscheck run aanwezig (draai poc-minigim/run.py eerst)")
    out = execute_local("minigim-gebiedscheck-run", {"mode": "replay"})
    summary = out["summary"]
    assert summary["mode"] == "replay"
    assert summary["items"] == 74
    assert summary["verdict"] in {"pass", "fail"}


def test_rijnland_peil_conflict_replay():
    run_dir = WORKSPACE / "poc-rijnland" / "runs" / "20260914Tcanonical-rijnland-peil"
    if not (run_dir / "peil-conflict-report.json").is_file():
        pytest.skip("canonical Rijnland peil run missing")
    out = execute_local(
        "rijnland-peil-conflict",
        {"mode": "replay", "runDir": str(run_dir)},
    )
    summary = out["summary"]
    assert summary["mode"] == "replay"
    assert summary["verdict"]
    assert summary["runDir"]


def test_rijnland_peil_conflict_execute_no_h3(tmp_path):
    out_dir = tmp_path / "rijnland-peil-exec"
    out = execute_local(
        "rijnland-peil-conflict",
        {
            "mode": "execute",
            "outDir": str(out_dir),
            "noH3": True,
            "noKrw": True,
            "noWq": True,
        },
    )
    assert out["summary"]["exitCode"] == 0
    assert (out_dir / "peil-conflict-report.json").is_file()
    assert out["summary"]["verdict"]


def test_breda_scan_query_offline():
    run_dir = WORKSPACE / "poc-breda" / "runs" / "20260913T152919Z-breda-scan"
    if not (run_dir / "value-scan.json").is_file():
        pytest.skip("canonical Breda scan run missing")
    out = execute_local(
        "breda-scan-query",
        {
            "runDir": str(run_dir),
            "question": "waarom scoort Belcrum laag op ruimtelijke waarde?",
            "asker": "auto",
        },
    )
    result = out["result"]
    assert result["status"] in ("answered", "abstained", "grounding_failed")
    if result["status"] == "answered":
        assert result["answer"]
        assert result["query"]


def test_scenario_author_propose_auto():
    baseline = WORKSPACE / "poc" / "runs" / "20260830T113234Z-wind"
    if not (baseline / "formalrules.json").is_file():
        pytest.skip("wind baseline run missing")
    out = execute_local(
        "scenario-author-propose",
        {"baselineRunDir": str(baseline), "author": "auto", "maxScenarios": 5},
    )
    proposals = out["proposals"]
    assert proposals["acceptedCount"] >= 1
    assert isinstance(proposals["accepted"], list)
    assert isinstance(proposals["rejected"], list)


def test_scenario_author_propose_hybrid_without_llm_falls_back():
    baseline = WORKSPACE / "poc" / "runs" / "20260830T113234Z-wind"
    if not (baseline / "formalrules.json").is_file():
        pytest.skip("wind baseline run missing")
    import os
    os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
    out = execute_local(
        "scenario-author-propose",
        {"baselineRunDir": str(baseline), "author": "hybrid", "maxScenarios": 5},
    )
    proposals = out["proposals"]
    assert proposals["author"] == "hybrid"
    assert proposals["acceptedCount"] >= 1
    kinds = {r.get("kind") for r in proposals["rejected"]}
    assert "llm-unavailable" in kinds


def test_scenario_author_propose_llm_requires_endpoint():
    baseline = WORKSPACE / "poc" / "runs" / "20260830T113234Z-wind"
    if not (baseline / "formalrules.json").is_file():
        pytest.skip("wind baseline run missing")
    import os
    os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
    with pytest.raises(Exception):
        execute_local(
            "scenario-author-propose",
            {"baselineRunDir": str(baseline), "author": "llm", "maxScenarios": 2},
        )


def test_crosstrack_replay():
    xroot = WORKSPACE / "poc" / "crosstrack-runs"
    if not xroot.is_dir() or not list(xroot.glob("*-xtrack")):
        pytest.skip("no crosstrack runs")
    out = execute_local("crosstrack-overlay", {"mode": "replay"})
    assert out["summary"]["mode"] == "replay"
    assert out["summary"].get("runDir")


def test_breda_scan_qa_recipe_runner():
    run_dir = WORKSPACE / "poc-breda" / "runs" / "20260913T152919Z-breda-scan"
    if not (run_dir / "value-scan.json").is_file():
        pytest.skip("canonical Breda scan run missing")

    class LocalClient(ProcessClient):
        def execute(self, process_id, inputs, backend="local"):
            return job_store.create_job(process_id, inputs, backend=backend)

    execution = run_recipe(
        "breda-scan-qa",
        {
            "runDir": str(run_dir),
            "question": "welke buurten scoren het hoogst op democratische waarde?",
        },
        process_client=LocalClient(),
    )
    assert execution["recipeId"] == "breda-scan-qa"
    assert "result" in execution["outputs"]
