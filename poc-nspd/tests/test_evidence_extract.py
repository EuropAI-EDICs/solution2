import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.evidence_extract import extract_candidates, merge_brondocumenten  # noqa: E402

_MINI_TEKST = """\
Hoofdstuk 3 Energie
Artikel 3.5 Windenergie
1  Binnen het provinciale windgebied zijn windturbines toegelaten tot een
   maximale tiphoogte van 220 meter.
2  Buiten het windgebied zijn windturbines verboden.
Artikel 3.6 Zonnevelden
1  Zonnevelden zijn toegelaten in het landelijk gebied, mits landschappelijk
   ingepast.
"""


def test_extract_candidates_vindt_artikelen_per_trefwoord(tmp_path):
    bron = tmp_path / "tekst.txt"
    bron.write_text(_MINI_TEKST, encoding="utf-8")
    kandidaten = extract_candidates(
        tekst=bron.read_text(encoding="utf-8"),
        track="wind",
        trefwoorden=("windturbine", "windenergie"),
        jurisdictie="nl",
        source_url="https://lokaleregelgeving.overheid.nl/CVDR709135",
    )
    assert len(kandidaten) == 1
    k = kandidaten[0]
    assert k["id"] == "EVW-01"
    assert k["locator"] == "Artikel 3.5"
    assert "tiphoogte" in k["quote"]
    assert k["jurisdictie"] == "nl"


def test_extract_candidates_met_bron_label_plaatst_bron_in_record():
    bron = tmp_bron_tekst()
    kandidaten = extract_candidates(
        tekst=bron,
        track="wind",
        trefwoorden=("windturbine",),
        jurisdictie="be",
        source_url="https://example.org/rup",
        bron_label="rup-zeehaven-gent-fase2",
    )
    assert len(kandidaten) == 1
    assert kandidaten[0]["bron"] == "rup-zeehaven-gent-fase2"
    # bron_label verdwijnt uit de quote-opmaak: quote blijft bloktekst
    assert "rup-zeehaven-gent-fase2" not in kandidaten[0]["quote"]


def test_extract_candidates_zonder_bron_label_heeft_geen_bron_veld():
    kandidaten = extract_candidates(
        tekst=tmp_bron_tekst(),
        track="wind",
        trefwoorden=("windturbine",),
        jurisdictie="nl",
        source_url="https://lokaleregelgeving.overheid.nl/CVDR709135",
    )
    assert len(kandidaten) == 1
    assert "bron" not in kandidaten[0]


def tmp_bron_tekst() -> str:
    return (
        "Artikel 1. Zone voor bedrijven\n"
        "In dit gebied is de plaatsing van een windturbine toegelaten.\n"
    )


def test_merge_brondocumenten_leest_meta_en_txtlagen(tmp_path):
    (tmp_path / "a.txt").write_text("tekst A\n", encoding="utf-8")
    # b.pdf heeft geen .txt-laag -> moet worden overgeslagen
    (tmp_path / "b.pdf").write_bytes(b"%PDF-")
    meta = {
        "instrumenten": [
            {"id": "inst-a", "titel": "Titel A", "bestand": "a.pdf"},
            {"id": "inst-b", "titel": "Titel B", "bestand": "b.pdf"},
        ]
    }
    meta_path = tmp_path / "META.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    docs = merge_brondocumenten(meta_path)
    assert docs == [("inst-a", "Titel A", "tekst A\n")]
