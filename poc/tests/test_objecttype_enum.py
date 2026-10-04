# poc/tests/test_objecttype_enum.py
import json
from pathlib import Path

import jsonschema

SCHEMA = json.loads(Path("schemas/opportunity-map-request.schema.json").read_text())
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
