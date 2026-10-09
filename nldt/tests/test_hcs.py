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
