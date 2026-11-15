"""gent-life-event-run wrapper: replay op run-dir, execute via echte CLI (offline)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
POC_GENT = NLDT_ROOT.parent / "poc-gent"
for _p in (str(NLDT_ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from services.process_adapter import poc_handlers  # noqa: E402
from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def test_gent_replay_leest_nieuwste_run_dir(tmp_path, monkeypatch):
    run = tmp_path / "runs" / "20261102T121500Z-gent-transactional-fien"
    run.mkdir(parents=True)
    (run / "run.json").write_text(
        json.dumps({"runId": "20261102T121500Z-gent-transactional-fien", "routing": {"outcome": "indienen"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(poc_handlers, "POC_GENT", tmp_path)
    out = execute_poc_process("gent-life-event-run", {"mode": "replay"})
    s = out["summary"]
    assert s["mode"] == "replay"
    assert s["runDir"] == str(run)
    assert s["runId"] == "20261102T121500Z-gent-transactional-fien"
    assert s["outcome"] == "indienen"


def test_gent_execute_draait_echte_replay_cli():
    """Deterministisch en offline: de CLI repstudt fase 1+2+3 uit het gecommitte pakket."""
    out = execute_poc_process(
        "gent-life-event-run",
        {"mode": "execute", "package": "gent-mobiliteit-ondernemer", "persona": "sanne"},
    )
    s = out["summary"]
    assert s["mode"] == "execute"
    assert Path(s["runDir"]).is_dir()
    assert (Path(s["runDir"]) / "run.json").is_file()
    assert s["runId"]


def test_gent_onbekende_mode_geweigerd():
    try:
        execute_poc_process("gent-life-event-run", {"mode": "anders"})
    except ValueError:
        pass
    else:
        raise AssertionError("onbekende mode moet geweigerd worden")
