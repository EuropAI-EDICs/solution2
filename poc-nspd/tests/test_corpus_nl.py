import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

META_PATH = ROOT / "corpus" / "nl" / "CVDR709135" / "META.json"


def test_corpus_nl_aanwezig_en_verifieerbaar():
    base = META_PATH.parent
    assert META_PATH.is_file(), "taak 2 nog niet uitgevoerd (META.json ontbreekt)"
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    assert meta["cvdrId"] == "CVDR709135"
    assert meta["titel"].lower().startswith("omgevingsverordening")
    assert meta["consolidatieDatum"], "geldende versie-datum moet vastgelegd zijn"
    html = (base / "index.html").read_bytes()
    assert hashlib.sha256(html).hexdigest() == meta["sha256Html"]
    tekst = (base / "tekst.txt").read_text(encoding="utf-8")
    assert "windturbine" in tekst.lower() or "windenergie" in tekst.lower()
