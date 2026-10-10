"""Breda-tool: de vijf-waardenscan écht uitvoeren voor de live-run (fase 3).

Draait de deterministische scan-engine (``poc-breda/run.py``, cache-first en
offline — zie PoC-4 design) naar ``runs/<stamp>-breda-scan/`` en journalleert
een viz-entry zodat het dashboard de scan-kaart in het rechterpaneel laadt.
Patroon: ``tools/utrecht.py`` (worldscene).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import journal

HERE = Path(__file__).resolve().parents[1]   # deep-agents/
RUNS_DIR = HERE / "runs"
POC_BREDA = HERE.parent / "poc-breda"
ENGINE_TIMEOUT_S = 300


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rollup_summary(value_scan: dict) -> dict:
    """Per waarde de top- en bottom-2 uit het scan-artefact (compact voor de agent)."""
    out = {}
    for value, roll in (value_scan.get("rollup") or {}).items():
        out[value] = {
            "top": roll.get("top", [])[:2],
            "bottom": roll.get("bottom", [])[:2],
        }
    return out


def run_breda_scan() -> dict:
    """Voer de vijf-waardenscan uit en publiceer de kaart in het dashboard-paneel.

    Deterministisch en offline (cache-first): dezelfde engine als het
    ``breda-scan-run``-proces. De map verschijnt in het rechterpaneel zodra de
    tool klaar is; de agent vat de uitslag samen (verdict, rollup, zwakste
    buurten) — het aantal en de cijfers komen uit het artefact, niet uit zichzelf.
    """
    rid = _stamp()   # viz.runId zónder suffix; de map krijgt '-breda-scan' (Utrecht-conventie)
    work = RUNS_DIR / f"{rid}-breda-scan"
    journal.append("tool_call", "breda", "run_breda_scan() — vijf-waardenscan (cache-first, offline)")

    result = subprocess.run(
        [sys.executable, str(POC_BREDA / "run.py"), "--out", str(work)],
        capture_output=True, text=True, timeout=ENGINE_TIMEOUT_S, cwd=str(POC_BREDA),
        env={**os.environ},
    )
    if result.returncode != 0 or not (work / "run_summary.json").is_file():
        tail = (result.stderr or result.stdout or "")[-400:]
        journal.append("error", "breda", f"run_breda_scan: engine faalde (rc={result.returncode}): {tail}")
        return {
            "error": f"De scan-engine faalde (rc={result.returncode}). Laatste regels: {tail}",
        }

    summary = json.loads((work / "run_summary.json").read_text(encoding="utf-8"))
    value_scan = json.loads((work / "value-scan.json").read_text(encoding="utf-8"))
    rollup = _rollup_summary(value_scan)

    journal.append(
        "tool_result", "breda",
        f"five-value scan built: verdict {summary.get('verdict')}, "
        f"{summary.get('nBuurten')} buurten, {len(rollup)} waarden — kaart in het paneel",
        viz={"kind": "breda-scan", "runId": rid},
    )
    return {
        "scanRunId": rid,
        "verdict": summary.get("verdict"),
        "nBuurten": summary.get("nBuurten"),
        "degradations": summary.get("degradations"),
        "rollupTopBottom": rollup,
        "dashboard": "De scan-kaart staat in het rechterpaneel; verwijs de gebruiker daarheen.",
    }
