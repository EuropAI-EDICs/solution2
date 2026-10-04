"""Human-readable labels for poc/scenario-runs (Utrecht / Crosstrack demos)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_OBJECT_NL: dict[str, str] = {
    "wind_turbine": "windturbines",
    "solar_field": "zonneparken",
    "solar_farm": "zonneparken",
    "forest": "bos",
    "forest_planting": "bosplanting",
}

_FEATURED_SUFFIXES = (
    "20260831T074521Z-wind-scen",
    "20260831T074604Z-zon-scen",
    "20260831T074610Z-bos-scen",
)


def _track_nl(run_id: str) -> str:
    rid = run_id.lower()
    if "wind" in rid:
        return "Wind"
    if "zon" in rid or "solar" in rid:
        return "Zon"
    if "bos" in rid or "forest" in rid:
        return "Bos"
    return "Meerdere tracks"


def _kind_nl(run_id: str) -> str:
    if run_id.startswith("_fixture"):
        return "Test-fixture (ontwikkeling)"
    if "authorcmp" in run_id:
        return "Authoring vs engine (vergelijking)"
    if "scen" in run_id:
        return "Beleidsvarianten (world scene)"
    return "Scenario-run"


def describe_scenario_run(run_dir: Path) -> dict[str, Any]:
    run_id = run_dir.name
    report_path = run_dir / "scenario-report.json"
    report: dict[str, Any] = {}
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))

    track = _track_nl(run_id)
    kind = _kind_nl(run_id)
    obj = _OBJECT_NL.get(str(report.get("objectType", "")), str(report.get("objectType", "") or "locaties"))
    n_var = len(report.get("scenarios") or [])
    featured = any(run_id.endswith(s) or run_id == s for s in _FEATURED_SUFFIXES)

    label_parts = [track, kind]
    if n_var and "authorcmp" not in run_id and not run_id.startswith("_fixture"):
        label_parts.append(f"{n_var} varianten")
    label = " · ".join(label_parts)
    if featured:
        label = f"★ {label}"

    hints: list[str] = []
    if obj and obj != "locaties":
        hints.append(f"Vraagtype: waar mogen {obj}?")
    for sc in (report.get("scenarios") or [])[:2]:
        name = (sc.get("name") or "").strip()
        if name:
            hints.append(name)
    hint = " — ".join(hints) if hints else f"Technische run-id: {run_id}"

    return {
        "id": run_id,
        "label": label,
        "hint": hint,
        "featured": featured,
        "track": track,
        "variantCount": n_var,
        "sortKey": ("0" if featured else "1") + run_id,
    }


def list_scenario_runs(scenario_runs_root: Path) -> list[dict[str, Any]]:
    if not scenario_runs_root.is_dir():
        return []
    rows = [
        describe_scenario_run(p)
        for p in scenario_runs_root.iterdir()
        if p.is_dir() and (p / "scenario-report.json").is_file()
    ]
    rows.sort(key=lambda r: r["sortKey"])
    return rows
