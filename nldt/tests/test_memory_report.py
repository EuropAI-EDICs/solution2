from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import report, store

TRAIL = {
    "trailId": "dt-11111111", "observation": {"type": "journal_error", "source": "s", "detail": "d"},
    "what": "w", "why": "o", "whatShouldChange": "v", "whoDecides": "operator",
    "didItHelp": None, "learningLevel": "operationeel", "status": "open", "createdAt": "2026-10-07T00:00:00+00:00",
}


def _trail(**over) -> dict:
    t = json.loads(json.dumps(TRAIL))
    t.update(over)
    return t


def test_promote_candidates_threshold_and_level() -> None:
    trails = [_trail(trailId=f"dt-{i:08d}", observation={"type": "journal_error", "source": "s", "detail": "d"}) for i in range(3)]
    trails.append(_trail(trailId="dt-99999999", observation={"type": "hitl_needs_human", "source": "s", "detail": "d"}))
    trails.append(_trail(trailId="dt-99999998", observation={"type": "journal_error", "source": "s", "detail": "d"}, status="handled"))
    assert report.promote_candidates(trails) == ["operationeel:journal_error"]


def test_promote_candidates_ignores_non_operational() -> None:
    trails = [_trail(trailId=f"dt-{i:08d}", observation={"type": "journal_error", "source": "s", "detail": "d"}, learningLevel="organisatie") for i in range(3)]
    assert report.promote_candidates(trails) == []


def test_report_main_runs_on_empty_store(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(tmp_path / "trails"))
    assert report.main([]) == 0
    assert "0 trail-record(s)" in capsys.readouterr().out


def test_report_main_lists_open_items(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(tmp_path / "trails"))
    store.append_trails([_trail()])
    assert report.main([]) == 0
    out = capsys.readouterr().out
    assert "open (1)" in out and "dt-11111111" in out
