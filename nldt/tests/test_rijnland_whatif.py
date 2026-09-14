from __future__ import annotations

import json
from pathlib import Path

import pytest

NLDT = Path(__file__).resolve().parents[1]
WORKSPACE = NLDT.parent
PEILEN = WORKSPACE / "poc-rijnland" / "data" / "peilen" / "peilen.json"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    yield


def test_apply_scenario_boezem_delta():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import apply_scenario_to_archive, load_archive

    archive = load_archive(PEILEN)
    scenario = {"id": "t1", "delta_m": 0.05, "layer": "boezem", "limit": 10}
    out, changes = apply_scenario_to_archive(archive, scenario)
    assert len(changes) == 10
    assert all(c["delta_m"] == 0.05 for c in changes)
    assert all(c["layer"] == "boezem" for c in changes)
    # baseline unchanged
    sid = changes[0]["peilgebied_id"]
    assert archive["stations"][sid]["latest"]["value"] == changes[0]["before_m"]
    assert out["stations"][sid]["latest"]["value"] == changes[0]["waterstand_m"]


def test_run_whatif_offline(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import run_whatif

    out_dir = tmp_path / "whatif-run"
    result = run_whatif(
        {
            "id": "boezem-plus5cm-test",
            "title": "test",
            "delta_m": 0.05,
            "layer": "boezem",
            "limit": 8,
        },
        archive_path=PEILEN,
        out_dir=out_dir,
        apply_to_lake=True,
        attach_conflict_replay=False,
    )
    summary = result["summary"]
    assert summary["stationsTouched"] == 8
    assert (out_dir / "whatif-report.json").is_file()
    assert (out_dir / "whatif-diff.html").is_file()
    assert (out_dir / "peilen-whatif.json").is_file()
    assert summary.get("cdcBatch")
    assert summary.get("silverUri")


def test_process_rijnland_peil_whatif(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.process_adapter.handlers import execute_local

    out = execute_local(
        "rijnland-peil-whatif",
        {
            "delta_m": 0.05,
            "layer": "boezem",
            "limit": 5,
            "scenarioId": "proc-test",
            "outDir": str(tmp_path / "proc-whatif"),
            "attachConflictReplay": False,
        },
    )
    assert out["summary"]["stationsTouched"] == 5
    assert out["summary"]["mode"] == "whatif"


def test_recipe_schema():
    from services.common.schema import load_recipe, validate_instance

    recipe = load_recipe("rijnland-peil-whatif")
    validate_instance(recipe, "recipe.schema.json")


def test_poc_tool_registered():
    from services.mcp_servers.poc_tools import POC_TOOLS

    assert POC_TOOLS["run_peil_whatif"]["process_id"] == "rijnland-peil-whatif"
