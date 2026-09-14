from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from agents.orchestrator.graph import build_graph
from services.process_adapter import jobs as job_store
from services.mcp_servers.client import ProcessClient


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class LocalProcessClient(ProcessClient):
    def execute(self, process_id, inputs, backend="local"):
        return job_store.create_job(process_id, inputs, backend=backend)


@pytest.fixture(autouse=True)
def patch_process_client(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    monkeypatch.setattr(
        "services.recipe_runner.ProcessClient",
        LocalProcessClient,
    )


def test_orchestrator_e2e():
    layer_a = f"file://{EXAMPLES / 'layer-a.geojson'}"
    layer_b = f"file://{EXAMPLES / 'layer-b.geojson'}"
    with (EXAMPLES / "aoi.geojson").open() as f:
        aoi = json.load(f)

    run_id = str(uuid4())[:8]
    app = build_graph()
    result = app.invoke(
        {
            "run_id": run_id,
            "natural_language_request": "spatial overlay analysis",
            "recipe_id": "spatial-overlay-analysis",
            "resolved_inputs": {
                "aoi": aoi,
                "layerAUri": layer_a,
                "layerBUri": layer_b,
            },
            "auto_approve_hitl": True,
            "register_pv": True,
            "export_3d": True,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert not result.get("error")
    assert result["validation_report"]["verdict"] == "pass"
    assert "statistics" in result["execution"]["outputs"]
    assert result.get("hybrid", {}).get("web3dContext")
