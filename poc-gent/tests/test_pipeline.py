"""F1-replay end-to-end: personas → gate → GIS → H1 → routing (FR-03/04/05/06/07/23)."""

from pathlib import Path

from core import events as events_mod
from core import pipeline, runs

POC_ROOT = Path(__file__).resolve().parents[1]


def test_sanne_krijgt_bele_ontheffingen_met_uitleg():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    runs.validate(run, POC_ROOT)
    routing = run["transaction"]["routing"]
    assert routing["outcome"] == "paden"
    assert routing["paths"]["transactions"] == ["ontheffing-lez", "ontheffing-autovrij"]
    assert all(u["bron"] for u in routing["uitleg"])
    assert events_mod.verify_chain(log) is True


def test_fatima_gate_vraagt_activity_en_antwoord_telt_meer():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "fatima")
    vragen = [e for e in log if e["kind"] == "context_vraag"]
    assert [v["payload"]["slot"] for v in vragen] == ["activity"]
    assert run["transaction"]["context"]["regels"]  # activity is gevuld: context compleet
    assert run["transaction"]["routing"]["paths"]["transactions"] == ["ontheffing-lez"]


def test_jeroen_correctie_herberekent_routing():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "jeroen")
    herkomst = {r["feit"]: r for r in run["transaction"]["context"]["regels"]}
    assert herkomst["address"]["label"] == "correctie"
    assert run["transaction"]["routing"]["paths"]["transactions"] == ["ontheffing-lez", "ontheffing-autovrij"]
    verdict = [e for e in log if e["kind"] == "gate_verdict"][0]
    assert verdict["payload"]["correcties"] == {"address": "Korenmarkt 1, Gent"}


def test_escalatie_levert_handoverstap_gentinfo():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne",
                                   override_slots={"applicantType": "organisatie"})
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["routing"]["outcome"] == "escalatie"
    stappen = {s["stepId"] for s in run["steps"]}
    assert "escalatie" in stappen
    esc = [s for s in run["steps"] if s["stepId"] == "escalatie"][0]
    assert esc["handover"]["to"] == "Gentinfo"
    assert any(e["kind"] == "handover" for e in log)


def test_canonieke_replay_is_deterministisch():
    r1, _ = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "ahmed")
    r2, _ = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "ahmed")
    assert runs.canonical(r1) == runs.canonical(r2)
