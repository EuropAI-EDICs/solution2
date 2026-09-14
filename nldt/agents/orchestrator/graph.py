from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.orchestrator.nodes.catalog import catalog_search
from agents.orchestrator.nodes.critic import validate_outputs, validate_plan
from agents.orchestrator.nodes.executor import execute_steps
from agents.orchestrator.nodes.explainer import explain
from agents.orchestrator.nodes.hybrid import register_hybrid
from agents.orchestrator.nodes.planner import plan_recipe
from agents.orchestrator.state import OrchestratorState


def _route_after_plan(state: OrchestratorState) -> Literal["execute", "end"]:
    if state.get("error"):
        return "end"
    report = state.get("validation_report") or {}
    if report.get("verdict") == "needs_human":
        return "end"
    if report.get("verdict") == "fail":
        return "end"
    return "execute"


def _route_after_exec(state: OrchestratorState) -> Literal["validate_outputs", "end"]:
    if state.get("error"):
        return "end"
    return "validate_outputs"


def build_graph():
    graph = StateGraph(OrchestratorState)
    graph.add_node("catalog_search", catalog_search)
    graph.add_node("plan_recipe", plan_recipe)
    graph.add_node("validate_plan", validate_plan)
    graph.add_node("execute_steps", execute_steps)
    graph.add_node("validate_outputs", validate_outputs)
    graph.add_node("register_hybrid", register_hybrid)
    graph.add_node("explain", explain)

    graph.set_entry_point("catalog_search")
    graph.add_edge("catalog_search", "plan_recipe")
    graph.add_edge("plan_recipe", "validate_plan")
    graph.add_conditional_edges("validate_plan", _route_after_plan, {"execute": "execute_steps", "end": END})
    graph.add_conditional_edges(
        "execute_steps", _route_after_exec, {"validate_outputs": "validate_outputs", "end": END}
    )
    graph.add_edge("validate_outputs", "register_hybrid")
    graph.add_edge("register_hybrid", "explain")
    graph.add_edge("explain", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
