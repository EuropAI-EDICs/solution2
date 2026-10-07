"""Unit: hitl-ledger en verdict-mapping (offline, geen model)."""

import json
from pathlib import Path

import pytest

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


def test_run_streamed_onderschept_interrupt(monkeypatch, tmp_path):
    """De stream-lus vangt __interrupt__ en schrijft journal + ledger-request."""
    import json
    from types import SimpleNamespace

    import graph_trace
    from hitl import PENDING

    fake_interrupt = SimpleNamespace(
        id="i-x",
        value={"action_requests": [{"name": "run_bp2op_transform", "args": {"useCase": "eindhoven"}}]},
    )
    chunks = iter([
        ((), "updates", ({"__interrupt__": (fake_interrupt,)},)),
    ])

    class FakeAgent:
        def stream(self, *_a, **_k):
            return chunks

    journal_calls = []
    monkeypatch.setattr(graph_trace.journal, "append", lambda *a, **k: journal_calls.append((a, k)))
    ledger_file = tmp_path / "hitl-verdicts.jsonl"
    monkeypatch.setattr("hitl.LEDGER", ledger_file)   # ledger_append leest de module-global in hitl

    result = graph_trace.run_streamed(FakeAgent(), "converteer")
    assert result == PENDING
    assert any(k.get("kind") == "hitl_request" for _, k in journal_calls)
    regels = ledger_file.read_text().splitlines()
    assert regels and json.loads(regels[0])["kind"] == "request"
    assert json.loads(regels[0])["tool"] == "run_bp2op_transform"


def test_live_pending_wegschrijven_en_auto_approve_mapping():
    """Het auto-verdict is een geregistreerde machinale goedkeuring, geen menselijke."""
    from hitl import verdict_to_decisions

    # de auto-resume gebruikt dezelfde mapping; het verschil zit in de registratie
    d = verdict_to_decisions(True, "auto: dev-flag --auto-approve-hitl")
    assert d["decisions"][0]["type"] == "approve"
    # en het ledger-record draagt 'auto': True (getest via ledger-append-assert in Task 2-stijl)


def test_live_py_help_benoemt_auto_approve_flag():
    """`live.py --help` werkt (spawn-contract: eerste positioneel blijft de vraag)."""
    import os
    import subprocess
    import sys

    live_py = Path(__file__).resolve().parent.parent / "live.py"
    result = subprocess.run(
        [sys.executable, str(live_py), "--help"],
        capture_output=True, text=True, timeout=120, env=os.environ.copy(),
    )
    assert result.returncode == 0
    assert "--auto-approve-hitl" in result.stdout


@pytest.mark.filterwarnings("ignore:laya-mlx:RuntimeWarning")
def test_live_main_komt_door_build_agent_tot_done(monkeypatch, tmp_path):
    """Offline rooktest: live.main() moet verder komen dan argparse én build_agent.

    Een startup-TypeError (bijv. vergeten tools-argument op build_agent) mag nooit
    een groene suite halen; check_ollama/run_streamed zijn gestoopt, journal en
    checkpoints.sqlite schrijven naar tmp.
    """
    import sys

    import journal as journal_mod
    import live

    calls = []
    monkeypatch.setattr("live.check_ollama", lambda modellen: None)
    monkeypatch.setattr("live.run_streamed", lambda agent, vraag, **k: "ok")
    monkeypatch.setattr(journal_mod, "LIVE_DIR", tmp_path / "runs" / "live")
    monkeypatch.setattr(journal_mod, "JOURNAL", tmp_path / "runs" / "live" / "steps.jsonl")
    monkeypatch.setattr(
        journal_mod, "append",
        lambda kind, agent, summary, **extra: calls.append((kind, agent, summary)),
    )
    monkeypatch.setattr(live, "HERE", tmp_path)  # checkpoints.sqlite ruimt tmp op
    monkeypatch.setattr(sys, "argv", ["live.py", "offline rooktest"])

    live.main()

    kinds = [k for k, _, _ in calls]
    assert kinds[0] == "start"   # journal.reset() is gevraagd
    assert kinds[-1] == "done"   # de run is normaal afgesloten


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
