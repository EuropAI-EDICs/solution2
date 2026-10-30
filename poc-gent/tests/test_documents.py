"""Documentenmodule: compleetheid, type, grootte en scan (FR-12; OCR assisterend — buiten F3)."""

from pathlib import Path

from core import catalog, documents

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def test_verplicht_bewijs_ontbreekt_is_blokkade():
    uitslag = documents.controleer(MANIFEST, "ontheffing-lez", [])
    assert uitslag["volledig"] is False
    assert uitslag["bevindingen"][0]["id"] == "D0-kentekenbewijs"


def test_geldig_bewijs_is_volledig():
    uitslag = documents.controleer(
        MANIFEST, "ontheffing-lez",
        [{"id": "kentekenbewijs", "bestand": "k.pdf", "type": "pdf", "grootteKB": 240, "scanSchoon": True}])
    assert uitslag == {"volledig": True, "bevindingen": []}


def test_te_groot_bestand_is_blokkade():
    uitslag = documents.controleer(
        MANIFEST, "ontheffing-lez",
        [{"id": "kentekenbewijs", "bestand": "k.tiff", "type": "tiff", "grootteKB": 20480, "scanSchoon": True}])
    ids = {b["id"] for b in uitslag["bevindingen"]}
    assert ids == {"D1-kentekenbewijs", "D2-kentekenbewijs"}


def test_scan_niet_schoon_is_waarschuwing():
    uitslag = documents.controleer(
        MANIFEST, "ontheffing-lez",
        [{"id": "kentekenbewijs", "bestand": "k.pdf", "type": "pdf", "grootteKB": 240, "scanSchoon": False}])
    assert uitslag["volledig"] is False
    assert uitslag["bevindingen"][0]["ernst"] == "waarschuwing"
