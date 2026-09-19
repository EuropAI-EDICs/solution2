"""LangGraph orchestration for Breda what-if scenarios."""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.breda_scenario.nodes import (
    assemble,
    author_floor,
    author_llm,
    deep_research,
    horizon_inputs,
    merge_and_gate,
    pathways_node,
    run_scenarios_node,
)
from agents.breda_scenario.state import BredaScenarioState


def _route_after_horizon(state: BredaScenarioState) -> Literal["author", "end"]:
    if state.get("error"):
        return "end"
    return "author"


def _route_after_merge(state: BredaScenarioState) -> Literal["run", "end"]:
    if state.get("error"):
        return "end"
    if not (state.get("specs") or []):
        return "end"
    return "run"


def build_breda_scenario_graph():
    """catalog-style linear graph with S10 → S7 hybrid → dispose stubs."""
    graph = StateGraph(BredaScenarioState)
    graph.add_node("deep_research", deep_research)
    graph.add_node("horizon_inputs", horizon_inputs)
    graph.add_node("author_floor", author_floor)
    graph.add_node("author_llm", author_llm)
    graph.add_node("merge_and_gate", merge_and_gate)
    graph.add_node("run_scenarios", run_scenarios_node)
    graph.add_node("pathways", pathways_node)
    graph.add_node("assemble", assemble)

    graph.set_entry_point("deep_research")
    graph.add_edge("deep_research", "horizon_inputs")
    graph.add_conditional_edges(
        "horizon_inputs", _route_after_horizon, {"author": "author_floor", "end": END}
    )
    graph.add_edge("author_floor", "author_llm")
    graph.add_edge("author_llm", "merge_and_gate")
    graph.add_conditional_edges(
        "merge_and_gate", _route_after_merge, {"run": "run_scenarios", "end": END}
    )
    graph.add_edge("run_scenarios", "pathways")
    graph.add_edge("pathways", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile(checkpointer=MemorySaver())
