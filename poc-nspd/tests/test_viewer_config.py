import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import contracts  # noqa: E402
from make_viewer_config import make_viewer_config  # noqa: E402


def test_config_valid_en_lagen_aanwezig(tmp_path):
    src = ROOT / "tests" / "fixtures" / "viewer" / "run-wind"
    run_dir = tmp_path / "run"
    shutil.copytree(src, run_dir)
    pad = make_viewer_config(track="wind", run_dir=run_dir, out_dir=tmp_path / "viewer-data")
    cfg = json.loads(pad.read_text(encoding="utf-8"))
    contracts.validate(cfg, "leia-config")
    titels = json.dumps(cfg["layers"])
    for vereist in ("3D BAG", "Zones wind NL", "Zones wind BE"):
        assert vereist in titels
    assert (pad.parent / "layers" / "zones-wind-nspd.geojson").is_file()
