"""Unit: hitl-ledger en verdict-mapping (offline, geen model)."""

import json

from hitl import (
    LEDGER,
    PENDING_EXIT_CODE,
    args_summary,
    ledger_append,
    ledger_read,
    pending_from_ledger,
    verdict_to_decisions,
)


def test_ledger_append_voegt_ts_toe_en_is_append_only(tmp_path, monkeypatch):
    monkeypatch.setattr("hitl.LEDGER", tmp_path / "hitl-verdicts.jsonl")
    ledger_append({"kind": "request", "interruptId": "i-1", "tool": "run_bp2op_transform"})
    ledger_append({"kind": "verdict", "interruptId": "i-1", "approved": True, "comment": "ok"})
    lines = ledger_read()
    assert [r["kind"] for r in lines] == ["request", "verdict"]
    assert all("ts" in r for r in lines)


def test_pending_is_request_zonder_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr("hitl.LEDGER", tmp_path / "hitl-verdicts.jsonl")
    ledger_append({"kind": "request", "interruptId": "i-1"})
    assert pending_from_ledger()["interruptId"] == "i-1"
    ledger_append({"kind": "verdict", "interruptId": "i-1", "approved": False, "comment": "nee"})
    assert pending_from_ledger() is None


def test_verdict_mapping_conform_resume_contract():
    assert verdict_to_decisions(True, "wat dan ook") == {"decisions": [{"type": "approve"}]}
    assert verdict_to_decisions(False, "niet koppelen") == {
        "decisions": [{"type": "reject", "message": "niet koppelen"}]
    }


def test_args_summary_is_kort_en_deterministisch():
    a = args_summary({"useCase": "eindhoven", "source": "bestemming.xml"})
    b = args_summary({"source": "bestemming.xml", "useCase": "eindhoven"})
    assert a == b and len(a) <= 120 and "eindhoven" in a


def test_pending_exit_code_is_2():
    assert PENDING_EXIT_CODE == 2


def test_build_agent_geeft_interrupt_en_checkpointer_door(tmp_path):
    """build_agent plakt de interrupt-config op create_deep_agent (offline bewijs)."""
    import inspect

    import agent as agent_module
    from hitl import HITL_TOOLS

    src = inspect.getsource(agent_module.build_agent)
    assert "interrupt_on" in src and "checkpointer" in src
    assert "run_bp2op_transform" in src or "HITL_TOOLS" in src
    assert isinstance(HITL_TOOLS, dict) and "run_bp2op_transform" in HITL_TOOLS
    # Versterking (geen nieuwe deps): keyword-only params + compileerbaarheid.
    params = inspect.signature(agent_module.build_agent).parameters
    assert params["checkpointer"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["interrupt_on"].kind is inspect.Parameter.KEYWORD_ONLY
    compile(inspect.getsource(agent_module), str(agent_module.__file__), "exec")
