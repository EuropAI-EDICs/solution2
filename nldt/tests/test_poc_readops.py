from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.process_adapter.poc_readops import (
    crosscheck_formal_rule,
    get_provenance,
    inspect_geo_layer,
)


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "20261006T120133Z-biomassa"
    d.mkdir()
    (d / "prov.json").write_text(json.dumps({
        "flavour": "poc", "runId": "20261006T120133Z-biomassa",
        "entity": [
            {"id": "e1", "type": "NormCard", "generatedBy": "NormAnalyst", "sha256": "abc"},
            {"id": "e2", "type": "ZoneResult", "generatedBy": "ZoneEngine", "extra": "drop"},
        ],
    }), encoding="utf-8")
    (d / "layers.json").write_text(json.dumps({
        "gebied_energie_biomassa_landelijk": {
            "zoneId": "gebied_energie_biomassa_landelijk",
            "aliasSourceId": "agrest-ov-gebied-energie-biomassa-landelijk",
            "title": "Gebied energie uit biomassa landelijk gebied",
        },
    }), encoding="utf-8")
    (d / "zones.json").write_text(json.dumps([
        {"zoneId": "gebied_energie_biomassa_landelijk", "areaKm2": 1560.054},
        {"zoneId": "aoi", "areaKm2": 1560.054},
    ]), encoding="utf-8")
    return d


def test_get_provenance_maps_entities(run_dir: Path) -> None:
    out = get_provenance("20261006T120133Z-biomassa", runs_dir=run_dir.parent)
    assert out["runId"] == "20261006T120133Z-biomassa"
    assert out["entities"][0] == {"id": "e1", "type": "NormCard", "generatedBy": "NormAnalyst", "sha256": "abc"}
    assert "extra" not in out["entities"][1]


def test_get_provenance_missing_run_is_explicit_error(run_dir: Path) -> None:
    out = get_provenance("bestaatniet", runs_dir=run_dir.parent)
    assert "error" in out and "bestaatniet" in out["error"]


def test_inspect_geo_layer_returns_meta_and_matching_zones(run_dir: Path) -> None:
    out = inspect_geo_layer("20261006T120133Z-biomassa", "gebied_energie_biomassa_landelijk", runs_dir=run_dir.parent)
    assert out["meta"]["aliasSourceId"] == "agrest-ov-gebied-energie-biomassa-landelijk"
    assert out["zoneCount"] == 1
    assert out["zones"][0]["areaKm2"] == 1560.054


def test_inspect_geo_layer_unknown_layer_lists_available(run_dir: Path) -> None:
    out = inspect_geo_layer("20261006T120133Z-biomassa", "onbekend", runs_dir=run_dir.parent)
    assert "error" in out
    assert "gebied_energie_biomassa_landelijk" in out["available"]


def test_crosscheck_formal_rule_scans_report(run_dir: Path) -> None:
    (run_dir / "scenario-report.json").write_text(json.dumps({
        "scenarios": [
            {"scenarioId": "s1", "mutationsApplied": [{"ruleId": "FR-BM-01", "action": "flip"}], "mutationsSkipped": []},
            {"scenarioId": "s2", "mutationsApplied": [], "mutationsSkipped": [{"ruleId": "FR-BM-01", "reason": "floor"}]},
        ],
    }), encoding="utf-8")
    out = crosscheck_formal_rule("20261006T120133Z-biomassa", "FR-bm-01", runs_dir=run_dir.parent)
    assert out["executedByEngine"] is True
    assert out["appliedMutations"][0]["scenarioId"] == "s1"
    assert out["skippedMutations"][0]["reason"] == "floor"


def test_crosscheck_without_report_is_explicit(run_dir: Path) -> None:
    out = crosscheck_formal_rule("20261006T120133Z-biomassa", "FR-BM-01", runs_dir=run_dir.parent)
    assert "error" in out and "scenario-report" in out["error"]
