"""Leerrapport (retrieval v1): aggregatie per leerniveau/observationType/status.

    python -m services.memory.report
"""
from __future__ import annotations

import collections
from typing import Any

from services.memory.store import load_trails

PROMOTION_THRESHOLD = 3


def promote_candidates(trails: list[dict[str, Any]]) -> list[str]:
    """Observatietypen met ≥ PROMOTION_THRESHOLD open trails op operationeel niveau."""
    counter = collections.Counter(
        (t["observation"]["type"], t["learningLevel"])
        for t in trails
        if t["status"] == "open"
    )
    return sorted(
        f"operationeel:{type_}"
        for type_, level in counter
        if counter[(type_, level)] >= PROMOTION_THRESHOLD and level == "operationeel"
    )


def report() -> int:
    trails = load_trails()
    print(f"{len(trails)} trail-record(s)")
    if not trails:
        return 0
    by_level = collections.Counter(t["learningLevel"] for t in trails)
    by_type = collections.Counter(t["observation"]["type"] for t in trails)
    print(f"per leerniveau: {dict(by_level)}")
    print(f"per observationType: {dict(by_type)}")
    open_items = [t for t in trails if t["status"] == "open"]
    print(f"\nopen ({len(open_items)}):")
    for t in open_items:
        print(f"  {t['trailId']} [{t['learningLevel']}/{t['observation']['type']}] {t['what'][:80]}")
    candidates = promote_candidates(trails)
    if candidates:
        print("\npromotie-kandidaten (≥3 open op operationeel):")
        for candidate in candidates:
            print(f"  {candidate}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
