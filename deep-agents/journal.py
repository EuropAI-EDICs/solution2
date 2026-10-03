"""Run journal: append-only steps.jsonl consumed by the live dashboard.

Every agent-observable event (delegations, tool calls/results, answers) is
appended as one JSON line so the dashboard can show what the agents are
doing while they do it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LIVE_DIR = HERE / "runs" / "live"
JOURNAL = LIVE_DIR / "steps.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def append(kind: str, agent: str, summary: str, **extra: Any) -> None:
    entry = {"ts": _ts(), "kind": kind, "agent": agent, "summary": summary}
    entry.update(extra)
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def reset(question: str) -> None:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text("", encoding="utf-8")
    append("start", "user", question)
