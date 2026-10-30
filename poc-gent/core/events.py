"""Hash-chained events per run (SEC-04-richting): elke gebeurtenis wordt
onmiskenbaar vastgelegd; tamperen breekt de ketting."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

GENESIS = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(kind: str, payload: dict, prev: str) -> str:
    basis = json.dumps({"kind": kind, "payload": payload, "prev": prev}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def emit(events: list, kind: str, payload: dict) -> dict:
    prev = events[-1]["hash"] if events else GENESIS
    event = {"seq": len(events), "ts": _now(), "kind": kind, "payload": payload,
             "prevHash": prev, "hash": _hash(kind, payload, prev)}
    events.append(event)
    return event


def verify_chain(events: list) -> bool:
    prev = GENESIS
    for ev in events:
        if ev["prevHash"] != prev or ev["hash"] != _hash(ev["kind"], ev["payload"], prev):
            return False
        prev = ev["hash"]
    return True
