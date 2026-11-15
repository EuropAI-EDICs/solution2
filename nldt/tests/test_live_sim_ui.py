"""UI-startpagina: server serves index.html met kaart, trace en EventSource-wiring.

Let op: httpx.ASGITransport is async-only (httpx 0.28: subclass van
AsyncBaseTransport, geen sync `__enter__`/`handle_request`). Daarom de
canonieke AsyncClient + asyncio.run-vorm; assertions identiek aan de brief.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx  # noqa: E402

import server  # noqa: E402


def test_index_bevat_kaart_trace_en_eventsource():
    app = server.create_app()

    async def _haal_index() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, timeout=10.0) as http:
            return await http.get("http://test/")

    resp = asyncio.run(_haal_index())
    assert resp.status_code == 200
    html = resp.text
    for naald in ('id="kaart"', 'id="trace"', 'id="start"', 'id="ngsi-badge"',
                  'id="chain-switcher"', "EventSource", "/api/session", "/api/chains"):
        assert naald in html, f"index.html mist {naald}"
