"""Orchestrator tool: on-demand Laya routing advice (Apple Silicon MLX)."""

from __future__ import annotations

import json

import journal
from laya_router import format_routing_hint, laya_available, passes_confidence_gate, predict_routing, routing_confidence, confidence_threshold


def laya_advise_request(request: str) -> str:
    """Classify an nLDT user request with Laya (typed decisions, ~ms on MLX).

    Returns JSON with routing answers and a text hint for delegation order.
    No-op message when Laya is disabled or Metal is unavailable."""
    if not laya_available():
        return json.dumps(
            {
                "ok": False,
                "reason": "Laya uitgeschakeld of laya-mlx/Metal niet beschikbaar (DEEP_AGENT_LAYA, macOS arm64).",
            },
            ensure_ascii=False,
        )
    journal.append("tool_call", "orchestrator", f"laya_advise_request({request[:80]!r}…)")
    result = predict_routing(request)
    if result is None:
        journal.append("tool_result", "orchestrator", "laya_advise_request → geen resultaat")
        return json.dumps({"ok": False, "reason": "Laya predict mislukt"}, ensure_ascii=False)
    hint = format_routing_hint(result)
    min_conf, per_q = routing_confidence(result)
    threshold = confidence_threshold()
    if not passes_confidence_gate(result):
        journal.append(
            "tool_result",
            "orchestrator",
            f"laya_advise_request → onderdrukt (min conf {min_conf:.2f} < {threshold:.2f})",
        )
        return json.dumps(
            {
                "ok": False,
                "suppressed": True,
                "reason": f"confidence onder drempel {threshold:.2f}",
                "min_confidence": min_conf,
                "per_question": per_q,
                "hint": hint,
                "laya": result,
            },
            ensure_ascii=False,
            default=str,
        )
    journal.append("tool_result", "orchestrator", f"laya_advise_request → {hint.splitlines()[0][:120]}")
    return json.dumps(
        {"ok": True, "hint": hint, "min_confidence": min_conf, "threshold": threshold, "laya": result},
        ensure_ascii=False,
        default=str,
    )
