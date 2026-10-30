"""Prefill-engine: elk formulierveld draagt zichtbaar herkomstlabel en bron;
authentieke velden komen uit de Magda-mock, gespreksvelden uit de context
(FR-11, once-only)."""

from pathlib import Path

from core import catalog, context, prefill

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest
RECORDS = {"magda:kenteken": {"kenteken": "1-ABC-123", "euroklasse": "Euro 6", "brandstof": "diesel"}}


def _context():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken"}
    return context.build(MANIFEST, slots, POC_ROOT)


def test_authentiek_en_gebruiker_labels_zichtbaar_per_veld():
    ctx, herkomst = _context()
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, RECORDS)
    velden = {v["veld"]: v for v in formulier["velden"]}
    assert velden["kenteken"] == {"veld": "kenteken", "waarde": "1-ABC-123", "label": "authentiek", "bron": "magda:kenteken (mock v1)"}
    assert velden["adres-werkzaamheden"]["waarde"] == "Korenmarkt 1, Gent"
    assert velden["adres-werkzaamheden"]["label"] in ("gebruiker", "correctie", "afgeleid")
    assert formulier["ontbrekend"] == []


def test_afwezig_magda_record_landt_in_ontbrekend():
    ctx, herkomst = _context()
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, {})
    velden = {v["veld"]: v for v in formulier["velden"]}
    assert velden["kenteken"]["waarde"] is None
    assert velden["kenteken"]["label"] == "authentiek"
    assert set(formulier["ontbrekend"]) == {"kenteken", "euroklasse", "brandstof"}


def test_h1_correctie_draagt_door_naar_het_formulier():
    from core import gates
    ctx, herkomst = _context()
    ctx, herkomst = gates.confirm_h1(MANIFEST, ctx, herkomst, {"address": "Veldstraat 1, Gent"}, POC_ROOT)
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, RECORDS)
    velden = {v["veld"]: v for v in formulier["velden"]}
    assert velden["adres-werkzaamheden"]["waarde"] == "Veldstraat 1, Gent"
    assert velden["adres-werkzaamheden"]["label"] == "correctie"


def test_labelset_is_gesloten():
    ctx, herkomst = _context()
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, RECORDS)
    assert {v["label"] for v in formulier["velden"]} <= {"authentiek", "gebruiker", "correctie", "afgeleid"}
