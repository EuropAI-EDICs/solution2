"""Critic checks for S7 hybrid scenario author."""

from __future__ import annotations

from agents.orchestrator.nodes.critic import _validate_poc_outputs


def test_critic_hybrid_floor_and_explorer():
    outputs = {
        "proposals": {
            "author": "hybrid",
            "accepted": [
                {
                    "id": "SC-A",
                    "proposedBy": "deterministic-scenario-author#poc-v1-auto",
                    "mutations": [{"ruleId": "FR-1", "action": "drop"}],
                },
                {
                    "id": "SC-B",
                    "proposedBy": "llm-proposal#test-model",
                    "mutations": [{"ruleId": "FR-2", "action": "drop"}],
                },
            ],
            "rejected": [],
            "acceptedCount": 2,
        }
    }
    checks, _v2, verdict, _ev = _validate_poc_outputs("utrecht-scenario-author", outputs)
    ids = {c["id"]: c for c in checks}
    assert verdict == "pass"
    assert ids["s7-proposals"]["status"] == "pass"
    assert ids["s7-hybrid-floor"]["status"] == "pass"
    assert ids["s7-llm-explorer"]["status"] == "pass"
    assert "1" in ids["s7-llm-explorer"].get("detail", "")


def test_critic_hybrid_fails_without_det_floor():
    outputs = {
        "proposals": {
            "author": "hybrid",
            "accepted": [
                {
                    "id": "SC-B",
                    "proposedBy": "llm-proposal#test-model",
                    "mutations": [{"ruleId": "FR-2", "action": "drop"}],
                },
            ],
            "rejected": [],
            "acceptedCount": 1,
        }
    }
    checks, _v2, verdict, _ev = _validate_poc_outputs("utrecht-scenario-author", outputs)
    ids = {c["id"]: c for c in checks}
    assert verdict == "fail"
    assert ids["s7-hybrid-floor"]["status"] == "fail"


def test_critic_series_grounding():
    outputs = {
        "proposals": {
            "author": "auto",
            "accepted": [
                {
                    "id": "SC-1",
                    "proposedBy": "deterministic-scenario-author#poc-v1-auto",
                }
            ],
            "rejected": [],
            "acceptedCount": 1,
            "lakeSeriesHints": [{"seriesId": "knmi-daily-neerslag-260"}],
            "claimedSeriesIds": ["knmi-daily-neerslag-260", "ghost-series"],
        }
    }
    checks, _v2, verdict, _ev = _validate_poc_outputs("utrecht-scenario-author", outputs)
    ids = {c["id"]: c for c in checks}
    assert verdict == "fail"
    assert ids["s7-series-grounding"]["status"] == "fail"
