"""Hash-chained events per run (SEC-04-richting): elke gebeurtenis wordt
onmiskenbaar vastgelegd; tamperen breekt de ketting.
seq en ts vallen binnen de hash-basis, dus ook tijdstip- en volgordemanipulatie breekt de ketting."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

GENESIS = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(kind: str, payload: dict, prev: str, seq: int, ts: str) -> str:
    basis = json.dumps({"kind": kind, "payload": payload, "prev": prev, "seq": seq, "ts": ts},
                       sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def emit(events: list, kind: str, payload: dict) -> dict:
    prev = events[-1]["hash"] if events else GENESIS
    seq = len(events)
    ts = _now()
    event = {"seq": seq, "ts": ts, "kind": kind, "payload": payload,
             "prevHash": prev, "hash": _hash(kind, payload, prev, seq, ts)}
    events.append(event)
    return event


def verify_chain(events: list) -> bool:
    prev = GENESIS
    for index, ev in enumerate(events):
        if ev["seq"] != index:
            return False
        if ev["prevHash"] != prev or ev["hash"] != _hash(ev["kind"], ev["payload"], prev, ev["seq"], ev["ts"]):
            return False
        prev = ev["hash"]
    return True
