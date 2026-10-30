"""Events-ledger (hash-chain) en run-artefact: schema-validatie + canonical."""

import copy
from pathlib import Path

from core import events, runs

POC_ROOT = Path(__file__).resolve().parents[1]


def test_chain_is_verifieerbaar():
    log: list = []
    events.emit(log, "start", {"v": 1})
    events.emit(log, "gate_request", {"gate": "H1"})
    assert len(log) == 2
    assert events.verify_chain(log) is True


def test_tamper_breekt_de_ketting():
    log: list = []
    events.emit(log, "start", {"v": 1})
    log[0]["payload"]["v"] = 2
    assert events.verify_chain(log) is False


def _minimale_run():
    return {
        "schemaVersion": "1.0", "runId": runs.new_run_id("test"), "generatedAt": "2026-10-30T00:00:00+00:00",
        "recipeId": "gent-mobiliteit-ondernemer", "processId": "gent-transactional-run", "mode": "replay",
        "scenario": "test",
        "steps": [{"stepId": "routing", "title": "routing", "actor": "agent", "genAiTestPoint": "G2",
                   "dataUsed": [], "consent": "n.v.t.", "handover": None, "kpiEvents": [],
                   "prov": {"sources": ["test"]}}],
        "stopConditions": [], "kpiSnapshot": [],
        "transaction": {
            "context": {"tekst": "test", "regels": [{"feit": "address", "waarde": "Korenmarkt 1, Gent", "label": "gebruiker", "bron": "gesprek"}]},
            "routing": {"outcome": "paden", "paths": {"transactions": [], "info": []}, "trace": [], "uitleg": []},
            "h1": {"verdict": "gegeven", "correcties": {}},
        },
    }


def test_minimale_run_valideert_tegen_schema():
    runs.validate(_minimale_run(), POC_ROOT)


def test_schema_verwerpt_onbekende_herkomstlabel():
    run = _minimale_run()
    run["transaction"]["context"]["regels"][0]["label"] = "verzonnen"
    import jsonschema
    try:
        runs.validate(run, POC_ROOT)
    except jsonschema.ValidationError:
        return
    raise AssertionError("ValidationError werd verwacht")


def test_canonical_stript_runid_en_generatedat():
    run = _minimale_run()
    canon = runs.canonical(run)
    assert "runId" not in canon and "generatedAt" not in canon
    assert canon == runs.canonical(copy.deepcopy(run))
