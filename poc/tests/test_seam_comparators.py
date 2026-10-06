# poc/tests/test_seam_comparators.py
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

sys.path.insert(0, str(POC_ROOT / "llm"))
sys.path.insert(0, str(POC_ROOT / "scenarios"))


@pytest.mark.llm
@pytest.mark.skipif(not os.environ.get("LDT_NORM_LLM_ENDPOINT"), reason="LDT_NORM_LLM_ENDPOINT niet gezet — LLM-leg vergt een lokaal open model")
def test_norm_seam_comparator_wind() -> None:
    """S1/S2: deterministische replay vs LLM-hooks op de wind-shard; het
    harde invariant (nul drift op citaties/rechtskracht/geo-bindingen) zit
    in de comparator zelf — rc 0 betekent geen drift boven de drempels."""
    import compare_norm_llm

    # geen --out-vlag: de script schrijft zelf naar poc/llm-runs/<ts>-...-normcmp/
    rc = compare_norm_llm.main(["--use-case", "wind"])
    assert rc == 0


@pytest.mark.llm
@pytest.mark.skipif(not os.environ.get("LDT_SCENARIO_LLM_ENDPOINT"), reason="LDT_SCENARIO_LLM_ENDPOINT niet gezet — LLM-leg vergt een lokaal open model")
def test_scenario_author_comparator_wind() -> None:
    """S7: floor/hybrid/llm authors over de laatste wind-run; rc 0 betekent
    floorIntact en geen gate-rejecties boven de drempels."""
    import compare_authors

    # geen --out-vlag: het script schrijft zelf naar poc/scenario-runs/<ts>-...-authorcmp/
    rc = compare_authors.main(["--use-case", "wind"])
    assert rc == 0
