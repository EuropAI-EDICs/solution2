"""Smoke: interrupt-mechanisme van deepagents + SqliteSaver, volledig offline.

Bewijst het contract dat de rest van de HITL-bouw coded tegen:
interrupt-payload-vorm, resume-vorm en herstel uit de checkpointer.
"""

import sqlite3

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from deepagents import create_deep_agent


class _FakeToolChatModel(GenericFakeChatModel):
    """Offline model-stub met twee aanpassingen:

    - bind_tools: deepagents bindt de tools op het model; de scripted berichten
      bevatten de tool-calls al, dus binding is een no-op.
    - disable_streaming: deze langchain-core streamt tool_calls niet en een
      AIMessage met lege content levert een lege stream op; zonder deze vlag
      kiest invoke de streaming-pad en faalt met 'No generations found'.
    """

    disable_streaming: bool = True

    def bind_tools(self, tools, **kwargs):
        return self


def _fake_model_with_toolcall():
    """Model dat eerst een tool-call produceert en daarna stopt (offline)."""
    msgs = iter([
        AIMessage("", tool_calls=[{"name": "run_bp2op_transform", "args": {"useCase": "eindhoven"}, "id": "call-1"}]),
        AIMessage("klaar"),
    ])
    return _FakeToolChatModel(messages=msgs)


@tool
def run_bp2op_transform(useCase: str = "eindhoven") -> str:
    """Teststub: staat voor de echte bp2op-transform."""
    return "transform-uitgevoerd"


def _build(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "cp.sqlite"), check_same_thread=False)
    saver = SqliteSaver(conn)
    graph = create_deep_agent(
        model=_fake_model_with_toolcall(),
        tools=[run_bp2op_transform],
        system_prompt="test",
        interrupt_on={
            "run_bp2op_transform": {
                "allowed_decisions": ["approve", "reject"],
                "description": "MC-6: de jurist beslist over koppelen.",
            }
        },
        checkpointer=saver,
    )
    return graph, saver


def test_interrupt_vuur_bij_submit_en_resume_werkt(tmp_path):
    graph, _ = _build(tmp_path)
    config = {"configurable": {"thread_id": "smoke-1"}}
    seen_interrupt = None
    for chunk in graph.stream(
        {"messages": [{"role": "user", "content": "converteer"}]},
        config=config,
        stream_mode=["updates", "messages"],
        subgraphs=True,
    ):
        _ns, mode, payload = chunk
        items = payload if isinstance(payload, tuple) else [payload]
        for item in items:
            if isinstance(item, dict) and "__interrupt__" in item:
                seen_interrupt = item["__interrupt__"][0]

    assert seen_interrupt is not None, "geen __interrupt__-chunk gezien"
    value = seen_interrupt.value
    assert value["action_requests"][0]["name"] == "run_bp2op_transform"

    # state bevat de interrupt na de onderbroken run
    state = graph.get_state(config)
    assert any(t.interrupts for t in state.tasks), "interrupt niet in state terug te vinden"

    # resume: goedkeuren — de tool voert uit en de run loopt af.
    # Let op: graph.stream is lazy; de generator móét geïtereerd worden om de
    # graph daadwerkelijk te laten draaien (een kale aanroep doet niets).
    for _chunk in graph.stream(
        Command(resume={"decisions": [{"type": "approve"}]}),
        config=config,
        stream_mode=["updates", "messages"],
    ):
        pass

    state2 = graph.get_state(config)
    assert not any(t.interrupts for t in state2.tasks), "interrupt na approve niet verbruikt"
    assert state2.values["messages"][-1].content == "klaar"


def test_resume_reject_slaat_tool_over_en_loopt_af(tmp_path):
    """Eindreview: het reject-pad van het zelfde contract — de tool mag niet
    draaien en de afwijzing moet in de context van de aflopende run zitten."""
    from langchain_core.messages import ToolMessage

    graph, _ = _build(tmp_path)
    config = {"configurable": {"thread_id": "smoke-reject"}}
    seen_interrupt = None
    for chunk in graph.stream(
        {"messages": [{"role": "user", "content": "converteer"}]},
        config=config,
        stream_mode=["updates", "messages"],
        subgraphs=True,
    ):
        _ns, _mode, payload = chunk
        items = payload if isinstance(payload, tuple) else [payload]
        for item in items:
            if isinstance(item, dict) and "__interrupt__" in item:
                seen_interrupt = item["__interrupt__"][0]
    assert seen_interrupt is not None, "geen __interrupt__-chunk gezien"

    # resume: afkeuren met een opmerking (dashboard-verdict-vorm)
    for _chunk in graph.stream(
        Command(resume={"decisions": [{"type": "reject", "message": "niet koppelen"}]}),
        config=config,
        stream_mode=["updates", "messages"],
    ):
        pass

    state2 = graph.get_state(config)
    assert not any(t.interrupts for t in state2.tasks), "interrupt na reject niet verbruikt"
    berichten = state2.values["messages"]
    assert not any(
        isinstance(m, ToolMessage) and "transform-uitgevoerd" in str(m.content)
        for m in berichten
    ), "de transform draaide ondanks een reject"
    assert any(
        "niet koppelen" in str(getattr(m, "content", "")) for m in berichten
    ), "de reject-reden ontbreekt in de context"
    # de run loopt normaal af: het model krijgt de afwijzing te zien en sluit met "klaar"
    assert berichten[-1].content == "klaar"
