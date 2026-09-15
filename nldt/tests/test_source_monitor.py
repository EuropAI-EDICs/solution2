"""Source monitor — probe, diff, process, recipe."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

NLDT = Path(__file__).resolve().parents[1]
FIXTURES = NLDT / "data" / "source-monitor" / "fixtures"


def test_diff_detects_page_cap_collapse():
    from services.source_monitor.diff import diff_probe

    probe = {
        "probedAt": "2026-09-15T12:00:00Z",
        "mode": "replay",
        "registryPath": "fixture",
        "registrySnapshot": {
            "bomen-demo": {
                "featureCount": 117012,
                "maxRecordCount": 1000,
                "fieldNames": ["OBJECTID", "SOORT"],
            }
        },
        "results": [
            {
                "sourceId": "bomen-demo",
                "probeStatus": "ok",
                "featureCount": 1000,
                "maxRecordCount": 1000,
                "fieldNames": ["OBJECTID", "SOORT"],
            }
        ],
    }
    diff = diff_probe(probe)
    assert diff["worstSeverity"] == "critical"
    assert diff["criticalCount"] == 1


def test_diff_ok_when_stable():
    from services.source_monitor.diff import diff_probe

    probe = {
        "registrySnapshot": {"a": {"featureCount": 792, "maxRecordCount": 1000, "fieldNames": ["OID"]}},
        "results": [
            {
                "sourceId": "a",
                "probeStatus": "ok",
                "featureCount": 792,
                "maxRecordCount": 1000,
                "fieldNames": ["OID"],
            }
        ],
    }
    assert diff_probe(probe)["worstSeverity"] == "ok"


def test_replay_run_trees_collapse(tmp_path):
    from services.source_monitor.run import run_monitor

    watchlist = {
        "registries": [
            {
                "id": "trees",
                "registryPath": str(FIXTURES / "registry-trees.json"),
                "sourceIds": ["bomen-demo"],
            }
        ]
    }
    wl = tmp_path / "wl.json"
    wl.write_text(json.dumps(watchlist), encoding="utf-8")
    out = tmp_path / "run"
    result = run_monitor(
        mode="replay",
        watchlist_path=wl,
        fixture_dir=FIXTURES,
        out_dir=out,
    )
    assert result["worstSeverity"] == "critical"
    assert result["criticalCount"] >= 1
    assert result["autoApply"] is False
    assert (out / "change-report.md").is_file()
    assert (out / "registry-patch-proposal.json").is_file()
    patch = json.loads((out / "registry-patch-proposal.json").read_text())
    assert patch["autoApply"] is False
    assert patch["operations"]
    assert result["validationReport"]["verdict"] == "needs_human"


def test_live_probe_mocked(monkeypatch):
    from services.source_monitor import probe as probe_mod

    class FakeResp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            if "returnCountOnly" in url:
                return FakeResp(200, {"count": 42})
            return FakeResp(
                200,
                {
                    "maxRecordCount": 2000,
                    "geometryType": "esriGeometryPoint",
                    "fields": [{"name": "OBJECTID"}],
                },
            )

    monkeypatch.setattr(probe_mod.httpx, "Client", FakeClient)
    result = probe_mod.probe_source_live(
        {
            "id": "mock-layer",
            "serviceUrl": "https://example.test/arcgis/rest/services/X/FeatureServer",
            "layerId": 0,
        }
    )
    assert result["probeStatus"] == "ok"
    assert result["featureCount"] == 42
    assert result["maxRecordCount"] == 2000


def test_process_and_recipe():
    from services.common.schema import load_recipe, validate_instance
    from services.process_adapter.handlers import describe_process, execute_local

    assert describe_process("source-monitor-probe")["id"] == "source-monitor-probe"
    recipe = load_recipe("source-monitor-run")
    validate_instance(recipe, "recipe.schema.json")
    out = execute_local("source-monitor-probe", {"mode": "replay"})
    assert out["summary"]["status"] == "ok"
    assert out["summary"]["criticalCount"] >= 1


def test_orchestrator_needs_human(monkeypatch, tmp_path):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from agents.orchestrator.graph import build_graph

    app = build_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "natural_language_request": "Check open data continuity",
            "recipe_id": "source-monitor-run",
            "resolved_inputs": {"mode": "replay"},
            "auto_approve_hitl": False,
            "register_pv": False,
            "export_3d": False,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert result["validation_report"]["verdict"] == "needs_human"
    assert result.get("execution") is None


def test_orchestrator_runs_with_auto_approve(monkeypatch, tmp_path):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from agents.orchestrator.graph import build_graph

    app = build_graph()
    run_id = str(uuid4())[:8]
    result = app.invoke(
        {
            "run_id": run_id,
            "natural_language_request": "Check open data continuity",
            "recipe_id": "source-monitor-run",
            "resolved_inputs": {"mode": "replay"},
            "auto_approve_hitl": True,
            "register_pv": False,
            "export_3d": False,
        },
        config={"configurable": {"thread_id": run_id}},
    )
    assert not result.get("error")
    assert result["execution"]["outputs"]["summary"]["criticalCount"] >= 1
    # Critic marks needs_human because of critical findings even after auto-approve HITL plan gate
    assert result["validation_report"]["verdict"] == "needs_human"
