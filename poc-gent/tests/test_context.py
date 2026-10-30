"""Contextpipeline: gate vraagt alleen ontbrekende niet-authentieke
verplichte slots; build koppelt GIS; summary draagt herkomst (FR-04/05/23)."""

from pathlib import Path

from core import catalog, context

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def test_gate_vraagt_alleen_verplichte_niet_authentieke_slots():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent"}
    vragen = context.open_questions(MANIFEST, slots)
    assert [v["slot"] for v in vragen] == ["activity"]
    assert vragen[0]["vraag"].startswith("Wat gaat u")


def test_gate_vraagt_noit_om_authentiek_slot_ook_niet_verplicht_beschikbaar():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken"}
    assert all(v["slot"] != "vehicle" for v in context.open_questions(MANIFEST, slots))


def test_build_berekent_zones_met_herkomst_afgeleid():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken"}
    ctx, herkomst = context.build(MANIFEST, slots, POC_ROOT)
    assert ctx["zoneLez"] == "in"
    assert ctx["zoneAutovrij"] == "in"
    assert herkomst["zoneLez"]["label"] == "afgeleid"
    assert herkomst["zoneLez"]["bron"].startswith("gis:gent-lez (")
    assert herkomst["address"]["label"] == "gebruiker"


def test_summary_noemt_elk_feit_met_herkomst():
    slots = {"applicantType": "ondernemer", "address": "Sint-Pietersplein 1, Gent", "activity": "herstelwerken"}
    ctx, herkomst = context.build(MANIFEST, slots, POC_ROOT)
    som = context.summary(MANIFEST, ctx, herkomst)
    feiten = {r["feit"] for r in som["regels"]}
    assert {"applicantType", "address", "activity", "zoneLez", "zoneAutovrij"} <= feiten
    assert "Sint-Pietersplein" in som["tekst"]
