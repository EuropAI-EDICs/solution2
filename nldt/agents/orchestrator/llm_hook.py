from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Optional

from services.common import model_config

_JSON_FENCE_STARTS = ("```json", "```")


class LLMHook:
    """Optional GenAI seam (S1/S2/S3). Default: no-op."""

    def propose(self, prompt: str, schema_hint: str | None = None) -> Optional[dict[str, Any]]:
        return None


class OllamaLLMHook(LLMHook):
    """Live S1/S2-seam (harness-unificatie M2): temperatuur 0, JSON-gedwongen;
    faalt ALTIJD naar None zodat de deterministic paden (tag-overlap-rank,
    receptverplicht plan) de harness blijven dragen. Offline-gate per aanroep."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = model_config.build_chat_model(temperature=0)
        return self._model

    def propose(self, prompt: str, schema_hint: str | None = None) -> Optional[dict[str, Any]]:
        try:
            text = self._get_model().invoke(prompt).content
        except Exception as exc:  # onbereikbare Ollama e.d. — expliciet gelogd, geen raise
            print(f"[llm_hook] model onbereikbaar → deterministic fallback ({exc})", file=sys.stderr)
            return None
        text = str(text).strip()
        for fence in _JSON_FENCE_STARTS:
            if text.startswith(fence):
                text = text.strip("`").removeprefix("json").strip()
                break
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            print("[llm_hook] geen JSON in antwoord → deterministic fallback", file=sys.stderr)
            return None
        return parsed if isinstance(parsed, dict) else None


def hook_from_env() -> LLMHook | None:
    """Alleen een live hook als NLDT_LLM_HOOK=1; default uit (deterministisch)."""
    if os.environ.get("NLDT_LLM_HOOK") == "1":
        return OllamaLLMHook()
    return None


def rank_recipes(query: str, hits: list[dict[str, Any]], llm_hook: LLMHook | None = None) -> list[dict[str, Any]]:
    """S1: deterministic tag overlap ranking; LLM may re-rank if hook returns order."""
    if llm_hook:
        proposal = llm_hook.propose(f"Rank recipes for: {query}", "list of record ids")
        if proposal and "order" in proposal:
            order = {rid: i for i, rid in enumerate(proposal["order"])}
            return sorted(hits, key=lambda h: order.get(h.get("id", ""), 999))

    q_words = set(query.lower().split())

    def score(hit: dict[str, Any]) -> int:
        text = " ".join(
            [
                hit.get("title", ""),
                " ".join(hit.get("properties", {}).get("tags", [])),
                hit.get("id", ""),
            ]
        ).lower()
        return sum(1 for w in q_words if w in text)

    return sorted(hits, key=score, reverse=True)


def nl_to_plan_proposal(
    request: str,
    recipe_id: str,
    resolved_inputs: dict[str, Any],
    llm_hook: LLMHook | None = None,
) -> dict[str, Any] | None:
    """S2: LLM may propose AgentPlan fields; returns None to use deterministic planner."""
    if not llm_hook:
        return None
    return llm_hook.propose(
        f"Build agent plan for recipe {recipe_id}: {request}",
        "agent-plan.schema.json",
    )
