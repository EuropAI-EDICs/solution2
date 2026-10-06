# poc/tests/test_golden_regression.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import golden  # noqa: E402
from run import main as run_main  # noqa: E402


@pytest.mark.golden
@pytest.mark.parametrize("track", sorted(golden.CANONICAL_RUNS))
def test_golden_regression(track: str, tmp_path: Path) -> None:
    out = tmp_path / f"run-{track}"
    rc = run_main(["--use-case", track, "--out", str(out)])
    assert rc == 0, f"run.py faalde voor track {track}"
    result = golden.diff_runs(out, golden.golden_dir(track))
    assert result["pass"], f"golden-drift op {track}: {result['details']}"
