# toolbox-sim/tests/test_fixtures_full_catalogue.py
"""Nieuwe catalogus-fixtures: deterministisch en herleidbaar."""
import hashlib
import json
import sys
from pathlib import Path

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))

from build_fixtures import build_dp_temporal, build_participate_seed, copy_recipes

FIXTURES = SIM_ROOT / "fixtures"


def test_dp_temporal_knmi_instances_herleidbaar():
    entities = build_dp_temporal()
    knmi = entities["urn:ngsi-ld:WeatherObserved:knmi-260"]
    assert knmi["attribute"] == "rainfall"
    assert knmi["instances"][0]["value"] == 1.2  # eerste observatie uit observations.jsonl
    assert knmi["instances"] == sorted(knmi["instances"], key=lambda i: i["observedAt"])
    assert knmi["provenance"].startswith("lake://nldt-poc-lake/silver/timeseries/")


def test_dp_temporal_peilen_instances():
    entities = build_dp_temporal()
    peilen = entities["urn:ngsi-ld:WaterObserved:rijnland-peilen-latest"]
    assert peilen["instances"], "peilen_fixture leeg"
    first = peilen["instances"][0]
    assert first["unit"] == "mNAP"
    assert "T" in first["observedAt"] and first["observedAt"].endswith("Z")


def test_recipes_combined_dict():
    recipes = copy_recipes()
    assert "beleidskompas-omgevingsanalyse" in recipes
    assert all(isinstance(v, dict) for v in recipes.values())


def test_participate_seed_herleidbaar():
    seed = build_participate_seed()
    assert len(seed["proposals"]) == 3
    assert all(p["provenance"].startswith("canonical replay:") for p in seed["proposals"])


def test_fixturebestanden_deterministisch(tmp_path):
    # twee generatierondes geven byte-gelijke bestanden
    import subprocess
    for _ in range(2):
        subprocess.run(
            [sys.executable, str(SIM_ROOT / "build_fixtures.py"), "--catalogue-extras"],
            cwd=SIM_ROOT, check=True, capture_output=True,
        )
    shas = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (FIXTURES / "dp-temporal.jsonld", FIXTURES / "recipes.json", FIXTURES / "participate-seed.json")
    }
    subprocess.run(
        [sys.executable, str(SIM_ROOT / "build_fixtures.py"), "--catalogue-extras"],
        cwd=SIM_ROOT, check=True, capture_output=True,
    )
    for name, sha in shas.items():
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == sha, name
