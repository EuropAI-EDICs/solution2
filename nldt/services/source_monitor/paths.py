"""Shared paths for the source monitor package."""

from __future__ import annotations

from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WATCHLIST = NLDT_ROOT / "data" / "source-monitor-watchlist.json"
DEFAULT_FIXTURES = NLDT_ROOT / "data" / "source-monitor" / "fixtures"
DEFAULT_RUNS = NLDT_ROOT / "data" / "source-monitor" / "runs"
