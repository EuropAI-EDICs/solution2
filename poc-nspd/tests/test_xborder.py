"""Tests voor de grensvergelijkende merge + naast-elkaar-rapport (spec §4.4)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.xborder import load_run, merge_xborder, write_xborder_report  # noqa: E402


def _fc(land: str) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"ruleId": f"FR-{land}-01", "jurisdictie": land},
            "geometry": {"type": "Polygon", "coordinates": [[[3.5, 51.1], [3.6, 51.1], [3.6, 51.2], [3.5, 51.2], [3.5, 51.1]]]},
        }],
    }


def test_merge_behoudt_land_per_feature():
    merged = merge_xborder(
        {"land": "nl", "zones": _fc("nl"), "decisionRows": [{"id": "FR-NL-01", "land": "nl"}]},
        {"land": "be", "zones": _fc("be"), "decisionRows": [{"id": "FR-BE-01", "land": "be"}]},
        track="wind",
    )
    lands = {f["properties"]["land"] for f in merged["zones"]["features"]}
    assert lands == {"nl", "be"}
    assert len(merged["decisionRows"]) == 2
    assert all("land" in r for r in merged["decisionRows"])


def test_report_en_geojson_worden_geschreven(tmp_path):
    merged = merge_xborder(
        {"land": "nl", "zones": _fc("nl"), "decisionRows": []},
        {"land": "be", "zones": _fc("be"), "decisionRows": []},
        track="wind",
    )
    pad = write_xborder_report(tmp_path, merged, track="wind")
    assert pad.name == "report-xborder.html"
    html = pad.read_text(encoding="utf-8")
    assert "NL" in html and "BE" in html
    geo = __import__("json").loads((tmp_path / "zones-wind-nspd.geojson").read_text(encoding="utf-8"))
    assert geo["type"] == "FeatureCollection"


def test_load_run_mapt_zone_records_naar_features(tmp_path):
    """load_run zet de task-9-runvorm (lijst zone-records + decision-table) om naar merge-invoer."""
    (tmp_path / "zones.json").write_text(
        """[{"id": "ZR-1", "jurisdictie": "nl", "operation": "union", "geometryValid": true,
            "geometry": {"format": "GeoJSON", "crs": "EPSG:4326",
                         "payload": {"type": "Polygon", "coordinates": [[[3.5, 51.1], [3.6, 51.1], [3.6, 51.2], [3.5, 51.2], [3.5, 51.1]]]}}}]""",
        encoding="utf-8",
    )
    (tmp_path / "decision-table.json").write_text(
        """{"columns": ["ruleId", "norm"], "rows": [{"ruleId": "FR-WIND-01", "norm": "art. 18.17"}]}""",
        encoding="utf-8",
    )
    run = load_run(tmp_path)
    assert run["land"] == "nl"
    assert [f["geometry"]["type"] for f in run["zones"]["features"]] == ["Polygon"]
    assert run["zones"]["features"][0]["properties"]["id"] == "ZR-1"
    assert run["decisionRows"][0]["ruleId"] == "FR-WIND-01"


def test_load_run_land_fallback_uit_dirnaam(tmp_path):
    (tmp_path / "zones.json").write_text("[]", encoding="utf-8")
    (tmp_path / "decision-table.json").write_text('{"rows": []}', encoding="utf-8")
    be_dir = tmp_path / "20261014T185454Z-wind-be"
    be_dir.mkdir()
    for naam in ("zones.json", "decision-table.json"):
        (be_dir / naam).write_text((tmp_path / naam).read_text(encoding="utf-8"), encoding="utf-8")
    assert load_run(be_dir)["land"] == "be"


_RUNS = ROOT / "runs"


def _vind_run(achtervoegsel: str) -> Path | None:
    if not _RUNS.is_dir():
        return None
    kandidaten = sorted(_RUNS.glob(f"*-{achtervoegsel}"))
    return kandidaten[-1] if kandidaten else None


_NL_RUN = _vind_run("wind-nl")
_BE_RUN = _vind_run("wind-be")


@pytest.mark.skipif(_NL_RUN is None or _BE_RUN is None, reason="geen echte wind-runs onder poc-nspd/runs/")
def test_integratie_echte_runs(tmp_path):
    """load_run + merge_xborder + write_xborder_report op echte task-9 smoke-runs."""
    nl = load_run(_NL_RUN)
    be = load_run(_BE_RUN)
    assert nl["land"] == "nl" and be["land"] == "be"
    merged = merge_xborder(nl, be, track="wind")
    lands = {f["properties"]["land"] for f in merged["zones"]["features"]}
    assert lands == {"nl", "be"}
    assert merged["zones"]["features"], "verwacht zones uit beide runs"
    assert all(f["geometry"] is not None for f in merged["zones"]["features"])
    assert merged["decisionRows"], "verwacht decision-table-rows uit beide runs"
    pad = write_xborder_report(tmp_path, merged, track="wind")
    html = pad.read_text(encoding="utf-8")
    assert "Nederland" in html and "Vlaanderen" in html
    geo = __import__("json").loads((tmp_path / "zones-wind-nspd.geojson").read_text(encoding="utf-8"))
    feature_landen = {f["properties"]["land"] for f in geo["features"]}
    assert feature_landen == {"nl", "be"}
