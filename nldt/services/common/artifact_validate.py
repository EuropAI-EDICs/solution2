"""Validate JSON instances against nLDT or PoC schemas (Phase 5.0)."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from services.common.prov import utc_now
from services.common.schema import load_schema


def validate_artifact(
    schema_name: str,
    instance: Any,
    *,
    artifact_id: str = "artifact",
    artifact_type: str = "process-output",
) -> dict[str, Any]:
    """Validate ``instance`` against ``schema_name``; return a structured result.

    ``schema_name`` may be a bare file under ``nldt/schemas/`` or
    ``nldt/schemas/poc/`` (e.g. ``poc/norm-card.schema.json``).
    """
    errors: list[dict[str, str]] = []
    try:
        schema = load_schema(schema_name)
        Draft202012Validator(schema).validate(instance)
        valid = True
        v0_status = "pass"
    except FileNotFoundError as exc:
        valid = False
        v0_status = "fail"
        errors.append({"id": "schema-missing", "detail": str(exc)})
    except ValidationError as exc:
        valid = False
        v0_status = "fail"
        errors.append({"id": "schema", "detail": exc.message})

    safe_id = "".join(c if c.isalnum() or c in "._-" else "-" for c in (artifact_id or "artifact"))
    if len(safe_id) < 3:
        safe_id = f"art-{safe_id}"
    report = {
        "id": f"VR-{safe_id[:40]}",
        "artifactId": safe_id,
        "artifactType": artifact_type,
        "levels": {
            "V0": {
                "status": v0_status,
                "checks": [
                    {
                        "id": e["id"],
                        "status": "fail" if not valid else "pass",
                        "detail": e.get("detail", ""),
                    }
                    for e in (errors or [{"id": "schema", "detail": "ok"}])
                ],
            },
            "V1": {"status": "not_applicable"},
            "V2": {"status": "not_applicable"},
            "V3": {"status": "not_applicable"},
            "V4": {"status": "not_applicable"},
        },
        "verdict": "pass" if valid else "fail",
        "evaluatorRun": "validate-artifact#v0",
        "evaluatedAt": utc_now(),
    }
    if errors:
        report["evidence"] = [{"ref": schema_name, "note": e["detail"]} for e in errors]

    return {
        "valid": valid,
        "schemaName": schema_name,
        "errors": errors,
        "validationReport": report,
    }
