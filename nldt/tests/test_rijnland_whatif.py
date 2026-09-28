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
        build_multi_scenario_map_payload,
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
    payload = build_multi_scenario_map_payload(archive, scenario, demo_scenarios=[])
    dest = tmp_path / "whatif-map.html"
    build_whatif_map_html(payload, dest)
    html = dest.read_text(encoding="utf-8")
    assert "window.__DATA__" in html
    assert "leaflet@1.9.4" in html
    assert "service.pdok.nl/brt/achtergrondkaart" in html
    assert "basemaps.cartocdn.com" not in html
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
        include_demo_pack=False,
    )
    assert (out_dir / "whatif-map.html").is_file()
    assert result["summary"]["mapHtml"] == str(out_dir / "whatif-map.html")


def test_load_demo_pack_has_three_scenarios():
    from services.rijnland_whatif import DEFAULT_DEMO_PACK, load_demo_pack

    assert DEFAULT_DEMO_PACK.is_file()
    pack = load_demo_pack()
    assert len(pack) == 3
    ids = {s["id"] for s in pack}
    assert ids == {"boezem-plus5cm", "boezem-minus5cm", "polders-plus10cm"}
    for s in pack:
        assert "delta_m" in s and "layer" in s and "title" in s


def test_multi_scenario_payload_by_scenario_and_dedupe():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        build_multi_scenario_map_payload,
        load_archive,
        load_demo_pack,
    )

    baseline = load_archive(PEILEN)
    active = {
        "id": "boezem-plus5cm",
        "title": "CLI active",
        "delta_m": 0.05,
        "layer": "boezem",
        "limit": 20,
    }
    demos = [{**d, "limit": 20} for d in load_demo_pack()]
    payload = build_multi_scenario_map_payload(baseline, active, demos)
    assert payload["defaultMode"] == "after"
    assert payload["defaultScenarioId"] == "boezem-plus5cm"
    assert payload["modes"] == ["after", "before", "delta"]
    ids = [s["id"] for s in payload["scenarios"]]
    assert ids.count("boezem-plus5cm") == 1
    assert len(payload["scenarios"]) == 3
    lake = [s for s in payload["scenarios"] if s["id"] == "boezem-plus5cm"][0]
    assert lake["lakeApplied"] is True
    assert any(
        not s["lakeApplied"] for s in payload["scenarios"] if s["id"] != "boezem-plus5cm"
    )
    feats = payload["geo"]["features"]
    assert feats
    touched_plus = [
        f
        for f in feats
        if (f["properties"].get("byScenario") or {})
        .get("boezem-plus5cm", {})
        .get("touched")
    ]
    assert len(touched_plus) == 20
    sample = touched_plus[0]["properties"]["byScenario"]["boezem-plus5cm"]
    assert sample["after"] == pytest.approx(sample["before"] + 0.05)


def test_multi_payload_without_demos_is_single():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        build_multi_scenario_map_payload,
        load_archive,
    )

    baseline = load_archive(PEILEN)
    active = {
        "id": "only",
        "title": "only",
        "delta_m": 0.02,
        "layer": "boezem",
        "limit": 5,
    }
    payload = build_multi_scenario_map_payload(baseline, active, demo_scenarios=[])
    assert len(payload["scenarios"]) == 1
    assert payload["scenarios"][0]["lakeApplied"] is True


def test_run_whatif_multi_map_lake_only_active(tmp_path, monkeypatch):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from pathlib import Path

    from services import rijnland_whatif as rw

    calls = {"cdc": 0}

    def fake_write_cdc(changes, **kwargs):
        calls["cdc"] += 1
        p = tmp_path / "fake.parquet"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(rw, "write_cdc_batch", fake_write_cdc)
    monkeypatch.setattr(rw, "_load_apply_batches", lambda: (lambda batches, dest: {"ok": True}))

    active = {
        "id": "cli-active-unique",
        "title": "CLI unique",
        "delta_m": 0.05,
        "layer": "boezem",
        "limit": 5,
    }
    out = rw.run_whatif(
        active,
        archive_path=PEILEN,
        out_dir=tmp_path / "run",
        apply_to_lake=True,
        attach_conflict_replay=False,
        include_demo_pack=True,
    )
    html = Path(out["summary"]["mapHtml"]).read_text(encoding="utf-8")
    assert "cli-active-unique" in html
    assert "boezem-minus5cm" in html
    assert "polders-plus10cm" in html
    assert out["summary"]["scenariosOnMap"]
    assert calls["cdc"] == 1
    assert len(out["summary"]["scenariosOnMap"]) >= 3


def test_run_whatif_no_demo_pack_single(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from pathlib import Path

    from services.rijnland_whatif import run_whatif

    out = run_whatif(
        {"id": "solo", "title": "solo", "delta_m": 0.05, "layer": "boezem", "limit": 3},
        archive_path=PEILEN,
        out_dir=tmp_path / "solo",
        apply_to_lake=False,
        attach_conflict_replay=False,
        include_demo_pack=False,
    )
    html = Path(out["summary"]["mapHtml"]).read_text(encoding="utf-8")
    assert "solo" in html
    assert "boezem-minus5cm" not in html
