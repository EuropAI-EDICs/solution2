"""Offline-toolpaden blokkeren de event loop niet meer (asyncio.to_thread).

De SSE-stream moet levend blijven tijdens een multi-seconde pipeline-stap:
een ticker-task moet ticken TERWIJL een langzame sync-executor draait.

Meet binnen de trage aanroep (deadline-meting): ticker start eerst en de
tool draait concurrent; telticks op t≈0,30s (de executor staat 0,4s stil).
Bij een blokkerende sync-executor bevriest de loop en komt de ticker tot
~1 vangst; met asyncio.to_thread loopt hij vrij en haalt hij ≥ 4 ticks.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))


def test_poc_offline_pad_blokkeert_loop_niet(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from services.mcp_servers import poc_server
    from services.process_adapter import jobs as job_store

    def trage_route(process_id, inputs, backend="local"):
        import time

        time.sleep(0.4)
        return "j1", {"summary": {}}, {"startedAtTime": "t", "endedAtTime": "t"}

    monkeypatch.setattr(job_store, "route_execute", trage_route)

    async def scenario():
        ticks = []

        async def ticker():
            for _ in range(8):
                await asyncio.sleep(0.05)
                ticks.append(1)

        t = asyncio.create_task(ticker())
        await asyncio.sleep(0.02)  # laat de ticker éérst draaien
        tool = asyncio.create_task(
            poc_server._run_poc_tool("fetch_geo_layer", {"source_id": "agrest-ov-gebied-windenergie"})
        )
        await asyncio.sleep(0.3)  # meet BINNEN de trage executor-aanroep
        n = len(ticks)
        await asyncio.gather(t, tool, return_exceptions=True)
        return n

    assert asyncio.run(scenario()) >= 4, "event loop stond stil tijdens de executor"


def test_data_list_entities_blokkeert_loop_niet(monkeypatch):
    from services.adapters import data_platform
    from services.mcp_servers import data_server

    def trage_list(entity_type, scope=None, geoproperty=None):
        import time

        time.sleep(0.4)
        return [{"id": "urn:ngsi-ld:X:1", "type": entity_type, "mock": True}]

    monkeypatch.setattr(data_platform, "NGSI_LD_URL", "")
    monkeypatch.setattr(data_platform, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(data_platform, "MOCK", True)
    monkeypatch.setattr(data_platform, "list_entities", trage_list)

    async def scenario():
        ticks = []

        async def ticker():
            for _ in range(8):
                await asyncio.sleep(0.05)
                ticks.append(1)

        t = asyncio.create_task(ticker())
        await asyncio.sleep(0.02)  # laat de ticker éérst draaien
        tool = asyncio.create_task(data_server.list_entities("AirQualityObserved"))
        await asyncio.sleep(0.3)  # meet BINNEN de trage executor-aanroep
        n = len(ticks)
        await asyncio.gather(t, tool, return_exceptions=True)
        return n

    assert asyncio.run(scenario()) >= 4
