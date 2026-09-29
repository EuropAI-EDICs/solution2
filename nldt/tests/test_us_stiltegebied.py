from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from services.common import us_stiltegebied as kern
from services.common import urbanstrategy_client as us

FIXDIR = Path(__file__).resolve().parents[1] / "fixtures" / "urbanstrategy"
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "us-stiltegebied-eval.schema.json"

# Square covering r-kern-* points (~5.12–5.13, 52.095–52.10)
STILLE_KERN = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"name": "stille_kern"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[5.11, 52.09], [5.13, 52.09], [5.13, 52.105],
                             [5.11, 52.105], [5.11, 52.09]]],
        },
    }],
}

# Ring-ish buffer covering r-buf-* (~5.135–5.14)
BUFFERZONE = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"name": "bufferzone"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[5.13, 52.09], [5.15, 52.09], [5.15, 52.105],
                             [5.13, 52.105], [5.13, 52.09]]],
        },
    }],
}


def test_evaluate_classifies_and_flags_exceedances():
    receptors = us.load_fixture("fixture://receptors-demo.geojson")
    result = kern.evaluate(receptors, STILLE_KERN, BUFFERZONE)

    assert result["counts"]["receptorsTotal"] == 5
    assert result["counts"]["inStilleKern"] == 2
    assert result["counts"]["inBufferzone"] == 2
    assert result["counts"]["outside"] == 1
    assert result["counts"]["exceedancesStilleKern"] == 1  # r-kern-hi 42.5 > 40
    assert result["counts"]["exceedancesBufferzone"] == 1  # r-buf-hi 47.1 > 45
    assert result["counts"]["exceedancesTotal"] == 2
    assert result["normCardId"] == "NC-W-11"
    assert result["formalRuleId"] == "FR-W-11"

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(result)


def test_evaluate_combined_stiltegebied_uses_stricter_threshold():
    receptors = us.load_fixture(str(FIXDIR / "receptors-demo.geojson"))
    # Treat whole area as stille kern only
    combined = {
        "type": "FeatureCollection",
        "features": STILLE_KERN["features"] + BUFFERZONE["features"],
    }
    result = kern.evaluate(receptors, combined, None)
    assert result["counts"]["inBufferzone"] == 0
    assert result["counts"]["exceedancesStilleKern"] >= 1
    assert any("bufferzone empty" in c for c in result["caveats"])


def test_evaluate_rejects_bad_input():
    with pytest.raises(kern.UsStiltegebiedError):
        kern.evaluate({"type": "Feature"}, STILLE_KERN, BUFFERZONE)
