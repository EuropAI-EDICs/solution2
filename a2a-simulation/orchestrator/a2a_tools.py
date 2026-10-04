"""LangChain tools: Deep Agents orchestrator → remote PoC via A2A 1.x."""

from __future__ import annotations

from typing import Any

from federator.a2a_client import send_message

POC_IDS = ("breda", "utrecht", "rijnland", "eindhoven", "crosstrack", "minigim")


def delegate_to_poc_agent(poc_id: str, message: str) -> dict[str, Any]:
    """Deterministic rekenblok: A2A Send Message naar PoC-server (architectuur §2, §6).

    LLM-laag levert alleen de tekst/spec; deze tool roept het **deterministische**
    rekenblok aan (simulate of nldt). Interpreteer de JSON-artifacts met subagent
    interpretatie — verzin geen getallen.
    """
    poc = poc_id.strip().lower()
    if poc not in POC_IDS:
        raise ValueError(f"Unknown poc_id {poc_id!r}. Choose from: {', '.join(POC_IDS)}")
    return send_message(poc, message)


def list_poc_agents() -> list[dict[str, str]]:
    """List PoC agent ids and their federation question (for routing)."""
    from agents.registry import load_catalog

    return [
        {"id": a["id"], "question": a.get("question", ""), "port": str(a["port"])}
        for a in load_catalog()["agents"]
    ]
