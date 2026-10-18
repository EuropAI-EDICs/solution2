"""Declaratieve track-lading (nspd-port fase 1): poc/tracks/*.json.

Enige lezer van poc/tracks/; run.py en agents.py zijn consumers. De
limitations-templates worden geformatteerd met de coverage-dict van de
formalizer (keys: ambiguous, output_rules, formalized) — format_map faalt
luid op een onbekende placeholder (geen stil geweid gedrag).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

POC_ROOT = Path(__file__).resolve().parents[1]
TRACKS_DIR = POC_ROOT / "tracks"


def _read(name: str) -> Any:
    return json.loads((TRACKS_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _load_track_raw(track_id: str) -> dict:
    data = _read(f"{track_id}.json")
    templates = data.pop("limitationsTemplate")
    if not isinstance(templates, list) or not templates:
        raise ValueError(
            f"tracks/{track_id}.json: limitationsTemplate ontbreekt of is leeg "
            "(vul de template-strings in — task 1 stap 3)")

    def limitations(cov: dict, abst: list) -> list:
        return [t.format_map(dict(cov)) for t in templates]

    data["limitations"] = limitations
    return data


def load_track(track_id: str) -> dict:
    return dict(_load_track_raw(track_id))


def load_all_tracks() -> dict:
    return {t: load_track(t) for t in sorted(
        p.stem for p in TRACKS_DIR.glob("*.json") if not p.stem.startswith("_"))}


def _merge_dir(subdir: str) -> dict:
    merged: dict = {}
    for p in sorted((TRACKS_DIR / subdir).glob("*.json")):
        merged.update(json.loads(p.read_text(encoding="utf-8")))
    return merged


@lru_cache(maxsize=None)
def load_enrichment() -> dict:
    return _merge_dir("_enrichment")


@lru_cache(maxsize=None)
def load_templates() -> dict:
    return _merge_dir("_templates")


@lru_cache(maxsize=None)
def load_zone_sources() -> dict:
    return _read("_zone-sources.json")
