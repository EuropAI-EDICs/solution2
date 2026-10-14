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

# Canonieke Utrecht-runs (normcards + formalrules per track)
UTRECHT_TRACK_RUNS = [
    ("wind", ROOT / "poc/runs/20260830T113234Z-wind"),
    ("zon", ROOT / "poc/runs/20260830T142439Z-zon"),
    ("bos", ROOT / "poc/runs/20260830T142446Z-bos"),
    ("water", ROOT / "poc/runs/20261004T185116Z-water"),
    ("bodem", ROOT / "poc/runs/20261004T185509Z-bodem"),
    ("landschap", ROOT / "poc/runs/20261005T070621Z-landschap"),
    ("mobiliteit", ROOT / "poc/runs/20261005T072839Z-mobiliteit"),
    ("landbouw", ROOT / "poc/runs/20261005T094244Z-landbouw"),
    ("wonen", ROOT / "poc/runs/20261005T100258Z-wonen"),
    ("recreatie", ROOT / "poc/runs/20261006T114934Z-recreatie"),
    ("biomassa", ROOT / "poc/runs/20261006T120133Z-biomassa"),
    ("werken", ROOT / "poc/runs/20261006T121921Z-werken"),
    ("energietoets", ROOT / "poc/runs/20261006T171730Z-energietoets"),
]

EINDHOVEN_RUN = ROOT / "poc-bp2op/runs/20260830-124515-eindhoven"
