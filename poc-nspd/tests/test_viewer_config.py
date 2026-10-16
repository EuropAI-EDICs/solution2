import json
import shutil
import sys
import tempfile
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


def test_zone_lagen_bevatten_alleen_final_zones(tmp_path):
    """Tussenstappen (inclusion_union/intersection/difference) mogen niet als
    kaartlaag: AOI-brede polygonen stapelen dan over elkaar (demo-bevinding
    'oranje vlak over het gebied', 2026-10-15)."""
    src = ROOT / "tests" / "fixtures" / "viewer" / "run-wind"
    run_dir = tmp_path / "run"
    shutil.copytree(src, run_dir)
    pad = make_viewer_config(track="wind", run_dir=run_dir, out_dir=tmp_path / "viewer-data")
    for land in ("nl", "be"):
        fc = json.loads((pad.parent / "layers" / f"zones-wind-{land}.geojson").read_text(encoding="utf-8"))
        ids = [f["properties"]["id"] for f in fc["features"]]
        assert ids == [i for i in ids if i.startswith("ZR-final-")], f"{land}: {ids}"
        assert len(ids) == 1


def test_zone_stijl_en_camera_zichtbaar_demo():
    """Leia-contract (geojson-layer.ts, pin 7351002): stijl uitsluitend uit
    settings.style {fill, stroke}; transparantie uit laag-opacity (0-100,
    hex-alpha wordt door withAlpha() overschreven); strokeWidth weglaten
    (upstream-bug stopt de kleurstring in de lijnbreedte). Plus een
    overzichtscamera die het hele NSPD-gebied in beeld brengt."""
    src = ROOT / "tests" / "fixtures" / "viewer" / "run-wind"
    run_dir = Path(tempfile.mkdtemp())
    shutil.copytree(src, run_dir, dirs_exist_ok=True)
    pad = make_viewer_config(track="wind", run_dir=run_dir, out_dir=run_dir / "vd")
    cfg = json.loads(pad.read_text(encoding="utf-8"))
    zones = [l for l in cfg["layers"] if str(l["id"]).startswith("zones-")]
    assert len(zones) == 2
    for laag in zones:
        assert 0 < laag["opacity"] <= 30, laag
        stijl = laag["settings"]["style"]
        assert len(stijl["fill"]) == 7 and stijl["fill"].startswith("#"), stijl
        assert len(stijl["stroke"]) == 7 and stijl["stroke"].startswith("#"), stijl
        assert "strokeWidth" not in stijl
        assert "fill" not in laag["settings"] and "stroke" not in laag["settings"]
    pos = cfg["viewer"]["startPosition"]
    assert pos["z"] >= 10000 and pos["pitch"] <= -45, pos


def test_grb_laag_en_besluit_vermeld():
    cfg_pad = ROOT / "viewer-data" / "nspd.config.json"
    if not cfg_pad.is_file():
        return  # pas na eerste echte run-generatie; besluit-test moet altijd draaien
    cfg = json.loads(cfg_pad.read_text(encoding="utf-8"))
    assert "GRB gebouwen" in json.dumps(cfg["layers"])


def test_dhm_beslispunt_gedocumenteerd():
    besluit = ROOT / "data" / "grb_extrusie_besluit.json"
    assert besluit.is_file()
    b = json.loads(besluit.read_text(encoding="utf-8"))
    assert b["keuze"] in ("vlak", "extrusie")
    assert b["motivering"] and b["beslotenIn"] == "plan 2026-10-14-poc-nspd taak 12"
