"""Source monitor — continuity of open data as a monitored process."""

from __future__ import annotations

from services.source_monitor.paths import (
    DEFAULT_FIXTURES,
    DEFAULT_RUNS,
    DEFAULT_WATCHLIST,
    NLDT_ROOT,
)
from services.source_monitor.run import run_monitor

__all__ = [
    "NLDT_ROOT",
    "DEFAULT_WATCHLIST",
    "DEFAULT_FIXTURES",
    "DEFAULT_RUNS",
    "run_monitor",
]
