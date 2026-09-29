from pathlib import Path

import pytest

from services.process_adapter.poc_handlers import execute_world_scene_build

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURE_RUN = WORKSPACE / "poc" / "scenario-runs" / "_fixture-zon-scen"


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_execute_world_scene_build():
    result = execute_world_scene_build(
        {"scenarioRunDir": str(FIXTURE_RUN), "hitlApproved": True}
    )
    bundle = result["bundle"]
    assert bundle["specCount"] >= 2
    path = Path(bundle["path"])
    assert path.is_file()
