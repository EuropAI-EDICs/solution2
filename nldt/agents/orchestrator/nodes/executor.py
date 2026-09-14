from __future__ import annotations

from typing import Any

from services.recipe_runner import run_recipe


from services.common.telemetry import init_telemetry, span


def execute_steps(state: dict[str, Any]) -> dict[str, Any]:
    init_telemetry("nldt-orchestrator")
    plan = state["agent_plan"]
    if plan.get("requiresHitl") and not state.get("auto_approve_hitl"):
        return {"error": "HITL approval required (--auto-approve-hitl to bypass in dev)"}
    with span("recipe.execute", {"recipe.id": plan["recipeId"], "run.id": state.get("run_id", "")}):
        execution = run_recipe(plan["recipeId"], plan["resolvedInputs"])
    return {"execution": execution}
