from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("A2A_SIM_AUTH", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "sim-toolbox-token")
    monkeypatch.setenv("A2A_SIM_MODE", "simulate")


def test_agent_card_declares_toolbox_bearer():
    from agents.card import build_agent_card

    card = build_agent_card("breda")
    assert "euLdtToolboxBearer" in card.security_schemes
    assert card.security_schemes["euLdtToolboxBearer"].http_auth_security_scheme.scheme == "bearer"
    assert len(card.security_requirements) >= 1


def test_auth_middleware_blocks_jsonrpc_without_token():
    from fastapi.testclient import TestClient

    from agents.server import create_app

    os.environ["A2A_SIM_AUTH"] = "static"
    os.environ["NLDT_STATIC_TOKENS"] = "sim-toolbox-token"
    client = TestClient(create_app("breda"))
    resp = client.post("/a2a/jsonrpc", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert resp.status_code == 401
    ok = client.post(
        "/a2a/jsonrpc",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": "Bearer sim-toolbox-token"},
    )
    assert ok.status_code != 401


def test_architecture_prompts_exist():
    base = Path(__file__).resolve().parents[1] / "orchestrator" / "prompts"
    for name in ("orchestrator.md", "scenario_analist.md", "interpretatie.md"):
        assert (base / name).is_file()


def test_poc_executor_rejects_deep_mode_on_mesh():
    import asyncio

    from agents.poc_executor import _build_payload
    from agents.registry import agent_spec

    spec = agent_spec("breda")
    with pytest.raises(RuntimeError, match="orchestrator"):
        asyncio.run(_build_payload("x", spec, "task-1", "deep"))
