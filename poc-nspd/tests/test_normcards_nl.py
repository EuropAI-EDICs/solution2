import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import contracts  # noqa: E402

TRACKS = ("wind", "zon", "energietoets")


def _load(rel: str):
    return json.loads((ROOT / "corpus" / rel).read_text(encoding="utf-8"))


def test_nl_normcards_schema_en_evidence_links():
    for track in TRACKS:
        evidence = {e["id"] for e in _load(f"evidence-nl-{track}.json") if e.get("verified")}
        kaarten = _load(f"normcards-nl-{track}.json")
        assert kaarten, f"geen normcards voor {track}"
        for k in kaarten:
            contracts.validate(k, "norm-card")
            assert k["jurisdictie"] == "nl"
            assert k["evidenceId"] in evidence, k["id"]


def test_nl_formal_rules_schema_en_kaartlinks():
    for track in TRACKS:
        kaarten = {k["id"] for k in _load(f"normcards-nl-{track}.json")}
        for fr in _load(f"formal-rules-nl-{track}.json"):
            contracts.validate(fr, "formal-rule")
            assert fr["jurisdictie"] == "nl"
            assert fr["normCardId"] in kaarten, fr["id"]
