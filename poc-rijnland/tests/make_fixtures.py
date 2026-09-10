"""Regenerate offline geo fixtures for a small Leiden bbox (optional live).

Usage:

    cd poc-rijnland
    ../nldt/.venv/bin/python tests/make_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POC_ROOT = ROOT.parent / "poc"
sys.path[:0] = [str(ROOT), str(POC_ROOT)]

from pipeline import geodata  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "fixtures"
BBOX = "94000,462000,96000,464000"  # small Leiden slice


def main() -> int:
    FIXDIR.mkdir(parents=True, exist_ok=True)
    sources = geodata.load_sources(ROOT / "data" / "sources.json")
    cache = ROOT / "data" / "cache"
    for sid in ("rijnland-peilgebied-vigerend", "rijnland-peilafwijking-praktijk"):
        fc = geodata.fetch_layer(
            sid, bbox=BBOX, refresh=True, sources=sources,
            cache_dir=cache, simplify_m=25, timeout=180)
        out = FIXDIR / f"{sid}.bbox.json"
        # slim fixture: geometry only, for documentation / optional reload
        slim = {
            "type": "FeatureCollection",
            "properties": {"bbox": BBOX, "sourceId": sid,
                           "featureCount": len(fc.get("features") or [])},
            "features": fc.get("features") or [],
        }
        out.write_text(json.dumps(slim, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[fixture] {sid}: {slim['properties']['featureCount']} features -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
