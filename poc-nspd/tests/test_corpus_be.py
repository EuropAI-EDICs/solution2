import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BE_META = ROOT / "corpus" / "be" / "META.json"

_VERWACHT_MIN = {"rup-be": 2, "gewestplan-be": 1, "vcro-be": 1}


def test_corpus_be_minimale_instrumenten():
    assert BE_META.is_file(), "taak 3 nog niet uitgevoerd"
    meta = json.loads(BE_META.read_text(encoding="utf-8"))
    geteld: dict[str, int] = {}
    for ins in meta["instrumenten"]:
        assert ins["instrumentType"] in _VERWACHT_MIN, ins
        assert ins["bronUrl"].startswith("http"), ins["id"]
        bestand = BE_META.parent / ins["bestand"]
        assert bestand.is_file(), ins["id"]
        assert hashlib.sha256(bestand.read_bytes()).hexdigest() == ins["sha256"], ins["id"]
        geteld[ins["instrumentType"]] = geteld.get(ins["instrumentType"], 0) + 1
    for itype, minimum in _VERWACHT_MIN.items():
        assert geteld.get(itype, 0) >= minimum, f"minimaal {minimum}× {itype} vereist"
