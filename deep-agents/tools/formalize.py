"""Norm-formalizer tools (role 4 of the multi-agent plan): browse the formal
rule corpus and run the schema gate on a drafted FormalRule.

The formalizer agent (LLM) converts a NormCard into a typed FormalRule; the
corpus holds the POC's formalized rules (including rejected ones with
reasons — use those as calibration before drafting).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

import journal

HERE = Path(__file__).resolve().parents[1]
REPO_ROOT = HERE.parent
CORPUS_DIR = REPO_ROOT / "poc" / "corpus"
RULE_SCHEMA = REPO_ROOT / "poc" / "schemas" / "formal-rule.schema.json"
POC_DIR = REPO_ROOT / "poc"


def _zone_projector():
    """Lazy import of poc/pipeline/zone_projector (same sys.path pattern as tools/utrecht.py)."""
    if str(POC_DIR) not in sys.path:
        sys.path.insert(0, str(POC_DIR))
    from pipeline.zone_projector import ProjectionError, project_zone

    return ProjectionError, project_zone


def _projection_errors(rule: dict[str, Any]) -> list[str]:
    """For status 'formalized': zone fields must equal project_zone(execution, zoneBinding)."""
    if rule.get("status") != "formalized":
        return []
    if not rule.get("execution"):
        return ["execution: required for formalized rules (RegelRecht execution is the source of truth)"]
    projection_error, project_zone = _zone_projector()
    try:
        proj = project_zone(
            rule["execution"],
            rule.get("zoneBinding"),
            zone_semantics=rule["zoneSemantics"],
            rule_type=rule["ruleType"],
        )
    except (projection_error, KeyError, TypeError, AttributeError) as exc:
        return [f"zone projection failed: {exc}"]
    if proj["zoneSelector"] != rule.get("zoneSelector") or proj["conditions"] != rule.get("conditions"):
        return ["zone fields must equal zone_projector(execution): zoneSelector/conditions are derived, do not hand-author them"]
    return []


def get_formal_rules(track: str | None = None, norm_card_id: str | None = None) -> list[dict[str, Any]]:
    """Browse the formalized rule corpus (e.g. track 'wind' or 'zon', or rules formalized from one norm card like 'NC-W-04'). Includes rejected rules with their reason — use those to calibrate before drafting a new rule."""
    matches: list[dict[str, Any]] = []
    for path in sorted(CORPUS_DIR.glob("formalrules-*.json")):
        if track and track.lower() not in path.stem.lower():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data if isinstance(data, list) else data.get("rules", [])
        for rule in rules:
            if norm_card_id and rule.get("normCardId") != norm_card_id.upper():
                continue
            matches.append(
                {
                    "id": rule.get("id"),
                    "normCardId": rule.get("normCardId"),
                    "status": rule.get("status"),
                    "ruleType": rule.get("ruleType"),
                    "zoneSemantics": rule.get("zoneSemantics"),
                    "reason": (rule.get("reason") or "")[:200],
                }
            )
    journal.append(
        "tool_call",
        "formalizer",
        f"get_formal_rules(track={track}, norm_card_id={norm_card_id}) → {len(matches)} rule(s)",
    )
    return matches[:12]


def validate_formal_rule(rule_json: str) -> dict[str, Any]:
    """Validate a drafted FormalRule (JSON string) against the POC formal-rule schema. Returns pass/fail with per-error evidence; fix the listed errors and re-validate."""
    try:
        rule = json.loads(rule_json)
    except json.JSONDecodeError as exc:
        journal.append("tool_result", "formalizer", f"validate_formal_rule() → FAIL (invalid JSON: {exc})")
        return {"passed": False, "errors": [f"invalid JSON: {exc}"], "ruleId": None}
    schema = json.loads(RULE_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(rule), key=str)
    messages = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors[:8]]
    if not errors and isinstance(rule, dict):
        messages = _projection_errors(rule)
    result = {
        "passed": not messages,
        "errors": messages,
        "ruleId": rule.get("id") if isinstance(rule, dict) else None,
    }
    journal.append(
        "tool_result",
        "formalizer",
        f"validate_formal_rule('{result['ruleId']}') → {'PASS' if result['passed'] else 'FAIL'} ({len(messages)} error(s))",
    )
    return result
