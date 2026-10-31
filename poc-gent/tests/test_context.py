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


def test_summary_contextzin_is_per_pakket_configureerbaar():
    manifest = {**MANIFEST, "texts": {**MANIFEST["texts"],
                                      "contextZin": "U bent {applicantType} en wilt: {activity}."}}
    ctx = {"applicantType": "ondernemer", "activity": "herstelwerken", "address": "Korenmarkt 1, Gent"}
    herkomst = {s: {"label": "gebruiker", "bron": "gesprek"} for s in ctx}
    som = context.summary(manifest, ctx, herkomst)
    assert som["tekst"] == "U bent ondernemer en wilt: herstelwerken."


def test_summary_default_zin_blijft_ongewijzigd_oud_gedrag():
    ctx = {"applicantType": "burger", "address": "Veldstraat 1, Gent"}  # geen activity
    herkomst = {s: {"label": "gebruiker", "bron": "gesprek"} for s in ctx}
    som = context.summary(MANIFEST, ctx, herkomst)
    assert som["tekst"] == "U bent burger en wilt: onbekend. Adres: Veldstraat 1, Gent."


def test_summary_noemt_datacheck_outputs_met_herkomst():
    manifest = {**MANIFEST, "dataChecks": [
        {"id": "afvalkalender", "dataset": "ivago-ophaalkalender", "input": "address",
         "outputs": ["afvalPmd"], "unknownPolicy": "fallback"}]}
    ctx = {"applicantType": "ondernemer", "address": "Veldstraat 1, Gent",
           "afvalPmd": "maandag"}
    herkomst = {s: {"label": "gebruiker", "bron": "gesprek"} for s in ctx}
    herkomst["afvalPmd"] = {"label": "afgeleid", "bron": "dataset:ivago-ophaalkalender (test)"}
    som = context.summary(manifest, ctx, herkomst)
    regel = next(r for r in som["regels"] if r["feit"] == "afvalPmd")
    assert regel["waarde"] == "maandag" and regel["bron"].startswith("dataset:")


def test_build_voert_datachecks_uit_naast_gis():
    manifest = {**MANIFEST, "dataChecks": [
        {"id": "afvalkalender", "dataset": "ivago-ophaalkalender", "input": "address",
         "outputs": ["afvalPmd", "afvalRest"], "unknownPolicy": "fallback"}]}
    ctx, herkomst = context.build(manifest, {"applicantType": "burger",
                                             "address": "Veldstraat 1, Gent"}, POC_ROOT)
    assert ctx["afvalPmd"] == "maandag"   # echte IVAGO-cache: Veldstraat Z1B
    assert herkomst["afvalPmd"]["bron"].startswith("dataset:ivago-ophaalkalender")
