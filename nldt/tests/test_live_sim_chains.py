"""Chain-registry: zes chains, alle stappen naar geregistreerde tools, resolver-flow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import chains  # noqa: E402
from live_sim_fakes import FakeMcpClient  # noqa: E402

VERWACHT = {
    "utrecht": (8, 4),
    "eindhoven": (4, 0),
    "breda": (3, 1),
    "gent": (3, 0),
    "veenendaal": (3, 0),
    "dsorr": (4, 0),
}


def test_registry_heeft_zes_chains_met_verwachte_stappen_en_lagen():
    assert set(chains.CHAINS) == set(VERWACHT)
    for cid, (stappen, lagen) in VERWACHT.items():
        chain = chains.CHAINS[cid]
        assert chain["id"] == cid and chain["label"]
        assert len(chain["stappen"]) == stappen, cid
        assert len([s for s in chain["stappen"] if "laag" in s]) == lagen, cid


def test_alle_stappen_gebruiken_geregistreerde_tools():
    bekende = {
        ("catalog", "list_poc_capabilities"),
        ("dso", "dso_kb_overview"),
        ("dso", "dso_kb_annotations"),
        ("dso", "dso_kb_tpod"),
        ("poc", "fetch_geo_layer"),
        ("data", "list_entities"),
        ("data", "entities_to_geojson"),
        ("poc", "run_opportunity_map"),
        ("poc", "run_bp2op_transform"),
        ("poc", "run_value_scan"),
        ("poc", "gent_life_event_run"),
        ("poc", "veenendaal_gebiedscheck_run"),
        ("poc", "run_artifact"),
    }
    for chain in chains.CHAINS.values():
        for stap in chain["stappen"]:
            assert (stap["server"], stap["tool"]) in bekende, stap


def test_args_uit_vorige_resolvets_rundir_uit_pipeline_resultaat():
    raw = json.dumps(
        {
            "tool": "run_opportunity_map",
            "outputs": {"summary": {"mode": "execute", "runDir": "/x/runs/20261115-wind"}},
        }
    )
    stap = chains.CHAINS["utrecht"]["stappen"][-1]
    args = stap["args_uit_vorige"](raw)
    assert args == {"run_dir": "/x/runs/20261115-wind", "artifact": "zones.geojson"}


def test_chain_met_mode_geeft_kopie_met_andere_mode():
    origineel = chains.CHAINS["breda"]["stappen"]
    replay = chains.chain_met_mode("breda", "replay")
    assert origineel[1]["args"]["mode"] == "execute"  # productie blijft execute
    assert replay[1]["args"]["mode"] == "replay"  # kopie overgeschreven
    assert chains.CHAINS["breda"]["stappen"][1]["args"]["mode"] == "execute"  # onveranderd


def test_agent_draait_utrecht_chain_end_to_end_met_fake():
    import asyncio

    import agent

    events = []
    fake = FakeMcpClient()

    def emit(ev, data):
        events.append((ev, data))

    agent_ = agent.ScriptedAgent(fake, stappen=chains.CHAINS["utrecht"]["stappen"])
    result = asyncio.run(agent_.run(emit))
    namen = [ev for ev, _ in events]
    assert namen.count("step_started") == 8
    assert namen.count("tool_result") == 8
    assert namen.count("layer_ready") == 4
    assert namen[-1] == "run_done"
    assert result["status"] == "ok"
    # zones-laag komt uit run_artifact (artifact_content), niet de ruwe payload
    zones = [d for ev, d in events if ev == "layer_ready" and d.get("source_id") == "utrecht-zones"]
    assert zones[0]["geojson"]["type"] == "FeatureCollection"
    # run_artifact kreeg de runDir uit de opportunity-map-stap
    run_artifact_calls = [c for c in fake.calls if c[1] == "run_artifact"]
    assert run_artifact_calls and "/fake-run/run_opportunity_map" in run_artifact_calls[0][2]["run_dir"]
