"""Orchestrator uit architectuur §2: LLM-laag met scenario-analist + interpretatie; A2A = rekenblok."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEEP = REPO / "deep-agents"
PROMPTS = Path(__file__).resolve().parent / "prompts"


def build_agent():
    from deepagents import create_deep_agent

    sys.path.insert(0, str(DEEP))
    from models import check_ollama, ollama_model, orchestrator_model_name, subagent_model_name  # noqa: WPS433
    from tools.recipes import get_recipe, list_recipes  # noqa: WPS433

    from orchestrator.a2a_tools import delegate_to_poc_agent, list_poc_agents

    check_ollama([orchestrator_model_name(), subagent_model_name()])
    submodel = ollama_model(subagent_model_name())

    subagents = [
        {
            "name": "scenario_analist",
            "description": (
                "Forms scenario specs and nLDT run plans from recipes (JSON contracts). "
                "No execution — specs only."
            ),
            "system_prompt": (PROMPTS / "scenario_analist.md").read_text(encoding="utf-8"),
            "tools": [list_recipes, get_recipe],
            "model": submodel,
        },
        {
            "name": "interpretatie",
            "description": (
                "Interprets deterministic A2A/MCP results; trade-offs and policy linkage. "
                "Never recomputes numbers."
            ),
            "system_prompt": (PROMPTS / "interpretatie.md").read_text(encoding="utf-8"),
            "tools": [],
            "model": submodel,
        },
    ]

    system_prompt = (PROMPTS / "orchestrator.md").read_text(encoding="utf-8")
    return create_deep_agent(
        model=ollama_model(orchestrator_model_name()),
        tools=[delegate_to_poc_agent, list_poc_agents],
        subagents=subagents,
        system_prompt=system_prompt,
    )


def main() -> None:
    question = " ".join(sys.argv[1:]) or (
        "Plan en run via A2A een Rijnland peil-conflict demo; interpreteer de artifact."
    )
    agent = build_agent()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": "a2a-arch-run"}},
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
