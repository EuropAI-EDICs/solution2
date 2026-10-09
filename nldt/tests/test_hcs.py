"""Tests voor de HCS-recipes (spec 2026-10-09-hcs-recipes-pocs-design, fase 1)."""
import json
from pathlib import Path

import pytest

from services.common.schema import load_recipe, validate_instance

NLDT_ROOT = Path(__file__).resolve().parents[1]
HCS_ROOT = NLDT_ROOT / "simulation" / "hcs"

SERVICE_MIN = {
    "dish": "the-key",
    "serviceType": "reactive",
}


def test_service_block_accepted():
    recipe = {
        "id": "probe-hcs",
        "title": "Schema-probe met service-blok",
        "version": "1.0.0",
        "inputs": {},
        "outputs": {},
        "steps": [
            {"id": "s1", "processId": "hcs-life-event-run", "inputs": {}}
        ],
        "riskLevel": "low",
        "service": dict(
            SERVICE_MIN,
            lifeEventCode="THK-08",
            blueprintSteps=[1, 2, 3, 4, 5],
            parties=[{"name": "Gemeente Zoetermeer", "role": "lead"}],
            legalBasis=[{"basis": "Wet BRP", "timeLimit": "redelijke termijn (Awb)"}],
            humanMeasure={"handover": ["adresonderzoek bij twijfel → medewerker"], "exceptions": []},
            localVariant="gemeentelijk parkeerbeleid",
            genAiTestPoints=[{"point": "G1", "description": "intake-assistent", "testCases": ["laaggeletterde persona"]}],
            kpis=[{
                "kpi": "Moves processed without manual handling",
                "kpiType": "outcome", "unit": "%", "outcomeLens": "Z",
                "baseline": "", "target": "", "dataSource": "case system",
                "frequency": "monthly", "kviRollup": "KVI 5 (Digital)",
            }],
        ),
    }
    validate_instance(recipe, "recipe.schema.json")


def test_service_block_rejects_unknown_field_and_bad_point():
    recipe = {
        "id": "probe-hcs",
        "title": "Schema-probe onbekend veld",
        "version": "1.0.0",
        "inputs": {}, "outputs": {},
        "steps": [{"id": "s1", "processId": "x", "inputs": {}}],
        "riskLevel": "low",
        "service": {"dish": "the-key", "serviceType": "reactive", "onbekend": True},
    }
    with pytest.raises(Exception):
        validate_instance(recipe, "recipe.schema.json")

    recipe["service"] = {"dish": "the-key", "serviceType": "reactive",
                         "genAiTestPoints": [{"point": "G9", "description": "bestaat niet"}]}
    with pytest.raises(Exception):
        validate_instance(recipe, "recipe.schema.json")


RUN_MIN = {
    "schemaVersion": "1.0",
    "runId": "thk-08-move-home-sanne-20261009T000000Z",
    "generatedAt": "2026-10-09T00:00:00Z",
    "recipeId": "thk-08-move-home",
    "processId": "hcs-life-event-run",
    "mode": "replay",
    "scenario": "sanne",
    "steps": [{
        "stepId": "intake", "title": "Life event & intake", "actor": "agent",
        "genAiTestPoint": "G1", "dataUsed": ["BRP (Haal Centraal)"],
        "consent": "n.v.t.", "handover": None, "kpiEvents": [],
        "prov": {"sources": ["BRP (Haal Centraal)"]},
    }],
    "stopConditions": [{"id": "sc-1", "condition": "mens-overnames > 20%", "action": "pauzeer"}],
    "kpiSnapshot": [{"kpi": "Moves processed without manual handling", "baseline": "", "target": ""}],
}


def test_hcs_run_schema():
    validate_instance(RUN_MIN, "hcs-run.schema.json")
    bad = dict(RUN_MIN, steps=[dict(RUN_MIN["steps"][0], actor="robot")])
    with pytest.raises(Exception):
        validate_instance(bad, "hcs-run.schema.json")
    bad2 = dict(RUN_MIN, steps=[dict(RUN_MIN["steps"][0], handover={"reden": "x"})])
    with pytest.raises(Exception):
        validate_instance(bad2, "hcs-run.schema.json")  # handover vereist reason+to


def test_hcs_baseline_schema():
    baseline = {
        "recipeId": "thk-08-move-home",
        "publicOutcome": "verhuizen is één gesorteerde reis",
        "disappearingStep": "herhaalde loketbezoeken",
        "kpis": [{"kpi": "Moves processed without manual handling", "kpiType": "outcome",
                  "unit": "%", "outcomeLens": "Z"}],
        "stopConditions": [{"condition": "c", "action": "a"}],
        "goNoGo": ["accuracy ≥ 95% op testbank-personas"],
    }
    validate_instance(baseline, "hcs-baseline.schema.json")
    with pytest.raises(Exception):
        validate_instance(dict(baseline, kpis=[{"kpi": "x"}]), "hcs-baseline.schema.json")


LIFE_FIXTURES = HCS_ROOT / "fixtures" / "life-events"
EXPECTED_LIFE = {"thk-08-move-home", "thk-02-having-a-baby", "thk-24-build-renovate"}


def test_life_event_fixtures_present_and_consistent():
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text())
    assert set(common["parties"].keys()) >= {"gemeente", "energie", "bank", "verzekeraar", "zorgverzekeraar"}
    found = {p.stem for p in LIFE_FIXTURES.glob("*.json")}
    assert found == EXPECTED_LIFE
    for path in LIFE_FIXTURES.glob("*.json"):
        fx = json.loads(path.read_text())
        persona_ids = {p["id"] for p in fx["personas"]}
        assert len(persona_ids) >= 2
        assert len(fx["steps"]) == 5  # de vijf blueprint-stappen
        for step in fx["steps"]:
            for pid in step.get("perPersona", {}):
                assert pid in persona_ids, f"onbekende persona {pid} in {path.name}"
        assert fx["stopConditions"], "poort 5: stopcondities verplicht"
        assert fx["kpiSnapshot"], "poort 1: KPI-snapshot verplicht"
