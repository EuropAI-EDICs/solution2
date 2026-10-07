"""Draait de golden-regressie en leg per-track resultaten vast als
poc/eval/golden-diff.json — de observatiebron voor golden_drift-consolidatie.

Op verzoek draaien, nooit onderdeel van de standaard consolidatie:

    python3 poc/eval/golden_report.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
OUT = POC_ROOT / "eval" / "golden-diff.json"

_TRACK_LINE = re.compile(r"test_golden_regression\[(\w+)\] (PASSED|FAILED)")


def parse_pytest_output(text: str) -> dict[str, dict]:
    tracks: dict[str, dict] = {}
    for match in _TRACK_LINE.finditer(text):
        tracks[match.group(1)] = {"pass": match.group(2) == "PASSED"}
    return tracks


def main(argv: list[str] | None = None) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-m", "golden", "-v"],
        cwd=POC_ROOT,
        capture_output=True,
        text=True,
    )
    tracks = parse_pytest_output(result.stdout)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "ranAt": datetime.now(timezone.utc).isoformat(),
        "tracks": tracks,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(tracks)} track-resultaat(en) → {OUT}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
