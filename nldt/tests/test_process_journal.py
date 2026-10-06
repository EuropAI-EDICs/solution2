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
