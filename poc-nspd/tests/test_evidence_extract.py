import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.evidence_extract import extract_candidates  # noqa: E402

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
