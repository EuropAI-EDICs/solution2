# toolbox-sim/tests/test_full_catalogue.py
"""Contract- en determinismetests voor de catalogus-apps (7 algoritmmodellen eerst)."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))

from app.algorithms import Ground, MODEL_IDS, MissingGround, SYNTHETIC, load_ground, run_model

FIXTURES = SIM_ROOT / "fixtures"


@pytest.fixture(scope="module")
def ground():
    return load_ground(FIXTURES)


def test_model_ids_compleet():
    assert set(MODEL_IDS) == {
        "neighbourhood-energy-demand", "building-environmental-footprint", "renovation-strategies",
        "urban-planning-vulnerability", "urban-mobility", "pollution-propagation", "police-routing",
    }
    assert SYNTHETIC == {"urban-mobility", "pollution-propagation", "police-routing"}


def test_energy_eist_parameter(ground):
    with pytest.raises(ValueError):
        run_model("neighbourhood-energy-demand", {}, ground)  # geen intensiteit verzinnen


def test_energy_berekent_over_echte_areas(ground):
    out = run_model("neighbourhood-energy-demand", {"intensity_kwh_per_m2_year": 10.0}, ground)
    assert out["outputs"]["area_m2_total"] > 0
    assert abs(out["outputs"]["kwh_total"] - out["outputs"]["area_m2_total"] * 10.0) < 0.2
    assert out["provenance"]["areas"].startswith("fixtures/ngsi-ld/eubd-buildings.jsonld")


def test_footprint_en_renovatie_grondslag(ground):
    fp = run_model("building-environmental-footprint", {"carbon_kg_per_m2": 200.0}, ground)
    assert fp["outputs"]["carbon_kg_total"] > 0
    rn = run_model("renovation-strategies", {}, ground)
    assert len(rn["outputs"]["priority_by_tile"]) > 0


def test_vulnerability_uit_peilen(ground):
    out = run_model("urban-planning-vulnerability", {}, ground)
    rows = out["outputs"]["peilgebieden"]
    assert rows and 0.0 <= rows[0]["index"] <= 1.0
    assert out["provenance"]["source"] == "fixtures/dp-temporal.jsonld#peilen_latest"


def test_synthetische_modellen_gemarkeerd(ground):
    for name in sorted(SYNTHETIC):
        out = run_model(name, {}, ground)
        assert out["synthetic"] is True and out["provenance"]["syntheticSeed"] is True


def test_determinisme(ground):
    a = run_model("urban-mobility", {}, ground)
    b = run_model("urban-mobility", {}, ground)
    assert a == b


def test_missing_ground():
    with pytest.raises(MissingGround) as exc:
        run_model("urban-planning-vulnerability", {}, Ground())
    assert exc.value.need == "peilen"


def test_unknown_model():
    with pytest.raises(KeyError):
        run_model("bestaat-niet", {}, Ground())
