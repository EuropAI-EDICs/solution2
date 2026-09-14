from __future__ import annotations

from typing import Any, Callable, Optional


class LLMHook:
    """Optional GenAI seam (S1/S2/S3). Default: no-op."""

    def propose(self, prompt: str, schema_hint: str | None = None) -> Optional[dict[str, Any]]:
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
