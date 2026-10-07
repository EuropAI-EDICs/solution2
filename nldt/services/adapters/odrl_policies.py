"""ODRL usage-policy-bibliotheek (dataspacebeleidsobjecten).

De drie vaste policies leven in nldt/schemas/dataspace-policies.json (in git —
beleid is contract). Pure lader; enforcement is een EDC-verantwoordelijkheid
zodra live — deze laag levert de beleidsobjecten.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.common.schema import validate_instance

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"
POLICIES_PATH = SCHEMAS_DIR / "dataspace-policies.json"
POLICY_SCHEMA = "dataspace-policy.schema.json"

CLASS_TO_POLICY = {
    "open": "policy-open",
    "internal": "policy-internal",
    "restricted": "policy-restricted",
}


def load_policies() -> dict[str, Any]:
    data = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
    policies = {p["@id"]: p for p in data["policies"]}
    for policy in policies.values():
        validate_instance(policy, POLICY_SCHEMA)
    return policies


def policy_for(access_class: str) -> dict[str, Any]:
    policies = load_policies()
    policy_id = CLASS_TO_POLICY.get(access_class)
    if policy_id is None:
        raise KeyError(f"onbekende accessClass: {access_class}")
    return policies[policy_id]


def policy_ids_referenced_by(offer: dict[str, Any]) -> list[str]:
    policy_id = CLASS_TO_POLICY.get(str(offer.get("accessClass")), "")
    return [policy_id] if policy_id else []
