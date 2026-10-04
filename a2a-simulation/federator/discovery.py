from __future__ import annotations

import os
from typing import Any

import httpx

from agents.registry import agent_spec, load_catalog
from federator.a2a_client import agent_base_url, fetch_agent_card_proto


def catalog_only() -> dict[str, Any]:
    return load_catalog()


def list_agents_live() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in load_catalog()["agents"]:
        try:
            card = fetch_agent_card_proto(row["id"])
            out.append(
                {
                    "id": row["id"],
                    "port": row["port"],
                    "url": agent_base_url(int(row["port"])),
                    "reachable": True,
                    "agentCard": _card_to_dict(card),
                }
            )
        except Exception as exc:
            out.append(
                {
                    "id": row["id"],
                    "port": row["port"],
                    "reachable": False,
                    "error": str(exc),
                }
            )
    return out


def _card_to_dict(card: Any) -> dict[str, Any]:
    from google.protobuf.json_format import MessageToDict

    return MessageToDict(card, preserving_proto_field_name=True)
