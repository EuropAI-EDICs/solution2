"""Uitdagingen-curation: 5 opgaven die samen exact de 13 tracks dekken."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UJV = ROOT / "scenarios" / "uitdagingen.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline import contracts  # noqa: E402

ALLE_TRACKS = {
    "wind", "zon", "bos", "water", "bodem", "mobiliteit", "landschap",
    "landbouw", "wonen", "werken", "recreatie", "biomassa", "energietoets",
}


def _load() -> dict:
    return json.loads(UJV.read_text(encoding="utf-8"))


def test_vijf_uitdagingen_dekken_exact_de_13_tracks():
    u = _load()
    assert len(u["uitdagingen"]) == 5
    seen: list[str] = []
    for uit in u["uitdagingen"]:
        assert set(uit) == {"id", "titel", "tracks"}
        assert uit["id"] and uit["titel"]
        seen.extend(uit["tracks"])
    assert sorted(seen) == sorted(ALLE_TRACKS)
    assert len(seen) == len(set(seen)), "elke track in precies één uitdaging"


SET_IDS = {
    "wind": 3, "zon": 3, "bos": 3, "water": 3, "bodem": 3, "mobiliteit": 3,
    "landschap": 3, "landbouw": 3, "wonen": 3, "werken": 3, "recreatie": 3,
    "biomassa": 3, "energietoets": 2,  # plan 2 maakt dit 3 (SC-ET-NETCONGESTIE)
}


def test_demo_sets_tellen_exact_3_scenarios_per_track():
    for track, n in SET_IDS.items():
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        assert s["useCase"] == track, track
        assert len(s["scenarios"]) == n, track
        ids = [sc["id"] for sc in s["scenarios"]]
        assert len(ids) == len(set(ids)), f"dubbele ids in {track}"


def test_wind_set_bevat_hetzelfde_drietal():
    s = json.loads((ROOT / "scenarios" / "wind.json").read_text(encoding="utf-8"))
    assert [sc["id"] for sc in s["scenarios"]] == [
        "SC-W-NNN-EXCEPTION", "SC-W-STILTE-HARD", "SC-W-NATURA-SETBACK"]


# --------------------------------------------------------------------------- #
# Curation-contract: id-resolutie t.o.v. de baseline-runs, basis-verdeling en
# de featured pass-runs in uitdagingen.json::scenarioRuns.
# --------------------------------------------------------------------------- #

BASELINES = {
    "wind": "20260830T113234Z-wind", "zon": "20260830T142439Z-zon",
    "bos": "20260830T142446Z-bos", "water": "20261004T185116Z-water",
    "bodem": "20261004T185509Z-bodem", "mobiliteit": "20261005T072839Z-mobiliteit",
    "landschap": "20261005T070621Z-landschap", "landbouw": "20261005T094244Z-landbouw",
    "wonen": "20261005T100258Z-wonen", "werken": "20261006T121921Z-werken",
    "recreatie": "20261006T114934Z-recreatie", "biomassa": "20261006T120133Z-biomassa",
    "energietoets": "20261006T171730Z-energietoets",
}


def test_elke_basis_normcardid_resolvet_in_baseline():
    for track in ALLE_TRACKS:
        cards = json.loads(
            (ROOT / "runs" / BASELINES[track] / "normcards.json")
            .read_text(encoding="utf-8"))
        cards = cards if isinstance(cards, list) else cards.get("normCards", [])
        card_ids = {c["id"] for c in cards}
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        for sc in s["scenarios"]:
            nc = sc["basis"].get("normCardId")
            if nc:
                assert nc in card_ids, f"{sc['id']}: {nc} niet in baseline {track}"


def test_elke_mutation_ruleid_resolvet_in_baseline():
    for track in ALLE_TRACKS:
        rules = json.loads(
            (ROOT / "runs" / BASELINES[track] / "formalrules.json")
            .read_text(encoding="utf-8"))
        rules = rules.get("formalRules", rules) if isinstance(rules, dict) else rules
        rule_ids = {r["id"] for r in rules}
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        for sc in s["scenarios"]:
            for m in sc["mutations"]:
                assert m["ruleId"] in rule_ids, f"{sc['id']}: {m['ruleId']} niet in baseline {track}"


def test_basis_verdeling_volgt_curation_principe():
    for track in ALLE_TRACKS:
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        types = [sc["basis"]["type"] for sc in s["scenarios"]]
        assert types.count("policy_variant") >= 1, track
        assert types.count("hypothetical") >= 1 or types.count("policy_variant") >= 2, track
        for sc in s["scenarios"]:
            b = sc["basis"]
            if b["type"] == "hypothetical":
                assert "NOT legally grounded" in b["provenanceNote"], sc["id"]


def test_scenarioRuns_wijzen_naar_bestaande_pass_runs():
    for track, run in _load()["scenarioRuns"].items():
        assert run is not None, track
        rep = json.loads(
            (ROOT / "scenario-runs" / run / "scenario-report.json")
            .read_text(encoding="utf-8"))
        assert rep["verdict"] == "pass", track


def test_scenarioRuns_shape_dekt_alle_tracks():
    runs = _load()["scenarioRuns"]
    assert set(runs.keys()) == ALLE_TRACKS
    for track, run in runs.items():
        assert run is None or isinstance(run, str), track


def test_set_bestanden_valideren_tegen_contract_schemas():
    for track in ALLE_TRACKS:
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        contracts.validate(s, "scenario-set")
        for sc in s["scenarios"]:
            contracts.validate(sc, "scenario-spec")


# --------------------------------------------------------------------------- #
# Landelijke bronnen (kalibratie plan 2 task 3): 8 nationale registry-entries —
# context-rollen plus één scenario-basis voor SC-ET-NETCONGESTIE. Nooit een
# juridische rol: data onderbouwt, wet- en regelgeving beslist.
# --------------------------------------------------------------------------- #

NATIONALE_BRONNEN = {
    "cbs-grid-kerncijfers-100m": "context",
    "cbs-landgebruik-100m": "context",
    "rce-monumenten": "context",
    "rce-iam-archeologie": "context",
    "dino-bro-ondergrond": "context",
    "rws-nwb-wegen": "context",
    "prorail-spoor": "context",
    "netbeheerder-netcongestie": "scenario-basis",
}


def test_nationale_bronnen_staan_in_registry_met_juiste_rol():
    reg = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    items = reg.get("sources", reg) if isinstance(reg, dict) else reg
    by_id = {it["id"]: it for it in items}
    for sid, role in NATIONALE_BRONNEN.items():
        assert sid in by_id, sid
        assert by_id[sid].get("role") == role, sid
        assert "serviceUrl" in by_id[sid] or "url" in by_id[sid], sid


def test_nationale_bronnen_dragen_geen_juridische_rol():
    reg = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    items = reg.get("sources", reg) if isinstance(reg, dict) else reg
    juridisch = {"inclusion", "exclusion", "conditional", "attention", "compensation"}
    for it in items:
        if it["id"] in NATIONALE_BRONNEN:
            assert it.get("role") not in juridisch, it["id"]
