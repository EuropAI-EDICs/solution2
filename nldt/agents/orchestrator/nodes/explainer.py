from __future__ import annotations

from typing import Any

from services.common.prov import utc_now


def explain(state: dict[str, Any]) -> dict[str, Any]:
    plan = state.get("agent_plan") or {}
    execution = state.get("execution") or {}
    report = state.get("validation_report") or {}
    steps = execution.get("steps", [])
    explanation = {
        "summary": f"Executed recipe '{plan.get('recipeId')}' in {len(steps)} steps.",
        "recipeId": plan.get("recipeId"),
        "validationVerdict": report.get("verdict"),
        "hybrid": state.get("hybrid"),
        "steps": [
            {
                "stepId": s.get("stepId"),
                "processId": steps[i]["processId"] if i < len(steps) else None,
                "jobId": s.get("jobId"),
            }
            for i, s in enumerate(steps)
        ],
        "outputs": list((execution.get("outputs") or {}).keys()),
        "provenance": [s.get("prov") for s in steps if s.get("prov")],
        "explainedAt": utc_now(),
    }
    return {"explanation": explanation}
