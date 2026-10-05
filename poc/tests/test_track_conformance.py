# poc/tests/test_track_conformance.py
"""Data-driven conformatie voor nieuwe verordening-tracks.

Per manifest-track: shard-schema, letterlijkheid (citaat-containment tegen de
snapshot), bronresolutie en artikeldekking (shard ∪ ledger.articlesConsidered
== alle snapshot-artikelen van de hoofdstukken). De dekking wordt afgeleid
uit de snapshot zelf, niet handgetypt.
"""
import json
import re
import sys
from pathlib import Path

import pytest

POC = Path(__file__).resolve().parents[1]
SNAPSHOT = (POC.parent / "docs/research/sources/cvdr704250-tekst-extract.txt").read_text(encoding="utf-8")

SHARD_FIELDS = {"id", "sourceId", "instrument", "article", "quote_nl", "theme", "url", "verified", "notes"}


def snapshot_norm() -> str:
    return re.sub(r"\s+", " ", SNAPSHOT)


def chapter_articles(chapter: str) -> set[str]:
    return set(re.findall(rf"^Artikel {chapter}\.\d+[a-z]?", SNAPSHOT, flags=re.M))


def load_manifest() -> dict:
    return json.loads((POC / "corpus/track-manifest.json").read_text())["tracks"]


def test_chapter_articles_known_counts():  # snapshot-sanity van de afleider zelf
    assert "2.15" in {a.split()[-1] for a in chapter_articles("2")}
    assert "3.2" in {a.split()[-1] for a in chapter_articles("3")}
    assert len(chapter_articles("2")) > 30 and len(chapter_articles("3")) > 20


@pytest.mark.parametrize("track_id", ["water", "bodem", "mobiliteit", "landschap", "landbouw", "wonen", "biomassa"])
def test_track_conformance(track_id):
    tracks = load_manifest()
    if track_id not in tracks:
        pytest.skip(f"{track_id} nog niet in manifest (taak volgt)")
    entry = tracks[track_id]
    shard = json.loads((POC / entry["shard"]).read_text())
    ledger = json.loads((POC / entry["ledger"]).read_text())
    sources = json.loads((POC / "corpus/sources.json").read_text())
    source_ids = {s["id"] for s in sources}
    norm = snapshot_norm()

    covered: set[str] = set()
    for rec in shard:
        assert SHARD_FIELDS <= set(rec), rec.get("id")
        assert rec["verified"] is True
        assert rec["sourceId"] in source_ids
        assert rec["url"].startswith("https://")
        quote = re.sub(r"\s+", " ", rec["quote_nl"]).strip()
        assert quote in norm, f"citaat niet letterlijk in snapshot: {rec['id']} ({rec['article']})"
        m = re.match(r"Artikel (\d+\.\d+[a-z]?)", rec["article"])
        assert m, f"article-veld zonder artikelnummer: {rec['article']}"
        covered.add(m.group(1))
    considered = {a.split()[-1] for a in ledger.get("articlesConsidered", [])}
    expected = set().union(*({a.split()[-1] for a in chapter_articles(c)} for c in entry["chapters"]))
    missing = expected - covered - considered
    assert not missing, f"artikelen zonder thuis in {track_id}: {sorted(missing)}"
    assert set(entry["formalizableArticles"]) <= covered, "manifest belooft formaliseerbaar wat niet geciteerd is"


def test_multichapter_track_dekt_alle_hoofdstukken(monkeypatch, tmp_path):
    """Verplichte carry-forward (fase-1-review): een manifestentry met meerdere
    hoofdstukken moet dekking eisen over álle chapter-artikellijsten, niet
    alleen chapters[0]. Fixture: de bestaande fase-1 water+bodem-bestanden
    samengevoegd tot één mini-entry chapters ["2","3"], geïnjecteerd via
    monkeypatch op load_manifest.
    """
    tracks = load_manifest()
    shard = json.loads((POC / tracks["water"]["shard"]).read_text()) + json.loads((POC / tracks["bodem"]["shard"]).read_text())
    considered = (json.loads((POC / tracks["water"]["ledger"]).read_text()).get("articlesConsidered", [])
                  + json.loads((POC / tracks["bodem"]["ledger"]).read_text()).get("articlesConsidered", []))
    formalizable = sorted(set(tracks["water"]["formalizableArticles"]) | set(tracks["bodem"]["formalizableArticles"]))

    def inject_mini(considered_list: list) -> None:
        shard_file = tmp_path / "evidence-water-en-bodem.json"
        ledger_file = tmp_path / "normcards-rejected-water-en-bodem.json"
        shard_file.write_text(json.dumps(shard), encoding="utf-8")
        ledger_file.write_text(json.dumps({"articlesConsidered": considered_list}), encoding="utf-8")
        entry = {"chapters": ["2", "3"], "shard": str(shard_file), "ledger": str(ledger_file),
                 "formalizableArticles": formalizable}
        monkeypatch.setattr(sys.modules[__name__], "load_manifest", lambda: {"water_en_bodem": entry})

    # complete mini-entry: de gate accepteert een multi-hoofdstuktrack
    inject_mini(considered)
    test_track_conformance("water_en_bodem")

    # carry-forward-gat: H3-artikel "3.1" (alleen via considered gedekt) zonder
    # thuis moet afkeuren; op chapters[0]-code blijft dit onopgemerkt (geen raise)
    inject_mini([a for a in considered if a.split()[-1] != "3.1"])
    with pytest.raises(AssertionError, match="zonder thuis"):
        test_track_conformance("water_en_bodem")
