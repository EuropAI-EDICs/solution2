"""Phase 5.0 / 5.4 — contract bridge + uniform Critic."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from services.common.artifact_validate import validate_artifact
from services.common.schema import load_schema
from services.process_adapter.handlers import describe_process, execute_local


def test_poc_schemas_resolvable_via_bridge():
    for name in (
        "poc/norm-card.schema.json",
        "norm-card.schema.json",  # falls through to schemas/poc/
        "validation-report.schema.json",
    ):
        schema = load_schema(name)
        assert schema.get("title") or schema.get("$id")


def test_validate_artifact_process_pass():
    assert describe_process("validate-artifact")["id"] == "validate-artifact"
    recipe = json.loads(
        (Path(__file__).resolve().parents[1] / "recipes" / "breda-scan-qa.json").read_text()
    )
    out = execute_local(
        "validate-artifact",
        {
            "schemaName": "recipe.schema.json",
            "instance": recipe,
            "artifactId": "breda-scan-qa",
            "artifactType": "recipe",
        },
    )
    assert out["result"]["valid"] is True
    assert out["result"]["validationReport"]["verdict"] == "pass"


def test_validate_artifact_process_fail():
    out = execute_local(
        "validate-artifact",
        {
            "schemaName": "recipe.schema.json",
            "instance": {"id": "x"},
            "artifactId": "bad-recipe",
        },
    )
    assert out["result"]["valid"] is False
    assert out["result"]["validationReport"]["verdict"] == "fail"


def test_validate_artifact_helper_poc_schema():
    # Minimal structurally invalid norm-card should fail V0
    result = validate_artifact(
        "poc/norm-card.schema.json",
        {"id": "NC-1"},
        artifact_id="nc-test",
    )
    assert result["valid"] is False


def test_critic_uniform_poc_recipes():
    from agents.orchestrator.nodes.critic import validate_outputs

    cases = [
        (
            "utrecht-opportunity-map",
            {"summary": {"mode": "replay", "runDir": "/tmp/run"}},
            "pass",
            False,
        ),
        (
            "eindhoven-bp2op",
            {"summary": {"mode": "replay", "runDir": "/tmp/bp2op"}},
            "needs_human",
            True,
        ),
        (
            "rijnland-peil-conflict",
            {"summary": {"mode": "replay", "verdict": "pass"}},
            "pass",
            False,
        ),
        (
            "breda-five-value-scan",
            {"summary": {"mode": "replay", "runDir": "/tmp/breda"}},
            "pass",
            False,
        ),
        (
            "breda-gebiedsafweging",
            {
                "summary": {
                    "mode": "offline-fixtures",
                    "outDir": "/tmp/afw",
                    "verdict": "needs_human",
                    "nAccepted": 2,
                }
            },
            "needs_human",
            True,
        ),
    ]
    for recipe_id, outputs, expected_verdict, requires_hitl in cases:
        state = {
            "run_id": "t1",
            "recipe_id": recipe_id,
            "auto_approve_hitl": False,
            "agent_plan": {
                "id": "plan-1",
                "requiresHitl": requires_hitl,
                "riskLevel": "high" if requires_hitl else "medium",
            },
            "execution": {"recipeId": recipe_id, "outputs": outputs},
        }
        out = validate_outputs(state)
        assert out["validation_report"]["verdict"] == expected_verdict, recipe_id
        assert "V2" in out["validation_report"]["levels"]
        assert "V4" in out["validation_report"]["levels"]


def test_orchestrator_eindhoven_hitl_gates(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from agents.orchestrator.graph import build_graph

    app = build_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "natural_language_request": "Eindhoven bp2op",
            "recipe_id": "eindhoven-bp2op",
            "resolved_inputs": {"mode": "replay"},
            "auto_approve_hitl": False,
            "register_pv": False,
            "export_3d": False,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    # High-risk: stop before execute without auto-approve
    assert result["validation_report"]["verdict"] == "needs_human"
    assert result.get("execution") is None


def test_orchestrator_eindhoven_auto_approve_replay(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from unittest.mock import patch

    from agents.orchestrator.graph import build_graph
    from services.mcp_servers.client import ProcessClient
    from services.process_adapter import jobs as job_store

    class LocalClient(ProcessClient):
        def execute(self, process_id, inputs, backend="local"):
            return job_store.create_job(process_id, inputs, backend=backend)

    import services.recipe_runner as rr

    with patch.object(rr, "ProcessClient", LocalClient):
        app = build_graph()
        run_id = str(uuid4())[:8]
        result = app.invoke(
            {
                "run_id": run_id,
                "natural_language_request": "Eindhoven bp2op replay",
                "recipe_id": "eindhoven-bp2op",
                "resolved_inputs": {"mode": "replay"},
                "auto_approve_hitl": True,
                "register_pv": False,
                "export_3d": False,
            },
            config={"configurable": {"thread_id": run_id}},
        )
    assert not result.get("error")
    assert result["validation_report"]["verdict"] == "pass"
    assert result["validation_report"]["levels"]["V4"]["status"] == "pass"
