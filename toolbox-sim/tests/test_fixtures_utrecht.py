# toolbox-sim/tests/test_fixtures_utrecht.py
import json
from pathlib import Path

import pytest

from build_fixtures import CANONICAL_RUNS, build_utrecht_batch, zone_role

REPO = Path(__file__).resolve().parents[2]
WIND = CANONICAL_RUNS["utrecht-wind"]


def _load(name: str):
    return json.loads((WIND / name).read_text())


@pytest.mark.parametrize("key", ["utrecht-wind", "utrecht-zon", "utrecht-bos"])
def test_batch_counts_match_artifacts(key):
    run_dir = CANONICAL_RUNS[key]
    batch = build_utrecht_batch(run_dir)
    by_type = {}
    for e in batch:
        by_type.setdefault(e["type"], []).append(e)
    assert len(by_type["ldt:OpportunityZone"]) == len(json.loads((run_dir / "zones.json").read_text()))
    assert len(by_type["ldt:FormalRule"]) == len(json.loads((run_dir / "formalrules.json").read_text()))
    assert len(by_type["ldt:NormCard"]) == len(json.loads((run_dir / "normcards.json").read_text()))
    assert len(by_type["ldt:PipelineRun"]) == 1


def test_zone_entity_shape_and_grounding():
    batch = build_utrecht_batch(WIND)
    zones = [e for e in batch if e["type"] == "ldt:OpportunityZone"]
    rules = {e["id"] for e in batch if e["type"] == "ldt:FormalRule"}
    run = [e for e in batch if e["type"] == "ldt:PipelineRun"][0]
    for z in zones:
        assert z["location"]["type"] == "GeoProperty"
        assert z["location"]["value"]["type"] in {"Polygon", "MultiPolygon"}
        assert isinstance(z["areaKm2"]["value"], float)
        assert z["zoneRole"]["value"] in {"final", "inclusion", "exclusion", "marker", "other"}
        for ref in z["derivedFromRule"]["object"]:
            assert ref in rules  # geen zwevende randen
        assert z["generatedBy"]["object"] == run["id"]
    assert run["verdict"]["value"] == "pass"
    assert run["runId"]["value"] == "20260830T113234Z-wind"


def test_rule_and_normcard_chain():
    batch = build_utrecht_batch(WIND)
    rules = [e for e in batch if e["type"] == "ldt:FormalRule"]
    cards = {e["id"] for e in batch if e["type"] == "ldt:NormCard"}
    for r in rules:
        assert r["groundedIn"]["object"] in cards
    for c in [e for e in batch if e["type"] == "ldt:NormCard"]:
        assert c["cites"]["object"].startswith("http")


def test_unique_ids_and_sorted():
    batch = build_utrecht_batch(WIND)
    ids = [e["id"] for e in batch]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_deterministic_bytes(tmp_path):
    import hashlib

    from build_fixtures import write_batch

    p1, p2 = tmp_path / "a.jsonld", tmp_path / "b.jsonld"
    write_batch(p1, build_utrecht_batch(WIND))
    write_batch(p2, build_utrecht_batch(WIND))
    assert hashlib.sha256(p1.read_bytes()).digest() == hashlib.sha256(p2.read_bytes()).digest()


def test_zone_role_derivation():
    assert zone_role("ZR-final-opportunity-xyz") == "final"
    assert zone_role("ZR-inclusion_union-813") == "inclusion"
    assert zone_role("ZR-exclusion_natura-1") == "exclusion"
    assert zone_role("ZR-marker_groene_contour-2") == "marker"
    assert zone_role("ZR-something") == "other"
