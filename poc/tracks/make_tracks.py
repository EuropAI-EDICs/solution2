"""One-shot extractor: TRACKS/ZONE_SOURCES uit poc/run.py -> poc/tracks/*.json.

Run: cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 tracks/make_tracks.py
Limitations-lambdas worden niet geserialiseerd: elk <track>.json krijgt
"limitationsTemplate": null en wordt handmatig gevuld (task 2, wind is het
uitgewerkte voorbeeld). Idempotent: herschrijft de gegenereerde bestanden.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # poc/ op pad zodat `run` importeerbaar is

from run import TRACKS, ZONE_SOURCES  # noqa: E402


def main() -> None:
    for track, cfg in TRACKS.items():
        out = {k: v for k, v in cfg.items() if k != "limitations"}
        out["limitationsTemplate"] = None  # handmatig vullen (task 2)
        (HERE / f"{track}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"tracks/{track}.json ({', '.join(sorted(out))})")
    (HERE / "_zone-sources.json").write_text(
        json.dumps(ZONE_SOURCES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"tracks/_zone-sources.json ({len(ZONE_SOURCES)} aliassen)")


if __name__ == "__main__":
    main()
