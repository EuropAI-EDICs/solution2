"""Gedeelde test-hulp: laadt poc-breda/run.py op bestandspad (immuun voor de
naamcollisie met poc/run.py) en bouwt het volledige scan-artefact."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POC_ROOT = ROOT.parent / "poc"
for p in (str(POC_ROOT), str(ROOT)):  # ROOT laatste -> index 0
    if p not in sys.path:
        sys.path.insert(0, p)

_RUN_CACHE = None


def run_module():
    global _RUN_CACHE
    if _RUN_CACHE is None:
        spec = importlib.util.spec_from_file_location("poc_breda_run", ROOT / "run.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["poc_breda_run"] = mod
        spec.loader.exec_module(mod)
        _RUN_CACHE = mod
    return _RUN_CACHE


def full_scan(layers: dict) -> dict:
    """Volledig scan-artefact (met scan/sources/values-meta) op fixture-lagen."""
    run = run_module()
    return run.build_scan(layers, [], run.fetch.load_sources())
