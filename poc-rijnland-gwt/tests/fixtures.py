"""Offline fixtures: small deterministic logger/rain/gemaal sets."""

from __future__ import annotations

import datetime as _dt

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT.parent / "poc"), str(ROOT.parent / "poc-rijnland")):
    if p not in sys.path:
        sys.path.insert(0, p)

END_DATE = _dt.date(2026, 10, 12)


def make_dates(n: int = 60, end: _dt.date = END_DATE) -> list:
    return [(end - _dt.timedelta(days=n - 1 - i)).isoformat()
            for i in range(n)]


def make_rain(dates: list) -> dict:
    """Wet spell mid-window, scattered light rain before day 40, fully dry
    tail — enough structure for the tree (and days with zero 3-day sum)."""
    rain = {}
    for i, d in enumerate(dates):
        rain[d] = 8.0 if 20 <= i < 26 else (2.0 if (i % 3 == 0 and i < 40)
                                            else 0.0)
    return rain


def make_loggers(n: int = 6) -> list:
    out = []
    for i in range(n):
        out.append({
            "code": f"GWT-{i:03d}",
            "name": f"Test logger {i}",
            "lizardId": f"lizard-{i}",
            "polder": f"Polder {i % 2}",
            "peilgebied": f"PG-{i % 2}",
            "zomerpeil": -2.2 - 0.1 * i,
            "winterpeil": -2.0 - 0.1 * i,
            "x": 95000.0 + 500.0 * i,
            "y": 460000.0 + 300.0 * i,
        })
    return out


def make_gemalen(n: int = 2) -> list:
    return [
        {"code": "GAL-A", "name": "Gemaal A", "x": 95100.0, "y": 460100.0,
         "capaciteit": 1.5},
        {"code": "GAL-B", "name": "Gemaal B", "x": 97000.0, "y": 461200.0,
         "capaciteit": 3.0},
    ]


def make_feature_collection(loggers: list) -> dict:
    """ArcGIS-style FC in EPSG:28992 as parse_loggers expects."""
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"CODE": lg["code"], "NAAM": lg["name"],
                        "LIZARDID": lg["lizardId"],
                        "SOORTOBJECT": "Meetopstelling: Logger grondwater",
                        "XCOORDINAAT": lg["x"], "YCOORDINAAT": lg["y"],
                        "NAAMPOLDER": lg["polder"],
                        "NAAMPEILGEBIED": lg["peilgebied"],
                        "SOORTPEILGEBIED": "vast",
                        "ZOMERPEIL": lg["zomerpeil"],
                        "WINTERPEIL": lg["winterpeil"]},
         "geometry": {"type": "Point",
                      "coordinates": [lg["x"], lg["y"]]}}
        for lg in loggers]}
