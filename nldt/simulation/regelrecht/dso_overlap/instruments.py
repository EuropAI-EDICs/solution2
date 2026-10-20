"""Instrument- en locatiefixtures voor DSO↔RegelRecht-overlap."""
from __future__ import annotations

import json
import pathlib
from typing import Any

DIR = pathlib.Path(__file__).resolve().parent
REGELRECHT_DIR = DIR.parent
FULL_EXPORT_OUT = REGELRECHT_DIR / "full_export" / "out"
FIXTURES = DIR / "fixtures"
DEFAULT_OUT = DIR / "out"

CRS_DSO = "http://www.opengis.net/def/crs/EPSG/0/28992"
CRS_RP = "epsg:28992"

DEFAULT_PRESENTEREN_BASE = (
    "https://service.pre.omgevingswet.overheid.nl"
    "/publiek/omgevingsdocumenten/api/presenteren/v8"
)
DEFAULT_RP_BASE = (
    "https://ruimte.omgevingswet.overheid.nl"
    "/ruimtelijke-plannen/api/opvragen/v4"
)

INSTRUMENTS: dict[str, dict[str, Any]] = {
    "eindhoven": {
        "label": "Omgevingsplan gemeente Eindhoven",
        "akn_uri": "_akn_nl_act_gm0772_2020_omgevingsplan",
        "akn_path": "/akn/nl/act/gm0772/2020/omgevingsplan",
        "cvdr": "CVDR696400",
        "bevoegd_gezag": "gm0772",
        "formalization_report": FULL_EXPORT_OUT / "eindhoven-formalization-report.json",
        "instrument_yaml": FULL_EXPORT_OUT / "eindhoven-cvdr696400.yaml",
        "default_location_id": "eindhoven-woensel-proxy",
    },
    "utrecht": {
        "label": "Omgevingsverordening provincie Utrecht",
        "akn_uri": "_akn_nl_act_pv26_2022_omgevingsverordening",
        "akn_path": "/akn/nl/act/pv26/2022/omgevingsverordening",
        "cvdr": "CVDR704250",
        "bevoegd_gezag": "pv26",
        "formalization_report": FULL_EXPORT_OUT / "utrecht-formalization-report.json",
        "instrument_yaml": FULL_EXPORT_OUT / "utrecht-cvdr704250.yaml",
        "default_location_id": "utrecht-domplein",
    },
}


def load_locations() -> dict[str, dict[str, Any]]:
    path = FIXTURES / "locations.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {loc["id"]: loc for loc in data["locations"]}


def resolve_location(instrument_id: str, location_id: str | None = None) -> dict[str, Any]:
    locs = load_locations()
    meta = INSTRUMENTS[instrument_id]
    lid = location_id or meta["default_location_id"]
    if lid not in locs:
        raise KeyError(f"onbekende location_id={lid!r}")
    loc = locs[lid]
    if loc.get("instrument") and loc["instrument"] != instrument_id:
        raise ValueError(
            f"location {lid} hoort bij {loc['instrument']}, niet bij {instrument_id}"
        )
    return loc
