"""Validatie-engine: geconfigureerde voorwaarden en ontbrekende velden worden
gecontroleerd; het systeem beslist niet autonoom maar benoemt blokkades en
waarschuwingen met correctiepad (FR-13)."""

from pathlib import Path

from core import catalog, validate

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def _formulier(euroklasse="Euro 6", ontbrekend=None):
    waarden = {"kenteken": "1-ABC-123", "euroklasse": euroklasse, "brandstof": "diesel",
               "adres-werkzaamheden": "Korenmarkt 1, Gent", "omschrijving-werkzaamheden": "herstelwerken",
               "aanvrager": "ondernemer"}
    velden = [{"veld": v, "waarde": w, "label": "authentiek" if v in ("kenteken", "euroklasse", "brandstof") else "gebruiker",
               "bron": "test"} for v, w in waarden.items()]
    return {"service": "ontheffing-lez", "velden": velden, "ontbrekend": ontbrekend or []}


def test_euro6_is_gereed_zonder_bevindingen():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier())
    assert resultaat == {"status": "gereed", "bevindingen": []}


def test_euro5_geeft_waarschuwing():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier(euroklasse="Euro 5"))
    assert resultaat["status"] == "gereed-met-waarschuwing"
    assert resultaat["bevindingen"][0]["id"] == "V2-euroklasse"


def test_euro4_geeft_blokkade_met_correctiepad():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier(euroklasse="Euro 4"))
    assert resultaat["status"] == "blokkade"
    assert resultaat["bevindingen"][0]["ernst"] == "blokkade"
    assert "Vervang" in resultaat["bevindingen"][0]["melding"]


def test_ontbrekend_gegeven_is_automatische_blokkade():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier(ontbrekend=["kenteken"]))
    bevindingen = {b["id"] for b in resultaat["bevindingen"]}
    assert "V0-kenteken" in bevindingen
    assert resultaat["status"] == "blokkade"
