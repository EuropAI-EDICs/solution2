"""Fase-2-curatievalidators (plan 2026-10-14-poc-nspd-fase2, taken 3-7).

Parametrisch over alle fase-2-tracks waarvan shards bestaan: schema-validiteit,
evidence-links (verified), allOf jurisdictie↔instrumentType, instrument- en
versie-overeenstemming met corpus/sources.json, en de quote-guard over het
hele corpus (ook de fase-1-kaarten).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import contracts  # noqa: E402
from pipeline.quote_guard import verify_all  # noqa: E402

FASE2_TRACKS = ("bos", "water", "bodem", "mobiliteit", "landschap",
                "landbouw", "wonen", "werken", "recreatie", "biomassa")

REGISTER = json.loads((ROOT / "corpus" / "sources.json").read_text(encoding="utf-8"))
_BE_TYPES = {"S02": "rup-be", "S03": "rup-be", "S04": "gewestplan-be", "S05": "vcro-be"}


def _shard(naam: str, land: str, track: str):
    pad = ROOT / "corpus" / f"{naam}-{land}-{track}.json"
    return json.loads(pad.read_text(encoding="utf-8")) if pad.is_file() else None


def _aanwezige_tracks():
    return [t for t in FASE2_TRACKS
            if _shard("normcards", "nl", t) is not None or _shard("normcards", "be", t) is not None]


@pytest.mark.parametrize("track,land", [(t, l) for t in _aanwezige_tracks() for l in ("nl", "be")])
def test_normcards_fase2_schema_en_links(track, land):
    kaarten = _shard("normcards", land, track)
    if kaarten is None:
        pytest.skip(f"geen {land}-shard voor {track} (later groepstaak)")
    if kaarten == []:
        # expliciete abstention: lege shard hoort bij een abstention-record in de ledger
        ledger = _shard("normcards-rejected", land, track) or []
        assert any("abstention" in str(r.get("reden", "")) for r in ledger), \
            f"lege shard {land}-{track} zonder abstention-record"
        pytest.skip(f"{land}-{track}: abstention (gedocumenteerde onthouding)")
    evidence = {e["id"]: e for e in _shard("evidence", land, track) or []}
    for k in kaarten:
        contracts.validate(k, "norm-card")
        assert k["jurisdictie"] == land
        assert k["evidenceId"] in evidence, k["id"]
        assert evidence[k["evidenceId"]]["verified"] is True
        docid = k["source"]["docId"]
        if land == "nl":
            assert docid == "S01" and k["instrumentType"] == "omgevingsverordening-nl"
        else:
            assert docid in _BE_TYPES and k["instrumentType"] == _BE_TYPES[docid]
        # instrumentbeschrijving en versie zijn register-conform
        assert k["source"]["version"] == REGISTER[docid]["version"], k["id"]
        assert k["source"]["uri"] == REGISTER[docid]["uri"], k["id"]
        assert k["appliesTo"]["track"] == track


@pytest.mark.parametrize("track,land", [(t, l) for t in _aanwezige_tracks() for l in ("nl", "be")])
def test_formal_rules_fase2_links(track, land):
    rules = _shard("formal-rules", land, track)
    if rules is None:
        pytest.skip(f"geen {land}-rules voor {track} (later groepstaak)")
    kaarten = {k["id"] for k in _shard("normcards", land, track) or []}
    from run import ZONE_SOURCES
    from pipeline.agents import ENGINE_OPERATIONS
    for fr in rules:
        contracts.validate(fr, "formal-rule")
        assert fr["jurisdictie"] == land
        assert fr["normCardId"] in kaarten, fr["id"]
        tags = fr["appliesTo"].get("contextTags", [])
        if fr["status"] == "formalized":
            # fase 3: alleen met een geregistreerde operatie én gepinde zone-alias
            assert fr["executableRef"] in ENGINE_OPERATIONS, fr["id"]
            assert set(fr.get("zoneSelector", {}).get("zoneIds", [])) <= set(ZONE_SOURCES), fr["id"]
            assert any(t.startswith("geometry_") or t.startswith("exclusion_")
                       for t in tags), fr["id"]
        else:
            assert "zone_loos_gedocumenteerd" in tags and "v4_human_review" in tags, fr["id"]


def test_quote_guard_over_hele_corpus():
    assert verify_all() == []
