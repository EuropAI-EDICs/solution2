from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "poc-agents.json"


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def agent_spec(agent_id: str) -> dict[str, Any]:
    for row in load_catalog()["agents"]:
        if row["id"] == agent_id:
            return row
    raise KeyError(f"unknown PoC agent: {agent_id}")


POC_AGENTS: list[dict[str, Any]] = load_catalog()["agents"]
