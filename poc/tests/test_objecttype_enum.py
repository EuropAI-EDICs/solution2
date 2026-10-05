# poc/tests/test_objecttype_enum.py
import json
from pathlib import Path

import jsonschema
import pytest

POC = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((POC / "schemas/opportunity-map-request.schema.json").read_text())
NEW = ["riparian_development", "soil_activity", "roadside_development",
       "landscape_intervention", "agricultural_expansion", "housing_development"]


def _request(object_type: str) -> dict:
    return {
        "id": "0d9f61aa-4e8a-4b8f-8a3f-6f21cb1f0011",
        "objectType": object_type,
        "ambitions": ["water_safety"],
        "areaOfInterest": {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}, "crs": "EPSG:28992"},
        "policyStage": "programming",
        "effortBudget": {"maxSubagents": 10},
        "requestedAt": "2026-10-04T10:00:00Z",
    }


def test_new_objecttypes_validate():
    for object_type in NEW:
        jsonschema.validate(_request(object_type), SCHEMA)


def test_existing_objecttypes_still_validate():
    for object_type in ["wind_turbine", "solar_field", "forest_planting", "biomass_installation", "energy_storage"]:
        jsonschema.validate(_request(object_type), SCHEMA)


def test_ambition_mobility_safety_validates():
    request = _request("roadside_development")
    request["ambitions"] = ["mobility_safety"]
    jsonschema.validate(request, SCHEMA)


def test_existing_ambitions_still_validate():
    for ambition in ["energy", "nature", "climate_adaptation", "landscape", "heritage", "water_safety", "housing"]:
        request = _request("wind_turbine")
        request["ambitions"] = [ambition]
        jsonschema.validate(request, SCHEMA)


def test_ambition_agriculture_validates():
    # fase 3 (landbouw-track): de enum miste een landbouwwaarde
    request = _request("agricultural_expansion")
    request["ambitions"] = ["agriculture"]
    jsonschema.validate(request, SCHEMA)


def test_fase5_objecttypes_and_ambitions_validate():
    # fase 5 (werken + recreatie tracks)
    request = _request("business_development")
    request["ambitions"] = ["economic_vitality"]
    jsonschema.validate(request, SCHEMA)
    request = _request("recreation_development")
    request["ambitions"] = ["recreation"]
    jsonschema.validate(request, SCHEMA)


def test_unknown_objecttype_rejected():
    # negatieve kant van de enum (eindreview-backlog fase 1): een objectType
    # buiten de enum moet de request-gate laten falen, niet stil passeren.
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_request("zeppelin_mooring"), SCHEMA)


def test_unknown_ambition_rejected():
    request = _request("wind_turbine")
    request["ambitions"] = ["intergalactic_travel"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(request, SCHEMA)
