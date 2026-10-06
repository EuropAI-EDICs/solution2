"""Subagents for the nLDT orchestrator: per-POC specialists (prompts/poc/)
plus functional specialists from the multi-agent plan (prompts/roles/):
geospecialist, normspecialist, critic, explainer. The orchestrator
delegates via the task tool.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from models import ollama_model, subagent_model_name
from tools.artifacts import submit_formal_rule, submit_norm_cards, submit_request
from tools.explain import crosscheck_formal_rule, get_provenance
from tools.formalize import get_formal_rules, validate_formal_rule
from tools.geo import compare_layers, inspect_geo_layer
from tools.intake import request_template, validate_request
from tools.norms import search_norms
from tools.recipes import get_recipe, list_recipes
from tools.utrecht import render_world_scene_demo, run_world_scene
from tools.validate import validate_world_scene

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts" / "poc"
ROLE_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts" / "roles"

POC_AGENTS: list[dict[str, str]] = [
    {
        "name": "breda",
        "description": (
            "Breda POC specialist: five-value scan (Plane A) and grounded scan "
            "QA with cite-or-abstain (GENAI seam S4). Use for anything about "
            "the Breda value scan, its QA or beleidskompas substantiation."
        ),
    },
    {
        "name": "rijnland",
        "description": (
            "Rijnland water-level POC specialist: peil conflict detection "
            "(vigerend peilgebied x praktijk peilafwijking, H3), what-if "
            "peilen scenarios via CDC, and the live freshness-gated variant."
        ),
    },
    {
        "name": "utrecht",
        "description": (
            "Utrecht POC specialist: Plane A opportunity map, Plane B "
            "world-scene building, S7 scenario authoring and offline "
            "scenario sweeps."
        ),
    },
    {
        "name": "crosstrack",
        "description": (
            "Crosstrack (Utrecht Plane C) specialist: multi-track overlay "
            "across wind x solar x forest baseline runs."
        ),
    },
    {
        "name": "minigim",
        "description": (
            "MiniGIM POC specialist: gebiedscheck/omgevingsanalyse for an "
            "AOI with the 74-item Lijst-v0.91 checklist auto-filled from "
            "keyless open sources."
        ),
    },
    {
        "name": "eindhoven",
        "description": (
            "Eindhoven bp2op POC specialist: bestemmingsplan -> "
            "omgevingsplan conversion (V4 human-in-the-loop always pending)."
        ),
    },
]


ROLE_AGENTS: list[dict[str, Any]] = [
    {
        "name": "geospecialist",
        "description": (
            "Geo Analyst: inspects and compares the GeoJSON layers of built "
            "world-scene runs — areas in km2, bboxes, control-vs-scenario "
            "deltas. Use for 'how big / where / what changed spatially' "
            "questions."
        ),
        "tools": [inspect_geo_layer, compare_layers],
    },
    {
        "name": "normspecialist",
        "description": (
            "Norm Analyst: searches the machine-verifiable norm-card corpus "
            "(legal claims with source article and version, wind/zon tracks). "
            "Use for questions about which norms, rules or legal force apply."
        ),
        "tools": [search_norms, submit_norm_cards],
    },
    {
        "name": "critic",
        "description": (
            "Critic/Validator: runs the deterministic validation gate over a "
            "built world-scene bundle (schema, unique ids, deltas, HITL-gated "
            "rendering, grounding stamps). ALWAYS delegate to the critic "
            "after a world-scene build."
        ),
        "tools": [validate_world_scene],
    },
    {
        "name": "explainer",
        "description": (
            "Explainer: provenance-driven explanations — which scenario, norm "
            "card and mutation produced each spec, decision-table style. Use "
            "for 'why/traceability/onderbouwing' questions."
        ),
        "tools": [get_provenance, crosscheck_formal_rule],
    },
    {
        "name": "intake",
        "description": (
            "Intake: normalizes a vague user brief into a schema-valid "
            "OpportunityMapRequest (object type, AOI GeoJSON with crs, policy "
            "stage, effort budget), then SUBMITS it — submission is the "
            "artifact of record and the world-scene build refuses to run "
            "without it."
        ),
        "tools": [request_template, validate_request, submit_request],
    },
    {
        "name": "formalizer",
        "description": (
            "Norm Formalizer: converts a NormCard (NC-*) into a typed, "
            "executable FormalRule (FR-*) — calibrates against the corpus "
            "including rejected rules with reasons, then passes the schema "
            "gate until PASS."
        ),
        "tools": [get_formal_rules, validate_formal_rule, submit_formal_rule],
    },
]


def _mcp(mcp_tools: list | None, names: list[str]) -> list:
    """Selecteer tools op naam uit de geladen MCP-tools (harness-unificatie M1)."""
    by_name = {getattr(t, "name", ""): t for t in (mcp_tools or [])}
    return [by_name[n] for n in names if n in by_name]


# MCP-namen: catalog-replacement voor alle PoC-agenten + utrecht run/read-operaties
POC_CATALOG_MCP = ["search_records", "get_record"]
UTRECHT_OPS_MCP = [
    "run_opportunity_map",
    "propose_scenarios",
    "run_scenario_sweep",
    "build_world_scene",
    "inspect_geo_layer",
    "get_provenance",
    "crosscheck_formal_rule",
    "describe_process",
    "execute_process",
]


def poc_subagents(mcp_tools: list | None = None) -> list[dict[str, Any]]:
    """Build the declarative subagent specs (one per POC) on the subagent model.

    Met mcp_tools (M1) komen nldt-capabiliteiten uit de nldt-MCP-servers;
    zonder blijven de lokale wrapper-tools actief als expliciete fallback
    (M2-cleanup verwijdert die wrappers).
    """
    submodel = ollama_model(subagent_model_name())
    mcp_catalog = _mcp(mcp_tools, POC_CATALOG_MCP)
    mcp_utrecht = _mcp(mcp_tools, UTRECHT_OPS_MCP)
    extra_tools = {
        "utrecht": [run_world_scene, render_world_scene_demo] + mcp_utrecht,
    }

    def spec_to_subagent(spec: dict[str, Any], prompt_dir: Path, base_tools: list) -> dict[str, Any]:
        return {
            "name": spec["name"],
            "description": spec["description"],
            "system_prompt": (prompt_dir / f"{spec['name']}.md").read_text(encoding="utf-8"),
            "tools": base_tools + extra_tools.get(spec["name"], []),
            "model": submodel,
        }

    poc_base = mcp_catalog or [list_recipes, get_recipe]
    poc_specs = [spec_to_subagent(spec, PROMPTS_DIR, poc_base) for spec in POC_AGENTS]
    role_specs = [spec_to_subagent(spec, ROLE_PROMPTS_DIR, spec["tools"]) for spec in ROLE_AGENTS]
    return poc_specs + role_specs


def roster() -> list[dict[str, str]]:
    """The full agent roster (name + description) without building models."""
    return [{"name": s["name"], "description": s["description"], "kind": "poc"} for s in POC_AGENTS] + [
        {"name": s["name"], "description": s["description"], "kind": "role"} for s in ROLE_AGENTS
    ]


def build_standalone_poc_agent(poc_name: str):
    """Single PoC Deep Agent (no orchestrator) — for A2A AgentExecutor backends."""
    from deepagents import create_deep_agent

    spec = next((s for s in POC_AGENTS if s["name"] == poc_name), None)
    if spec is None:
        raise KeyError(f"unknown PoC agent: {poc_name}")

    submodel = ollama_model(subagent_model_name())
    extra_tools = {
        "utrecht": [run_world_scene, render_world_scene_demo],
    }
    tools = [list_recipes, get_recipe] + extra_tools.get(poc_name, [])
    system_prompt = (PROMPTS_DIR / f"{poc_name}.md").read_text(encoding="utf-8")
    return create_deep_agent(
        model=submodel,
        tools=tools,
        system_prompt=system_prompt,
    )


def run_standalone_poc_agent(poc_name: str, user_message: str, thread_id: str) -> dict[str, Any]:
    """Invoke one PoC deep agent; returns assistant text and a compact tool trace."""
    agent = build_standalone_poc_agent(poc_name)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    trace: list[str] = []
    for msg in result["messages"]:
        for call in getattr(msg, "tool_calls", None) or []:
            args = call.get("args", {})
            target = args.get("recipe_id", args.get("subagent_type", ""))
            trace.append(f"{call['name']}({target})" if target else call["name"])
    last = result["messages"][-1]
    content = last.content if isinstance(last.content, str) else str(last.content)
    return {"answer": content, "toolTrace": trace, "pocId": poc_name, "mode": "deep-agents"}
