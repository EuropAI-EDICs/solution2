"""Tests voor de HCS-LLM-intake (fase 3, benadering C-aanzet).

De gate-tests zijn offline en LLM-vrij (pure functie); de volledige
LLM-intake staat achter de `llm`-marker en skipit zonder
LDT_DEEP_AGENTS_ENDPOINT (patroon test_hitl_llm.py).

Run-conventie: cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages
../nldt/.venv/bin/python -m pytest tests/test_hcs_intake.py -q
"""

import os

import pytest

ENDPOINT_ENV = "LDT_DEEP_AGENTS_ENDPOINT"


def test_load_thk08_personas():
    from hcs_intake import load_thk08_personas

    personas = load_thk08_personas()
    assert [p["id"] for p in personas] == ["sanne", "ahmed", "maria", "jeroen"]
    ahmed = next(p for p in personas if p["id"] == "ahmed")
    assert ahmed["expected_handover_reason"], "ahmed heeft een intake-handover in de fixture"
    sanne = next(p for p in personas if p["id"] == "sanne")
    assert sanne["expected_handover_reason"] is None


def test_gate_passes_clean_questions():
    from hcs_intake import gate_intake, load_thk08_personas

    persona = next(p for p in load_thk08_personas() if p["id"] == "sanne")
    result = {"asks": ["Op welke datum ga je verhuizen?"], "handover": None}
    gate = gate_intake(result, persona)
    assert gate["passed"], gate


def test_gate_fails_on_known_brp_question():
    from hcs_intake import gate_intake, load_thk08_personas

    persona = next(p for p in load_thk08_personas() if p["id"] == "sanne")
    result = {"asks": ["Wat is uw naam en wat wordt uw nieuwe adres?"], "handover": None}
    gate = gate_intake(result, persona)
    only = next(c for c in gate["checks"] if c["check"] == "only-new-questions")
    assert not only["passed"] and not gate["passed"]


def test_gate_fails_on_jargon():
    from hcs_intake import gate_intake, load_thk08_personas

    persona = next(p for p in load_thk08_personas() if p["id"] == "maria")
    result = {"asks": ["Wat is uw BSN voor de zaakverhuizing?"], "handover": None}
    gate = gate_intake(result, persona)
    plain = next(c for c in gate["checks"] if c["check"] == "plain-language")
    assert not plain["passed"]


def test_gate_requires_handover_for_edge_persona():
    from hcs_intake import gate_intake, load_thk08_personas

    ahmed = next(p for p in load_thk08_personas() if p["id"] == "ahmed")
    without = gate_intake({"asks": ["Wanneer verhuis je?"], "handover": None}, ahmed)
    assert not without["passed"], "ahmed zonder overname moet falen (edge: adres-twijfel)"
    with_handover = gate_intake(
        {"asks": [], "handover": {"reason": "Twijfel over het adres"}}, ahmed)
    assert with_handover["passed"]


def test_gate_rejects_unexpected_handover():
    from hcs_intake import gate_intake, load_thk08_personas

    sanne = next(p for p in load_thk08_personas() if p["id"] == "sanne")
    gate = gate_intake({"asks": [], "handover": {"reason": "omdat"}}, sanne)
    edge = next(c for c in gate["checks"] if c["check"] == "edge-handover")
    assert not edge["passed"]


@pytest.mark.llm
@pytest.mark.skipif(
    not os.environ.get(ENDPOINT_ENV),
    reason=f"{ENDPOINT_ENV} niet gezet — de echte intake vergt een lokaal LLM-endpoint",
)
def test_llm_intake_sanne_parses_and_passes_gate(monkeypatch):
    from hcs_intake import run_intake

    monkeypatch.setenv("OLLAMA_BASE_URL", os.environ[ENDPOINT_ENV])
    result = run_intake("sanne")
    assert not result["abstained"], "antwoord moet parseerbaar JSON zijn"
    assert result["gate"]["passed"], result["gate"]
