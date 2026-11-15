"""Gescripte agent: doorloopt de stappen van de gekozen chain (chains.CHAINS),
elke stap één echte MCP-toolcall.

emit(event, data) is de sink (SessionStore-queue in de server; list in tests).
Deterministisch: geen condities, geen LLM — "no invented numbers".
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Callable

from chains import CHAINS

Emit = Callable[[str, dict], None]


def _json_object(raw: str) -> Any:
    return json.loads(raw) if isinstance(raw, str) else raw


class ScriptedAgent:
    def __init__(self, client, stappen: list[dict[str, Any]] | None = None):
        self.client = client
        self.stappen = stappen if stappen is not None else CHAINS["utrecht"]["stappen"]

    async def run(self, emit: Emit) -> dict[str, Any]:
        per_stap: list[dict[str, Any]] = []
        vorige_raw: str | None = None
        for i, stap in enumerate(self.stappen):
            args = stap["args_uit_vorige"](vorige_raw) if "args_uit_vorige" in stap else stap["args"]
            emit(
                "step_started",
                {
                    "index": i,
                    "label": stap["label"],
                    "server": stap["server"],
                    "tool": stap["tool"],
                    "args": args,
                },
            )
            t0 = time.perf_counter()
            try:
                raw = await self.client.call_tool(stap["server"], stap["tool"], args)
                vorige_raw = raw
                duur_ms = int((time.perf_counter() - t0) * 1000)
                samenvatting = stap["samenvatting"](raw)
            except Exception as exc:  # stap faalt → run stopt (spec: foutafhandeling)
                duur_ms = int((time.perf_counter() - t0) * 1000)
                emit(
                    "tool_result",
                    {"index": i, "ok": False, "duration_ms": duur_ms, "summary": str(exc)[:300]},
                )
                emit("error", {"stap": i, "label": stap["label"], "melding": str(exc)[:300]})
                return {"status": "error", "stap": i, "per_stap": per_stap}
            emit(
                "tool_result",
                {"index": i, "ok": True, "duration_ms": duur_ms, "summary": samenvatting},
            )
            per_stap.append({"index": i, "ok": True})
            laag = stap.get("laag")
            if laag:
                event: dict[str, Any] = {"laagtype": laag["laagtype"], "source_id": laag["source_id"]}
                if laag.get("inline"):
                    obj = _json_object(raw)
                    if laag.get("inline_uit") == "artifact_content":
                        obj = obj["outputs"]["artifact"]["content"]
                    event["geojson"] = obj
                emit("layer_ready", event)
        emit("run_done", {"per_stap": per_stap, "totaal": len(per_stap)})
        return {"status": "ok", "per_stap": per_stap}


def run_sync(agent_: ScriptedAgent, emit: Emit) -> dict[str, Any]:
    return asyncio.run(agent_.run(emit))


class SessionStore:
    """Eén actieve sessie; events via asyncio.Queue tot sluiting.

    Het sessie-slot komt vrij zodra de agent klaar is — ook als niemand de
    events ophaalt (een POST /api/session zonder verbindende EventSource
    blokkeert de demo dus niet met 409's). De queue verhuist dan van
    `_queues` (actief) naar `_done` (afgerond, ongelezen): een late streamer
    leest de gebufferde events alsnog en ruimt die done-entry pas op als hij
    het sluit-sentinel (`_close`) zelf heeft gezien. De task-referentie
    (`_tasks`) gaat pas weg als de task klaar is, zodat asyncio die niet
    voortijdig opschoont.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}  # actieve sessies
        self._done: dict[str, asyncio.Queue] = {}  # afgerond, nog niet gestreamd
        self._tasks: dict[str, asyncio.Task] = {}  # refs: voorkomt GC van de task

    def start(self, agent_factory) -> str:
        if self._queues:
            raise RuntimeError("er draait al een sessie")
        sid = uuid.uuid4().hex[:12]
        q: asyncio.Queue = asyncio.Queue()
        self._queues[sid] = q
        self._tasks[sid] = asyncio.get_running_loop().create_task(
            self._run(sid, q, agent_factory)
        )
        return sid

    async def _run(self, sid: str, q: asyncio.Queue, agent_factory) -> None:
        try:
            agent_ = agent_factory()
            await agent_.run(lambda ev, data: q.put_nowait((ev, data)))
        finally:
            q.put_nowait(("_close", None))
            # slot vrijgeven ook als niemand streamt: eerst uit actief, dan done
            self._queues.pop(sid, None)
            self._done[sid] = q
            self._tasks.pop(sid, None)

    async def stream(self, sid: str):
        q = self._queues.get(sid)
        if q is None:
            q = self._done.get(sid)
        if q is None:
            raise KeyError(sid)
        afgesloten = False
        try:
            while True:
                ev, data = await q.get()
                if ev == "_close":
                    afgesloten = True
                    return
                yield ev, data
        finally:
            # alleen de done-entry opruimen; een actieve sessie nooit — een
            # vroeg afgebroken stream mag de lopende agent niet weggooien
            if afgesloten:
                self._done.pop(sid, None)
