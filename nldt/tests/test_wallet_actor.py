from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from services.process_adapter.app import app as process_app
from services.run_annex import build_run_annex

AGENT_CLAIMS = {
    "subject_type": "agent",
    "agentId": "beleidskompas-svc",
    "deployingOrg": "Provincie Test",
    "capabilities": ["breda-scan-query"],
    "assurance": "attested",
    "exp": 9999999999,
}

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_execute_records_wallet_actor(monkeypatch):
    import services.common.auth as auth

    async def fake(token: str) -> dict:
        return {"active": True, **AGENT_CLAIMS}

    monkeypatch.setattr(auth, "introspect_wallet", fake)
    monkeypatch.setenv("NLDT_AUTH_MODE", "wallet")
    client = TestClient(process_app)
    job = client.post(
        "/processes/fetch-features/execution",
        json={"inputs": {"source": f"file://{EXAMPLES / 'hex-points.geojson'}"}, "backend": "local"},
        headers={"Authorization": "Bearer t"},
    )
    assert job.status_code == 200
    actor = job.json()["actor"]
    assert actor["executor"]["agentId"] == "beleidskompas-svc"
    assert actor["executor"]["deployingOrg"] == "Provincie Test"


def test_execute_without_wallet_auth_has_no_actor():
    client = TestClient(process_app)
    job = client.post(
        "/processes/fetch-features/execution",
        json={"inputs": {"source": f"file://{EXAMPLES / 'hex-points.geojson'}"}, "backend": "local"},
    ).json()
    assert "actor" not in job


def test_annex_carries_actor():
    execution = {
        "recipeId": "beleidskompas-omgevingsanalyse",
        "steps": [{"stepId": "s", "processId": "p", "jobId": "j", "prov": {}}],
        "outputs": {},
        "actor": {"executor": AGENT_CLAIMS},
    }
    annex = build_run_annex([execution])
    assert annex["runs"][0]["actor"]["executor"]["agentId"] == "beleidskompas-svc"
