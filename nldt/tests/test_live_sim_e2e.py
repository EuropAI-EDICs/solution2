"""E2E per chain over echt MCP-loopback, offline (cache + gecommitte runs).

Productie-chains draaien execute; in deze E2E staan de pipeline-stappen op
replay (chains.chain_met_mode) zodat elke chain deterministisch en offline in
seconden draait en het hele wiring bewijst: registry → agent → echte MCP →
executor → runDir-doorvoer → run_artifact → events/lagen.
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

import chains  # noqa: E402
import server  # noqa: E402


def _vrije_poort():
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


def _lees_events(http, base, chain):
    resp = http.post(f"{base}/api/session", params={"chain": chain})
    assert resp.status_code == 200, resp.text
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


def _basis_asserts(events, stappen_count, lagen_count):
    namen = [ev for ev, _ in events]
    assert "error" not in namen, [d for ev, d in events if ev == "error"]
    assert namen.count("step_started") == stappen_count
    assert namen.count("tool_result") == stappen_count
    assert all(d["ok"] for ev, d in events if ev == "tool_result")
    assert namen.count("layer_ready") == lagen_count
    assert namen[-1] == "run_done"


def test_chains_endpoint_noemt_zes_chains(e2e):
    with httpx.Client(timeout=30.0) as http:
        resp = http.get(f"{e2e}/api/chains")
    assert resp.status_code == 200
    lijst = resp.json()
    assert {c["id"] for c in lijst} == {"utrecht", "eindhoven", "breda", "gent", "veenendaal", "dsorr"}


def test_e2e_utrecht(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "utrecht": {**chains.CHAINS["utrecht"], "stappen": chains.chain_met_mode("utrecht", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "utrecht")
        _basis_asserts(events, 8, 4)
        # zones-laag is inline geojson uit run_artifact (canonical wind-run)
        zones = [d for ev, d in events if ev == "layer_ready" and d.get("source_id") == "utrecht-zones"]
        assert zones and zones[0]["geojson"]["type"] == "FeatureCollection"
        # fetch-lagen zijn via /api/layers op te halen
        for sid in ("agrest-ov-gebied-windenergie", "arcgis-et-wind-gebieden"):
            resp = http.get(f"{e2e}/api/layers/{sid}")
            assert resp.status_code == 200
            assert resp.json()["type"] == "FeatureCollection"


def test_e2e_breda(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "breda": {**chains.CHAINS["breda"], "stappen": chains.chain_met_mode("breda", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "breda")
        _basis_asserts(events, 3, 1)
        buurt = [d for ev, d in events if ev == "layer_ready" and d.get("source_id") == "breda-buurten"]
        assert buurt and buurt[0]["geojson"]["type"] == "FeatureCollection"
        assert buurt[0]["geojson"]["features"], "buurtkaart heeft features"


def test_e2e_eindhoven(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "eindhoven": {**chains.CHAINS["eindhoven"], "stappen": chains.chain_met_mode("eindhoven", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "eindhoven")
        _basis_asserts(events, 4, 0)
        art = [d for ev, d in events if ev == "tool_result"][-1]
        assert "omzettabel.json" in art["summary"]


def test_e2e_gent(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "gent": {**chains.CHAINS["gent"], "stappen": chains.chain_met_mode("gent", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "gent")
        _basis_asserts(events, 3, 0)
        art = [d for ev, d in events if ev == "tool_result"][-1]
        assert "run.json" in art["summary"]


def test_e2e_veenendaal(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "veenendaal": {**chains.CHAINS["veenendaal"], "stappen": chains.chain_met_mode("veenendaal", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "veenendaal")
        _basis_asserts(events, 3, 0)
        art = [d for ev, d in events if ev == "tool_result"][-1]
        assert "indicators.json" in art["summary"]


def test_e2e_dsorr(e2e):
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "dsorr")
        _basis_asserts(events, 4, 0)
