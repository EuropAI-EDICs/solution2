"""Norm-specialist tools: search the Utrecht POC norm-card corpus
(poc/corpus/normcards-*.json) — machine-verifiable legal claims with sources.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import journal

HERE = Path(__file__).resolve().parents[1]
CORPUS_DIR = HERE.parent / "poc" / "corpus"


def _load_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for path in sorted(CORPUS_DIR.glob("normcards*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for card in data if isinstance(data, list) else []:
            card["_file"] = path.stem
            cards.append(card)
    return cards


def search_norms(query: str, track: str | None = None) -> list[dict[str, Any]]:
    """Search the norm-card corpus (legal claims with source, article, version, legal force). Optional track filter: 'wind', 'zon' or 'bos'. Returns matches ranked by term coverage with id, claim, source and verification status."""
    terms = [t.lower() for t in query.split() if len(t) > 2]
    matches = []
    for card in _load_cards():
        if track and track.lower() not in card.get("_file", ""):
            continue
        source = card.get("source", {})
        haystack = " ".join(
            str(card.get(k, ""))
            for k in ("id", "claim", "theme", "legalForce", "appliesTo", "notes")
        ) + " " + " ".join(str(v) for v in source.values())
        low = haystack.lower()
        hits = sum(1 for t in terms if t in low)
        if hits == 0:
            continue
        matches.append(
            {
                "id": card.get("id"),
                "claim": card.get("claim", "")[:400],
                "source": {k: source.get(k) for k in ("docId", "article", "version") if source.get(k)},
                "legalForce": card.get("legalForce"),
                "verified": card.get("verified"),
                "corpusFile": card.get("_file"),
                "termHits": hits,
            }
        )
    matches.sort(key=lambda m: -m["termHits"])
    result = matches[:8]
    journal.append(
        "tool_call", "normspecialist", f"search_norms('{query}') → {len(result)} normcard(s)"
    )
    return result
