"""Server-mounts + echte MCP-loopback-client + lagen-endpoint (real sockets, offline).

De server draait in-thread op een vrije poort; de client callingt over echt
HTTP tegen de mounts. NGSI-LD draait op de adapter-mock (module-attrs leeg).
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx
import pytest
import uvicorn

import server  # noqa: E402
from mcp_client import McpLoopbackClient  # noqa: E402


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


def _vrije_poort() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def live_server(monkeypatch):
    from services.adapters import data_platform

    monkeypatch.setattr(data_platform, "NGSI_LD_URL", "")
    monkeypatch.setattr(data_platform, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(data_platform, "MOCK", True)

    port = _vrije_poort()
    config = uvicorn.Config(server.create_app(), host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if uv_server.started:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("live-server startte niet")
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=5)


def test_mcp_loopback_data_list_entities_mock(live_server):
    client = McpLoopbackClient(live_server)
    raw = asyncio_run(client.call_tool("data", "list_entities", {"entity_type": "AirQualityObserved"}))
    ents = json.loads(raw)
    assert isinstance(ents, list) and ents
    assert ents[0]["id"].startswith("urn:ngsi-ld:AirQualityObserved:")
    assert ents[0].get("mock") is True


def test_mcp_loopback_poc_fetch_geo_layer_cache(live_server):
    client = McpLoopbackClient(live_server)
    raw = asyncio_run(
        client.call_tool("poc", "fetch_geo_layer", {"source_id": "agrest-ov-gebied-windenergie"})
    )
    payload = json.loads(raw)
    assert payload["status"] == "successful"
    assert payload["outputs"]["summary"]["featureCount"] == 44


def test_layers_endpoint_dient_4326_twin(live_server):
    with httpx.Client(timeout=10.0) as http:
        resp = http.get(f"{live_server}/api/layers/agrest-ov-gebied-windenergie")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/geo+json")
    fc = resp.json()
    assert fc["type"] == "FeatureCollection" and fc["features"]


def test_layers_endpoint_404_bij_onbekende_bron(live_server):
    with httpx.Client(timeout=10.0) as http:
        resp = http.get(f"{live_server}/api/layers/bestaat-niet")
    assert resp.status_code == 404
