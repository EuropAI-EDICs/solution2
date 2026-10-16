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
    assert pos["z"] >= 3000 and pos["pitch"] <= -40, pos


def _cfg_uit_fixture() -> dict:
    src = ROOT / "tests" / "fixtures" / "viewer" / "run-wind"
    run_dir = Path(tempfile.mkdtemp())
    shutil.copytree(src, run_dir, dirs_exist_ok=True)
    pad = make_viewer_config(track="wind", run_dir=run_dir, out_dir=run_dir / "vd")
    return json.loads(pad.read_text(encoding="utf-8"))


def test_zeeland_referentielagen_overgenomen():
    """Lagen uit de Zeeland NSPD-viewer (data/reference/zeeland-nspd.config.json,
    opgehaald 2026-10-16) worden overgenomen — behalve map5.nl (betaalde
    klantsleutel van de provincie). De Vlaamse detailkaart en de 3D-gebouwen
    staan standaard aan (gebruikersvraag 2026-10-16); layerLibrary ontsluit
    de rest."""
    cfg = _cfg_uit_fixture()
    contracts.validate(cfg, "leia-config")
    per_titel = {l["title"]: l for l in cfg["layers"]}
    for vereist in ("GRB Vlaanderen", "3D Gebouwen België", "Begrenzing NSPD",
                    "Luchtfoto Vlaanderen", "Luchtfoto Actueel HR (NL)",
                    "3D Gebouwen Nederland (BAG)", "Natura2000 gebieden"):
        assert vereist in per_titel, vereist
    assert per_titel["GRB Vlaanderen"]["defaultOn"] is True
    # 3D Gebouwen België: tileset origin-vergrendeld door Zeeland (CORS) → niet
    # standaard aan, wél in de bibliotheek met uitleg
    assert per_titel["3D Gebouwen België"]["defaultOn"] is False
    assert "origin-vergrendeld" in per_titel["3D Gebouwen België"]["description"]
    assert per_titel["Begrenzing NSPD"]["defaultOn"] is True
    # buurt-/sectorgrenzen bij Zeeland aan, hier uit (grove WMS-lijnen over de detailkaart)
    assert per_titel["CBS buurten Nederland"]["defaultOn"] is False
    assert per_titel["Statistische sectoren van België"]["defaultOn"] is False
    assert not any("map5.nl" in l["settings"].get("url", "") for l in cfg["layers"])
    ids = [l["id"] for l in cfg["layers"]]
    assert len(ids) == len(set(ids)), "dubbele laag-ids"
    assert not any(l.get("opacity") == 0 for l in cfg["layers"]), "onzichtbare laag (opacity 0)"
    groep_ids = {g["id"] for g in cfg["groups"]}
    for l in cfg["layers"]:
        if l.get("groupId"):
            assert l["groupId"] in groep_ids, (l["id"], l["groupId"])
    assert {t["id"] for t in cfg["tools"]} >= {"layerLibrary", "layerManager", "featureInfo"}
    # eigen pijplijnlagen blijven aanwezig naast de referentielagen
    assert "Zones wind NL" in per_titel and "Zones wind BE" in per_titel
    # de fase-1-laag was foutief 'gebouwen' genoemd: GRB:ADP = administratieve percelen
    assert "GRB percelen (BE, ADP, vlak)" in per_titel
    assert not any("GRB gebouwen" in t for t in per_titel)


def _cfg_twee_tracks() -> dict:
    """Fixture met twee tracks: wind (ruimtelijke regel) + zon (AOI-breed)."""
    src = ROOT / "tests" / "fixtures" / "viewer"
    basis = Path(tempfile.mkdtemp())
    shutil.copytree(src / "run-wind", basis / "wind")
    shutil.copytree(src / "run-zon", basis / "zon")
    pad = make_viewer_config(track="wind", run_dir=basis / "wind", out_dir=basis / "vd")
    return json.loads(pad.read_text(encoding="utf-8"))


def test_scenario_lagen_alle_tracks():
    """AI-scenario-planning in de viewer: alle xborder-tracks als geneste
    scenario-groep; hoofdtrack standaard aan; AOI-only-tracks eerlijk gelabeld
    (hun eindzone is het aanvraaggebied, geen ruimtelijke operand)."""
    cfg = _cfg_twee_tracks()
    contracts.validate(cfg, "leia-config")
    groepen = {g["id"]: g for g in cfg["groups"]}
    assert groepen["scenario"]["title"] == "Scenario-zones (AI-pipeline)"
    assert groepen["scenario-wind"]["parentId"] == "scenario"
    assert groepen["scenario-zon"]["parentId"] == "scenario"
    assert groepen["scenario-zon"]["title"] == "Scenario: zon (AOI-breed)"
    assert "(AOI-breed)" not in groepen["scenario-wind"]["title"]
    assert groepen["scenario-wind"]["isOpen"] is True
    assert groepen["scenario-zon"]["isOpen"] is False
    per_titel = {l["title"]: l for l in cfg["layers"]}
    for t in ("wind", "zon"):
        for land in ("NL", "BE"):
            assert f"Zones {t} {land}" in per_titel
    assert per_titel["Zones wind NL"]["defaultOn"] is True
    assert per_titel["Zones zon NL"]["defaultOn"] is False
    assert per_titel["Zones zon BE"]["defaultOn"] is False
    assert "FR-WIND-03" in per_titel["Zones wind NL"]["description"]
    assert "geen ruimtelijke norm-operand" in per_titel["Zones zon NL"]["description"]


def test_scenario_rapporten_gerekopieerd():
    """Het xborder-rapport van een track komt per track benoemd mee naar
    reports/ (alle bronrapporten heten report-xborder.html) en staat in de
    laagbeschrijving; tracks zonder rapportbestand krijgen geen verwijzing."""
    cfg = _cfg_twee_tracks()
    per_titel = {l["title"]: l for l in cfg["layers"]}
    assert "Rapport: reports/wind.html" in per_titel["Zones wind NL"]["description"]
    assert "Rapport:" not in per_titel["Zones zon NL"]["description"]


def test_scenario_bronlagen():
    """Bronlagen-groep met de regel-operanden: Natura 2000 NL (exclusion van
    wind/zon), SBZ Vlaanderen (gepin, nog door geen BE-regel gebruikt), DHMV
    (context); netcongestie-laag alleen als het laagbestand bestaat."""
    src = ROOT / "tests" / "fixtures" / "viewer"
    basis = Path(tempfile.mkdtemp())
    shutil.copytree(src / "run-wind", basis / "wind")
    # netcongestie-laag niet aanwezig → laag niet in de config
    pad = make_viewer_config(track="wind", run_dir=basis / "wind", out_dir=basis / "vd")
    cfg = json.loads(pad.read_text(encoding="utf-8"))
    titels = {l["title"]: l for l in cfg["layers"]}
    assert "Natura 2000-gebieden (NL) — exclusion" in titels
    assert titels["Natura 2000-gebieden (NL) — exclusion"]["defaultOn"] is True
    assert "geformaliseerde BE-regel" in titels["SBZ/Natura2000 Vlaanderen — exclusion (gepin)"]["description"]
    assert titels["DHM Vlaanderen II (hillshade) — context"]["settings"]["featureName"] == "DHMV_II_HILL_25cm"
    assert "Netcongestie afname (NL) — context" not in titels
    # bestand aanwezig → laag mét stijl en uitleg
    vd = basis / "vd" / "layers"
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "netcongestie-afname-nl.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    pad = make_viewer_config(track="wind", run_dir=basis / "wind", out_dir=basis / "vd")
    cfg = json.loads(pad.read_text(encoding="utf-8"))
    titels = {l["title"]: l for l in cfg["layers"]}
    nc = titels["Netcongestie afname (NL) — context"]
    assert nc["defaultOn"] is False and nc["settings"]["style"]["stroke"] == "#620e14"
    assert "energietoets" in nc["description"]


def test_grb_laag_en_besluit_vermeld():
    cfg_pad = ROOT / "viewer-data" / "nspd.config.json"
    if not cfg_pad.is_file():
        return  # pas na eerste echte run-generatie; besluit-test moet altijd draaien
    cfg = json.loads(cfg_pad.read_text(encoding="utf-8"))
    assert "GRB percelen" in json.dumps(cfg["layers"])


def test_dhm_beslispunt_gedocumenteerd():
    besluit = ROOT / "data" / "grb_extrusie_besluit.json"
    assert besluit.is_file()
    b = json.loads(besluit.read_text(encoding="utf-8"))
    assert b["keuze"] in ("vlak", "extrusie")
    assert b["motivering"] and b["beslotenIn"] == "plan 2026-10-14-poc-nspd taak 12"
