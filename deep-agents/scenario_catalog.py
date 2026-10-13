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

# track-key → Nederlands label (behavior behouden uit de oude _track_nl)
_TRACK_KEY_NL: dict[str, str] = {
    "wind": "Wind", "zon": "Zon", "bos": "Bos", "water": "Water",
    "bodem": "Bodem", "mobiliteit": "Mobiliteit", "landschap": "Landschap",
    "landbouw": "Landbouw", "wonen": "Wonen", "werken": "Werken",
    "recreatie": "Recreatie", "biomassa": "Biomassa", "energietoets": "Energietoets",
}

# langste tokens eerst: 'energietoets' vóór 'et' nooit nodig, maar
# 'wonen'/'werken' niet laten botsen met 'wind'/'water'
_TRACK_TOKENS: list[tuple[str, str]] = [
    ("energietoets", "energietoets"), ("biomassa", "biomassa"),
    ("recreatie", "recreatie"), ("landschap", "landschap"),
    ("landbouw", "landbouw"), ("mobiliteit", "mobiliteit"),
    ("werken", "werken"), ("wonen", "wonen"), ("water", "water"),
    ("bodem", "bodem"), ("forest", "bos"), ("solar", "zon"), ("zon", "zon"),
    ("wind", "wind"), ("bos", "bos"),
]


def _uitdagingen_doc(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "poc" / "scenarios" / "uitdagingen.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# deze module leeft in <repo>/deep-agents, dus twee niveaus omhoog = repo-root
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _track_key(run_id: str) -> str | None:
    rid = run_id.lower()
    for token, key in _TRACK_TOKENS:
        if token in rid:
            return key
    return None


def _kind_nl(run_id: str) -> str:
    if run_id.startswith("_fixture"):
        return "Test-fixture (ontwikkeling)"
    if "authorcmp" in run_id:
        return "Authoring vs engine (vergelijking)"
    if "scen" in run_id:
        return "Beleidsvarianten (world scene)"
    return "Scenario-run"


def describe_scenario_run(
    run_dir: Path, utd_doc: dict[str, Any] | None = None
) -> dict[str, Any]:
    if utd_doc is None:
        utd_doc = _uitdagingen_doc(_REPO_ROOT)
    run_id = run_dir.name
    report_path = run_dir / "scenario-report.json"
    report: dict[str, Any] = {}
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))

    track_key = _track_key(run_id)
    track = _TRACK_KEY_NL.get(track_key, "Meerdere tracks") if track_key else "Meerdere tracks"
    kind = _kind_nl(run_id)
    obj = _OBJECT_NL.get(str(report.get("objectType", "")), str(report.get("objectType", "") or "locaties"))
    n_var = len(report.get("scenarios") or [])

    uitdaging: dict[str, str] | None = None
    featured = False
    utd_order = ""
    # _fixture-runs zijn ontwikkelmateriaal; authorcmp-runs zijn oude
    # authoring-vs-engine-vergelijkingen — beide vallen onder "Overig"
    # (spec §5), dus geen uitdaging-groepering
    if (utd_doc and not run_id.startswith("_fixture")
            and "authorcmp" not in run_id):
        for i, utd in enumerate(utd_doc.get("uitdagingen", [])):
            if track_key and track_key in utd.get("tracks", []):
                uitdaging = {"id": utd["id"], "titel": utd["titel"]}
                j = utd["tracks"].index(track_key)
                utd_order = f"{i}{j:02d}"
                featured = utd_doc.get("scenarioRuns", {}).get(track_key) == run_id
                break

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
        "trackKey": track_key,
        "uitdaging": uitdaging,
        "variantCount": n_var,
        "sortKey": ("0" if featured else "1") + (utd_order or "9") + run_id,
    }


def list_scenario_runs(scenario_runs_root: Path) -> list[dict[str, Any]]:
    if not scenario_runs_root.is_dir():
        return []
    repo_root = scenario_runs_root.parent.parent
    utd_doc = _uitdagingen_doc(repo_root)
    rows = [
        describe_scenario_run(p, utd_doc)
        for p in scenario_runs_root.iterdir()
        if p.is_dir() and (p / "scenario-report.json").is_file()
    ]
    rows.sort(key=lambda r: r["sortKey"])
    return rows
