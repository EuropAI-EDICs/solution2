from __future__ import annotations

import pathlib

DIR = pathlib.Path(__file__).resolve().parent
ROOT = DIR.parents[3]  # repo root (nldt/simulation/regelrecht/full_export → 4 up)
OUT = DIR / "out"
HTML_UTRECHT = ROOT / "docs/research/sources/cvdr704250-omgevingsverordening-geldend-2025-10-13.html"
HTML_EINDHOVEN = (
    ROOT / "poc-bp2op/corpus/eindhoven/omgevingsplan-eindhoven-cvdr696400-geldend-2026-06-29.html"
)

INSTRUMENTS = {
    "utrecht": {
        "cvdr": "CVDR704250",
        "versie": 8,
        "html": HTML_UTRECHT,
        "title": "Omgevingsverordening provincie Utrecht",
        "regulatory_layer": "PROVINCIALE_VERORDENING",
        "organisation": "Provincie Utrecht",
        "provincie_code": "PV26",
        "url": "https://lokaleregelgeving.overheid.nl/CVDR704250",
        "valid_from": "2025-10-13",
        "publication_date": "2025-10-13",
    },
    "eindhoven": {
        "cvdr": "CVDR696400",
        "versie": 4,
        "html": HTML_EINDHOVEN,
        "title": "Omgevingsplan gemeente Eindhoven",
        "regulatory_layer": "GEMEENTELIJKE_VERORDENING",
        "organisation": "Gemeente Eindhoven",
        "gemeente_code": "GM0772",
        "url": "https://lokaleregelgeving.overheid.nl/CVDR696400",
        "valid_from": "2026-06-29",
        "publication_date": "2026-06-29",
    },
}
