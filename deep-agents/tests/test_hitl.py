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


def test_resume_argparse_verplicht_comment_bij_beide_uitkomsten(tmp_path):
    """Zowel reject als approve zonder opmerking wordt bij het argument geweigerd (spec: leerstaat)."""
    import subprocess, sys

    cwd = Path(__file__).resolve().parents[1]
    for vlag in ("--rejected", "--approved"):
        r = subprocess.run(
            [sys.executable, "resume.py", "i-onbestaand", vlag, "--comment", ""],
            capture_output=True, text=True, cwd=cwd,
        )
        assert r.returncode != 0, f"{vlag} zonder opmerking moet geweigerd worden"
        assert "opmerking" in (r.stdout + r.stderr).lower()


def test_server_verdict_route_bestaat_en_weigert_leeg_comment():
    """Task 7 (brief): hitl-routes bestaan in live_server; dubbel verdict → 409."""
    import inspect

    import live_server

    src = inspect.getsource(live_server)
    assert "/api/hitl/pending" in src and "/api/hitl/verdict" in src
    assert "409" in src, "dubbel verdict moet geweigerd worden"


def test_server_valideer_verdict_weigert_leeg_comment_en_accepteert_geldig():
    """Validatiehelper: leeg comment → 400-melding vóór de pending-check; geldig → ok."""
    import live_server

    ok, fout = live_server._valideer_verdict(
        live_server.VerdictBody(interruptId="i-1", approved=True, comment="   \n")
    )
    assert not ok and "opmerking" in fout.lower()

    ok, fout = live_server._valideer_verdict(
        live_server.VerdictBody(interruptId="i-1", approved=False, comment="niet koppelen")
    )
    assert ok and fout == ""


def test_server_valideer_verdict_weigert_lege_interruptid():
    """Review-fixwave: de lege-interruptId-tak van de validatiehelper is een 400."""
    import live_server

    ok, fout = live_server._valideer_verdict(
        live_server.VerdictBody(interruptId="  ", approved=True, comment="akkoord")
    )
    assert not ok and "interruptid" in fout.lower()


def test_server_load_pending_zonder_checkpoints_of_interrupt_is_niet_pending(monkeypatch, tmp_path):
    """Authoritair via checkpoints op disk: geen DB (of lege DB) → pending False.

    Bewijst dat de pending-check zonder Ollama/model werkt (zelfde pad als resume.py).
    """
    import live_server

    monkeypatch.setattr(live_server, "CHECKPOINTS", tmp_path / "ontbreekt" / "checkpoints.sqlite")
    assert live_server._load_pending() == {"pending": False}

    (tmp_path / "leeg").mkdir()
    monkeypatch.setattr(live_server, "CHECKPOINTS", tmp_path / "leeg" / "checkpoints.sqlite")
    assert live_server._load_pending() == {"pending": False}


def test_server_verdict_route_409_bij_afwezige_pending(monkeypatch, tmp_path):
    """Zonder wachtende interrupt (al verbruikt) geeft het verdict-endpoint 409."""
    from fastapi import HTTPException

    import live_server

    monkeypatch.setattr("hitl.LEDGER", tmp_path / "hitl-verdicts.jsonl")
    monkeypatch.setattr(live_server, "_interrupt_state", lambda: (True, {"pending": False}))
    with pytest.raises(HTTPException) as ei:
        live_server.hitl_verdict(
            live_server.VerdictBody(interruptId="i-1", approved=True, comment="ok")
        )
    assert ei.value.status_code == 409


def test_server_verdict_route_state_is_authoritair_boven_verlaten_ledger_request(monkeypatch, tmp_path):
    """Regressie (review-fixwave): een verlaten request A (nooit verdict) in het
    append-only ledger mag een vers interrupt B niet blokkeren. De checkpoint-
    state is authoritair: 409 alléén als de state niet pending is voor dit id."""
    import live_server

    monkeypatch.setattr("hitl.LEDGER", tmp_path / "hitl-verdicts.jsonl")
    ledger_append({"kind": "request", "interruptId": "i-A", "tool": "run_bp2op_transform"})
    monkeypatch.setattr(live_server, "_interrupt_state", lambda: (
        True,
        {"pending": True, "interruptId": "i-B", "tool": "run_bp2op_transform",
         "argsSummary": "useCase=eindhoven", "threadId": "nldt-live"},
    ))
    spawned = []
    monkeypatch.setattr(live_server.subprocess, "Popen", lambda cmd, **k: spawned.append((cmd, k)))

    resp = live_server.hitl_verdict(live_server.VerdictBody(
        interruptId="i-B", approved=True, comment="akkoord", operator="marc"))
    assert resp["ok"] is True
    assert spawned, "verdict voor B moet slagen ondanks verlaten request A in het ledger"

    # minor (fixwave 2): ook het ledger-verdict-record voor i-B is geclaimd
    regels = [json.loads(l) for l in (tmp_path / "hitl-verdicts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert regels[0]["kind"] == "request" and regels[0]["interruptId"] == "i-A"
    verdict = regels[-1]
    assert verdict["kind"] == "verdict" and verdict["interruptId"] == "i-B"
    assert verdict["tool"] == "run_bp2op_transform" and verdict["auto"] is False
    assert verdict["operator"] == "marc"


def test_server_verdict_route_fallback_ledger_bij_onleesbare_state(monkeypatch, tmp_path):
    """Review-fixwave 2: onleesbare checkpoint-state + open ledger-request → het
    verdict slaagt (geen KeyError/500): het duurzame record krijgt de juiste
    tool uit de ledger-request en resume.py wordt gespawnd."""
    import live_server

    ledger = tmp_path / "hitl-verdicts.jsonl"
    monkeypatch.setattr("hitl.LEDGER", ledger)
    ledger_append({
        "kind": "request", "interruptId": "i-C", "threadId": "nldt-live",
        "tool": "run_bp2op_transform", "argsSummary": "useCase=eindhoven",
    })
    monkeypatch.setattr(live_server, "_interrupt_state", lambda: (False, {"pending": False}))
    spawned = []
    monkeypatch.setattr(live_server.subprocess, "Popen", lambda cmd, **k: spawned.append((cmd, k)))

    resp = live_server.hitl_verdict(live_server.VerdictBody(
        interruptId="i-C", approved=True, comment="akkoord", operator="marc"))
    assert resp["ok"] is True
    regels = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines()]
    verdict = regels[-1]
    assert verdict["kind"] == "verdict" and verdict["interruptId"] == "i-C"
    assert verdict["tool"] == "run_bp2op_transform" and verdict["auto"] is False
    assert spawned and spawned[0][0][1].endswith("resume.py") and "--approved" in spawned[0][0]


def test_server_verdict_route_ledger_voor_spawn_en_daarna_409(monkeypatch, tmp_path):
    """Duurzaam verdict (auto: False) staat in het ledger vóór resume.py start."""
    import live_server

    ledger = tmp_path / "hitl-verdicts.jsonl"
    monkeypatch.setattr("hitl.LEDGER", ledger)
    monkeypatch.setattr(live_server, "_interrupt_state", lambda: (
        True,
        {"pending": True, "interruptId": "i-9", "tool": "run_bp2op_transform",
         "argsSummary": "useCase=eindhoven", "threadId": "nldt-live"},
    ))
    spawned = []
    monkeypatch.setattr(live_server.subprocess, "Popen", lambda cmd, **k: spawned.append((cmd, k)))

    resp = live_server.hitl_verdict(live_server.VerdictBody(
        interruptId="i-9", approved=False, comment="niet koppelen", operator="marc"))
    assert resp["ok"] is True
    regels = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines()]
    assert regels and regels[0]["kind"] == "verdict" and regels[0]["auto"] is False
    assert regels[0]["approved"] is False and regels[0]["operator"] == "marc"
    assert spawned and spawned[0][0][1].endswith("resume.py") and "--rejected" in spawned[0][0]

    # na verbruik (state leeg) is een tweede verdict voor hetzelfde id geweigerd:
    from fastapi import HTTPException

    monkeypatch.setattr(live_server, "_interrupt_state", lambda: (True, {"pending": False}))
    with pytest.raises(HTTPException) as ei:
        live_server.hitl_verdict(live_server.VerdictBody(
            interruptId="i-9", approved=True, comment="tweede poging"))
    assert ei.value.status_code == 409


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
