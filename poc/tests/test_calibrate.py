"""Kalibratieloop — offline, op fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))

import calibrate as cal  # noqa: E402


def test_drift_verdict():
    assert cal.drift_verdict(859.463, 859.463) == "pass"
    assert cal.drift_verdict(859.463, 859.549) == "pass"   # 0.01% < 0.1%
    assert cal.drift_verdict(859.463, 860.400) == "drift"  # 0.109% > 0.1%


def test_rapport_bevat_uitdagingen_en_amendementsvlag(tmp_path):
    md = cal.render_markdown({
        "datum": "2026-10-13",
        "amendement": "PS-besluit wijziging Omgevingsverordening verwacht 18-11-2026 — herkalibreren na vaststelling",
        "uitdagingen": [{
            "id": "energietransitie", "titel": "Energietransitie",
            "tracks": [{"track": "energietoets", "drift": "pass",
                        "lastChecked": "2026-10-13", "wijzigingen": 0}],
        }],
    })
    assert "Energietransitie" in md
    assert "18-11-2026" in md
    assert "energietoets" in md


def test_layer_freshness_resolves_baselinerun_and_skips_nonlive(tmp_path, monkeypatch):
    """Offline: scenario-run → baselineRunId → layers.json; live-loze zones overgeslagen."""
    sid = "20261013T193408Z-wind-scen"
    base = "20260830T113234Z-wind"
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenario-runs" / sid).mkdir(parents=True)
    (tmp_path / "scenario-runs" / sid / "scenario-report.json").write_text(
        json.dumps({"id": f"SR-{base}-{sid}", "baselineRunId": base}),
        encoding="utf-8")
    manifest = {
        "gebied_windenergie": {"serviceUrl": "https://agrest.example/FeatureServer",
                               "layerId": 0, "lastChecked": "2026-08-30T07:45:26Z"},
        "nationale_laag": {"serviceUrl": "https://national.example/FeatureServer",
                           "geometrySource": "national_source"},
        "aoi": {"role": "aoi", "geometrySource": "none"},  # energietoets-AOI: geen serviceUrl
    }
    (tmp_path / "runs" / base).mkdir(parents=True)
    (tmp_path / "runs" / base / "layers.json").write_text(
        json.dumps(manifest), encoding="utf-8")
    (tmp_path / "scenarios" / "uitdagingen.json").write_text(
        json.dumps({"scenarioRuns": {"wind": sid}}), encoding="utf-8")

    monkeypatch.setattr(cal, "POC", tmp_path)
    monkeypatch.setattr(cal, "arcgis_count", lambda url, lid: 42)

    rows = cal.layer_freshness()
    assert rows == [{"track": "wind", "zoneId": "gebied_windenergie",
                     "count": 42, "cached": "2026-08-30T07:45:26Z"}]
