"""Gedeelde modelconfig voor nldt + deep-agents (harness-unificatie M2).

Één plek voor modelnamen en -bouw; alleen lokale Ollama of expliciete
`zai:`-prefix (Z.ai GLM via het Anthropic-compatibele endpoint). Ollama's
betaalde cloud-tier wordt geweigerd.
"""
from __future__ import annotations

import os
from typing import Any

ZAI_ANTHROPIC_URL = "https://api.z.ai/api/anthropic"


def orchestrator_model_name() -> str:
    return os.environ.get("DEEP_AGENT_MODEL", "gemma4:31b-mlx")


def subagent_model_name() -> str:
    return os.environ.get("DEEP_AGENT_SUBMODEL", "gemma4:12b-mlx")


def is_zai(model: str) -> bool:
    return model.startswith("zai:")


def build_chat_model(spec: str | None = None, **overrides: Any):
    name = spec or orchestrator_model_name()
    if "cloud" in name and not is_zai(name):
        raise SystemExit(
            f"Model '{name}' routeert naar Ollama's betaalde cloud — alleen lokale "
            "modellen. Gebruik `zai:glm-...` of een lokaal model uit `ollama list`."
        )
    if is_zai(name):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise SystemExit("langchain-anthropic ontbreekt in deze omgeving.") from exc
        key = os.environ.get("ZAI_API_KEY")
        if not key:
            raise SystemExit(f"Model '{name}' vereist ZAI_API_KEY.")
        kwargs: dict[str, Any] = dict(
            model=name.removeprefix("zai:"),
            base_url=ZAI_ANTHROPIC_URL,
            api_key=key,
            max_retries=2,
            timeout=300,
        )
        kwargs.update(overrides)
        return ChatAnthropic(**kwargs)
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise SystemExit("langchain-ollama ontbreekt in deze omgeving.") from exc
    kwargs = dict(
        model=name,
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_ctx=int(os.environ.get("OLLAMA_NUM_CTX", "16384")),
        request_timeout=int(os.environ.get("OLLAMA_REQUEST_TIMEOUT", "600")),
    )
    kwargs.update(overrides)
    return ChatOllama(**kwargs)
