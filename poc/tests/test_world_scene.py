"""World scene spec builder (Utrecht scenario-copilot)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts, world_scene  # noqa: E402

FIXTURE_RUN = POC_ROOT / "scenario-runs" / "_fixture-zon-scen"


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_build_specs_from_fixture_run():
    specs = world_scene.build_specs_from_run_dir(FIXTURE_RUN)
    assert len(specs) >= 2
    for spec in specs:
        contracts.validate(spec, "world-scene-spec")
    hypo = [s for s in specs if s["provenanceBasis"]["type"] == "hypothetical"]
    policy = [s for s in specs if s["provenanceBasis"]["type"] != "hypothetical"]
    assert hypo and policy
    assert hypo[0]["allowGenerativeRenderer"] is True
    assert policy[0]["allowGenerativeRenderer"] is False
    assert policy[0]["groundingStamp"] == "engine-only"


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_marble_url_only_with_hitl(monkeypatch):
    monkeypatch.delenv("MARBLE_HITL_APPROVED", raising=False)
    specs_no = world_scene.build_specs_from_run_dir(FIXTURE_RUN, hitl_approved=False)
    hypo_no = next(s for s in specs_no if s["allowGenerativeRenderer"])
    assert hypo_no["marble"]["enabled"] is False
    assert hypo_no["marble"]["exploreUrl"] is None

    specs_yes = world_scene.build_specs_from_run_dir(FIXTURE_RUN, hitl_approved=True)
    hypo_yes = next(s for s in specs_yes if s["allowGenerativeRenderer"])
    assert hypo_yes["marble"]["enabled"] is True
    assert hypo_yes["marble"]["exploreUrl"] and "prompt=" in hypo_yes["marble"]["exploreUrl"]


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_write_bundle_roundtrip():
    out = world_scene.write_world_scene_bundle(FIXTURE_RUN, hitl_approved=True)
    assert out.name == "world-scene-specs.json"
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["specCount"] == len(bundle["specs"])


def test_engine_and_critic_do_not_import_marble():
    engine_path = Path(__file__).resolve().parents[1] / "pipeline" / "engine.py"
    critic_path = Path(__file__).resolve().parents[1] / "pipeline" / "critic.py"
    for path in (engine_path, critic_path):
        text = path.read_text(encoding="utf-8")
        assert "marble" not in text.lower()
