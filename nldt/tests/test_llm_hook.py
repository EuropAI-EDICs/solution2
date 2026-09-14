from __future__ import annotations

from agents.orchestrator.llm_hook import rank_recipes


def test_rank_recipes_deterministic():
    hits = [
        {"id": "recipe-a", "title": "Wind analysis", "properties": {"tags": ["wind"]}},
        {"id": "recipe-b", "title": "Spatial overlay analysis", "properties": {"tags": ["spatial", "overlay"]}},
    ]
    ranked = rank_recipes("spatial overlay", hits)
    assert ranked[0]["id"] == "recipe-b"
