"""Intake tools (role 2 of the multi-agent plan): normalize a user brief into
a typed OpportunityMapRequest.

The intake agent (LLM) drafts the JSON from the conversation; these tools
give it the required shape and run the deterministic schema gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

import journal

HERE = Path(__file__).resolve().parents[1]
REPO_ROOT = HERE.parent
REQUEST_SCHEMA = REPO_ROOT / "poc" / "schemas" / "opportunity-map-request.schema.json"


def request_template() -> dict[str, Any]:
    """Return the OpportunityMapRequest template: required fields, per-field type/description/enum from the POC schema, so you can draft a normalized request from the user's brief."""
    schema = json.loads(REQUEST_SCHEMA.read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    template = {
        "required": schema.get("required", []),
        "fields": {
            name: {
                "type": p.get("type"),
                "description": p.get("description", ""),
                "enum": p.get("enum"),
            }
            for name, p in props.items()
        },
    }
    journal.append("tool_call", "intake", "request_template() opgevraagd")
    return template


def validate_request(request_json: str) -> dict[str, Any]:
    """Validate a drafted OpportunityMapRequest (JSON string) against the POC schema. Returns pass/fail with per-error evidence; fix the listed errors and re-validate."""
    try:
        request = json.loads(request_json)
    except json.JSONDecodeError as exc:
        journal.append("tool_result", "intake", f"validate_request() → FAIL (invalid JSON: {exc})")
        return {"passed": False, "errors": [f"invalid JSON: {exc}"], "requestId": None}
    schema = json.loads(REQUEST_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(request), key=str)
    result = {
        "passed": not errors,
        "errors": [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors[:8]],
        "requestId": request.get("id") if isinstance(request, dict) else None,
    }
    journal.append(
        "tool_result",
        "intake",
        f"validate_request('{result['requestId']}') → {'PASS' if result['passed'] else 'FAIL'} ({len(errors)} error(s))",
    )
    return result
