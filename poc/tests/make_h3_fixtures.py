"""Regenerate the committed H3 cache fixtures for test_h3step.

Usage (live, needs nldt/.venv with h3 installed):

    cd poc && POC_H3_OFFLINE= ../nldt/.venv/bin/python tests/make_h3_fixtures.py

Writes input copies next to the fixtures so tests construct byte-identical
request dicts. Commit poc/data/cache/h3/<fp>.json + tests/h3_fixtures/*.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POC_ROOT))

from pipeline import h3step  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "h3_fixtures"

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.11],
                     [5.10, 52.11], [5.10, 52.08]]],
}


def fc(geom):
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": geom}]}


def main() -> int:
    FIXDIR.mkdir(parents=True, exist_ok=True)
    cases = {
        "square-res9-input.json": ("h3-polygon-to-cells",
                                   {"polygon": fc(SQUARE), "resolution": 9}),
        "square-res8-input.json": ("h3-polygon-to-cells",
                                   {"polygon": fc(SQUARE), "resolution": 8}),
    }
    for name, (pid, inputs) in sorted(cases.items()):
        out = h3step.call(pid, inputs)  # live: writes the cache entry
        (FIXDIR / name).write_text(json.dumps(inputs, sort_keys=True) + "\n")
        print(f"[fixture] {name} -> {h3step.fingerprint(pid, inputs)}.json "
              f"(coverage cells: {out['coverage']['cellCount']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
