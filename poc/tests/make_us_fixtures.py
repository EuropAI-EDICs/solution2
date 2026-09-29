"""Regenerate committed Urban Strategy cache fixtures for test_usstep.

Usage (live, needs nldt/.venv):

    cd poc && POC_US_OFFLINE= ../nldt/.venv/bin/python tests/make_us_fixtures.py

Writes input copies under tests/us_fixtures/ and cache under
poc/data/cache/us/<fp>.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POC_ROOT))

from pipeline import usstep  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "us_fixtures"

STILLE_KERN = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"name": "stille_kern"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[5.11, 52.09], [5.13, 52.09], [5.13, 52.105],
                             [5.11, 52.105], [5.11, 52.09]]],
        },
    }],
}

BUFFERZONE = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "properties": {"name": "bufferzone"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[5.13, 52.09], [5.15, 52.09], [5.15, 52.105],
                             [5.13, 52.105], [5.13, 52.09]]],
        },
    }],
}


def main() -> int:
    FIXDIR.mkdir(parents=True, exist_ok=True)
    # 1) fetch fixtures (demo + utrecht)
    for source, label in (
        ("fixture://receptors-demo.geojson", "fetch-demo-input.json"),
        ("fixture://receptors-stiltegebied-utrecht.geojson", "fetch-utrecht-input.json"),
    ):
        fetch_inputs = {"source": source}
        fetch_out = usstep.call("us-fetch-noise-receptors", fetch_inputs)
        (FIXDIR / label).write_text(
            json.dumps(fetch_inputs, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[fixture] {label} -> {usstep.fingerprint('us-fetch-noise-receptors', fetch_inputs)}.json "
              f"({len(fetch_out['receptors']['features'])} receptors)")

    # keep primary fetch-input.json as demo (unit tests)
    fetch_inputs = {"source": "fixture://receptors-demo.geojson"}
    fetch_out = usstep.call("us-fetch-noise-receptors", fetch_inputs)
    (FIXDIR / "fetch-input.json").write_text(
        json.dumps(fetch_inputs, sort_keys=True) + "\n", encoding="utf-8")

    # 2) eval fixtures
    eval_inputs = {
        "receptors": fetch_out["receptors"],
        "stilleKern": STILLE_KERN,
        "bufferzone": BUFFERZONE,
    }
    eval_out = usstep.call("us-stiltegebied-noise-eval", eval_inputs)
    (FIXDIR / "eval-input.json").write_text(
        json.dumps(eval_inputs, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[fixture] eval -> {usstep.fingerprint('us-stiltegebied-noise-eval', eval_inputs)}.json "
          f"(exceedances={eval_out['evaluation']['counts']['exceedancesTotal']})")

    # 3) combined screen helper path with demo receptors + synthetic zones
    screen = usstep.stiltegebied_noise_screen(
        STILLE_KERN,
        bufferzone_4326=BUFFERZONE,
        receptor_source="fixture://receptors-demo.geojson",
    )
    (FIXDIR / "screen-summary.json").write_text(
        json.dumps({"exceedancesTotal": screen["counts"]["exceedancesTotal"]},
                   sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"[fixture] screen helper exceedances={screen['counts']['exceedancesTotal']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
