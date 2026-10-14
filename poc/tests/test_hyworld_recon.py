"""HY-World WorldMirror reconstruction adapter (Utrecht Renderer context)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts, hyworld_recon  # noqa: E402

FIXTURE_RUN = POC_ROOT / "scenario-runs" / "_fixture-zon-scen"
RECON_DIR = FIXTURE_RUN / "recon"
SAMPLE_PLY = RECON_DIR / "sample.ply"


@pytest.mark.skipif(not RECON_DIR.is_dir(), reason="recon fixture missing")
def test_fixture_points_cesium_shape():
    payload = json.loads((RECON_DIR / "points.cesium.json").read_text(encoding="utf-8"))
    assert payload["type"] == hyworld_recon.CESIUM_POINTS_VERSION
    assert payload["crs"] == "EPSG:4326"
    assert payload["count"] == len(payload["points"])
    assert payload["count"] >= 10
    lon, lat, h = payload["points"][0]
    assert 4.5 < lon < 6.0
    assert 51.5 < lat < 53.0
    assert isinstance(h, (int, float))


@pytest.mark.skipif(not SAMPLE_PLY.is_file(), reason="sample.ply missing")
def test_export_points_for_cesium(tmp_path):
    out = tmp_path / "points.cesium.json"
    payload = hyworld_recon.export_points_for_cesium(
        SAMPLE_PLY, out, max_points=50, assume_lon_lat_height=True
    )
    assert out.is_file()
    assert payload["count"] == 12
    assert payload["crs"] == "EPSG:4326"
    assert len(payload["points"]) == 12


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_register_recon_assets_fixture_mode(tmp_path):
    work = tmp_path / "_fixture-zon-scen"
    shutil.copytree(FIXTURE_RUN, work)
    # Strip hyworld so we exercise register on a clean bundle
    bundle_path = work / "world-scene-specs.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    for spec in bundle["specs"]:
        spec.pop("hyworldRecon", None)
        if spec.get("groundingStamp") == hyworld_recon.GROUNDING_STAMP:
            spec["groundingStamp"] = "engine-only"
    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")

    out = hyworld_recon.register_recon_assets(
        work, work / "recon", fixture_mode=True
    )
    assert out == bundle_path
    refreshed = json.loads(bundle_path.read_text(encoding="utf-8"))
    for spec in refreshed["specs"]:
        contracts.validate(spec, "world-scene-spec")
        hr = spec["hyworldRecon"]
        assert hr["enabled"] is True
        assert hr["hitlRequired"] is False
        assert any(a["role"] == "points" for a in hr["assetRefs"])
        assert all(a["path"].startswith("recon/") for a in hr["assetRefs"])


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_register_live_requires_hitl(tmp_path, monkeypatch):
    work = tmp_path / "_fixture-zon-scen"
    shutil.copytree(FIXTURE_RUN, work)
    monkeypatch.delenv("HYWORLD_HITL_APPROVED", raising=False)
    hyworld_recon.register_recon_assets(work, work / "recon", hitl_approved=False, fixture_mode=False)
    bundle = json.loads((work / "world-scene-specs.json").read_text(encoding="utf-8"))
    for spec in bundle["specs"]:
        assert spec["hyworldRecon"]["enabled"] is False
        assert spec["hyworldRecon"]["hitlRequired"] is True


def test_worldmirror_cli_fixture_only_without_root(monkeypatch, tmp_path):
    monkeypatch.delenv("HYWORLD_ROOT", raising=False)
    code = hyworld_recon.try_run_worldmirror(tmp_path / "in", tmp_path / "out")
    assert code == 2


def test_engine_and_critic_do_not_import_hyworld():
    engine_path = POC_ROOT / "pipeline" / "engine.py"
    critic_path = POC_ROOT / "pipeline" / "critic.py"
    for path in (engine_path, critic_path):
        text = path.read_text(encoding="utf-8")
        assert "hyworld" not in text.lower()
        assert "marble" not in text.lower()


@pytest.mark.skipif(not FIXTURE_RUN.is_dir(), reason="fixture scenario run missing")
def test_committed_fixture_specs_validate_with_hyworld():
    bundle = json.loads((FIXTURE_RUN / "world-scene-specs.json").read_text(encoding="utf-8"))
    assert any("hyworldRecon" in s for s in bundle["specs"])
    for spec in bundle["specs"]:
        contracts.validate(spec, "world-scene-spec")
