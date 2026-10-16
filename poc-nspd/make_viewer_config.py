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
    "nl": {"stroke": "#1a5fb4", "fill": "#1a5fb426"},
    "be": {"stroke": "#c64600", "fill": "#c6460026"},
}


def _final_zones(feats: list[dict]) -> list[dict]:
    """Alleen de eindzones (ZR-final-*) zijn bedoeld voor de kaart; de
    tussenstappen (inclusion_union/intersection/difference) zijn elk AOI-breed
    en stapelen zich tot een bijna dekkend vlak (demo-bevinding 2026-10-15)."""
    final = [f for f in feats if str(f.get("properties", {}).get("id", "")).startswith("ZR-final-")]
    if not final:
        ids = [str(f.get("properties", {}).get("id", "")) for f in feats]
        raise SystemExit(f"geen ZR-final-*-zones in run-output (ids: {ids}) — xborder-merge nakijken")
    return final


def make_viewer_config(*, track: str, run_dir: Path, out_dir: Path) -> Path:
    geo_src = run_dir / f"zones-{track}-nspd.geojson"
    if not geo_src.is_file():
        raise SystemExit(f"ontbreekt: {geo_src} — draai eerst de xborder-merge (taak 10)")
    layers_dir = out_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(geo_src, layers_dir / geo_src.name)

    fc = json.loads(geo_src.read_text(encoding="utf-8"))
    per_land = {}
    for feat in _final_zones(fc.get("features", [])):
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
            "defaultOn": True, "defaultAddToManager": True,
            "settings": {
                "url": f"layers/{laag_bestanden[land]}",
                "stroke": st["stroke"], "fill": st["fill"], "strokeWidth": 2,
            },
        }

    cfg = {
        "name": f"poc-nspd — NSPD {track}",
        "viewer": {
            "title": f"poc-nspd — NSPD {track}",
            "subTitle": "grensvergelijkende scan (plan 2026-10-14)",
            # Overzichtscamera: zuidelijk van het district, noordwaarts kijkend —
            # het volledige NSPD-gebied in beeld (bewezen 2026-10-15: 12 km / −45°
            # toont Westerschelde + kanaalzone + beide zones; 30 km/−55° onbeproefd)
            "startPosition": {"x": 3.66, "y": 51.15, "z": 12000, "heading": 0, "pitch": -45, "duration": 3},
        },
        "groups": [
            {"id": "achtergrond", "title": "Achtergrond", "isOpen": True},
            {"id": "d3", "title": "3D gebouwcontext", "isOpen": True},
            {"id": "pipeline", "title": f"Zones {track} (pipeline)", "isOpen": True},
        ],
        "layers": [
            {"id": "bg-brt", "type": "wmts", "title": "BRT Achtergrondkaart (NL)", "groupId": "achtergrond",
             "isBackground": True, "defaultOn": True, "attribution": "PDOK", "defaultAddToManager": True,
             "settings": {"url": BRT_WMTS, "featureName": "standaard", "contentType": "image/png"}},
            {"id": "bg-be", "type": "wms", "title": "Vlaanderen basiskaart", "groupId": "achtergrond",
             "defaultOn": False, "attribution": "Geopunt", "defaultAddToManager": True,
             "settings": {"url": GEOPUNT_BASIS, "featureName": "omwrgbmrvl", "contenttype": "image/png"}},
            {"id": "bag3d", "type": "3dtiles", "title": "3D BAG LoD2.2 (NL-gebouwen)", "groupId": "d3",
             "defaultOn": True, "attribution": "3D BAG / TU Delft, CC-BY-4.0", "defaultAddToManager": True,
             "settings": {"url": BAG_3D, "enableHeightControl": True}},
            zone_layer("nl"), zone_layer("be"),
        ],
        # Leia verwacht tools als ARRAY van {id, enabled} met exacte tool-id's
        # (zie viewer/static/example.config.json); een object breekt de tool-init
        "tools": [{"id": "layerManager", "enabled": True},
                  {"id": "featureInfo", "enabled": True}],
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
            "defaultOn": False, "defaultAddToManager": True,
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
