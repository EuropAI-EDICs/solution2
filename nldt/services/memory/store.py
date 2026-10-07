"""Durabele decision-trail store (semantic memory, leerstaat B10).

Append-only JSONL onder ${NLDT_MEMORY_DIR:-nldt/data/memory/trails}/
YYYYMMDD-trails.jsonl. Schrijven valideert elk record tegen
decision-trail.schema.json; --handle/--promote herschrijven de dagfile
die de trail bevat (in-place, regelvolgorde blijft).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.common.schema import validate_instance

MEMORY_ROOT = Path(__file__).resolve().parents[2] / "data" / "memory" / "trails"


def memory_dir() -> Path:
    return Path(os.environ.get("NLDT_MEMORY_DIR", str(MEMORY_ROOT)))


def _day_file() -> Path:
    return memory_dir() / f"{datetime.now(timezone.utc):%Y%m%d}-trails.jsonl"


def trail_id(observation: dict[str, Any]) -> str:
    ident = json.dumps(
        {k: observation.get(k) for k in ("type", "source", "detail")},
        sort_keys=True,
        ensure_ascii=False,
    )
    return "dt-" + hashlib.sha256(ident.encode("utf-8")).hexdigest()[:8]


def make_trail(
    observation: dict[str, Any],
    what: str,
    why: str,
    what_should_change: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    record = {
        "trailId": trail_id(observation),
        "observation": {k: observation[k] for k in ("type", "source", "provenance", "detail") if k in observation},
        "what": what,
        "why": why,
        "whatShouldChange": what_should_change,
        "whoDecides": "operator",
        "didItHelp": None,
        "learningLevel": "operationeel",
        "status": "open",
        "createdAt": created_at or datetime.now(timezone.utc).isoformat(),
    }
    validate_instance(record, "decision-trail.schema.json")
    return record


def append_trails(records: list[dict[str, Any]]) -> int:
    existing = {t["trailId"] for t in load_trails()}
    path = _day_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            if record["trailId"] in existing:
                continue
            validate_instance(record, "decision-trail.schema.json")
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            existing.add(record["trailId"])
            written += 1
    return written


def load_trails() -> list[dict[str, Any]]:
    trails: list[dict[str, Any]] = []
    if not memory_dir().is_dir():
        return trails
    for path in sorted(memory_dir().glob("*-trails.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                trails.append(json.loads(line))
    return trails


def update_trail(
    trail_id: str,
    *,
    status: str | None = None,
    did_it_help: str | None = None,
    learning_level: str | None = None,
) -> dict[str, Any] | None:
    """Pas één trail aan en herschrijf de dagfile waarin hij staat."""
    for path in sorted(memory_dir().glob("*-trails.jsonl")):
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        hit = False
        for record in records:
            if record["trailId"] != trail_id:
                continue
            hit = True
            if status is not None:
                record["status"] = status
            if did_it_help is not None:
                record["didItHelp"] = did_it_help
            if learning_level is not None:
                record["learningLevel"] = learning_level
        if hit:
            for record in records:
                validate_instance(record, "decision-trail.schema.json")
            path.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in records), encoding="utf-8")
            return next(r for r in records if r["trailId"] == trail_id)
    return None
