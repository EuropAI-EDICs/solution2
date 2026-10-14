"""Quote-literaliteitsguard (fase 2, task 1A): elke normcard-quote moet een
whitespace-genormaliseerde substring zijn van de .txt-laag van het eigen
docId (cite-or-abstain, fase-1-reviewpraktijk).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import quote_guard  # noqa: E402


def test_alle_bestaande_normcards_letterlijk():
    """Uiteindelijke acceptatie: alle 16 fase-1-kaarten (nl+be, 3 tracks)
    slagen op de genormaliseerde substring-check."""
    meldingen = quote_guard.verify_all()
    assert meldingen == [], f"quotes niet letterlijk: {meldingen}"


def test_faalpad_kapote_kaart_in_tmp_corpus(tmp_path):
    """Faalpad: één kapotte kaart in een tmp-corpus → precies één melding
    met kaart-id en docId; de goede kaart op hetzelfde docId blijft stil."""
    corpus = tmp_path
    (corpus / "corpus" / "nl" / "CVDR709135").mkdir(parents=True)
    (corpus / "corpus" / "nl" / "CVDR709135" / "tekst.txt").write_text(
        "Artikel 1. Een omgevingsplan kan voorzien in de realisatie van een "
        "nieuwe windturbine binnen een globaal aangegeven locatie.\n",
        encoding="utf-8")
    goed = {
        "id": "NC-TEST-01", "source": {
            "docId": "S01",
            "quote": "Een omgevingsplan kan voorzien in de realisatie van een nieuwe "
                     "windturbine binnen een globaal aangegeven locatie."}}
    kapot = {
        "id": "NC-TEST-02", "source": {
            "docId": "S01",
            "quote": "Een omgevingsplan kan voorzien in de realisatie van twee "
                     "windturbines binnen een globaal aangegeven locatie."}}
    (corpus / "corpus" / "normcards-nl-test.json").write_text(
        json.dumps([goed, kapot]), encoding="utf-8")
    meldingen = quote_guard.verify_all(corpus_root=corpus)
    assert meldingen == ["NC-TEST-02: quote niet letterlijk in S01"]


def test_normalisatie_tolerant_voor_whitespace_en_leesteken():
    """De fase-1-normalisatie: whitespace-collapse + geen spatie vóór
    leesteken (PDF-extractie-artefacten) mag het citaat niet breken."""
    assert quote_guard._normalize(
        "woord ,  volgende.\n\tzin") == "woord, volgende. zin"
