"""Tests voor de generieke live-panel-tools (fase 3): Rijnland / MiniGIM /
Eindhoven — engines gemonkeypatcht (offline, snel); de echte engine-runs zijn
handmatig geverifieerd (rijnland 0,8 s · minigim 16 s · eindhoven ~2 min).

Run-conventie: cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages
../nldt/.venv/bin/python -m pytest tests/test_poc_live.py -q
"""

import json
from pathlib import Path

import pytest


@pytest.fixture()
def live_env(tmp_path, monkeypatch):
    import tools.poc_live as pl

    journal_events = []
    monkeypatch.setattr(pl.journal, "append",
                        lambda kind, agent, summary, **kw: journal_events.append(
                            (kind, agent, summary, kw)))
    calls = []

    def fake_engine(files: dict, rc: int = 0):
        """fake_run: schrijft `files` (relatief aan --out/cwd Werkmap) en geeft rc."""
        def run(cmd, capture_output, text, timeout, cwd, env):
            calls.append(cmd)
            flag = "--out" if "--out" in cmd else "--runs-dir"
            work = Path(cmd[cmd.index(flag) + 1])
            for rel, content in files.items():
                target = work / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            return type("R", (), {"returncode": rc, "stderr": "", "stdout": ""})()
        return run

    return {"monkeypatch": monkeypatch, "events": journal_events,
            "fake_engine": fake_engine, "calls": calls}


def test_rijnland_live_publishes_panel(live_env):
    from tools import poc_live as pl

    live_env["monkeypatch"].setattr(
        pl.subprocess, "run",
        live_env["fake_engine"]({
            "peilen.html": "<!doctype html><title>peilen</title>",
            "peilen.json": json.dumps({"stations": 315, "window": ["2026-08-28", "2026-09-11"],
                                        "computedBy": "poc-rijnland-peilen/0.1"}),
        }))
    out = pl.run_rijnland_live()
    assert out["poc"] == "rijnland"
    rid = out["runId"]
    panel = json.loads((pl.RUNS_DIR / rid / "panel.json").read_text())
    assert panel["poc"] == "rijnland" and panel["iframe"] == "panel.html"
    assert (pl.RUNS_DIR / rid / "panel.html").is_file()
    assert "315" in panel["cards"][0]["lines"][0]
    viz = live_env["events"][-1][3]["viz"]
    assert viz == {"kind": "rijnland-viz", "runId": rid, "poc": "rijnland"}


def test_minigim_live_finds_subdir_report(live_env):
    from tools import poc_live as pl

    live_env["monkeypatch"].setattr(
        pl.subprocess, "run",
        live_env["fake_engine"]({
            "20260101T000000Z-minigim-gebiedscheck/report.html": "<html>rapport</html>",
            "20260101T000000Z-minigim-gebiedscheck/run_summary.json": json.dumps(
                {"verdict": "pass", "label": "Breda Teteringen (pilot)",
                 "summary": {"itemCount": 74,
                              "bindingStatus": {"manual": 45, "auto": 14, "partial": 15}}}),
        }))
    out = pl.run_minigim_live()
    panel = json.loads((pl.RUNS_DIR / out["runId"] / "panel.json").read_text())
    assert panel["iframe"] == "panel.html"
    assert "74 items" in panel["cards"][0]["lines"][1]
    assert panel["cards"][0]["lines"][0] == "verdict: pass — Breda Teteringen (pilot)"


def test_eindhoven_live_cards_from_summary(live_env):
    from tools import poc_live as pl

    live_env["monkeypatch"].setattr(
        pl.subprocess, "run",
        live_env["fake_engine"]({
            "20260101T000000Z-eindhoven/report.html": "<html>rapport</html>",
            "20260101T000000Z-eindhoven/run_summary.json": json.dumps(
                {"verdict": "pass (V4 human: pending by design)",
                 "counts": {"bronregels": 33, "doelregels": 21}}),
        }))
    out = pl.run_eindhoven_live()
    panel = json.loads((pl.RUNS_DIR / out["runId"] / "panel.json").read_text())
    assert panel["poc"] == "eindhoven"
    assert "pending by design" in panel["cards"][0]["lines"][0]


def test_engine_failure_reports_error(live_env):
    from tools import poc_live as pl

    live_env["monkeypatch"].setattr(
        pl.subprocess, "run",
        live_env["fake_engine"]({}, rc=3))
    out = pl.run_rijnland_live()
    assert "error" in out and "rc=3" in out["error"]
    assert live_env["events"][-1][0] == "error"


def test_unknown_poc_raises():
    from tools.poc_live import run_poc_live

    with pytest.raises(KeyError):
        run_poc_live("crosstrack")  # bewust buiten scope (gebruikersbesluit)
