"""Tests voor de crosstrack-tool (fase 3, Utrecht Plane C): journal-viz,
summary-contract en foutpad — engine gemonkeypatcht (offline, snel); de echte
engine-run is handmatig geverifieerd (~14 s, verdict pass).

Run-conventie: cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages
../nldt/.venv/bin/python -m pytest tests/test_crosstrack_tool.py -q
"""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture()
def xt_env(tmp_path, monkeypatch):
    import tools.crosstrack as ct

    journal_events = []

    monkeypatch.setattr(ct, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(ct.journal, "append",
                        lambda kind, agent, summary, **kw: journal_events.append(
                            (kind, agent, summary, kw)))

    def fake_engine(files: dict, rc: int = 0):
        def run(cmd, capture_output, text, timeout, cwd, env):
            out_root = Path(cmd[cmd.index("--out") + 1])
            for rel, content in files.items():
                target = out_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            return type("R", (), {"returncode": rc, "stderr": "", "stdout": ""})()
        return run

    return {"monkeypatch": monkeypatch, "events": journal_events,
            "fake_engine": fake_engine}


def test_run_crosstrack_overlay_publishes_viz_and_summary(xt_env):
    from tools.crosstrack import run_crosstrack_overlay

    xt_env["monkeypatch"].setattr(
        subprocess, "run",
        xt_env["fake_engine"]({
            "crosstrack-report.json": json.dumps({
                "tracks": [{"useCase": "wind", "finalAreaKm2": 859.5},
                            {"useCase": "zon", "finalAreaKm2": 1167.9},
                            {"useCase": "bos", "finalAreaKm2": 23.9}],
                "conflicts": [{"pair": ["wind", "zon"], "areaKm2": 845.4,
                                "geometryFile": "conflicts/wind-x-zon.geojson"}],
                "sharedZones": [{"zoneId": "groene_contour", "areaKm2": 23.9,
                                  "perTrack": [{"useCase": "bos", "shareOfZone": 100.0}]}],
                "verdict": "pass",
            }, ensure_ascii=False),
        }))
    out = run_crosstrack_overlay()
    assert out["crosstrackRunId"].endswith("crosstrack")
    assert out["verdict"] == "pass"
    assert out["tracks"][0]["useCase"] == "wind"
    assert out["conflicts"][0]["pair"] == "wind × zon"
    assert out["shared"][0]["zone"] == "groene_contour"
    kinds = [e[0] for e in xt_env["events"]]
    assert kinds == ["tool_call", "tool_result"]
    viz = xt_env["events"][1][3]["viz"]
    assert viz["kind"] == "crosstrack-viz" and viz["poc"] == "crosstrack"
    assert viz["runId"] == out["crosstrackRunId"]


def test_run_crosstrack_overlay_reports_engine_failure(xt_env):
    from tools.crosstrack import run_crosstrack_overlay

    xt_env["monkeypatch"].setattr(
        subprocess, "run",
        xt_env["fake_engine"]({}, rc=1))
    out = run_crosstrack_overlay()
    assert "error" in out and "rc=1" in out["error"]
    assert xt_env["events"][-1][0] == "error"
