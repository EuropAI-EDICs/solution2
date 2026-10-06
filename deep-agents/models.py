"""Chat models for the nLDT deep agents.

Sinds de harness-unificatie (M2) is `nldt/services/common/model_config.py` de
canonieke bron voor modelnamen en -bouw; deze module delegeert en houdt
alleen `check_ollama` (fail-fast diagnose) lokaal. Twee providers:

- Local Ollama (default): `ollama_model()` builds ChatOllama; names must
  match `ollama list`. Cloud-routed Ollama variants (`:cloud`) are refused —
  they hit Ollama's paid tier with a 402.
- Z.ai GLM (like the ZCode assistant): `zai:<model>` strings (e.g.
  `zai:glm-5.3-flash`) resolve to ChatAnthropic against Z.ai's
  Anthropic-compatible endpoint. Requires ZAI_API_KEY in the environment
  or deep-agents/.env — create a key at https://z.ai/manage-apikey/apikey-list.

Env vars (read at build time, after .env is loaded): DEEP_AGENT_MODEL
(orchestrator), DEEP_AGENT_SUBMODEL (POC specialists), OLLAMA_BASE_URL,
OLLAMA_NUM_CTX, ZAI_API_KEY.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nldt"))

from services.common.model_config import (  # noqa: E402,F401
    ZAI_ANTHROPIC_URL,
    build_chat_model as _build_chat_model,
    is_zai,
    orchestrator_model_name,
    subagent_model_name,
)


def ollama_model(model: str | None = None, **overrides):
    """Build the chat model for a spec string: `ollama-name` (local) or
    `zai:glm-...` (Z.ai GLM over the Anthropic-compatible endpoint)."""
    return _build_chat_model(model or orchestrator_model_name(), **overrides)


def check_ollama(models: list[str]) -> None:
    """Fail fast with a clear message if a provider is unreachable or a model is missing."""
    cloud = [m for m in models if "cloud" in m and not is_zai(m)]
    if cloud:
        raise SystemExit(
            f"Model(s) {', '.join(cloud)} route to Ollama's PAID cloud service — "
            "only local models are allowed. For GLM use `zai:glm-...` (Z.ai) or a "
            "local model from `ollama list`."
        )
    zai = [m for m in models if is_zai(m)]
    if zai and not os.environ.get("ZAI_API_KEY"):
        raise SystemExit(
            f"Model(s) {', '.join(zai)} need ZAI_API_KEY (set it in deep-agents/.env). "
            "Create a key at https://z.ai/manage-apikey/apikey-list — your GLM Coding "
            "Plan subscription includes API access."
        )
    ollama_names = [m for m in models if not is_zai(m)]
    if not ollama_names:
        return
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=5) as resp:
            installed = {m["name"] for m in json.load(resp).get("models", [])}
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Ollama is not reachable at {base} ({exc.reason}). "
            "Start it with `ollama serve` or the Ollama app."
        ) from exc
    missing = [m for m in ollama_names if m.split(":")[0] not in installed and m not in installed]
    if missing:
        raise SystemExit(
            f"Model(s) {', '.join(missing)} not in `ollama list` — pull with "
            f"`ollama pull {' '.join(missing)}` or set DEEP_AGENT_MODEL / "
            "DEEP_AGENT_SUBMODEL to an installed model."
        )
