from __future__ import annotations

import json

from services.process_adapter import journal as pj


def test_append_writes_deep_agents_format(tmp_path, monkeypatch) -> None:
    path = tmp_path / "steps.jsonl"
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(path))
    pj.journal_process_event("opportunity-map-run", "ok", "verdict pass", durationMs=1234)
    entry = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["kind"] == "process_result"
    assert entry["agent"] == "opportunity-map-run"
    assert entry["summary"] == "verdict pass"
    assert entry["status"] == "ok"
    assert entry["durationMs"] == 1234
    assert len(entry["ts"].split(":")) == 3  # HH:MM:SS


def test_default_path_points_at_deep_agents_live(monkeypatch) -> None:
    monkeypatch.delenv("NLDT_JOURNAL_PATH", raising=False)
    assert pj.journal_path().name == "steps.jsonl"
    assert "deep-agents" in str(pj.journal_path())


def test_execute_local_journals_success_and_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(tmp_path / "steps.jsonl"))
    import pytest

    from services.process_adapter.handlers import execute_local

    out = execute_local("compute-area-statistics", {
        "features": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]}},
        ]},
    })
    assert "statistics" in out
    lines = (tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()
    ok_entry = json.loads(lines[-1])
    assert ok_entry["kind"] == "process_result" and ok_entry["status"] == "ok"

    with pytest.raises(Exception):
        execute_local("bestaat-niet", {})
    error_entry = json.loads((tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert error_entry["status"] == "error"


def test_journal_schema_matches_deep_agents_writer(tmp_path, monkeypatch) -> None:
    """Eén format: onze writer gebruikt dezelfde verplichte velden als de
    deep-agents-journal-writer (`deep-agents/journal.py::append`)."""
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(tmp_path / "steps.jsonl"))
    pj.journal_process_event("x", "ok", "hello")
    from pathlib import Path as _P

    da_journal_src = (_P(__file__).parents[2] / "deep-agents" / "journal.py").read_text(encoding="utf-8")
    assert "def append(" in da_journal_src and '"ts"' in da_journal_src and '"kind"' in da_journal_src
    required = {"ts", "kind", "agent", "summary"}
    entry = json.loads((tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert required <= set(entry)
