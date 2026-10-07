from __future__ import annotations

import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

sys.path.insert(0, str(POC_ROOT / "eval"))

from golden_report import parse_pytest_output  # noqa: E402

SAMPLE = (
    "poc/tests/test_golden_regression.py::test_golden_regression[wind] PASSED [  7%]\n"
    "poc/tests/test_golden_regression.py::test_golden_regression[zon] PASSED [ 15%]\n"
    "poc/tests/test_golden_regression.py::test_golden_regression[biomassa] FAILED [100%]\n"
    "=== 12 passed, 1 failed ===\n"
)


def test_parse_extracts_track_results() -> None:
    tracks = parse_pytest_output(SAMPLE)
    assert tracks["wind"]["pass"] is True
    assert tracks["biomassa"]["pass"] is False
    assert set(tracks) == {"wind", "zon", "biomassa"}


def test_parse_empty_output() -> None:
    assert parse_pytest_output("") == {}
