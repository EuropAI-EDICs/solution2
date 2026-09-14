# eID Wallet W3 Implementation Plan (trust-policy gates + verified approver)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute phase W3 of [`nldt/16-eid-wallet-identity.md`](../../../nldt/16-eid-wallet-identity.md) §7: enforce identity gates at execution time (trustPolicy: LoA / roles / agent assurance / agent capability / human-only), record a wallet-verified **approver** alongside the executor, and update the doctrine docs.

**Architecture:** A trust-policy JSON (env `NLDT_TRUST_POLICY_FILE`) declares per-process gates. The process adapter enforces them after auth, before job creation — fail-closed (missing/invalid policy entries refuse rather than allow). Human executors are checked for LoA (low<substantial<high) and roles; agent executors for assurance (basic<attested<audited) AND that the process id is in the credential's `capabilities` (RP-side enforcement — the agent wallet's client-side check is convenience, not security); `humanOnly` gates refuse agents. An optional `X-nLDT-Approver-Token` header is introspected like the caller token and recorded as `actor.approver` (must be a *human* subject — the named person who takes responsibility for the run).

**Tech Stack:** Python/FastAPI, existing auth/claims machinery. **No new dependencies.**

**Spec:** nldt/16-eid-wallet-identity.md §6 (claims/governance), §7 W3, §10 decisions 1–10. Suite baseline: 182 (177 wallet + user WIP; record actuals).

## Global Constraints

- Repo root `/Users/marc/Projecten/ldttoolbox`; commands from `nldt/` with `PYTHONPATH=.`; venv `nldt/.venv`.
- **Fail-closed:** a gate on a process + no wallet claims → 403; invalid/unreadable policy file → 503 on gated paths (never silently ungated); claims missing required fields → 403 with machine-readable reason `{"detail": {"gate": ..., "reason": ...}}`.
- Backward compatible: **no policy file configured → behavior identical to today** (all existing tests untouched and green).
- Gates apply on the process adapter's execution path (covers HTTP + MCP servers, which call it with tokens). Recipes' riskLevel is NOT re-derived here — the policy file is the twin's declaration (W4 may derive defaults from recipe riskLevel).
- Actor dict grows additively: `{executor: claims}` and optionally `{approver: claims}`; annex passthrough unchanged (already copies the dict).
- Commits prefixed `BK-3/W3:`; per task; never `git add -A`.

---

### Task 1: Trust policy loader + execution gates

**Files:**
- Create: `nldt/services/common/trust_policy.py`
- Create: `nldt/data/trust-policy.example.json`
- Modify: `nldt/services/process_adapter/app.py` (gate check in `execute`)
- Test: `nldt/tests/test_trust_gates.py`

**Interfaces:**
- `load_trust_policy() -> dict | None` (env `NLDT_TRUST_POLICY_FILE`; absent → None; unreadable/invalid JSON → raises). `check_gate(policy, process_id, actor) -> None | raises GateDenied(reason: dict)`.
- Policy shape (documented in the example file):
```json
{
  "gates": {
    "breda-scan-query": {"minLoa": "substantial", "requiredRoles": ["policy-officer"]},
    "rijnland-peil-conflict": {"minLoa": "high", "humanOnly": true},
    "crosstrack-overlay": {"agentAssurance": "attested"}
  }
}
```
  Gate fields (all optional): `minLoa`, `requiredRoles`, `agentAssurance`, `humanOnly`. No `gates` entry for a process → ungated (even with a policy file).
- Ordering maps: LOA `low<substantial<high`; assurance `basic<attested<audited`.
- Agent capability enforcement: any gated process executed by an agent requires `process_id ∈ claims["capabilities"]` (in addition to the gate's own fields).
- `GateDenied` carries `{"gate": <process_id>, "reason": <code>}` where reason ∈ `missing_wallet_claims|loa_below_minimum|missing_role|agent_not_allowed|agent_capability_missing|agent_assurance_below_minimum`; FastAPI maps it to 403 with that dict as detail. Policy load errors (unreadable/invalid) → 503 `trust policy unavailable`.

- [ ] **Step 1: Failing tests** (`nldt/tests/test_trust_gates.py`):

```python
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.process_adapter.app import app as process_app

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
POLICY = {
    "gates": {
        "breda-scan-query": {"minLoa": "substantial", "requiredRoles": ["policy-officer"]},
        "rijnland-peil-conflict": {"minLoa": "high", "humanOnly": True},
        "crosstrack-overlay": {"agentAssurance": "attested"},
    }
}


def _run(client, process_id, headers=None):
    return client.post(
        f"/processes/{process_id}/execution",
        json={"inputs": {"question": "q"}, "backend": "local"},
        headers=headers or {},
    )


@pytest.fixture
def wallet_env(tmp_path, monkeypatch):
    import json as j

    p = tmp_path / "policy.json"
    p.write_text(j.dumps(POLICY))
    monkeypatch.setenv("NLDT_TRUST_POLICY_FILE", str(p))


HUMAN_OK = {
    "active": True,
    "subject_type": "human",
    "sub": "u1",
    "loa": "substantial",
    "org": "Provincie Test",
    "roles": ["policy-officer"],
    "exp": 9999999999,
}
HUMAN_LOW = {**HUMAN_OK, "loa": "low"}
AGENT_OK = {
    "active": True,
    "subject_type": "agent",
    "agentId": "beleidskompas-svc",
    "deployingOrg": "Provincie Test",
    "capabilities": ["breda-scan-query"],
    "assurance": "attested",
    "exp": 9999999999,
}
AGENT_WEAK = {**AGENT_OK, "assurance": "basic"}


def _auth(monkeypatch, claims):
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        return claims

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    return {"Authorization": "Bearer t"}


def test_gated_process_runs_for_qualified_human(wallet_env, monkeypatch):
    resp = _run(TestClient(process_app), "breda-scan-query", _auth(monkeypatch, HUMAN_OK))
    assert resp.status_code == 200
    assert resp.json()["actor"]["executor"]["sub"] == "u1"


def test_gated_process_denied_below_loa(wallet_env, monkeypatch):
    resp = _run(TestClient(process_app), "breda-scan-query", _auth(monkeypatch, HUMAN_LOW))
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason"] == "loa_below_minimum"


def test_gated_process_denied_without_wallet(wallet_env):
    resp = _run(TestClient(process_app), "breda-scan-query")
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason"] == "missing_wallet_claims"


def test_human_only_denies_agent(wallet_env, monkeypatch):
    resp = _run(TestClient(process_app), "rijnland-peil-conflict", _auth(monkeypatch, AGENT_OK))
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason"] == "agent_not_allowed"


def test_agent_gate_requires_capability_and_assurance(wallet_env, monkeypatch):
    ok = _run(TestClient(process_app), "crosstrack-overlay", _auth(monkeypatch, {**AGENT_OK, "capabilities": ["crosstrack-overlay"]}))
    assert ok.status_code == 200
    denied = _run(TestClient(process_app), "crosstrack-overlay", _auth(monkeypatch, {**AGENT_OK, "capabilities": ["other"]}))
    assert denied.status_code == 403
    assert denied.json()["detail"]["reason"] == "agent_capability_missing"
    weak = _run(TestClient(process_app), "crosstrack-overlay", _auth(monkeypatch, {**AGENT_OK, "capabilities": ["crosstrack-overlay"], "assurance": "basic"}))
    assert weak.status_code == 403
    assert weak.json()["detail"]["reason"] == "agent_assurance_below_minimum"


def test_ungated_process_unchanged(wallet_env):
    from pathlib import Path as P

    examples = P(__file__).resolve().parents[1] / "examples"
    resp = TestClient(process_app).post(
        "/processes/fetch-features/execution",
        json={"inputs": {"source": f"file://{examples / 'hex-points.geojson'}"}, "backend": "local"},
    )
    assert resp.status_code == 200
    assert "actor" not in resp.json()


def test_invalid_policy_fails_closed(tmp_path, monkeypatch):
    import json as j

    p = tmp_path / "policy.json"
    p.write_text("{not json")
    monkeypatch.setenv("NLDT_TRUST_POLICY_FILE", str(p))
    monkeypatch.setenv("NLDT_AUTH_MODE", "off")
    resp = _run(TestClient(process_app), "breda-scan-query")
    assert resp.status_code == 503
```

- [ ] **Step 2: RED** → **Step 3: implement** `trust_policy.py` (loader cached per-path mtime or per-call — keep per-call read, cheap for the testbed; document), `GateDenied` exception, gate logic with the ordering maps, and the check wired into `execute` after auth/before `create_job` (claims from `request.state.wallet_claims`; 403/503 mapping via exception handlers or inline raises). Create the example policy file (contents = POLICY above, with a comment-free JSON + README-pointer in the module docstring). → **Step 4: GREEN + full suite.** → **Step 5: commit** `BK-3/W3: trust-policy gates at execution (LoA/roles/agent assurance+capability, humanOnly) — fail closed`.

---

### Task 2: Wallet-verified approver (`X-nLDT-Approver-Token`)

**Files:**
- Modify: `nldt/services/process_adapter/app.py` (header introspection + actor.approver)
- Test: `nldt/tests/test_trust_gates.py` (append)

**Interfaces:**
- Optional header `X-nLDT-Approver-Token`: when present (and wallet mode active), introspect it like the caller token; MUST be `subject_type: human` and satisfy the same gate as the executor — else 403 (`approver_not_human` / approver gate reasons). Recorded as `actor.approver` (claims minus `active`); jobs.actor becomes `{"executor": ..., **({"approver": ...} if present)}`. Absent header → unchanged behavior.
- Rationale: an agent may execute a gated high-risk process only when a wallet-verified human approver token accompanies the request — the "named person takes responsibility" chain. (`humanOnly` gates still refuse agents even with an approver — approver ≠ executor.)

- [ ] **Step 1: Failing tests**: agent executor + valid human approver header on a gated process → 200 with `actor.approver.sub == "u1"`; agent + approver token that is an agent → 403 `approver_not_human`; agent + approver below gate LoA → 403. → **Step 2: RED** → **Step 3: implement** (reuse `introspect_wallet`; validate approver claims against the schema like the executor) → **Step 4: GREEN + suite** → **Step 5: commit** `BK-3/W3: wallet-verified approver header (agent runs need a named human approver)`.

---

### Task 3: Doctrine docs + example config + plan status

**Files:**
- Modify: `docs/GENAI_SEAMS.md` (technical annex: receipt-trail wording + note that executor/approver identity is wallet-anchored when wallet mode is on)
- Modify: `nldt/16-eid-wallet-identity.md` (W3 status line; trustPolicy block in §6 updated to the implemented file/env shape)
- Modify: `nldt/examples/twin-instance.example.json` + `nldt/03-building-blocks.md` (trustPolicy gains the `trustPolicyFile` pointer line, matching the implemented mechanism)
- Modify: `nldt/govchat/README.md` (§6 gains the gates + approver how-to with curl)

- [ ] Steps: apply the five doc edits (accurate to the implemented env/headers — no invented facts); full suite; live smoke optional (start nothing permanently: use TestClient-level only — skip live, W1's live chain precedent already covers service startup). Commit `BK-3/W3: docs — gates, approver chain, W3 done`.

## Definition of done

- Gates enforced fail-closed on the execution path; all seven denial reasons testable; no-policy behavior identical to today. (Task 1)
- Approver chain: agent executions can carry a wallet-verified human approver; non-human approvers refused. (Task 2)
- Docs honest (implemented shapes, not the earlier notional trustPolicy JSON); W3 status set; HITL-integration (orchestrator interrupt wiring) explicitly remains W4+. (Task 3)
