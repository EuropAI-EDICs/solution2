import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import contracts  # noqa: E402

TRACKS = ("wind", "zon", "energietoets")
_BE_TYPES = {"rup-be", "gewestplan-be", "vcro-be"}


def _load(rel: str):
    return json.loads((ROOT / "corpus" / rel).read_text(encoding="utf-8"))


def test_be_normcards_gebruiken_be_instrumenten():
    for track in TRACKS:
        evidence = {e["id"]: e for e in _load(f"evidence-be-{track}.json") if e.get("verified")}
        kaarten = _load(f"normcards-be-{track}.json")
        assert kaarten, f"geen BE-normcards voor {track}"
        for k in kaarten:
            contracts.validate(k, "norm-card")
            assert k["jurisdictie"] == "be"
            assert k["instrumentType"] in _BE_TYPES
            assert k["evidenceId"] in evidence, k["id"]
            bron = evidence[k["evidenceId"]]["sourceUrl"]
            assert bron.startswith("http"), "BE-evidence moet een publieke bron-URL hebben"


def test_be_formal_rules_linken_op_be_kaarten():
    for track in TRACKS:
        kaarten = {k["id"] for k in _load(f"normcards-be-{track}.json")}
        for fr in _load(f"formal-rules-be-{track}.json"):
            contracts.validate(fr, "formal-rule")
            assert fr["jurisdictie"] == "be"
            assert fr["instrumentType"] in _BE_TYPES
            assert fr["normCardId"] in kaarten, fr["id"]
