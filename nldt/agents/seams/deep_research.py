"""S10 — Deep Research seam (propose-only).

Optional harness: LangChain Deep Agents (`create_deep_agent`) for open-ended
source gathering. Output is always a schema-gated ``ResearchBrief``. The
brief may feed S7 digests (series hints / mutation *hints*) — it never
runs scans, applies mutations, or stamps its own identity.

Enable live harness with ``NLDT_DEEP_RESEARCH=1`` and optional package
``deepagents``. Default / offline: deterministic stub brief.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any
from uuid import uuid4

from services.common.schema import validate_instance

SCHEMA = "research-brief.schema.json"


def _stamp(harness: str) -> str:
    return f"deep-research#{harness}"


def _stub_brief(topic: str, hints: list[dict[str, Any]] | None) -> dict[str, Any]:
    series = [
        h.get("seriesId")
        for h in (hints or [])
        if isinstance(h, dict) and h.get("seriesId")
    ][:6]
    brief = {
        "briefId": f"RB-{uuid4().hex[:10]}",
        "topic": topic[:500],
        "findings": [
            {
                "claim": (
                    "Ageing and heat-stress narratives dominate 2050 urban "
                    "value debates in Dutch mid-size cities."
                ),
                "sourceHint": "CBS KWB 65+ trends; KNMI regional climate",
                "confidence": 0.55,
            },
            {
                "claim": (
                    "Roof solar saturation is a plausible economic-weight "
                    "driver where municipal projections approach 100%."
                ),
                "sourceHint": "CBS percentageWoningenMetZonnestroom",
                "confidence": 0.5,
            },
        ],
        "suggestedSeriesIds": series,
        "suggestedMutationHints": [
            {
                "aspect": "social_rule",
                "rationale": "Calibrate heat focus to projected 65+ share.",
            },
            {
                "aspect": "spatial_weights",
                "rationale": "Emphasise green cover and park distance under heat.",
            },
        ],
        "citations": [],
        "proposedBy": _stamp("stub"),
        "harness": "stub",
    }
    return brief


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _gate(draft: dict[str, Any], *, harness: str) -> tuple[dict[str, Any] | None, list[dict]]:
    """Stamp identity, validate schema; reject into ledger on failure."""
    rejected: list[dict] = []
    out = dict(draft)
    out["proposedBy"] = _stamp(harness)
    out["harness"] = harness
    if not out.get("briefId"):
        out["briefId"] = f"RB-{uuid4().hex[:10]}"
    try:
        validate_instance(out, SCHEMA)
    except Exception as exc:  # noqa: BLE001 — schema errors are ledger material
        rejected.append({
            "briefId": out.get("briefId"),
            "reden": f"schema: {exc}",
            "harness": harness,
        })
        return None, rejected
    return out, rejected


def _try_deepagents(topic: str, hints: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Best-effort Deep Agents call; returns raw draft dict or None."""
    if os.environ.get("NLDT_DEEP_RESEARCH", "").strip() not in ("1", "true", "yes"):
        return None
    try:
        from deepagents import create_deep_agent  # type: ignore
    except ImportError:
        return None

    series_note = ", ".join(
        h.get("seriesId", "") for h in (hints or []) if isinstance(h, dict)
    )[:400]
    system = (
        "You are a research assistant for Dutch Local Digital Twin what-if "
        "scenarios. Propose ONLY a single JSON object matching ResearchBrief "
        "(briefId, topic, findings[], suggestedSeriesIds[], "
        "suggestedMutationHints[], citations[]). Do not execute analyses. "
        "Do not invent series IDs that were not hinted. No markdown prose."
    )
    user = f"Topic: {topic}\nKnown series hints: {series_note or '(none)'}"

    try:
        agent = create_deep_agent()
        # deepagents returns a compiled graph; invoke with messages when available
        result = agent.invoke({"messages": [{"role": "user", "content": f"{system}\n\n{user}"}]})
        messages = result.get("messages") if isinstance(result, dict) else None
        text = ""
        if messages:
            last = messages[-1]
            text = getattr(last, "content", None) or (
                last.get("content") if isinstance(last, dict) else str(last)
            )
        elif isinstance(result, dict):
            text = json.dumps(result)
        else:
            text = str(result)
        return _extract_json_object(text if isinstance(text, str) else str(text))
    except Exception:  # noqa: BLE001 — loud fallback to stub
        return None


def propose_research_brief(
    topic: str,
    *,
    lake_series_hints: list[dict[str, Any]] | None = None,
    force_stub: bool = False,
) -> tuple[dict[str, Any] | None, list[dict]]:
    """Propose a ResearchBrief behind the S10 gate.

    Returns ``(brief_or_None, rejected_ledger_entries)``.
    """
    topic = (topic or "").strip() or "Breda five-value horizon research"
    if force_stub or os.environ.get("NLDT_OFFLINE") == "1":
        brief, rejected = _gate(_stub_brief(topic, lake_series_hints), harness="stub")
        return brief, rejected

    draft = None if force_stub else _try_deepagents(topic, lake_series_hints)
    if draft is None:
        brief, rejected = _gate(_stub_brief(topic, lake_series_hints), harness="stub")
        return brief, rejected

    brief, rejected = _gate(draft, harness="deepagents")
    if brief is None:
        # schema-failed deep output → stub floor (loud deterministic fallback)
        fallback, more = _gate(_stub_brief(topic, lake_series_hints), harness="stub")
        return fallback, rejected + more
    return brief, rejected
