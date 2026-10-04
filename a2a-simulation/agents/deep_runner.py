from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DEEP = REPO / "deep-agents"


def _ensure_deep_agents_path() -> None:
    deep_str = str(DEEP)
    if deep_str not in sys.path:
        sys.path.insert(0, deep_str)


def run_poc_deep_agent(agent_id: str, user_message: str, thread_id: str) -> dict[str, Any]:
    """Standalone PoC deep agent (dev only — production LLM path is orchestrator/)."""
    _ensure_deep_agents_path()
    from dotenv import load_dotenv

    load_dotenv(DEEP / ".env")

    from models import check_ollama, subagent_model_name
    from pocs import run_standalone_poc_agent

    check_ollama([subagent_model_name()])
    return run_standalone_poc_agent(agent_id, user_message, thread_id)
