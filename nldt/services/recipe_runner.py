from __future__ import annotations

from typing import Any

from services.common.schema import load_recipe, validate_instance
from services.common.templates import resolve_templates
from services.mcp_servers.client import ProcessClient


def run_recipe(
    recipe_id: str,
    inputs: dict[str, Any],
    *,
    process_client: ProcessClient | None = None,
) -> dict[str, Any]:
    recipe = load_recipe(recipe_id)
    client = process_client or ProcessClient()

    context: dict[str, Any] = {
        "recipe": {"inputs": inputs},
        "steps": {},
    }
    step_results: list[dict[str, Any]] = []
    final_outputs: dict[str, Any] = {}

    for step in recipe["steps"]:
        resolved_inputs = resolve_templates(step["inputs"], context)
        job = client.execute(
            step["processId"],
            resolved_inputs,
            backend=step.get("backend", "local"),
        )
        outputs = job.get("outputs", {})
        mapped: dict[str, Any] = {}
        for out_key, var_name in (step.get("outputs") or {}).items():
            value = outputs.get(out_key, outputs)
            mapped[out_key] = value
            mapped[var_name] = value
        context["steps"][step["id"]] = {"outputs": mapped}
        step_results.append(
            {
                "stepId": step["id"],
                "processId": step["processId"],
                "jobId": job.get("jobId"),
                "outputs": mapped,
                "prov": job.get("prov"),
            }
        )

    final_outputs: dict[str, Any] = {}
    for name in recipe.get("outputs", {}):
        for step_data in context["steps"].values():
            if name in step_data["outputs"]:
                final_outputs[name] = step_data["outputs"][name]
                break

    execution = {
        "recipeId": recipe_id,
        "inputs": inputs,
        "steps": step_results,
        "outputs": final_outputs,
    }
    return execution
