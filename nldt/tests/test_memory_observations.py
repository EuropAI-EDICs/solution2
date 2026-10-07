from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import observations as obs

PSEUDO_PATH = Path("steps.jsonl")  # relatief: trailId-machine-onafhankelijk


def _journal(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "steps.jsonl"
    p.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")
    return p


def test_journal_errors_extracted_with_provenance(tmp_path: Path) -> None:
    p = _journal(tmp_path, [
        {"ts": "10:00:00", "kind": "process_result", "agent": "compute-area-statistics", "status": "ok", "summary": "ok", "jobId": "j1"},
        {"ts": "10:00:01", "kind": "process_result", "agent": "run_opportunity_map", "status": "error", "summary": "KeyError: 'useCase'", "jobId": "j2"},
        {"ts": "10:00:02", "kind": "tool_call", "agent": "x", "status": "error", "summary": "geen process_result"},
        "geen json regel",
    ])
    out = obs.read_journal_errors(p)
    assert len(out) == 1
    o = out[0]
    assert o["type"] == "journal_error"
    assert o["provenance"]["jobId"] == "j2"
    assert "KeyError" in o["detail"]


def test_journal_missing_file_is_empty(tmp_path: Path) -> None:
    assert obs.read_journal_errors(tmp_path / "bestaatniet.jsonl") == []


def test_hitl_needs_human_from_validation_json(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    (runs / "run-a").mkdir(parents=True)
    (runs / "run-a" / "validation.json").write_text(json.dumps({"verdict": "needs_human", "artifactId": "bp2op"}), encoding="utf-8")
    (runs / "run-b").mkdir()
    (runs / "run-b" / "validation.json").write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")
    out = obs.read_hitl_observations(runs)
    assert len(out) == 1 and out[0]["provenance"]["runId"] == "run-a"


def test_hitl_missing_root_is_empty(tmp_path: Path) -> None:
    assert obs.read_hitl_observations(tmp_path / "runs") == []


def test_ledger_dict_and_list_forms(tmp_path: Path) -> None:
    scen = tmp_path / "scenario-runs" / "r1"
    scen.mkdir(parents=True)
    (scen / "proposals-rejected.json").write_text(json.dumps(
        {"author": "llm", "rejected": [{"ruleId": "s1", "reason": "schema"}], "note": "x"}), encoding="utf-8")
    run = tmp_path / "runs" / "r2"
    run.mkdir(parents=True)
    (run / "norm-llm-ledger.json").write_text(json.dumps([{"id": "NC-1", "reason": "unreachable"}]), encoding="utf-8")
    out = obs.read_ledger_observations(tmp_path)
    assert len(out) == 2
    assert all(o["type"] == "ledger_reject" for o in out)


def test_ledger_empty_rejected_list_is_no_observation(tmp_path: Path) -> None:
    scen = tmp_path / "scenario-runs" / "r1"
    scen.mkdir(parents=True)
    (scen / "proposals-rejected.json").write_text(json.dumps({"author": "llm", "rejected": [], "note": "x"}), encoding="utf-8")
    assert obs.read_ledger_observations(tmp_path) == []


def test_golden_drift_from_diff_file(tmp_path: Path) -> None:
    p = tmp_path / "golden-diff.json"
    p.write_text(json.dumps({"ranAt": "nu", "tracks": {
        "wind": {"pass": True, "iou": 1.0},
        "zon": {"pass": False, "iou": 0.99, "verdictsEqual": False},
    }}), encoding="utf-8")
    out = obs.read_golden_drift(p)
    assert len(out) == 1 and "zon" in out[0]["detail"]


def test_golden_drift_missing_file_is_empty(tmp_path: Path) -> None:
    assert obs.read_golden_drift(tmp_path / "bestaatniet.json") == []


def test_defaults_table_covers_all_types() -> None:
    assert set(obs.DEFAULTS) == {"journal_error", "hitl_needs_human", "ledger_reject", "golden_drift"}


def test_to_trail_fills_b10_defaults() -> None:
    observation = obs._obs("golden_drift", "poc/eval/golden-diff.json", "track zon: drift", {"runId": "r"})
    trail = obs.to_trail(observation)
    assert trail["why"] == obs.DEFAULTS["golden_drift"]["why"]
    assert trail["whatShouldChange"] == obs.DEFAULTS["golden_drift"]["whatShouldChange"]
    assert trail["trailId"].startswith("dt-")
