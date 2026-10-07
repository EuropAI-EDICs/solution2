"""LLM-gemarkeerde volledige-loop-test (spec §5): ééns de hele HITL-lus met
echt lokaal LLM — run → interrupt → (approve) → tool draait.

Volgt het S1/S7-patroon uit poc/tests/test_seam_comparators.py: expliciete
selectie met `pytest -m llm`; zonder LDT_DEEP_AGENTS_ENDPOINT geskipt, zodat
de standaardsuite offline en LLM-vrij blijft.
"""

import os

import pytest

ENDPOINT_ENV = "LDT_DEEP_AGENTS_ENDPOINT"  # bijv. http://localhost:11434 (Ollama)


@pytest.mark.llm
@pytest.mark.skipif(
    not os.environ.get(ENDPOINT_ENV),
    reason=f"{ENDPOINT_ENV} niet gezet — de volledige agent-loop vergt een lokaal LLM-endpoint",
)
def test_volledige_agent_loop_met_lokaal_llm(tmp_path, monkeypatch):
    """Run met vraag die de transform triggert → interrupt → approve → tool draait."""
    import sqlite3

    from langchain_core.messages import ToolMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command

    from deepagents import create_deep_agent
    from models import ollama_model

    @tool
    def run_bp2op_transform(useCase: str = "eindhoven") -> str:
        """Teststub: staat voor de echte bp2op-transform."""
        return "transform-uitgevoerd"

    monkeypatch.setenv("OLLAMA_BASE_URL", os.environ[ENDPOINT_ENV])
    conn = sqlite3.connect(str(tmp_path / "cp.sqlite"), check_same_thread=False)
    graph = create_deep_agent(
        model=ollama_model(),
        tools=[run_bp2op_transform],
        system_prompt=(
            "Je bent een testagent. Roep bij een conversatieverzoek altijd eerst "
            "de tool run_bp2op_transform aan en stop daarna."
        ),
        interrupt_on={
            "run_bp2op_transform": {
                "allowed_decisions": ["approve", "reject"],
                "description": "MC-6: de jurist beslist over koppelen.",
            }
        },
        checkpointer=SqliteSaver(conn),
    )
    config = {"configurable": {"thread_id": "llm-loop"}}
    seen_interrupt = None
    for chunk in graph.stream(
        {"messages": [{"role": "user", "content": "Converteer eindhoven naar bp2op."}]},
        config=config,
        stream_mode=["updates", "messages"],
        subgraphs=True,
    ):
        _ns, _mode, payload = chunk
        items = payload if isinstance(payload, tuple) else [payload]
        for item in items:
            if isinstance(item, dict) and "__interrupt__" in item:
                seen_interrupt = item["__interrupt__"][0]
    assert seen_interrupt is not None, "de run interrupte niet op run_bp2op_transform"

    # de mens keurt goed; daarna moet de tool echt gedraaid hebben
    for _chunk in graph.stream(
        Command(resume={"decisions": [{"type": "approve"}]}),
        config=config,
        stream_mode=["updates", "messages"],
    ):
        pass

    state = graph.get_state(config)
    assert not any(t.interrupts for t in state.tasks), "interrupt na approve niet verbruikt"
    tool_outputs = [
        str(m.content) for m in state.values["messages"] if isinstance(m, ToolMessage)
    ]
    assert any(
        "transform-uitgevoerd" in c for c in tool_outputs
    ), "de transform draaide niet na approve"
