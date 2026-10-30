"""F1-replay end-to-end: personas → gate → GIS → H1 → routing (FR-03/04/05/06/07/23)."""

import json
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


def test_sanne_doorloopt_tot_h3_gereed_met_authentieke_prefill():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "gereed"
    assert run["transaction"]["auth"] == {"authenticatie": "uitgevoerd", "toestemming": "gegeven", "mandaten": []}
    kenteken = [v for v in run["transaction"]["prefill"]["transacties"][0]["velden"] if v["veld"] == "kenteken"][0]
    assert kenteken["label"] == "authentiek"
    assert kenteken["bron"].startswith("magda:kenteken")
    assert run["transaction"]["h3"]["verdict"] == "gegeven"
    assert events_mod.verify_chain(log) is True


def test_ellen_weigering_stopt_netjes_zonder_prefill():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "ellen")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "geweigerd"
    assert run["transaction"]["prefill"]["transacties"] == []
    assert run["transaction"]["h3"]["verdict"] == "n.v.t."
    consent = [s for s in run["steps"] if s["stepId"] == "h2-gegevensgebruik"][0]["consent"]
    assert consent == "geweigerd"


def test_dirk_euro4_levert_blokkade_met_correctiepad():
    run, _log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "dirk")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "blokkade"
    bevindingen = run["transaction"]["validatie"]["transacties"][0]["bevindingen"]
    assert bevindingen[0]["id"] == "V1-euroklasse"
    assert "Vervang" in bevindingen[0]["melding"]


def test_bron_raadpleging_logt_sleutels_zonder_waarden():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    raadplegingen = [e for e in log if e["kind"] == "bron_raadpleging"]
    assert raadplegingen and all(set(r["payload"]["sleutels"]) <= {"kenteken", "euroklasse", "brandstof"} for r in raadplegingen)
    assert all("waarde" not in json.dumps(r) or "sleutels" in r for r in raadplegingen)


def test_maria_zonder_transacties_slaat_auth_over():
    run, _log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "maria")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "gereed"
    assert run["transaction"]["auth"]["authenticatie"] == "niet-uitgevoerd"
    assert run["transaction"]["auth"]["toestemming"] == "n.v.t."
