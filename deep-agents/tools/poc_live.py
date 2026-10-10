"""Live-panel tools voor Rijnland, MiniGIM en Eindhoven (fase 3).

Zelfde patroon als ``tools/breda.py``: per PoC een deterministische
engine-run (CLI, cache-first/offline) naar ``runs/<rid>/``, met een
genormaliseerd paneel-contract voor het dashboard:

  runs/<rid>/panel.json  — {poc, title, iframe, cards}
  runs/<rid>/panel.html  — self-contained kaart/rapport-pagina (optioneel)

Journal-viz: ``{"kind": "<poc>-viz", "runId": rid, "poc": poc}`` — het
dashboard laadt ``/<rid>/panel.html`` in een iframe en de kaarten uit
``panel.json``. Crosstrack is bewust buiten scope (verweven met de
Utrecht-scenario-runs; panel volgt later via het worldscene-patroon).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import journal

HERE = Path(__file__).resolve().parents[1]          # deep-agents/
REPO_ROOT = HERE.parent
RUNS_DIR = HERE / "runs"
ENGINE_TIMEOUT_S = 420                                # bp2op loopt ~2 min


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _cards_minigim(work: Path) -> list[dict]:
    runs = sorted(work.glob("*/run_summary.json"))
    summary = _read_json(runs[-1]) if runs else {}
    bind = (summary.get("summary") or {}).get("bindingStatus") or {}
    lines = [
        f"verdict: {summary.get('verdict')} — {summary.get('label')}",
        f"checklist: {summary.get('summary', {}).get('itemCount')} items — "
        f"binding manual {bind.get('manual')}, auto {bind.get('auto')}, partial {bind.get('partial')}",
    ]
    return [{"title": "Gebiedscheck", "lines": lines}]


def _cards_eindhoven(work: Path) -> list[dict]:
    runs = sorted(work.glob("*/run_summary.json"))
    summary = _read_json(runs[-1]) if runs else {}
    counts = summary.get("counts") or {}
    lines = [
        f"verdict: {summary.get('verdict')}",
        "counts: " + ", ".join(f"{k} {v}" for k, v in counts.items()),
    ]
    return [{"title": "bp2op-omzetting", "lines": lines}]


def _cards_rijnland(work: Path) -> list[dict]:
    peilen = _read_json(work / "peilen.json")
    window = peilen.get("window") or ["?", "?"]
    return [{
        "title": "Peilen what-if",
        "lines": [
            f"stations: {peilen.get('stations')} — venster {window[0]} … {window[-1]}",
            f"computedBy: {peilen.get('computedBy')}",
        ],
    }]


LIVE_POC: dict[str, dict[str, Any]] = {
    "rijnland": {
        "title": "Rijnland — peilen what-if (animated hex map)",
        "cwd": REPO_ROOT / "poc-rijnland",
        "engine": ["run_peilen.py", "--out", "{work}"],
        "panel_html": "peilen.html",
        "cards": _cards_rijnland,
    },
    "minigim": {
        "title": "MiniGIM — gebiedscheck Breda Teteringen (pilot)",
        "cwd": REPO_ROOT / "poc-minigim",
        "engine": ["run.py",
                   "--aoi", str(REPO_ROOT / "poc-minigim" / "examples" / "plangrens-breda-teteringen.28992.geojson"),
                   "--label", "Breda Teteringen (pilot)",
                   "--runs-dir", "{work}"],
        "panel_html": "report.html",
        "cards": _cards_minigim,
    },
    "eindhoven": {
        "title": "Eindhoven — bp2op: bestemmingsplan → omgevingsplan",
        "cwd": REPO_ROOT / "poc-bp2op",
        "engine": ["run.py", "--use-case", "eindhoven", "--out", "{work}"],
        "panel_html": "report.html",
        "cards": _cards_eindhoven,
    },
}


def run_poc_live(poc: str) -> dict:
    """Voer de deterministische engine van `poc` uit en publiceer het paneel."""
    spec = LIVE_POC.get(poc)
    if spec is None:
        raise KeyError(f"onbekende live-PoC: {poc} (beschikbaar: {', '.join(sorted(LIVE_POC))})")
    rid = f"{_stamp()}-{poc}"
    work = RUNS_DIR / rid
    work.mkdir(parents=True, exist_ok=True)
    journal.append("tool_call", poc, f"run_poc_live('{poc}') — deterministische engine-run (offline)")

    engine_args = [a.replace("{work}", str(work)) if isinstance(a, str) else a
                   for a in spec["engine"]]
    result = subprocess.run(
        [sys.executable] + engine_args,
        capture_output=True, text=True, timeout=ENGINE_TIMEOUT_S, cwd=str(spec["cwd"]),
        env={**os.environ},
    )

    panel_html_src = work / spec["panel_html"]
    if not panel_html_src.is_file():
        # sommige engines maken een run-subdir onder --out/--runs-dir
        subdirs = sorted(p for p in work.iterdir() if p.is_dir()) if work.is_dir() else []
        for sub in subdirs:
            candidate = sub / spec["panel_html"]
            if candidate.is_file():
                panel_html_src = candidate
                break

    if result.returncode != 0 or not panel_html_src.is_file():
        tail = (result.stderr or result.stdout or "")[-400:]
        journal.append("error", poc, f"run_poc_live: engine faalde (rc={result.returncode}): {tail}")
        return {"error": f"De {poc}-engine faalde (rc={result.returncode}). Laatste regels: {tail}"}

    if panel_html_src != work / "panel.html":
        (work / "panel.html").write_bytes(panel_html_src.read_bytes())

    cards = spec["cards"](work)
    panel = {"poc": poc, "title": spec["title"], "iframe": "panel.html", "cards": cards}
    (work / "panel.json").write_text(json.dumps(panel, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    journal.append(
        "tool_result", poc,
        f"live panel built: {spec['title']} — paneel staat klaar",
        viz={"kind": f"{poc}-viz", "runId": rid, "poc": poc},
    )
    return {
        "runId": rid, "poc": poc, "verdictOf": cards[0]["lines"][0] if cards else "",
        "dashboard": "Het paneel (kaart/rapport + kaarten) staat in het rechtervlak.",
    }


# benoemde wrappers zodat de agent herkenbare tool-namen krijgt
def run_rijnland_live() -> dict:
    """Rijnland: peilen what-if — animated hex map van de actuele peilafwijking."""
    return run_poc_live("rijnland")


def run_minigim_live() -> dict:
    """MiniGIM: gebiedscheck Breda Teteringen — 74-item checklist + ILS-kaart."""
    return run_poc_live("minigim")


def run_eindhoven_live() -> dict:
    """Eindhoven: bp2op — bestemmingsplan → omgevingsplan (V4 mens pending)."""
    return run_poc_live("eindhoven")
