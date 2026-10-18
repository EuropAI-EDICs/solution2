"""Validator voor poc/tracks/ (NSPD-refactor eindreview-fix).

Was de one-shot extractor van fase 1; sinds de refactor is run.py consumer
van deze bestanden en zou een her-extractie de handmatig gevulde
limitationsTemplates naar null clobberen. Dit script overschrijft niets: het
rapporteert drift (leeg/ontbrekend template, geen dict) en exit 1 bij problemen.

Run: cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 tracks/make_tracks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    problems: list[str] = []
    n = 0
    for p in sorted(HERE.glob("*.json")):
        if p.stem.startswith("_"):
            continue
        n += 1
        data = json.loads(p.read_text(encoding="utf-8"))
        tpl = data.get("limitationsTemplate")
        if not isinstance(tpl, list) or not tpl or not all(isinstance(t, str) for t in tpl):
            problems.append(f"{p.name}: limitationsTemplate leeg/ontbrekend")
    zs = HERE / "_zone-sources.json"
    if not zs.is_file() or not isinstance(json.loads(zs.read_text(encoding="utf-8")), dict):
        problems.append("_zone-sources.json: ontbreekt of geen dict")
    for name in ("make_tracks.py",):
        pass  # placeholder-vrij
    if problems:
        print("PROBLEMEN:")
        for pr in problems:
            print(" -", pr)
        return 1
    print(f"poc/tracks ok: {n} tracks, templates gevuld, zone-sources aanwezig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
