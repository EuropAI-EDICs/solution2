"""Trust policy loader + execution gates (BK-3 / eID Wallet W3).

Policy source: file at env NLDT_TRUST_POLICY_FILE. No env var (or empty)
means no policy is configured and every process is ungated — behavior is
byte-identical to running without this module.

The policy is re-read per call rather than cached: this is a testbed-scale
service, a policy file is a few hundred bytes, and per-call reads let
operators flip gates without restarts. Revisit with an mtime-based cache
if this ever fronts real traffic.

Policy shape (see nldt/data/trust-policy.example.json):

    {"gates": {"<process_id>": {"minLoa": "substantial",
                                 "requiredRoles": ["policy-officer"],
                                 "agentAssurance": "attested",
                                 "humanOnly": true}}}

All gate fields are optional; a process without a "gates" entry is
ungated even when a policy file is configured. Ordering maps:
LOA low < substantial < high; agent assurance basic < attested < audited.

Agent executors on ANY gated process additionally require the process id
in their claims "capabilities" (RP-side enforcement, independent of the
agent wallet's client-side check).
"""

from __future__ import annotations

import json
import os

LOA_ORDER = {"low": 0, "substantial": 1, "high": 2}
ASSURANCE_ORDER = {"basic": 0, "attested": 1, "audited": 2}


class GateDenied(Exception):
    """Execution denied by a trust gate; carries {"gate": ..., "reason": ...}."""

    def __init__(self, gate: str, reason: str) -> None:
        self.gate = gate
        self.reason = reason
        super().__init__(f"gate {gate} denied: {reason}")


class TrustPolicyUnavailable(Exception):
    """The configured policy file is unreadable or not a valid policy object."""


def load_trust_policy() -> dict | None:
    """Load the trust policy from NLDT_TRUST_POLICY_FILE.

    Returns None when no policy file is configured. Raises
    TrustPolicyUnavailable when the file cannot be read, is not valid
    JSON, or is not a JSON object (fail closed).
    """
    path = os.environ.get("NLDT_TRUST_POLICY_FILE", "").strip()
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            policy = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise TrustPolicyUnavailable(str(exc)) from exc
    if not isinstance(policy, dict):
        raise TrustPolicyUnavailable("policy file must contain a JSON object")
    _validate_policy(policy)
    return policy


def _validate_policy(policy: dict) -> None:
    """Validate gate structure/enums at load time (fail closed -> 503, not a
    later KeyError -> 500 mid-request)."""
    gates = policy.get("gates", {})
    if not isinstance(gates, dict):
        raise TrustPolicyUnavailable('policy "gates" must be an object')
    for process_id, gate in gates.items():
        if not isinstance(gate, dict):
            raise TrustPolicyUnavailable(f"gate {process_id!r} must be an object")
        if "minLoa" in gate and gate["minLoa"] not in LOA_ORDER:
            raise TrustPolicyUnavailable(
                f"gate {process_id!r}: unknown minLoa {gate['minLoa']!r} "
                f"(expected one of {sorted(LOA_ORDER)})"
            )
        if "agentAssurance" in gate and gate["agentAssurance"] not in ASSURANCE_ORDER:
            raise TrustPolicyUnavailable(
                f"gate {process_id!r}: unknown agentAssurance {gate['agentAssurance']!r} "
                f"(expected one of {sorted(ASSURANCE_ORDER)})"
            )


def check_gate(policy: dict | None, process_id: str, claims: dict | None) -> None:
    """Raise GateDenied if the executor may not run this process.

    `claims` are the validated wallet claims from
    request.state.wallet_claims (None when auth mode did not produce
    them). A gated process without claims fails closed.
    """
    gate = (policy or {}).get("gates", {}).get(process_id)
    if gate is None:
        return  # ungated process: policy never changes behavior

    if not claims:
        raise GateDenied(process_id, "missing_wallet_claims")

    is_agent = claims.get("subject_type") == "agent"

    if is_agent:
        if gate.get("humanOnly"):
            raise GateDenied(process_id, "agent_not_allowed")
        if process_id not in (claims.get("capabilities") or []):
            raise GateDenied(process_id, "agent_capability_missing")
        min_assurance = gate.get("agentAssurance")
        if min_assurance:
            assurance = claims.get("assurance", "")
            if ASSURANCE_ORDER.get(assurance, -1) < ASSURANCE_ORDER[min_assurance]:
                raise GateDenied(process_id, "agent_assurance_below_minimum")

    min_loa = gate.get("minLoa")
    if min_loa and LOA_ORDER.get(claims.get("loa", ""), -1) < LOA_ORDER[min_loa]:
        raise GateDenied(process_id, "loa_below_minimum")

    required_roles = gate.get("requiredRoles")
    if required_roles:
        roles = set(claims.get("roles") or [])
        if not all(role in roles for role in required_roles):
            raise GateDenied(process_id, "missing_role")
