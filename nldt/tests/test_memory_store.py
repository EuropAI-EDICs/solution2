from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import observations, store

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


def test_live_hitl_observaties_uit_ledger(tmp_path: Path) -> None:
    """Request-zonder-verdict → open observatie; mét verdict → afgehandeld met comment."""
    ledger = tmp_path / "hitl-verdicts.jsonl"
    regels = [
        {"kind": "request", "interruptId": "i-1", "threadId": "nldt-live", "tool": "run_bp2op_transform", "argsSummary": "useCase=eindhoven"},
        {"kind": "request", "interruptId": "i-2", "threadId": "nldt-live", "tool": "run_bp2op_transform", "argsSummary": "useCase=eindhoven"},
        {"kind": "verdict", "interruptId": "i-2", "approved": False, "comment": "niet dit gebied", "operator": "jurist", "auto": False},
    ]
    ledger.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in regels) + "\n", encoding="utf-8")

    obs = observations.read_live_hitl_observations(ledger=ledger)
    assert len(obs) == 2
    open_obs = next(o for o in obs if o["provenance"]["interruptId"] == "i-1")
    klaar = next(o for o in obs if o["provenance"]["interruptId"] == "i-2")
    assert open_obs["type"] == "hitl_needs_human" and "run_bp2op_transform" in open_obs["detail"]
    assert "afgewezen" in klaar["detail"] and "niet dit gebied" in klaar["detail"]
    assert klaar["detail"].count("jurist") == 1


def test_live_hitl_observaties_zonder_ledger_leeg(tmp_path: Path) -> None:
    """Afwezige ledger → lege lijst, nooit een fout."""
    assert observations.read_live_hitl_observations(ledger=tmp_path / "ontbreekt.jsonl") == []


def test_live_hitl_dubbel_verdict_collapsed(tmp_path: Path) -> None:
    """Dubbel verdict (server + resume.py) per interruptId → één afgehandelde observatie (last-wins)."""
    ledger = tmp_path / "hitl-verdicts.jsonl"
    regels = [
        {"kind": "request", "interruptId": "i-9", "threadId": "nldt-live", "tool": "run_bp2op_transform", "argsSummary": "useCase=utrecht"},
        {"kind": "verdict", "interruptId": "i-9", "approved": False, "comment": "eerste", "operator": "jurist", "auto": False},
        {"kind": "verdict", "interruptId": "i-9", "approved": True, "comment": "tweede", "operator": "robot", "auto": True},
    ]
    ledger.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in regels) + "\n", encoding="utf-8")

    obs = observations.read_live_hitl_observations(ledger=ledger)
    assert len(obs) == 1
    assert "goedgekeurd" in obs[0]["detail"] and "tweede" in obs[0]["detail"]
    assert obs[0]["provenance"] == {"threadId": "nldt-live", "interruptId": "i-9"}


def test_live_hitl_torn_regel_crasht_niet(tmp_path: Path) -> None:
    """Eindreview: een torn regel (halve JSON, crash midden in een append) mag de
    observatie-lezing niet laten crashen; de gezonde regels overleven."""
    ledger = tmp_path / "hitl-verdicts.jsonl"
    goed = json.dumps(
        {"kind": "request", "interruptId": "i-1", "threadId": "nldt-live",
         "tool": "run_bp2op_transform", "argsSummary": "useCase=eindhoven"},
        ensure_ascii=False,
    )
    torn = '{"kind": "verdict", "inter'  # halfweg afgebroken schrijfactie
    ledger.write_text(f"{goed}\n{torn}\n", encoding="utf-8")

    obs = observations.read_live_hitl_observations(ledger=ledger)
    assert len(obs) == 1
    assert obs[0]["provenance"] == {"threadId": "nldt-live", "interruptId": "i-1"}
    assert "hitl-pending" in obs[0]["detail"]
