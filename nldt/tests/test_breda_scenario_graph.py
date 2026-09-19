"""Breda LangGraph plane + S10 deep-research seam."""

from __future__ import annotations

from uuid import uuid4

from agents.breda_scenario.graph import build_breda_scenario_graph
from agents.seams.deep_research import propose_research_brief
from services.common.schema import validate_instance


def test_research_brief_stub_passes_schema():
    brief, rejected = propose_research_brief(
        "Breda heat and ageing 2050",
        lake_series_hints=[{"seriesId": "cbs-kwb-demo"}],
        force_stub=True,
    )
    assert rejected == []
    assert brief is not None
    assert brief["proposedBy"].startswith("deep-research#")
    assert brief["harness"] == "stub"
    validate_instance(brief, "research-brief.schema.json")
    assert "cbs-kwb-demo" in brief["suggestedSeriesIds"]


def test_research_brief_rejects_bad_draft(monkeypatch):
    monkeypatch.setenv("NLDT_DEEP_RESEARCH", "1")
    monkeypatch.delenv("NLDT_OFFLINE", raising=False)
    monkeypatch.setattr(
        "agents.seams.deep_research._try_deepagents",
        lambda topic, hints: {
            "briefId": "RB-bad",
            "topic": "t",
            "findings": [{"claim": "short", "confidence": 0.1}],  # claim too short
            "proposedBy": "model-lies",
        },
    )
    brief, rejected = propose_research_brief("topic here is long enough", force_stub=False)
    # deep draft fails gate → stub floor
    assert brief is not None
    assert brief["harness"] == "stub"
    assert any("schema" in (r.get("reden") or "") for r in rejected)


def test_breda_scenario_graph_stub_with_s10():
    app = build_breda_scenario_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "mode": "stub",
            "enable_deep_research": True,
            "horizon_year": 2050,
            "max_scenarios": 6,
            "research_topic": "Breda five-value 2050 research",
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert not result.get("error")
    report = result["report"]
    assert report["graph"] == "breda_scenario"
    assert report["nAccepted"] >= 2  # floor + stub llm
    assert result.get("research_brief")
    assert result["research_brief"]["proposedBy"].startswith("deep-research#")
    # per-AI pathways, not merged
    paths = report.get("llmScenarioPathways") or {}
    assert "VS-STUB-01" in paths
    assert "llmHorizonPathway" not in report


def test_breda_graph_skips_research_when_disabled():
    app = build_breda_scenario_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "mode": "stub",
            "enable_deep_research": False,
            "horizon_year": 2050,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert not result.get("error")
    assert not result.get("research_brief")


def test_live_run_requires_baseline(monkeypatch):
    app = build_breda_scenario_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "mode": "live",
            "enable_deep_research": False,
            "horizon_year": 2050,
            # no baseline_scan / layers
            "floor_specs": [],
            "llm_specs": [],
            "specs": [{"scenarioId": "X", "mutations": [], "proposedBy": "file"}],
        },
        config={"configurable": {"thread_id": run_id}},
    )
    # horizon live may fail first without lake — or run_scenarios complains
    assert result.get("error")


def test_live_run_scenarios_mocked(monkeypatch):
    from agents.breda_scenario import nodes as N

    def fake_run(baseline, layers, specs):
        return {
            "variants": [
                {
                    "scenarioId": s.get("scenarioId"),
                    "name": s.get("name"),
                    "mutations": s.get("mutations") or [],
                    "proposedBy": s.get("proposedBy") or "file",
                    "nBuurtenVeranderd": 1,
                    "deltas": {},
                    "profiel": {},
                    "grootsteVerschuivers": [],
                    "basis": {"type": "hypothetical"},
                }
                for s in specs
            ],
            "nAccepted": len(specs),
            "nScenarios": len(specs),
            "validation": {"verdict": "pass"},
            "control": {"identicalToBaseline": True},
        }

    class FakeBreda:
        @staticmethod
        def run_scenarios(baseline, layers, specs):
            return fake_run(baseline, layers, specs)

        @staticmethod
        def build_llm_scenario_pathways(*a, **k):
            return {
                "VS-L": {
                    "scenarioId": "VS-L",
                    "keyframes": {"2026": {}, "2050": {}},
                    "bron": "llm",
                }
            }

        @staticmethod
        def build_horizon_pathway_frames(*a, **k):
            return {"keyframes": {"2026": {}, "2050": {}}, "bron": "deterministisch"}

    monkeypatch.setattr(N, "_ensure_breda_path", lambda: None)

    import sys
    import types

    breda_mod = types.ModuleType("breda")
    scen_mod = types.ModuleType("breda.scenarios")
    for name in (
        "run_scenarios",
        "build_llm_scenario_pathways",
        "build_horizon_pathway_frames",
        "breda_horizon_projections",
        "breda_lake_series_hints",
        "enrich_hints_with_projections",
        "deterministic_scenarios_2050",
        "merge_horizon_floor_and_llm",
    ):
        setattr(scen_mod, name, getattr(FakeBreda, name, None))

    scen_mod.run_scenarios = FakeBreda.run_scenarios
    scen_mod.build_llm_scenario_pathways = FakeBreda.build_llm_scenario_pathways
    scen_mod.build_horizon_pathway_frames = FakeBreda.build_horizon_pathway_frames
    scen_mod.breda_horizon_projections = lambda y: [
        {"variable": "percentagePersonen65JaarEnOuder", "projected": 45, "horizon": y}
    ]
    scen_mod.breda_lake_series_hints = lambda: []
    scen_mod.enrich_hints_with_projections = lambda h, p: h
    scen_mod.deterministic_scenarios_2050 = lambda projections, max_scenarios=3: (
        [{
            "scenarioId": "VS-F",
            "name": "floor",
            "mutations": [{"action": "set_social_rule", "rule": "ouderen_gated", "thresholdPct": 45}],
            "proposedBy": "auto-horizon-2050",
        }],
        [],
    )
    scen_mod.merge_horizon_floor_and_llm = lambda floor, llm, max_scenarios=6: (
        floor + [{
            "scenarioId": "VS-L",
            "name": "llm",
            "mutations": [{"action": "set_economic_weights", "dak": 7, "bedrijven": 3}],
            "proposedBy": "llm-proposal#test",
        }],
        [],
    )

    class FakeAuthor:
        def propose(self, *a, **k):
            return [], []

    scen_mod.LLMScenarioAuthor = FakeAuthor
    breda_mod.scenarios = scen_mod
    monkeypatch.setitem(sys.modules, "breda", breda_mod)
    monkeypatch.setitem(sys.modules, "breda.scenarios", scen_mod)

    app = build_breda_scenario_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "mode": "live",
            "enable_deep_research": True,
            "horizon_year": 2050,
            "max_scenarios": 6,
            "baseline_scan": {"buurten": []},
            "layers": {"buurten": {"features": []}},
            "build_whatif": False,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert not result.get("error"), result.get("error")
    assert result["report"]["graph"] == "breda_scenario"
    assert result.get("research_brief")
    assert "VS-L" in (result.get("llm_pathway_ids") or [])
