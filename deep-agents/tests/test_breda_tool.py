"""Tests voor de Breda-scan-tool (fase 3): journal-viz, rid-naamgeving en
summary-parsing — de engine zelf wordt gemonkeypatcht (offline, snel);
de echte engine-run is handmatig geverifieerd (~35 s, verdict pass).

Run-conventie: cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages
../nldt/.venv/bin/python -m pytest tests/test_breda_tool.py -q
"""

import json
from pathlib import Path

import pytest


@pytest.fixture()
def scan_env(tmp_path, monkeypatch):
    """Fixture-dir als werkdirectory + stub-engine die artefacts schrijft."""
    import tools.breda as bt

    work = tmp_path / "20260101T000000Z-breda-scan"
    monkeypatch.setattr(bt, "RUNS_DIR", tmp_path)

    def fake_run(cmd, capture_output, text, timeout, cwd, env):
        work = Path(cmd[cmd.index("--out") + 1])
        work.mkdir(parents=True, exist_ok=True)
        (work / "run_summary.json").write_text(json.dumps(
            {"runId": work.name, "verdict": "pass", "nBuurten": 56,
             "nLandBuurten": 41, "degradations": 0}))
        (work / "value-scan.json").write_text(json.dumps({
            "values": {"democratic": {"label": "Democratic value"}},
            "rollup": {"democratic": {
                "top": [["Belcrum", 96.3]], "bottom": [["Hazeldonk", 2.2]], "n": 56}}},
            ensure_ascii=False))
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": "ok"})()

    calls = []
    monkeypatch.setattr(bt.subprocess, "run", lambda *a, **k: (calls.append(a), fake_run(*a, **k))[1])
    journal_events = []
    monkeypatch.setattr(bt.journal, "append",
                        lambda kind, agent, summary, **kw: journal_events.append((kind, agent, summary, kw)))
    return {"work": work, "calls": calls, "events": journal_events}


def test_run_breda_scan_publishes_viz_and_summary(scan_env):
    from tools.breda import run_breda_scan

    out = run_breda_scan()
    assert not out["scanRunId"].endswith("breda-scan"), "viz.runId blijft zónder suffix (dashboard plattt '-breda-scan' erachter)"
    assert out["verdict"] == "pass" and out["nBuurten"] == 56
    assert out["rollupTopBottom"]["democratic"]["top"] == [["Belcrum", 96.3]]
    kinds = [e[0] for e in scan_env["events"]]
    assert kinds == ["tool_call", "tool_result"]
    viz = scan_env["events"][1][3]["viz"]
    assert viz["kind"] == "breda-scan" and viz["runId"] == out["scanRunId"]
    from tools.breda import RUNS_DIR
    assert (RUNS_DIR / (out["scanRunId"] + "-breda-scan") / "run_summary.json").is_file()


def test_run_breda_scan_reports_engine_failure(scan_env, monkeypatch):
    from tools.breda import run_breda_scan

    def failing(cmd, capture_output, text, timeout, cwd, env):
        return type("R", (), {"returncode": 2, "stderr": "cache ontbreekt", "stdout": ""})()

    monkeypatch.setattr("subprocess.run", failing)
    out = run_breda_scan()
    assert "error" in out and "rc=2" in out["error"]
    assert scan_env["events"][-1][0] == "error"


def test_poc_demos_breda_is_scan_viz_with_execute_mode():
    from poc_demos import get_poc

    breda = get_poc("breda")
    assert breda["viz"] == "breda-scan"
    modes = {m["id"]: m for m in breda["modes"]}
    assert "scan_execute" in modes
    assert "run_breda_scan" in modes["scan_execute"]["template"]
