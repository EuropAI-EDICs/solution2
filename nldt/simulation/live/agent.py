"""Gescripte agent: doorloopt STAPPEN, elke stap één echte MCP-toolcall.

emit(event, data) is de sink (SessionStore-queue in de server; list in tests).
Deterministisch: geen condities, geen LLM — "no invented numbers".
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Callable

from fetch_script import STAPPEN

Emit = Callable[[str, dict], None]


def _json_object(raw: str) -> Any:
    return json.loads(raw) if isinstance(raw, str) else raw


class ScriptedAgent:
    def __init__(self, client, stappen: list[dict[str, Any]] | None = None):
        self.client = client
        self.stappen = stappen if stappen is not None else STAPPEN

    async def run(self, emit: Emit) -> dict[str, Any]:
        per_stap: list[dict[str, Any]] = []
        for i, stap in enumerate(self.stappen):
            emit(
                "step_started",
                {
                    "index": i,
                    "label": stap["label"],
                    "server": stap["server"],
                    "tool": stap["tool"],
                    "args": stap["args"],
                },
            )
            t0 = time.perf_counter()
            try:
                raw = await self.client.call_tool(stap["server"], stap["tool"], stap["args"])
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
                    event["geojson"] = _json_object(raw)
                emit("layer_ready", event)
        emit("run_done", {"per_stap": per_stap, "totaal": len(per_stap)})
        return {"status": "ok", "per_stap": per_stap}


def run_sync(agent_: ScriptedAgent, emit: Emit) -> dict[str, Any]:
    return asyncio.run(agent_.run(emit))


class SessionStore:
    """Eén actieve sessie; events via asyncio.Queue tot sluiting."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def start(self, agent_factory) -> str:
        if self._queues:
            raise RuntimeError("er draait al een sessie")
        sid = uuid.uuid4().hex[:12]
        q: asyncio.Queue = asyncio.Queue()
        self._queues[sid] = q
        asyncio.get_running_loop().create_task(self._run(sid, q, agent_factory))
        return sid

    async def _run(self, sid: str, q: asyncio.Queue, agent_factory) -> None:
        agent_ = agent_factory()
        try:
            await agent_.run(lambda ev, data: q.put_nowait((ev, data)))
        finally:
            q.put_nowait(("_close", None))

    async def stream(self, sid: str):
        q = self._queues.get(sid)
        if q is None:
            raise KeyError(sid)
        try:
            while True:
                ev, data = await q.get()
                if ev == "_close":
                    return
                yield ev, data
        finally:
            self._queues.pop(sid, None)
