"""Process-trajectories in het deep-agents journal-format (harness-unificatie M3).

Eén trajectory-format voor beide breinen: deep-agents schrijft zijn steps
hier al (`deep-agents/journal.py`); de process-adapter voegt elke
process-executie als `process_result` toe zodat het dashboard de hele
keten toont. Pad overridable via NLDT_JOURNAL_PATH.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_PATH = WORKSPACE / "deep-agents" / "runs" / "live" / "steps.jsonl"


def journal_path() -> Path:
    return Path(os.environ.get("NLDT_JOURNAL_PATH", str(DEFAULT_PATH)))


def journal_process_event(process_id: str, status: str, summary: str, **extra: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "kind": "process_result",
        "agent": process_id,
        "status": status,
        "summary": summary,
    }
    entry.update(extra)
    path = journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
