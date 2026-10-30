"""Centrale registratie: recipe + baseline bestaan en sluiten op het pakket aan."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_recipe_en_baseline_geregistreerd_en_consistent():
    recipe = json.loads((REPO / "nldt" / "recipes" / "gent-mobiliteit-ondernemer.json").read_text(encoding="utf-8"))
    baseline = json.loads((REPO / "nldt" / "recipes" / "baselines" / "gent-mobiliteit-ondernemer.baseline.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPO / "poc-gent" / "packages" / "gent-mobiliteit-ondernemer" / "manifest.json").read_text(encoding="utf-8"))
    assert recipe["service"]["lifeEventCode"] == manifest["lifeEventCode"] == "GT-MOB-01"
    assert recipe["requiredProcesses"] == ["gent-transactional-run"]
    assert baseline["stopConditions"] and baseline["goNoGo"]
