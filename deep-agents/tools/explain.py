"""DEPRECATED (M1, harness-unificatie): vervangen door de nldt-MCP-tools
(catalog :8090 / data :8092 / poc :8093). Nog aanwezig als expliciete
fallback voor het geval er geen MCP-stack draait; verwijderd in de
M2-cleanup zodra het MCP-pad standaard is.

Explainer tools: provenance and decision-table material for a built run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import journal
from tools.utrecht import normalize_run_id

HERE = Path(__file__).resolve().parents[1]
RUNS_DIR = HERE / "runs"


def get_provenance(scenario_run_id: str) -> dict[str, Any]:
    """Read the provenance (prov.json entities + world-scene spec provenance notes) of a built world-scene run, for traceable explanations: which scenario, which norm card variant, which mutation produced each spec."""
    scenario_run_id = normalize_run_id(scenario_run_id)
    work = RUNS_DIR / f"{scenario_run_id}-worldscene"
    prov_path = work / "prov.json"
    entities = []
    if prov_path.is_file():
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        entities = [
            {k: e.get(k) for k in ("id", "type", "generatedBy", "sha256") if e.get(k)}
            for e in prov.get("entity", [])
        ]
    notes = []
    bundle_path = work / "world-scene-specs.json"
    if bundle_path.is_file():
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        for s in bundle.get("specs", []):
            basis = s.get("provenanceBasis", {})
            notes.append(
                {
                    "spec": s.get("id"),
                    "scenario": s.get("scenarioId"),
                    "basis": basis.get("type"),
                    "normCard": basis.get("normCardId"),
                    "note": basis.get("provenanceNote", "")[:300],
                }
            )
    result = {"scenarioRunId": scenario_run_id, "entities": entities, "specProvenance": notes}
    journal.append(
        "tool_call", "explainer", f"get_provenance('{scenario_run_id}') → {len(notes)} spec(s), {len(entities)} entities"
    )
    return result


def crosscheck_formal_rule(scenario_run_id: str, formal_rule_id: str) -> dict[str, Any]:
    """Check whether a submitted FormalRule (FR-*) was actually executed by the scenario engine in a run: scans mutationsApplied, mutationsSkipped and rulesExecuted in the run's scenario-report, and links the rule to its norm card via the submitted formalization artifact. Closes the rule → engine loop for the explainer report."""
    rid_arg = formal_rule_id.upper()
    rid = normalize_run_id(scenario_run_id)
    work = RUNS_DIR / f"{rid}-worldscene"
    report_path = work / "scenario-report.json"
    if not report_path.is_file():
        journal.append(
            "error", "explainer", f"crosscheck: geen scenario-report voor '{scenario_run_id}' (gebruik '{rid}')"
        )
        return {
            "error": f"No scenario report for '{scenario_run_id}' — use the scenario-run id "
            f"(e.g. '{rid}', not the '-worldscene' directory) and run run_world_scene first.",
            "formalRuleId": rid_arg,
        }
    report = json.loads(report_path.read_text(encoding="utf-8"))
    applied, skipped = [], []
    for sc in report.get("scenarios", []):
        for m in sc.get("mutationsApplied") or []:
            if str(m.get("ruleId", "")).upper() == rid_arg:
                applied.append({"scenarioId": sc.get("scenarioId"), "action": m.get("action"), "note": (m.get("note") or "")[:120]})
        for m in sc.get("mutationsSkipped") or []:
            if str(m.get("ruleId", "")).upper() == rid_arg:
                skipped.append({"scenarioId": sc.get("scenarioId"), "reason": (m.get("reason") or m.get("note") or "")[:120]})
    norm_card = None
    rule_path = RUNS_DIR / "live" / "artifacts" / "formal-rule.json"
    if rule_path.is_file():
        rule = json.loads(rule_path.read_text(encoding="utf-8"))
        if str(rule.get("id", "")).upper() == rid_arg:
            norm_card = rule.get("normCardId")
    result = {
        "scenarioRunId": rid,
        "formalRuleId": rid_arg,
        "executedByEngine": bool(applied),
        "appliedMutations": applied,
        "skippedMutations": skipped,
        "normCardId": norm_card,
    }
    journal.append(
        "tool_result",
        "explainer",
        f"crosscheck_formal_rule('{rid_arg}') → {'UITGEVOERD door engine' if result['executedByEngine'] else 'NIET uitgevoerd in deze run'}",
    )
    return result
