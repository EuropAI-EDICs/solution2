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


SET_IDS = {
    "wind": 3, "zon": 3, "bos": 3, "water": 3, "bodem": 3, "mobiliteit": 3,
    "landschap": 3, "landbouw": 3, "wonen": 3, "werken": 3, "recreatie": 3,
    "biomassa": 3, "energietoets": 2,  # plan 2 maakt dit 3 (SC-ET-NETCONGESTIE)
}


def test_demo_sets_tellen_exact_3_scenarios_per_track():
    for track, n in SET_IDS.items():
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        assert s["useCase"] == track, track
        assert len(s["scenarios"]) == n, track
        ids = [sc["id"] for sc in s["scenarios"]]
        assert len(ids) == len(set(ids)), f"dubbele ids in {track}"


def test_wind_set_bevat_hetzelfde_drietal():
    s = json.loads((ROOT / "scenarios" / "wind.json").read_text(encoding="utf-8"))
    assert [sc["id"] for sc in s["scenarios"]] == [
        "SC-W-NNN-EXCEPTION", "SC-W-STILTE-HARD", "SC-W-NATURA-SETBACK"]
