from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import consolidate, store


@pytest.fixture
def memory_env(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "trails"
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(d))
    return d


@pytest.fixture
def journal_with_error(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "steps.jsonl"
    p.write_text(json.dumps({
        "ts": "10:00:01", "kind": "process_result", "agent": "run_opportunity_map",
        "status": "error", "summary": "KeyError: 'useCase'", "jobId": "j2",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(p))
    return p


def test_consolidate_writes_trails_and_is_idempotent(memory_env, journal_with_error) -> None:
    assert consolidate.consolidate() == 0
    trails = store.load_trails()
    journal_trails = [t for t in trails if t["observation"]["type"] == "journal_error"]
    assert len(journal_trails) == 1 and journal_trails[0]["status"] == "open"
    count_before = len(trails)
    assert consolidate.consolidate() == 0
    assert len(store.load_trails()) == count_before  # dedup op trailId


def test_handle_sets_status_and_did_it_help(memory_env, journal_with_error, capsys) -> None:
    consolidate.consolidate()
    trail = store.load_trails()[0]
    rc = consolidate.main(["--handle", trail["trailId"], "--note", "opgelost door invoerfix"])
    assert rc == 0
    updated = store.load_trails()[0]
    assert updated["status"] == "handled" and updated["didItHelp"] == "opgelost door invoerfix"


def test_handle_requires_note(memory_env, journal_with_error) -> None:
    consolidate.consolidate()
    trail = store.load_trails()[0]
    with pytest.raises(SystemExit):
        consolidate.main(["--handle", trail["trailId"]])


def test_promote_sets_learning_level(memory_env, journal_with_error) -> None:
    consolidate.consolidate()
    trail = store.load_trails()[0]
    rc = consolidate.main(["--promote", trail["trailId"], "--level", "organisatie"])
    assert rc == 0
    assert store.load_trails()[0]["learningLevel"] == "organisatie"


def test_unknown_trail_returns_one(memory_env) -> None:
    assert consolidate.main(["--handle", "dt-00000000", "--note", "x"]) == 1
