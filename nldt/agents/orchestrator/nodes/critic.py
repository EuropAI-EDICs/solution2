from __future__ import annotations

from typing import Any

from services.common.geo import validate_feature_collection
from services.common.prov import utc_now
from services.common.schema import validate_instance


def _level(status: str, checks: list[dict] | None = None) -> dict[str, Any]:
    return {"status": status, "checks": checks or []}


def _validate_poc_outputs(recipe_id: str, outputs: dict[str, Any]) -> tuple[list[dict], str, str]:
    """PoC-specific V2 checks for scenario/QA recipes."""
    checks_v2: list[dict] = []
    verdict = "pass"

    if recipe_id == "breda-scan-qa":
        result = outputs.get("result") or {}
        status = result.get("status")
        if status == "answered":
            if not result.get("answer"):
                checks_v2.append({"id": "s4-answer", "status": "fail", "detail": "missing answer"})
            elif result.get("groundingFails"):
                checks_v2.append({"id": "s4-grounding", "status": "fail", "detail": "grounding failed"})
            else:
                checks_v2.append({"id": "s4-cite-or-abstain", "status": "pass"})
        elif status == "abstained":
            checks_v2.append({"id": "s4-abstain", "status": "pass", "detail": "cite-or-abstain"})
        else:
            checks_v2.append({"id": "s4-status", "status": "fail", "detail": status})

    if recipe_id in ("utrecht-scenario-sweep", "utrecht-scenario-author"):
        summary = outputs.get("summary") or outputs.get("proposals") or {}
        if recipe_id == "utrecht-scenario-author":
            rejected = summary.get("rejected") or []
            accepted = summary.get("accepted") or []
            if not accepted and rejected:
                checks_v2.append({"id": "s7-all-rejected", "status": "fail"})
                verdict = "fail"
            else:
                checks_v2.append({"id": "s7-proposals", "status": "pass"})
        else:
            if summary.get("verdict") == "fail":
                checks_v2.append({"id": "scenario-sweep", "status": "fail"})
                verdict = "fail"
            else:
                checks_v2.append({"id": "scenario-sweep", "status": "pass"})

    if recipe_id == "multi-track-crosstrack":
        summary = outputs.get("summary") or {}
        if summary.get("mode") == "replay" and summary.get("runDir"):
            checks_v2.append({"id": "crosstrack-replay", "status": "pass"})
        else:
            checks_v2.append({"id": "crosstrack", "status": "pass" if summary else "fail"})
            if not summary:
                verdict = "fail"

    v2 = "pass" if all(c["status"] == "pass" for c in checks_v2) else "fail"
    if v2 == "fail":
        verdict = "fail"
    return checks_v2, v2 if checks_v2 else "not_applicable", verdict


def validate_plan(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("error"):
        return {}
    plan = state.get("agent_plan")
    if not plan:
        return {"error": "Missing agent plan"}
    checks_v0 = []
    try:
        validate_instance(plan, "agent-plan.schema.json")
        checks_v0.append({"id": "schema", "status": "pass"})
        v0 = "pass"
    except Exception as exc:
        checks_v0.append({"id": "schema", "status": "fail", "detail": str(exc)})
        v0 = "fail"

    report = {
        "id": f"VR-{state.get('run_id', 'run')}-plan",
        "artifactId": plan["id"],
        "artifactType": "agent-plan",
        "levels": {
            "V0": _level(v0, checks_v0),
            "V1": _level("not_applicable"),
            "V2": _level("pending"),
            "V3": _level("not_applicable"),
            "V4": _level("pending" if plan.get("requiresHitl") else "not_applicable"),
        },
        "verdict": "pass" if v0 == "pass" else "fail",
        "evaluatorRun": "critic#plan-validation",
        "evaluatedAt": utc_now(),
    }
    if plan.get("requiresHitl") and not state.get("auto_approve_hitl"):
        report["verdict"] = "needs_human"
    return {"validation_report": report}


def validate_outputs(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("error"):
        return {}
    execution = state.get("execution") or {}
    outputs = execution.get("outputs", {})
    recipe_id = execution.get("recipeId", "")
    checks_v0: list[dict] = []
    checks_v1: list[dict] = []

    for key, value in outputs.items():
        checks_v0.append({"id": f"output-{key}", "status": "pass"})
        if isinstance(value, dict) and value.get("type") == "FeatureCollection":
            errs = validate_feature_collection(value)
            if errs:
                checks_v1.append({"id": f"geo-{key}", "status": "fail", "detail": "; ".join(errs)})
            else:
                checks_v1.append({"id": f"geo-{key}", "status": "pass"})

    poc_checks, v2_status, poc_verdict = _validate_poc_outputs(recipe_id, outputs)
    v1 = "pass" if all(c["status"] == "pass" for c in checks_v1) else "fail"
    verdict = "pass" if v1 == "pass" and poc_verdict == "pass" else "fail"

    report = {
        "id": f"VR-{state.get('run_id', 'run')}-exec",
        "artifactId": recipe_id or "unknown",
        "artifactType": "recipe-execution",
        "levels": {
            "V0": _level("pass", checks_v0),
            "V1": _level(v1, checks_v1),
            "V2": _level(v2_status, poc_checks),
            "V3": _level("not_applicable"),
            "V4": _level("not_applicable"),
        },
        "verdict": verdict,
        "evaluatorRun": "critic#output-validation",
        "evaluatedAt": utc_now(),
    }
    validate_instance(report, "validation-report.schema.json")
    return {"validation_report": report}
