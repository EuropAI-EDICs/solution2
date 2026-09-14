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


AGENT_ON_BREDA = {
    **AGENT_OK,
    "capabilities": ["breda-scan-query"],
    "loa": "substantial",
    "roles": ["policy-officer"],
}


def _approver_headers(auth_headers):
    return {**auth_headers, "X-nLDT-Approver-Token": "approver-t"}


def test_agent_with_human_approver_runs_gated_process(wallet_env, monkeypatch):
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        return HUMAN_OK if token == "approver-t" else {**AGENT_OK, "capabilities": ["crosstrack-overlay"]}

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    headers = _approver_headers({"Authorization": "Bearer t"})
    resp = _run(TestClient(process_app), "crosstrack-overlay", headers)
    assert resp.status_code == 200
    actor = resp.json()["actor"]
    assert actor["approver"]["sub"] == "u1"
    assert actor["executor"]["agentId"] == "beleidskompas-svc"
    assert "active" not in actor["approver"]


def test_agent_type_approver_token_denied(wallet_env, monkeypatch):
    headers = _approver_headers(_auth(monkeypatch, {**AGENT_OK, "capabilities": ["crosstrack-overlay"]}))
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        # executor introspection and approver introspection share the function;
        # distinguish by token value.
        if token == "approver-t":
            return {**AGENT_OK, "capabilities": ["crosstrack-overlay"]}
        return {**AGENT_OK, "capabilities": ["crosstrack-overlay"]}

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    resp = _run(TestClient(process_app), "crosstrack-overlay", headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason"] == "approver_not_human"


def test_approver_below_gate_loa_denied(wallet_env, monkeypatch):
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        return HUMAN_LOW if token == "approver-t" else AGENT_ON_BREDA

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    headers = _approver_headers({"Authorization": "Bearer t"})
    resp = _run(TestClient(process_app), "breda-scan-query", headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason"] == "approver_loa_below_minimum"


def test_no_approver_header_actor_shape_unchanged(wallet_env, monkeypatch):
    headers = _auth(monkeypatch, {**AGENT_OK, "capabilities": ["crosstrack-overlay"]})
    resp = _run(TestClient(process_app), "crosstrack-overlay", headers)
    assert resp.status_code == 200
    assert list(resp.json()["actor"].keys()) == ["executor"]


def test_invalid_policy_enum_fails_closed(tmp_path, monkeypatch):
    import json as j

    p = tmp_path / "policy.json"
    p.write_text(j.dumps({"gates": {"breda-scan-query": {"minLoa": "medium"}}}))
    monkeypatch.setenv("NLDT_TRUST_POLICY_FILE", str(p))
    monkeypatch.setenv("NLDT_AUTH_MODE", "off")
    resp = _run(TestClient(process_app), "breda-scan-query")
    assert resp.status_code == 503


def test_invalid_policy_fails_closed(tmp_path, monkeypatch):
    import json as j

    p = tmp_path / "policy.json"
    p.write_text("{not json")
    monkeypatch.setenv("NLDT_TRUST_POLICY_FILE", str(p))
    monkeypatch.setenv("NLDT_AUTH_MODE", "off")
    resp = _run(TestClient(process_app), "breda-scan-query")
    assert resp.status_code == 503
