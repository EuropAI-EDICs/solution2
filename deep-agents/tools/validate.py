"""Critic tools: deterministic validation of built world-scene bundles.

Schema validation against the POC contract (poc/schemas/world-scene-spec.schema.json)
plus sanity checks — the V-level gate from the multi-agent plan: no artifact
is trusted without a validation report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

import journal

HERE = Path(__file__).resolve().parents[1]
REPO_ROOT = HERE.parent
RUNS_DIR = HERE / "runs"
SPEC_SCHEMA = REPO_ROOT / "poc" / "schemas" / "world-scene-spec.schema.json"


def validate_world_scene(scenario_run_id: str) -> dict[str, Any]:
    """Validate a built world-scene bundle: every spec against the world-scene-spec JSON schema, plus checks for unique ids, present deltas, gated Marble rendering and grounding stamps. Returns a pass/fail report with per-check evidence."""
    work = RUNS_DIR / f"{scenario_run_id}-worldscene"
    bundle_path = work / "world-scene-specs.json"
    if not bundle_path.is_file():
        raise FileNotFoundError(f"No bundle for '{scenario_run_id}' — run run_world_scene first.")

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    specs = bundle.get("specs", [])
    schema = json.loads(SPEC_SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, evidence: str) -> None:
        checks.append({"check": name, "passed": passed, "evidence": evidence})

    for spec in specs:
        errors = sorted(validator.iter_errors(spec), key=str)
        check(
            f"schema:{spec.get('id', '?')}",
            not errors,
            "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:3]) or "valid against world-scene-spec schema",
        )

    ids = [s.get("id") for s in specs]
    check("unique-spec-ids", len(ids) == len(set(ids)), f"{len(ids)} spec(s)")
    check(
        "deltas-present",
        all(isinstance(s.get("headlineDeltaKm2"), (int, float)) for s in specs),
        "every spec has headlineDeltaKm2" if specs else "no specs in bundle",
    )
    ungated = [s["id"] for s in specs if s.get("marble", {}).get("enabled") and not s.get("marble", {}).get("hitlRequired", True)]
    check("marble-gated", not ungated, "all generative rendering is HITL-gated" if not ungated else f"ungated: {ungated}")
    unstamped = [s.get("id") for s in specs if not s.get("groundingStamp")]
    check("grounding-stamps", not unstamped, "every spec carries a grounding stamp" if not unstamped else f"missing: {unstamped}")

    passed = all(c["passed"] for c in checks)
    result = {
        "scenarioRunId": scenario_run_id,
        "bundlePath": str(bundle_path),
        "generatedAt": bundle.get("generatedAt"),
        "specCount": len(specs),
        "passed": passed,
        "checks": checks,
    }
    journal.append(
        "tool_result",
        "critic",
        f"validate_world_scene('{scenario_run_id}') → {'PASS' if passed else 'FAIL'} ({sum(c['passed'] for c in checks)}/{len(checks)} checks)",
    )
    return result
