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


def test_stations_to_geojson_touched_points():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        apply_scenario_to_archive,
        load_archive,
        stations_to_geojson,
    )

    archive = load_archive(PEILEN)
    scenario = {"id": "t-map", "delta_m": 0.05, "layer": "boezem", "limit": 5}
    out, changes = apply_scenario_to_archive(archive, scenario)
    fc = stations_to_geojson(out, changes)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 5
    touched = [f for f in fc["features"] if f["properties"]["touched"]]
    assert len(touched) == 5
    for f in touched:
        lon, lat = f["geometry"]["coordinates"]
        assert isinstance(lon, (int, float)) and isinstance(lat, (int, float))
        assert f["properties"]["delta_m"] == 0.05
        assert f["properties"]["after"] == pytest.approx(
            f["properties"]["before"] + 0.05
        )


def test_build_whatif_map_html_has_data_and_modes(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        apply_scenario_to_archive,
        build_whatif_map_html,
        load_archive,
    )

    archive = load_archive(PEILEN)
    scenario = {
        "id": "boezem-plus5cm",
        "title": "Boezempeilen +5 cm",
        "description": "test",
        "delta_m": 0.05,
        "layer": "boezem",
        "limit": 5,
    }
    out, changes = apply_scenario_to_archive(archive, scenario)
    dest = tmp_path / "whatif-map.html"
    build_whatif_map_html(out, changes, scenario, dest)
    html = dest.read_text(encoding="utf-8")
    assert "window.__DATA__" in html
    assert "leaflet@1.9.4" in html
    assert '"defaultMode": "after"' in html or '"defaultMode":"after"' in html
    assert "before" in html and "after" in html and "delta" in html
    assert "Boezempeilen +5 cm" in html


def test_run_whatif_writes_map_html(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import run_whatif

    out_dir = tmp_path / "whatif-run-map"
    result = run_whatif(
        {
            "id": "map-test",
            "title": "map test",
            "delta_m": 0.05,
            "layer": "boezem",
            "limit": 5,
        },
        archive_path=PEILEN,
        out_dir=out_dir,
        apply_to_lake=False,
        attach_conflict_replay=False,
    )
    assert (out_dir / "whatif-map.html").is_file()
    assert result["summary"]["mapHtml"] == str(out_dir / "whatif-map.html")
