#!/usr/bin/env python3
"""Schrijft de agent–fase–tool matrix van NSPD als fase-matrix.md (op verzoek).

De engine wordt niet aangeraakt; dit is de leesbare vorm van het manifest.
    cd poc-nspd && .venv/bin/python tools/render_matrix.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT.parent / "poc-fundament"))  # brug-conventie: append, nooit insert

from fundament.manifest import load_manifest  # noqa: E402
from fundament.matrix import render_matrix  # noqa: E402


def main() -> None:
    manifest = load_manifest(ROOT / "fase-manifest.json")
    out = ROOT / "fase-matrix.md"
    out.write_text(render_matrix(manifest), encoding="utf-8")
    print(f"matrix → {out}")


if __name__ == "__main__":
    main()
