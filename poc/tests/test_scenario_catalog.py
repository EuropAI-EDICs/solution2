"""Scenario run labels for the deep-agent dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deep-agents"))

from scenario_catalog import describe_scenario_run, list_scenario_runs  # noqa: E402

RUNS = ROOT / "poc" / "scenario-runs"


def test_wind_scen_has_dutch_label():
    row = describe_scenario_run(RUNS / "20260831T074521Z-wind-scen")
    assert row["id"] == "20260831T074521Z-wind-scen"
    assert "Wind" in row["label"]
    assert row["variantCount"] >= 1
    assert "windturbine" in row["hint"].lower() or "Wind" in row["track"]


def test_featured_runs_sort_first():
    rows = list_scenario_runs(RUNS)
    assert rows[0]["featured"] is True
    assert any(r["id"].endswith("wind-scen") for r in rows[:3])


def test_uitdaging_groepering_wind():
    row = describe_scenario_run(RUNS / "20260831T074521Z-wind-scen")
    u = row.get("uitdaging")
    assert u is not None and u["id"] == "energietransitie" and u["titel"] == "Energietransitie"
    assert row["trackKey"] == "wind"


def test_uitdaging_volgt_trackkey():
    rows = list_scenario_runs(RUNS)
    for r in rows:
        if r["trackKey"] is None or r["id"].startswith("_fixture"):
            assert r["uitdaging"] is None, r["id"]
        else:
            assert r["uitdaging"] is not None, r["id"]
            assert r["uitdaging"]["titel"], r["id"]


def test_scenarioRuns_uit_uitdagingen_json_zijn_featured():
    rows = list_scenario_runs(RUNS)
    featured = [r for r in rows if r["featured"]]
    assert len(featured) >= 13
