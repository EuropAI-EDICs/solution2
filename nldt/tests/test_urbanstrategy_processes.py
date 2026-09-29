from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from services.common import urbanstrategy_client as us
from services.process_adapter.handlers import (
    PROCESS_DEFINITIONS,
    describe_process,
    execute_local,
)

FIXDIR = Path(__file__).resolve().parents[1] / "fixtures" / "urbanstrategy"
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "us-stiltegebied-eval.schema.json"

STILLE_KERN = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[5.11, 52.09], [5.13, 52.09], [5.13, 52.105],
                             [5.11, 52.105], [5.11, 52.09]]],
        },
    }],
}


def test_us_processes_listed():
    assert "us-fetch-noise-receptors" in PROCESS_DEFINITIONS
    assert "us-stiltegebied-noise-eval" in PROCESS_DEFINITIONS
    assert describe_process("us-fetch-noise-receptors")["id"] == "us-fetch-noise-receptors"


def test_us_fetch_from_fixture():
    out = execute_local(
        "us-fetch-noise-receptors",
        {"source": "fixture://receptors-demo.geojson"},
    )
    assert len(out["receptors"]["features"]) == 5


def test_us_stiltegebied_eval_process():
    receptors = us.load_fixture("fixture://receptors-demo.geojson")
    out = execute_local(
        "us-stiltegebied-noise-eval",
        {
            "receptors": receptors,
            "stilleKern": STILLE_KERN,
            "bufferzone": {"type": "FeatureCollection", "features": []},
        },
    )
    evaluation = out["evaluation"]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(evaluation)
    assert evaluation["counts"]["exceedancesStilleKern"] >= 1
