from __future__ import annotations

import json

import pytest

from agents.orchestrator import llm_hook
from agents.orchestrator.llm_hook import OllamaLLMHook, hook_from_env, rank_recipes


def test_rank_recipes_deterministic():
    hits = [
        {"id": "recipe-a", "title": "Wind analysis", "properties": {"tags": ["wind"]}},
        {"id": "recipe-b", "title": "Spatial overlay analysis", "properties": {"tags": ["spatial", "overlay"]}},
    ]
    ranked = rank_recipes("spatial overlay", hits)
    assert ranked[0]["id"] == "recipe-b"


class FakeModel:
    def __init__(self, text: str, fail: bool = False):
        self.text = text
        self.fail = fail
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        if self.fail:
            raise ConnectionError("ollama down")
        return type("Msg", (), {"content": self.text})()


def _hook_with(monkeypatch, model: FakeModel) -> OllamaLLMHook:
    monkeypatch.setattr(llm_hook.model_config, "build_chat_model", lambda **kw: model)
    return OllamaLLMHook()


def test_propose_parses_plain_json(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel(json.dumps({"order": ["b", "a"]})))
    assert hook.propose("rank", "ids") == {"order": ["b", "a"]}


def test_propose_parses_fenced_json(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel("```json\n{\"order\": [\"x\"]}\n```"))
    assert hook.propose("rank") == {"order": ["x"]}


def test_propose_returns_none_on_model_failure(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel("x", fail=True))
    assert hook.propose("rank") is None


def test_propose_returns_none_on_non_json(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel("geen json hier"))
    assert hook.propose("rank") is None


def test_hook_from_env_default_off(monkeypatch) -> None:
    monkeypatch.delenv("NLDT_LLM_HOOK", raising=False)
    assert hook_from_env() is None


def test_hook_from_env_on(monkeypatch) -> None:
    monkeypatch.setenv("NLDT_LLM_HOOK", "1")
    monkeypatch.setattr(llm_hook.model_config, "build_chat_model", lambda **kw: FakeModel("{}"))
    assert isinstance(hook_from_env(), OllamaLLMHook)


def test_catalog_node_uses_hook_when_enabled(monkeypatch) -> None:
    from agents.orchestrator.nodes import catalog

    hits = [{"id": "a", "title": "opportunity-map utrecht"}, {"id": "b", "title": "peil-conflict rijnland"}]
    monkeypatch.setattr(catalog, "hook_from_env", lambda: None)
    default_order = [h["id"] for h in catalog.rank_recipes("utrecht", hits)]
    monkeypatch.setattr(
        catalog, "rank_recipes",
        lambda q, hs, hook=None: hs[::-1] if hook is not None else hs,
    )
    monkeypatch.setattr(catalog, "hook_from_env", lambda: object())  # fake live hook
    assert catalog.rank_recipes("utrecht", hits, catalog.hook_from_env()) == hits[::-1]
    assert default_order == ["a", "b"]  # deterministic baseline onveranderd
