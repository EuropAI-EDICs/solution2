import shutil
from pathlib import Path

import pytest

from services.process_adapter.poc_handlers import execute_world_scene_build

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURE_RUN = WORKSPACE / "poc" / "scenario-runs" / "_fixture-zon-scen"


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_execute_world_scene_build(tmp_path):
    # De bundle-schrijver stampt generatedAt en werkt prov.json bij: de run
    # gaat daarom in een kopie (spiegel van de poc-test_world_scene-fix),
    # zodat de gecommitte fixture byte-identiek blijft.
    work = tmp_path / "_fixture-zon-scen"
    shutil.copytree(FIXTURE_RUN, work)
    result = execute_world_scene_build(
        {"scenarioRunDir": str(work), "hitlApproved": True}
    )
    bundle = result["bundle"]
    assert bundle["specCount"] >= 2
    path = Path(bundle["path"])
    assert path.is_file()
    assert (work / "prov.json").is_file()
