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
