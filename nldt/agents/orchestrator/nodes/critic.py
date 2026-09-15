from __future__ import annotations

from typing import Any

from services.common.geo import validate_feature_collection
from services.common.prov import utc_now
from services.common.schema import validate_instance


POC_RECIPES = {
    "breda-scan-qa",
    "breda-five-value-scan",
    "utrecht-opportunity-map",
    "utrecht-scenario-sweep",
    "utrecht-scenario-author",
    "multi-track-crosstrack",
    "rijnland-peil-conflict",
    "rijnland-peil-conflict-live",
    "rijnland-peil-whatif",
    "eindhoven-bp2op",
}


def _level(status: str, checks: list[dict] | None = None) -> dict[str, Any]:
    return {"status": status, "checks": checks or []}


def _summary_blob(outputs: dict[str, Any]) -> dict[str, Any]:
    return outputs.get("summary") or outputs.get("proposals") or outputs.get("result") or {}


def _reject_evidence(blob: dict[str, Any]) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for key in ("rejected", "proposalsRejected", "normcardsRejected", "groundingFails"):
        val = blob.get(key)
        if isinstance(val, list) and val:
            evidence.append({"ref": key, "note": f"{len(val)} entries"})
        elif val:
            evidence.append({"ref": key, "note": str(val)[:200]})
    return evidence


def _validate_poc_outputs(recipe_id: str, outputs: dict[str, Any]) -> tuple[list[dict], str, str, list[dict]]:
    """PoC-specific V2 checks. Returns checks, v2_status, verdict, evidence."""
    checks_v2: list[dict] = []
    verdict = "pass"
    evidence = _reject_evidence(_summary_blob(outputs))

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
            checks_v2.append({"id": "s4-status", "status": "fail", "detail": str(status)})

    elif recipe_id == "breda-five-value-scan":
        summary = outputs.get("summary") or {}
        if summary.get("runDir") or summary.get("mode") == "replay":
            checks_v2.append({"id": "breda-scan-run", "status": "pass"})
        else:
            checks_v2.append({"id": "breda-scan-run", "status": "fail", "detail": "missing summary"})
            verdict = "fail"

    elif recipe_id in ("utrecht-scenario-sweep", "utrecht-scenario-author"):
        summary = outputs.get("summary") or outputs.get("proposals") or {}
        if recipe_id == "utrecht-scenario-author":
            rejected = summary.get("rejected") or []
            accepted = summary.get("accepted") or summary.get("acceptedCount") or []
            if isinstance(accepted, int):
                has_accepted = accepted > 0
            else:
                has_accepted = bool(accepted)
            if not has_accepted and rejected:
                checks_v2.append({"id": "s7-all-rejected", "status": "fail"})
                verdict = "fail"
            else:
                checks_v2.append({"id": "s7-proposals", "status": "pass"})
                if rejected:
                    checks_v2.append(
                        {
                            "id": "s7-reject-ledger",
                            "status": "pass",
                            "detail": f"{len(rejected)} rejected (ledger retained)",
                        }
                    )
        else:
            if summary.get("verdict") == "fail":
                checks_v2.append({"id": "scenario-sweep", "status": "fail"})
                verdict = "fail"
            else:
                checks_v2.append({"id": "scenario-sweep", "status": "pass"})

    elif recipe_id == "utrecht-opportunity-map":
        summary = outputs.get("summary") or {}
        if summary.get("runDir") or summary.get("mode") in ("replay", "execute"):
            checks_v2.append({"id": "opportunity-map", "status": "pass"})
        else:
            checks_v2.append({"id": "opportunity-map", "status": "fail", "detail": "missing summary"})
            verdict = "fail"

    elif recipe_id == "multi-track-crosstrack":
        summary = outputs.get("summary") or {}
        if summary.get("mode") == "replay" and summary.get("runDir"):
            checks_v2.append({"id": "crosstrack-replay", "status": "pass"})
        elif summary:
            checks_v2.append({"id": "crosstrack", "status": "pass"})
        else:
            checks_v2.append({"id": "crosstrack", "status": "fail"})
            verdict = "fail"

    elif recipe_id in ("rijnland-peil-conflict", "rijnland-peil-conflict-live", "rijnland-peil-whatif"):
        summary = outputs.get("summary") or {}
        if summary.get("runDir") or summary.get("verdict") or summary.get("mode"):
            checks_v2.append({"id": "rijnland-peil", "status": "pass"})
        else:
            checks_v2.append({"id": "rijnland-peil", "status": "fail", "detail": "missing summary"})
            verdict = "fail"

    elif recipe_id == "eindhoven-bp2op":
        summary = outputs.get("summary") or {}
        if summary.get("runDir") or summary.get("mode") in ("replay", "execute"):
            checks_v2.append({"id": "bp2op", "status": "pass"})
            # Legal conversion always needs human sign-off at V4 when HITL not auto-approved
            # (handled in validate_outputs via plan.requiresHitl).
        else:
            checks_v2.append({"id": "bp2op", "status": "fail", "detail": "missing summary"})
            verdict = "fail"

    elif recipe_id in POC_RECIPES:
        if outputs:
            checks_v2.append({"id": "poc-outputs", "status": "pass"})
        else:
            checks_v2.append({"id": "poc-outputs", "status": "fail"})
            verdict = "fail"

    v2 = "pass" if checks_v2 and all(c["status"] == "pass" for c in checks_v2) else (
        "fail" if checks_v2 else "not_applicable"
    )
    if v2 == "fail":
        verdict = "fail"
    return checks_v2, v2, verdict, evidence


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
    recipe_id = execution.get("recipeId") or state.get("recipe_id") or ""
    plan = state.get("agent_plan") or {}
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

    poc_checks, v2_status, poc_verdict, evidence = _validate_poc_outputs(recipe_id, outputs)
    v1 = "pass" if all(c["status"] == "pass" for c in checks_v1) else "fail"
    verdict = "pass" if v1 == "pass" and poc_verdict == "pass" else "fail"

    requires_hitl = bool(plan.get("requiresHitl"))
    auto = bool(state.get("auto_approve_hitl"))
    if requires_hitl and not auto:
        v4 = _level("pending", [{"id": "hitl", "status": "fail", "detail": "human approval required"}])
        verdict = "needs_human"
    elif requires_hitl and auto:
        v4 = _level("pass", [{"id": "hitl", "status": "pass", "detail": "auto-approved"}])
    else:
        v4 = _level("not_applicable")

    report: dict[str, Any] = {
        "id": f"VR-{state.get('run_id', 'run')}-exec",
        "artifactId": recipe_id or "unknown",
        "artifactType": "recipe-execution",
        "levels": {
            "V0": _level("pass", checks_v0),
            "V1": _level(v1, checks_v1),
            "V2": _level(v2_status, poc_checks),
            "V3": _level("not_applicable"),
            "V4": v4,
        },
        "verdict": verdict,
        "evaluatorRun": "critic#output-validation",
        "evaluatedAt": utc_now(),
    }
    if evidence:
        report["evidence"] = evidence
    validate_instance(report, "validation-report.schema.json")
    return {"validation_report": report, "reject_ledger": evidence}
