"""SSE-sessie-endpoints met geïnjecteerde fake-toolclient (geen sockets).

Let op: httpx.ASGITransport is async-only (httpx 0.28: subclass van
AsyncBaseTransport, geen sync `__enter__`/`handle_request`). Daarom de
canonieke AsyncClient + asyncio.run-vorm; assertions identiek aan de brief.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx  # noqa: E402

import server  # noqa: E402
from agent import ScriptedAgent  # noqa: E402
from live_sim_fakes import FakeMcpClient  # noqa: E402 (sibling in tests/)


def _parse_sse(regels: list[str]) -> list[tuple[str, dict]]:
    events = []
    ev, data = None, None
    for regel in regels:
        if regel.startswith("event: "):
            ev = regel[len("event: "):].strip()
        elif regel.startswith("data: "):
            data = json.loads(regel[len("data: "):])
        elif regel == "" and ev is not None:
            events.append((ev, data))
            ev, data = None, None
    return events


async def _lees_sse(http, url) -> list[str]:
    """Lees alle SSE-regels; de server sluit de stream na run_done/error vanzelf."""
    regels = []
    async with http.stream("GET", url) as stream:
        async for regel in stream.aiter_lines():
            regels.append(regel)
    return regels


def test_sessie_start_en_eventstroom():
    app = server.create_app(tool_client_factory=lambda: ScriptedAgent(FakeMcpClient()))

    async def _main():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), timeout=20.0
        ) as http:
            resp = await http.post("http://test/api/session")
            assert resp.status_code == 200
            sid = resp.json()["sessionId"]

            events = _parse_sse(await _lees_sse(http, f"http://test/api/session/{sid}/events"))
        return events

    events = asyncio.run(_main())
    namen = [ev for ev, _ in events]
    assert namen.count("step_started") == 6
    assert namen.count("tool_result") == 6
    assert namen.count("layer_ready") == 3
    assert "run_done" in namen


def test_tweede_sessie_409_en_onbekende_sessie_error_event():
    app = server.create_app(tool_client_factory=lambda: ScriptedAgent(FakeMcpClient()))

    async def _main():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), timeout=20.0
        ) as http:
            eerste = await http.post("http://test/api/session")
            assert eerste.status_code == 200

            tweede = await http.post("http://test/api/session")
            assert tweede.status_code == 409

            # sessie aflopen: stream leeglezen tot sluiting, dan is een nieuwe sessie weer ok
            sid = eerste.json()["sessionId"]
            await _lees_sse(http, f"http://test/api/session/{sid}/events")
            derde = await http.post("http://test/api/session")
            assert derde.status_code == 200

            # onbekende sessie → error-event op de stream (200, SSE-error, geen 404)
            events = _parse_sse(await _lees_sse(http, "http://test/api/session/niets/events"))
        return events

    events = asyncio.run(_main())
    assert events and events[0][0] == "error"
