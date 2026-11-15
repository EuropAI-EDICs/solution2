from __future__ import annotations

import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent  # noqa: E402
import fetch_script  # noqa: E402
from live_sim_fakes import FakeMcpClient  # noqa: E402 (sibling in tests/, op sys.path via pytest)


def test_script_heeft_zes_stappen_drie_lagen():
    assert len(fetch_script.STAPPEN) == 6
    met_laag = [s for s in fetch_script.STAPPEN if "laag" in s]
    assert len(met_laag) == 3
    inline = [s for s in met_laag if s["laag"].get("inline")]
    assert len(inline) == 1 and inline[0]["laag"]["source_id"] == "ngsi-ld-dpl-airquality"
    servers = {(s["server"], s["tool"]) for s in fetch_script.STAPPEN}
    assert ("catalog", "list_poc_capabilities") in servers
    assert ("dso", "dso_kb_overview") in servers
    assert ("data", "list_entities") in servers
    assert ("data", "entities_to_geojson") in servers


def test_agent_event_volgorde_deterministisch():
    events = []

    def emit(ev, data):
        events.append((ev, data))

    fake = FakeMcpClient()
    result = agent.run_sync(agent.ScriptedAgent(fake), emit)
    namen = [ev for ev, _ in events]
    assert namen.count("step_started") == 6
    assert namen.count("tool_result") == 6
    assert namen.count("layer_ready") == 3
    assert namen[-1] == "run_done"
    assert result["status"] == "ok"
    # elke stap exact één call, in scriptvolgorde
    assert [c[:2] for c in fake.calls] == [(s["server"], s["tool"]) for s in fetch_script.STAPPEN]
    # inline NGSI-laag draagt het GeoJSON in het event
    ngsi_laag = [d for ev, d in events if ev == "layer_ready" and d.get("laagtype") == "punten"]
    assert ngsi_laag and ngsi_laag[0]["geojson"]["type"] == "FeatureCollection"
    assert ngsi_laag[0]["source_id"] == "ngsi-ld-dpl-airquality"
    # bestand-backed lagen verwijzen naar /api/layers/<source_id>
    zone_lagen = [d for ev, d in events if ev == "layer_ready" and d.get("laagtype") == "zone"]
    assert {z["source_id"] for z in zone_lagen} == {
        "agrest-ov-gebied-windenergie",
        "arcgis-et-wind-gebieden",
    }


def test_agent_stopt_met_error_event():
    events = []

    def emit(ev, data):
        events.append((ev, data))

    fake = FakeMcpClient(fail_on=("poc", "fetch_geo_layer"))
    result = agent.run_sync(agent.ScriptedAgent(fake), emit)
    namen = [ev for ev, _ in events]
    assert "error" in namen
    assert "run_done" not in namen
    assert result["status"] == "error"
    err = [d for ev, d in events if ev == "error"][0]
    assert err["label"] == "Inclusion-zone wind (agrest)"
    # stappen na de fout worden niet meer uitgevoerd
    assert len(fake.calls) == 3


def test_session_store_stream_sluit_en_bezet():
    import asyncio

    async def scenario():
        store = agent.SessionStore()
        sid = store.start(lambda: ScriptedAgentMetFake())
        verzameld = []
        async for ev, data in store.stream(sid):
            verzameld.append((ev, data))
        assert verzameld[-1][0] == "run_done"

        # na afloop is een nieuwe sessie weer toegestaan…
        sid2 = store.start(lambda: ScriptedAgentMetFake())
        async for ev, _ in store.stream(sid2):
            pass

        # …maar zolang er één actief is, is een tweede geweigerd
        sid3 = store.start(lambda: ScriptedAgentMetFake())
        try:
            store.start(lambda: None)
        except RuntimeError:
            pass
        else:
            raise AssertionError("tweede gelijktijdige sessie moet worden geweigerd")
        async for ev, _ in store.stream(sid3):
            pass

    asyncio.run(scenario())


class ScriptedAgentMetFake(agent.ScriptedAgent):
    def __init__(self):
        super().__init__(FakeMcpClient())
