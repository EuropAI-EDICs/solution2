"""Offline-precondities voor de chain-E2E's: canonical runs zijn gecommit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _tracked(rel: str) -> bool:
    uit = subprocess.run(
        ["git", "ls-files", rel], cwd=str(REPO), capture_output=True, text=True
    )
    return bool(uit.stdout.strip())


def test_breda_canonical_subset_gecommit():
    basis = "poc-breda/runs/20260913T192628Z-breda-scan"
    for naam in ("run_summary.json", "value-scan.json", "geo-buurten.wgs84.geojson"):
        assert _tracked(f"{basis}/{naam}"), f"{basis}/{naam} is niet gecommit"


def test_gent_canonical_run_gecommit():
    assert _tracked("poc-gent/runs/20261102T121500Z-gent-transactional-fien/run.json")


def test_overige_canonical_runs_gecommit():
    assert _tracked("poc-bp2op/runs/20260830-124515-eindhoven/run_summary.json")
    assert _tracked("poc-veenendaal/runs/20261106T151732Z-gebiedscheck/indicators.json")
    assert _tracked("poc/runs/20260830T113234Z-wind/zones.geojson")
