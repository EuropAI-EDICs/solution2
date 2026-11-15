from __future__ import annotations

import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent  # noqa: E402
import chains  # noqa: E402
from live_sim_fakes import FakeMcpClient  # noqa: E402 (sibling in tests/, op sys.path via pytest)


def test_agent_event_volgorde_deterministisch():
    events = []

    def emit(ev, data):
        events.append((ev, data))

    fake = FakeMcpClient()
    result = agent.run_sync(agent.ScriptedAgent(fake, stappen=chains.CHAINS["utrecht"]["stappen"]), emit)
    namen = [ev for ev, _ in events]
    assert namen.count("step_started") == 8
    assert namen.count("tool_result") == 8
    assert namen.count("layer_ready") == 4
    assert namen[-1] == "run_done"
    assert result["status"] == "ok"
    # elke stap exact één call, in chain-volgorde
    assert [c[:2] for c in fake.calls] == [(s["server"], s["tool"]) for s in chains.CHAINS["utrecht"]["stappen"]]
    # inline NGSI-laag draagt het GeoJSON in het event
    ngsi_laag = [d for ev, d in events if ev == "layer_ready" and d.get("laagtype") == "punten"]
    assert ngsi_laag and ngsi_laag[0]["geojson"]["type"] == "FeatureCollection"
    assert ngsi_laag[0]["source_id"] == "ngsi-ld-dpl-airquality"
    # bestand-backed lagen verwijzen naar /api/layers/<source_id>;
    # de zones-laag (inline uit artifact_content) komt erbij
    zone_lagen = [d for ev, d in events if ev == "layer_ready" and d.get("laagtype") == "zone"]
    assert {z["source_id"] for z in zone_lagen} == {
        "agrest-ov-gebied-windenergie",
        "arcgis-et-wind-gebieden",
        "utrecht-zones",
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
