"""Run-output → Leia-config + laagbestanden (spec §4.5). Run als module of CLI."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRT_WMTS = "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0?"
GEOPUNT_BASIS = "https://geo.api.vlaanderen.be/omw/wmts?"  # OMW ortho (statuspagina taak 1); featureName verifiëren in de capabilities bij eerste start — alleen defaultOn:false-laag
BAG_3D = "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json"
LAND_STIJL = {
    "nl": {"stroke": "#1a5fb4", "fill": "#1a5fb433"},
    "be": {"stroke": "#c64600", "fill": "#c6460033"},
}


def make_viewer_config(*, track: str, run_dir: Path, out_dir: Path) -> Path:
    geo_src = run_dir / f"zones-{track}-nspd.geojson"
    if not geo_src.is_file():
        raise SystemExit(f"ontbreekt: {geo_src} — draai eerst de xborder-merge (taak 10)")
    layers_dir = out_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(geo_src, layers_dir / geo_src.name)

    fc = json.loads(geo_src.read_text(encoding="utf-8"))
    per_land = {}
    for feat in fc.get("features", []):
        per_land.setdefault(feat["properties"].get("land", "nl"), []).append(feat)
    laag_bestanden = {}
    for land, feats in per_land.items():
        pad = layers_dir / f"zones-{track}-{land}.geojson"
        pad.write_text(json.dumps(
            {"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
        laag_bestanden[land] = pad.name

    def zone_layer(land: str) -> dict:
        st = LAND_STIJL[land]
        return {
            "id": f"zones-{track}-{land}",
            "type": "geojson",
            "title": f"Zones {track} {'NL' if land == 'nl' else 'BE'}",
            "groupId": "pipeline",
            "defaultOn": True,
            "settings": {
                "url": f"layers/{laag_bestanden[land]}",
                "stroke": st["stroke"], "fill": st["fill"], "strokeWidth": 2,
            },
        }

    cfg = {
        "name": f"poc-nspd — NSPD {track}",
        "viewer": {"x": 3.83, "y": 51.33, "z": 2500, "heading": 0, "pitch": -0.6, "duration": 3},
        "groups": [
            {"id": "achtergrond", "title": "Achtergrond", "isOpen": True},
            {"id": "d3", "title": "3D gebouwcontext", "isOpen": True},
            {"id": "pipeline", "title": f"Zones {track} (pipeline)", "isOpen": True},
        ],
        "layers": [
            {"id": "bg-brt", "type": "wmts", "title": "BRT Achtergrondkaart (NL)", "groupId": "achtergrond",
             "isBackground": True, "defaultOn": True, "attribution": "PDOK",
             "settings": {"url": BRT_WMTS, "featureName": "standaard", "contentType": "image/png"}},
            {"id": "bg-be", "type": "wms", "title": "Vlaanderen basiskaart", "groupId": "achtergrond",
             "defaultOn": False, "attribution": "Geopunt",
             "settings": {"url": GEOPUNT_BASIS, "featureName": "omwrgbmrvl", "contenttype": "image/png"}},
            {"id": "bag3d", "type": "3dtiles", "title": "3D BAG LoD2.2 (NL-gebouwen)", "groupId": "d3",
             "defaultOn": True, "attribution": "3D BAG / TU Delft, CC-BY-4.0",
             "settings": {"url": BAG_3D, "enableHeightControl": True}},
            zone_layer("nl"), zone_layer("be"),
        ],
        "tools": {"layermanager": {"enabled": True}, "featureinfo": {"enabled": True}},
    }
    # 3D-context BE-gebouwen: vlakke GRB-laag zodra het extrusie-besluit (taak 12)
    # bestaat — besluitdocument: data/grb_extrusie_besluit.json (keuze "vlak": GRB:ADP
    # heeft geen h_dak_50-achtig hoogteveld; DHM-extrusie niet in POC-scope).
    # NB: het laagbestand grb-gebouwen-be.geojson wordt (voorlopig) níét gegenereerd;
    # generatie of schrapping van deze laagverwijzing is fase 2 (eindreview-bevinding).
    if (ROOT / "data" / "grb_extrusie_besluit.json").is_file():
        json.loads((ROOT / "data" / "grb_extrusie_besluit.json").read_text(encoding="utf-8"))
        cfg["layers"].append({
            "id": "grb-gebouwen",
            "type": "geojson",
            "title": "GRB gebouwen (BE, vlak)",
            "groupId": "d3",
            "defaultOn": False,
            "attribution": "GRB via Geopunt, vrije open data-modellicentie",
            "settings": {"url": "layers/grb-gebouwen-be.geojson"},
        })
    uit = out_dir / "nspd.config.json"
    uit.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return uit


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--track", default="wind")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--out-dir", default=str(ROOT / "viewer-data"))
    a = p.parse_args()
    pad = make_viewer_config(track=a.track, run_dir=Path(a.run_dir), out_dir=Path(a.out_dir))
    print(f"Leia-config: {pad}")
