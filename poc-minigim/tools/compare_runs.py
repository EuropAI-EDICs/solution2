#!/usr/bin/env python3
"""Vergelijkt twee PoC-5-runs canonisch (voor/na refactor).

Gebruik: ../nldt/.venv/bin/python tools/compare_runs.py /tmp/m2-baseline/<run> /tmp/m2-na/<run>
Exit 0 = canonisch identiek. report.html/prov.json en de volatile velden
(runId, generatedAt, artifacts) zijn bewust uitgesloten; het aoi-invoerpad
(aoi.file) wordt genormaliseerd naar de bestandsnaam.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from minigim.canon import ARTIFACTS, canon  # noqa: E402


def main() -> int:
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    diffs = []
    for name in ARTIFACTS:
        da = canon(json.loads((a / name).read_text(encoding="utf-8")))
        db = canon(json.loads((b / name).read_text(encoding="utf-8")))
        if da != db:
            diffs.append(name)
    la = sorted(p.name for p in (a / "layers").glob("*.geojson"))
    lb = sorted(p.name for p in (b / "layers").glob("*.geojson"))
    if la != lb:
        diffs.append("layers/set")
    else:
        for n in la:
            if (a / "layers" / n).read_bytes() != (b / "layers" / n).read_bytes():
                diffs.append(f"layers/{n}")
    if diffs:
        print("VERSCHILLEN:", ", ".join(diffs))
        return 1
    print("canonisch identiek ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
