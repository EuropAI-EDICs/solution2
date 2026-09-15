from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import httpx

from services.common.prov import utc_now
from services.common.schema import validate_instance

COOKBOOK_URL = os.environ.get("NLDT_COOKBOOK_URL", "http://localhost:8081")


def plan_recipe(state: dict[str, Any]) -> dict[str, Any]:
    recipe_id = state.get("recipe_id")
    if not recipe_id:
        hits = state.get("catalog_hits", [])
        for hit in hits:
            if hit.get("type") == "recipe":
                recipe_id = hit.get("properties", {}).get("recipeId") or hit["id"].replace(
                    "recipe-", ""
                )
                break
        if not recipe_id:
            return {"error": "No recipe matched in catalog"}

    if os.environ.get("NLDT_OFFLINE") == "1":
        from services.common.schema import load_recipe

        recipe = load_recipe(recipe_id)
    else:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{COOKBOOK_URL}/recipes/{recipe_id}")
            resp.raise_for_status()
            recipe = resp.json()

    resolved = dict(state.get("resolved_inputs") or {})
    requires_hitl = recipe.get("riskLevel") == "high"
    # Phase 6: restricted Data Space offers always require HITL unless already approved
    if recipe_id == "lake-publish-offer":
        ac = str(resolved.get("accessClass") or "internal").lower()
        if ac == "restricted" and not resolved.get("forceHitlApproved"):
            requires_hitl = True
        elif ac == "open" and not resolved.get("forceHitlApproved"):
            requires_hitl = False
        elif resolved.get("forceHitlApproved"):
            requires_hitl = False  # approval already supplied as input
    # Source monitor: always human merge of patch proposals (V4)
    if recipe_id == "source-monitor-run":
        requires_hitl = True

    plan = {
        "id": str(uuid4()),
        "requestSummary": state.get("natural_language_request", f"Execute recipe {recipe_id}"),
        "naturalLanguageRequest": state.get("natural_language_request"),
        "recipeId": recipe_id,
        "recipeVersion": recipe.get("version", "1.0.0"),
        "resolvedInputs": resolved,
        "stepOrder": [s["id"] for s in recipe["steps"]],
        "proposedBy": {"agent": "recipe-planner", "llmUsed": False},
        "effortBudget": {"maxSteps": len(recipe["steps"])},
        "riskLevel": recipe.get("riskLevel", "low"),
        "requiresHitl": requires_hitl,
        "plannedAt": utc_now(),
    }
    validate_instance(plan, "agent-plan.schema.json")
    return {"agent_plan": plan, "recipe_id": recipe_id}
