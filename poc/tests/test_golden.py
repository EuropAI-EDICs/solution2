# poc/tests/test_golden.py
from __future__ import annotations

import json
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import golden  # noqa: E402

POLY = {
    "type": "Polygon",
    "coordinates": [[[120000.0, 450000.0], [150000.0, 450000.0], [150000.0, 480000.0], [120000.0, 480000.0], [120000.0, 450000.0]]],
}
POLY_SHIFTED = {
    "type": "Polygon",
    "coordinates": [[[125000.0, 450000.0], [155000.0, 450000.0], [155000.0, 480000.0], [125000.0, 480000.0], [125000.0, 450000.0]]],
}


def _mini_run(path: Path, verdict: str = "pass", geom=POLY) -> Path:
    path.mkdir(parents=True)
    (path / "run_summary.json").write_text(json.dumps({
        "runId": "x", "requestId": "r", "generatedAt": "nu", "durationS": 1.0,
        "verdict": verdict,
        "verdicts": {"norm-card-set": "pass", "zone-result-set": "pass"},
        "perRule": [{"ruleId": "WE-01", "verdict": "pass"}],
    }), encoding="utf-8")
    (path / "zones.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": geom}],
    }), encoding="utf-8")
    (path / "zones.gml").write_text(
        '<gml:FeatureCollection gml:id="aFeatureCollection">'
        '<gml:featureMember><imgeo:Zones gml:id="zones.0"><prop>a</prop></imgeo:Zones></gml:featureMember>'
        '<gml:featureMember><imgeo:Zones gml:id="zones.1"><prop>b</prop></imgeo:Zones></gml:featureMember>'
        "</gml:FeatureCollection>", encoding="utf-8")
    return path


def test_load_verdicts_extracts_exact_fields(tmp_path: Path) -> None:
    d = _mini_run(tmp_path / "run")
    summary = json.loads((d / "run_summary.json").read_text(encoding="utf-8"))
    assert golden.load_verdicts(summary) == {
        "verdict": "pass",
        "verdicts": {"norm-card-set": "pass", "zone-result-set": "pass"},
        "perRule": [("WE-01", "pass")],
    }


def test_zones_iou_identical_is_one(tmp_path: Path) -> None:
    a = tmp_path / "a.geojson"; b = tmp_path / "b.geojson"
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": POLY}]}
    a.write_text(json.dumps(fc), encoding="utf-8"); b.write_text(json.dumps(fc), encoding="utf-8")
    assert golden.zones_iou(a, b)["iou"] == 1.0
    assert golden.zones_iou(a, b)["pass"] is True


def test_zones_iou_shifted_below_tolerance(tmp_path: Path) -> None:
    a = tmp_path / "a.geojson"; b = tmp_path / "b.geojson"
    a.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": POLY}]}), encoding="utf-8")
    b.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": POLY_SHIFTED}]}), encoding="utf-8")
    out = golden.zones_iou(a, b)
    assert out["iou"] < 0.9999 and out["pass"] is False


def test_gml_zone_ids(tmp_path: Path) -> None:
    d = _mini_run(tmp_path / "run")
    assert golden.gml_zone_ids(d / "zones.gml") == ["zones.0", "zones.1"]


def test_diff_runs_equal_passes(tmp_path: Path) -> None:
    new = _mini_run(tmp_path / "new"); gold = _mini_run(tmp_path / "gold")
    out = golden.diff_runs(new, gold)
    assert out["pass"] is True and out["verdictsEqual"] is True and out["gmlEqual"] is True


def test_diff_runs_flags_verdict_drift(tmp_path: Path) -> None:
    new = _mini_run(tmp_path / "new", verdict="fail"); gold = _mini_run(tmp_path / "gold")
    out = golden.diff_runs(new, gold)
    assert out["pass"] is False and out["verdictsEqual"] is False
    assert "verdicts" in out["details"]


def test_diff_runs_flags_gml_drift(tmp_path: Path) -> None:
    new = _mini_run(tmp_path / "new"); gold = _mini_run(tmp_path / "gold")
    text = (new / "zones.gml").read_text(encoding="utf-8").replace('gml:id="zones.1"', 'gml:id="zones.2"')
    (new / "zones.gml").write_text(text, encoding="utf-8")
    out = golden.diff_runs(new, gold)
    assert out["pass"] is False and out["gmlEqual"] is False
    assert out["details"]["gmlOnlyInNew"] == ["zones.2"]
