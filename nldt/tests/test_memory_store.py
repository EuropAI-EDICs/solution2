from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import store

OBS = {
    "type": "journal_error",
    "source": "steps.jsonl",
    "provenance": {"jobId": "job-1", "agent": "compute-area-statistics"},
    "detail": "compute-area-statistics: KeyError: 'features'",
}


@pytest.fixture
def memory_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "trails"
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(d))
    return d


def test_make_trail_validates_and_fills_defaults(memory_dir: Path) -> None:
    trail = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    assert trail["trailId"] == store.trail_id(OBS)
    assert trail["status"] == "open"
    assert trail["learningLevel"] == "operationeel"
    assert trail["whoDecides"] == "operator"
    assert trail["didItHelp"] is None
    assert trail["observation"]["provenance"]["jobId"] == "job-1"


def test_trail_id_is_stable_over_dict_order(memory_dir: Path) -> None:
    a = store.trail_id({"type": "t", "source": "s", "detail": "d"})
    b = store.trail_id({"detail": "d", "source": "s", "type": "t"})
    assert a == b and a.startswith("dt-")


def test_append_and_load_roundtrip(memory_dir: Path) -> None:
    trail = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    assert store.append_trails([trail]) == 1
    assert store.append_trails([trail]) == 0  # idempotent op trailId
    assert [t["trailId"] for t in store.load_trails()] == [trail["trailId"]]


def test_append_trails_invalid_record_raises(memory_dir: Path) -> None:
    bad = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    bad["status"] = "onbekend"
    with pytest.raises(Exception):
        store.append_trails([bad])
    assert store.load_trails() == []  # niets weggeschreven


def test_update_trail_edits_in_place(memory_dir: Path) -> None:
    trail = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    store.append_trails([trail])
    updated = store.update_trail(trail["trailId"], status="handled", did_it_help="opgelost", learning_level="organisatie")
    assert updated["status"] == "handled" and updated["didItHelp"] == "opgelost" and updated["learningLevel"] == "organisatie"
    assert store.load_trails()[0]["status"] == "handled"


def test_update_trail_unknown_returns_none(memory_dir: Path) -> None:
    assert store.update_trail("dt-00000000", status="handled") is None
