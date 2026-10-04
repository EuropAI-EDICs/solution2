"""Laya routing hint formatting (no Metal required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "deep-agents"
sys.path.insert(0, str(ROOT))

from laya_router import (  # noqa: E402
    format_routing_hint,
    nldt_orchestrator_questions,
    passes_confidence_gate,
    routing_confidence,
)


def test_questions_schema_has_poc_and_workflow():
    q = nldt_orchestrator_questions()
    assert "primary_poc" in q and q["primary_poc"]["type"] == "choice"
    assert "workflow" in q


def test_format_routing_hint_parses_laya_payload():
    payload = {
        "routing": {"model": "english", "reason": "English Latin text"},
        "answers": {
            "primary_poc": {"type": "choice", "choice": "utrecht", "confidence": 0.71},
            "workflow": {"type": "choice", "choice": "execute_demo", "confidence": 0.65},
            "needs_intake": {"type": "noul", "noul": 0.12, "confidence": 0.88},
            "needs_build": {"type": "noul", "noul": 0.91, "confidence": 0.91},
            "needs_critic": {"type": "noul", "noul": 0.55, "confidence": 0.55},
        },
    }
    hint = format_routing_hint(payload)
    assert "utrecht" in hint.lower() or "Utrecht" in hint
    assert "execute_demo" in hint or "World-scene" in hint
    assert "intake" in hint.lower() or "utrecht" in hint.lower()


def test_confidence_gate_blocks_low_routing_conf():
    payload = {
        "answers": {
            "primary_poc": {"type": "choice", "choice": "utrecht", "confidence": 0.53},
            "workflow": {"type": "choice", "choice": "execute_demo", "confidence": 0.88},
        }
    }
    min_c, _ = routing_confidence(payload)
    assert min_c == 0.53
    import os

    os.environ["LAYA_MIN_CONFIDENCE"] = "0.55"
    assert passes_confidence_gate(payload) is False
    os.environ["LAYA_MIN_CONFIDENCE"] = "0.50"
    assert passes_confidence_gate(payload) is True
    del os.environ["LAYA_MIN_CONFIDENCE"]
