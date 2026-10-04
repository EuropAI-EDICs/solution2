"""Orchestrated deep agents for the nLDT POCs, running fully on local Ollama.

A main orchestrator delegates to per-POC specialist subagents (breda,
rijnland, utrecht, crosstrack, minigim, eindhoven) via the task tool.
Run with a request, or without arguments for a demo question.
"""

from __future__ import annotations

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
from pocs import poc_subagents  # noqa: E402
from tools.laya import laya_advise_request  # noqa: E402
from tools.recipes import get_recipe, list_recipes  # noqa: E402
from laya_router import augment_user_message, laya_enabled  # noqa: E402

HERE = Path(__file__).resolve().parent

DEFAULT_QUESTION = (
    "Which recipes exist for the Rijnland POC, and what inputs does the "
    "peil-conflict recipe need? Give me a run plan."
)

SYSTEM_PROMPT = (HERE / "prompts" / "recipe_driver.md").read_text(encoding="utf-8")


def build_agent():
    tools = [list_recipes, get_recipe]
    if laya_enabled():
        tools.append(laya_advise_request)
    return create_deep_agent(
        model=ollama_model(orchestrator_model_name()),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        subagents=poc_subagents(),
    )


def main() -> None:
    check_ollama([orchestrator_model_name(), subagent_model_name()])
    question = augment_user_message(" ".join(sys.argv[1:]) or DEFAULT_QUESTION)
    result = build_agent().invoke(
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
