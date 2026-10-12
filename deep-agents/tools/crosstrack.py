"""Crosstrack-tool (Utrecht Plane C): de multi-track overlay écht uitvoeren
voor de live-run — zelfde patroon als ``tools/breda.py`` en
``tools/poc_live.py``.

Draait de deterministische overlay-engine (``poc/crosstrack/run.py``,
offline/cache-first, ~14 s) naar ``runs/<rid>/`` en journalleert een
viz-entry zodat het dashboard de lagen kan afpellen: track-controles
(wind/zon/bos), de conflictparen en de gedeelde Groene contour.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import journal

HERE = Path(__file__).resolve().parents[1]          # deep-agents/
RUNS_DIR = HERE / "runs"
POC_CROSSTRACK = HERE.parent / "poc" / "crosstrack"
ENGINE_TIMEOUT_S = 420


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_crosstrack_overlay() -> dict:
    """Voer de multi-track overlay uit (wind × zon × bos) en publiceer de
    lagen in het dashboard-paneel: de drie track-controles, de drie
    conflictparen en de gedeelde Groene contour. Cijfers komen uit het
    engine-artefact, niet uit het model."""
    rid = f"{_stamp()}-crosstrack"
    work = RUNS_DIR / rid
    work.mkdir(parents=True, exist_ok=True)
    journal.append("tool_call", "crosstrack",
                   "run_crosstrack_overlay() — multi-track overlay (offline, ~14 s)")

    result = subprocess.run(
        [sys.executable, str(POC_CROSSTRACK / "run.py"), "--out", str(work)],
        capture_output=True, text=True, timeout=ENGINE_TIMEOUT_S, cwd=str(POC_CROSSTRACK),
        env={**os.environ},
    )
    report_path = work / "crosstrack-report.json"
    if result.returncode != 0 or not report_path.is_file():
        tail = (result.stderr or result.stdout or "")[-400:]
        journal.append("error", "crosstrack",
                       f"run_crosstrack_overlay: engine faalde (rc={result.returncode}): {tail}")
        return {"error": f"De crosstrack-engine faalde (rc={result.returncode}). Laatste regels: {tail}"}

    report = json.loads(report_path.read_text(encoding="utf-8"))
    journal.append(
        "tool_result", "crosstrack",
        f"crosstrack overlay built: {len(report.get('tracks', []))} tracks, "
        f"{len(report.get('conflicts', []))} conflictparen, "
        f"{len(report.get('sharedZones', []))} gedeelde zone(s) — lagen in het paneel",
        viz={"kind": "crosstrack-viz", "runId": rid, "poc": "crosstrack"},
    )
    tracks = [{"useCase": t.get("useCase"), "areaKm2": t.get("finalAreaKm2")}
              for t in report.get("tracks", [])]
    conflicts = [{"pair": " × ".join(c.get("pair", [])), "areaKm2": c.get("areaKm2")}
                 for c in report.get("conflicts", [])]
    shared = [{"zone": z.get("zoneId"), "areaKm2": z.get("areaKm2")}
              for z in report.get("sharedZones", [])]
    return {
        "crosstrackRunId": rid,
        "verdict": report.get("verdict") or (work / "run_summary.json" and json.loads(
            (work / "run_summary.json").read_text(encoding="utf-8")).get("verdict")),
        "tracks": tracks,
        "conflicts": conflicts,
        "shared": shared,
        "dashboard": "De lagen staan in het rechterpaneel — pak ze af met ▶ afpellen.",
    }
