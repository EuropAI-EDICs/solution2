"""E2E: volledige fetch-keten over echt MCP-loopback, offline (cache + mock)."""

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


def _vrije_poort():  # zelfde helper als test_live_sim_server
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def e2e(monkeypatch):
    from services.adapters import data_platform

    monkeypatch.setattr(data_platform, "NGSI_LD_URL", "")
    monkeypatch.setattr(data_platform, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(data_platform, "MOCK", True)

    port = _vrije_poort()
    monkeypatch.setenv("NLDT_LIVE_SIM_BASE", f"http://127.0.0.1:{port}")
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


def _lees_events(http, base):
    resp = http.post(f"{base}/api/session")
    assert resp.status_code == 200
    sid = resp.json()["sessionId"]
    events, ev, data = [], None, None
    with http.stream("GET", f"{base}/api/session/{sid}/events") as stream:
        for regel in stream.iter_lines():
            if regel.startswith("event: "):
                ev = regel[7:].strip()
            elif regel.startswith("data: "):
                data = json.loads(regel[6:])
            elif regel == "" and ev is not None:
                events.append((ev, data))
                if ev in ("run_done", "error"):
                    return events
                ev, data = None, None
    return events


def test_volledige_keten_over_echt_mcp(e2e):
    with httpx.Client(timeout=60.0) as http:
        events = _lees_events(http, e2e)
        namen = [ev for ev, _ in events]
        assert "error" not in namen, [d for ev, d in events if ev == "error"]
        assert namen.count("step_started") == 6
        assert namen.count("tool_result") == 6
        assert all(d["ok"] for ev, d in events if ev == "tool_result")
        assert namen.count("layer_ready") == 3
        assert "run_done" in namen

        # bestand-backed lagen zijn daadwerkelijk op te halen
        zone_ids = [d["source_id"] for ev, d in events if ev == "layer_ready" and d.get("source_id") and not d.get("geojson")]
        assert set(zone_ids) == {"agrest-ov-gebied-windenergie", "arcgis-et-wind-gebieden"}
        for sid in zone_ids:
            resp = http.get(f"{e2e}/api/layers/{sid}")
            assert resp.status_code == 200
            assert resp.json()["type"] == "FeatureCollection"

        # inline NGSI-laag is een FeatureCollection (mock-entity)
        ngsi = [d for ev, d in events if ev == "layer_ready" and d.get("geojson")][0]
        assert ngsi["source_id"] == "ngsi-ld-dpl-airquality"
        assert ngsi["geojson"]["type"] == "FeatureCollection"
        assert ngsi["geojson"]["features"]
