"""Orchestrated deep agents for the nLDT POCs, running fully on local Ollama.

A main orchestrator delegates to per-POC specialist subagents (breda,
rijnland, utrecht, crosstrack, minigim, eindhoven) via the task tool.
Run with a request, or without arguments for a demo question.

Harness-unificatie (M1): alle nldt-capabiliteit komt uit de nldt-MCP-servers
(mcp_client.load_mcp_tools); lokaal blijven alleen de chain-mode
artefactgates (submit_*) en laya-advies.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from deepagents import create_deep_agent  # noqa: E402  (env must be loaded first)

from models import (  # noqa: E402
    check_ollama,
    ollama_model,
    orchestrator_model_name,
    subagent_model_name,
)
from mcp_client import load_mcp_tools  # noqa: E402
from pocs import poc_subagents  # noqa: E402
from tools.artifacts import submit_formal_rule, submit_norm_cards, submit_request  # noqa: E402
from tools.laya import laya_advise_request  # noqa: E402
from laya_router import augment_user_message, laya_enabled  # noqa: E402
from hitl import HITL_TOOLS  # noqa: E402

HERE = Path(__file__).resolve().parent

DEFAULT_QUESTION = (
    "Which recipes exist for the Rijnland POC, and what inputs does the "
    "peil-conflict recipe need? Give me a run plan."
)

SYSTEM_PROMPT = (HERE / "prompts" / "recipe_driver.md").read_text(encoding="utf-8")

# Lokaal blijven alleen de chain-mode artefactgates + laya-advies; ALLE
# nldt-capabiliteit komt uit MCP (M1).
LOCAL_TOOLS = [laya_advise_request, submit_request, submit_norm_cards, submit_formal_rule]


def _tool_name(t) -> str:
    return getattr(t, "name", getattr(t, "__name__", ""))


def build_agent(tools: list, *, checkpointer=None, interrupt_on: dict | None = None):
    """Bouw de orchestrator; met checkpointer en HITL-config voor de live-run.

    interrupt_on=None betekent de standaardconfig (HITL_TOOLS); {} schakelt uit.
    """
    if not laya_enabled():
        tools = [t for t in tools if _tool_name(t) != "laya_advise_request"]
    return create_deep_agent(
        model=ollama_model(orchestrator_model_name()),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        subagents=poc_subagents(mcp_tools=tools),
        checkpointer=checkpointer,
        interrupt_on=interrupt_on if interrupt_on is not None else dict(HITL_TOOLS),
    )


async def build_agent_with_mcp():
    mcp_tools = await load_mcp_tools()
    return build_agent(list(mcp_tools) + LOCAL_TOOLS)


def main() -> None:
    check_ollama([orchestrator_model_name(), subagent_model_name()])
    question = augment_user_message(" ".join(sys.argv[1:]) or DEFAULT_QUESTION)
    agent = asyncio.run(build_agent_with_mcp())
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": "nldt-recipes"}},
    )
    print(result["messages"][-1].content)

    trace = []
    for msg in result["messages"]:
        for call in getattr(msg, "tool_calls", None) or []:
            args = call.get("args", {})
            target = args.get("subagent_type", args.get("recipe_id", ""))
            trace.append(f"{call['name']}({target})" if target else f"{call['name']}()")
    print("\n--- run trace:", " -> ".join(trace) if trace else "no tool calls")


if __name__ == "__main__":
    main()
