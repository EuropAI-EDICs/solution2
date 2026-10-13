"""Uitdagingen-curation: 5 opgaven die samen exact de 13 tracks dekken."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UJV = ROOT / "scenarios" / "uitdagingen.json"

ALLE_TRACKS = {
    "wind", "zon", "bos", "water", "bodem", "mobiliteit", "landschap",
    "landbouw", "wonen", "werken", "recreatie", "biomassa", "energietoets",
}


def _load() -> dict:
    return json.loads(UJV.read_text(encoding="utf-8"))


def test_vijf_uitdagingen_dekken_exact_de_13_tracks():
    u = _load()
    assert len(u["uitdagingen"]) == 5
    seen: list[str] = []
    for uit in u["uitdagingen"]:
        assert set(uit) == {"id", "titel", "tracks"}
        assert uit["id"] and uit["titel"]
        seen.extend(uit["tracks"])
    assert sorted(seen) == sorted(ALLE_TRACKS)
    assert len(seen) == len(set(seen)), "elke track in precies één uitdaging"
