"""Run-output → Leia-config + laagbestanden (spec §4.5). Run als module of CLI."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRT_WMTS = "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0?"
BAG_3D = "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json"
# Referentie: de Leia-config van de NSPD-viewer van Provincie Zeeland
# (https://virtueel.zeeland.nl/nspd → /prod/config/nspd.config.json, opgehaald
# 2026-10-16). Lagen worden 1-op-1 overgenomen, behalve de map5.nl-topokaarten:
# die draaien op een betaalde klantsleutel van de provincie, geen open dienst.
# De 3D-gebouwen-tilesets (tiles_other/…) worden door Zeeland zelf gehost.
ZEELAND_REFERENTIE = ROOT / "data" / "reference" / "zeeland-nspd.config.json"
_UITGESLOTEN_HOSTS = ("map5.nl",)
# Standaard aan voor de demo (gebruikersvraag 2026-10-16: Vlaamse detailkaart +
# gebouwen): 021 = GRB Vlaanderen (GRB_BSK, tekent de gebouwvoetafdrukken).
# 008 (3D Gebouwen België) kan NIET standaard aan: de tileset op
# virtueel.zeeland.nl is origin-vergrendeld (access-control-allow-origin:
# https://virtueel.dev.zeeland.nl) en faalt vanaf elke andere site — bewust
# beleid van de provincie, niet te omzeilen via een proxy. Blijft in de
# bibliotheek met uitleg; NL-3D komt uit 3D BAG (CORS *).
_STANDAARD_AAN = {"021"}
# Bij Zeeland standaard aan, hier uit: de buurt-/sectorgrenzen (CBS buurten NL,
# Statistische sectoren BE) tekenen als grove paarse WMS-lijnen over de
# detailkaart en vertroebelen de demo; één klik in Lagenbeheer zet ze aan.
_STANDAARD_UIT = {"030", "035"}
_ORIGIN_VERGRENDELD = {
    "008": ("Tileset gehost door Provincie Zeeland en origin-vergrendeld op hun eigen "
            "viewer (CORS) — rendert niet in deze POC. Voor Vlaamse 3D-gebouwen: "
            "toegang vragen aan Zeeland of eigen tileset uit GRB:GBG + DHM bouwen."),
}
LAND_STIJL = {
    "nl": {"stroke": "#1a5fb4", "fill": "#1a5fb4"},
    "be": {"stroke": "#c64600", "fill": "#c64600"},
}
# Leia (pin 7351002, geojson-layer.ts): de vul-transparantie komt uitsluitend uit
# de laag-opacity (0-100) — een hex-alpha in de kleur wordt door withAlpha()
# overschreven en zonder opacity is de vulling vol-dekkend. Contouren (polyline-
# outlines) blijven op volle sterkte. strokeWidth bewust weggelaten: upstream-bug
# stopt dan de kleurstring in de lijnbreedte (outlineWidth).
ZONE_OPACITY = 20


def _final_zones(feats: list[dict]) -> list[dict]:
    """Alleen de eindzones (ZR-final-*) zijn bedoeld voor de kaart; de
    tussenstappen (inclusion_union/intersection/difference) zijn elk AOI-breed
    en stapelen zich tot een bijna dekkend vlak (demo-bevinding 2026-10-15)."""
    final = [f for f in feats if str(f.get("properties", {}).get("id", "")).startswith("ZR-final-")]
    if not final:
        ids = [str(f.get("properties", {}).get("id", "")) for f in feats]
        raise SystemExit(f"geen ZR-final-*-zones in run-output (ids: {ids}) — xborder-merge nakijken")
    return final


def _zeeland_referentielagen() -> tuple[list[dict], list[dict]]:
    """(groepen, lagen) uit de Zeeland-config; alleen groepen die een
    overgenomen laag daadwerkelijk gebruikt. Het referentiebestand blijft
    ongemoeid (diepe kopie)."""
    if not ZEELAND_REFERENTIE.is_file():
        raise SystemExit(f"ontbreekt: {ZEELAND_REFERENTIE} — referentie-config niet opgehaald")
    ref = json.loads(ZEELAND_REFERENTIE.read_text(encoding="utf-8"))
    lagen = []
    for bron in ref.get("layers", []):
        url = str(bron.get("settings", {}).get("url", ""))
        if any(host in url for host in _UITGESLOTEN_HOSTS):
            continue
        laag = json.loads(json.dumps(bron))
        if laag["id"] in _STANDAARD_AAN:
            laag["defaultOn"] = True
            laag["defaultAddToManager"] = True
        if laag["id"] in _STANDAARD_UIT:
            laag["defaultOn"] = False
        if laag["id"] in _ORIGIN_VERGRENDELD:
            laag["defaultOn"] = False
            laag["description"] = _ORIGIN_VERGRENDELD[laag["id"]]
        if laag.get("opacity") == 0:  # referentie-quirk: de laag zou onzichtbaar zijn
            del laag["opacity"]
        lagen.append(laag)
    gebruikt = {l.get("groupId") for l in lagen if l.get("groupId")}
    groepen = [{"id": g["id"], "title": g["title"], "isOpen": False}
               for g in ref.get("groups", []) if g["id"] in gebruikt]
    return groepen, lagen


def _scenario_tracken(run_dir: Path, hoofd: str) -> dict[str, Path]:
    """Alle xborder-trackuitvoer naast ``run_dir`` (xborder-runs/*/zones-*-nspd.geojson),
    de hoofdtrack gegarandeerd eerst."""
    tracks: dict[str, Path] = {}
    for pad in sorted(run_dir.parent.glob("*/zones-*-nspd.geojson")):
        tracks.setdefault(pad.name[len("zones-"):-len("-nspd.geojson")], pad)
    tracks[hoofd] = run_dir / f"zones-{hoofd}-nspd.geojson"
    return dict(sorted(tracks.items(), key=lambda kv: kv[0] != hoofd))


def _scenario_bronnen(layers_dir: Path) -> list[dict]:
    """Bronlagen waarop de scenario-regels rekenen (regel-operanden + context)."""
    lagen = [
        {"id": "bron-natura2000-nl", "type": "wms",
         "title": "Natura 2000-gebieden (NL) — exclusion", "groupId": "scenario-bronnen",
         "defaultOn": True, "defaultAddToManager": True, "attribution": "PDOK / RVO",
         "description": "Exclusion-operand van FR-WIND-03 (wind) en FR-ZON-02 (zon): "
                        "bron pdok-natura2000 (rvo/natura2000; OGC API in de pipeline, WMS hier).",
         "settings": {"url": "https://service.pdok.nl/rvo/natura2000/wms/v1_0",
                      "featureName": "natura2000", "contentType": "image/png",
                      "webMercator": True}},
        {"id": "bron-sbz-be", "type": "wms",
         "title": "SBZ/Natura2000 Vlaanderen — exclusion (gepin)", "groupId": "scenario-bronnen",
         "defaultOn": True, "defaultAddToManager": True,
         "attribution": "Mercator publiek / Agentschap Natuur en Bos",
         "description": "Gepinde exclusion-bron voor BE (mercator-sbz-wms, "
                        "nz:nz_n_gevoelige_habitats_sbz_2025); nog niet gebruikt door een "
                        "geformaliseerde BE-regel — de BE-zones zijn (nog) AOI-breed.",
         "settings": {"url": "https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/ows",
                      "featureName": "nz:nz_n_gevoelige_habitats_sbz_2025",
                      "contentType": "image/png", "webMercator": True}},
        {"id": "bron-dhmv-be", "type": "wms",
         "title": "DHM Vlaanderen II (hillshade) — context", "groupId": "scenario-bronnen",
         "defaultOn": False, "defaultAddToManager": True, "attribution": "Geopunt / Vlaamse overheid",
         "description": "Hoogtecontext (geopunt-dhmv-wms); geen norm-operand — besluit 'vlak' "
                        "staat in data/grb_extrusie_besluit.json.",
         "settings": {"url": "https://geo.api.vlaanderen.be/DHMV/wms",
                      "featureName": "DHMV_II_HILL_25cm", "contentType": "image/png",
                      "webMercator": True}},
    ]
    if (layers_dir / "netcongestie-afname-nl.geojson").is_file():
        lagen.append({
            "id": "bron-netcongestie-nl", "type": "geojson",
            "title": "Netcongestie afname (NL) — context", "groupId": "scenario-bronnen",
            "defaultOn": False, "defaultAddToManager": True, "opacity": 45,
            "attribution": "Netbeheer Nederland, Landelijke Capaciteitskaart elektriciteitsnet",
            "description": "Voedingsgebieden met afnamecode (0=beschikbaar … 3=tekort met "
                           "wachtrij); scenario-basis voor energietoets "
                           "(fetch_netcongestie_layer.py, zelfde cache als de pipeline).",
            "settings": {"url": "layers/netcongestie-afname-nl.geojson",
                         "style": {"fill": "#a51d2d", "stroke": "#620e14"}},
        })
    return lagen


def make_viewer_config(*, track: str, run_dir: Path, out_dir: Path) -> Path:
    geo_src = run_dir / f"zones-{track}-nspd.geojson"
    if not geo_src.is_file():
        raise SystemExit(f"ontbreekt: {geo_src} — draai eerst de xborder-merge (taak 10)")
    layers_dir = out_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = out_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(geo_src, layers_dir / geo_src.name)

    # per track: final-only zonebestanden per land, AOI-only-label, rapport
    scenario_groepen: list[dict] = []
    scenario_lagen: list[dict] = []
    for t, bron in _scenario_tracken(run_dir, track).items():
        if not bron.is_file():
            continue
        fc = json.loads(bron.read_text(encoding="utf-8"))
        final = _final_zones(fc.get("features", []))
        per_land: dict[str, list[dict]] = {}
        for feat in final:
            per_land.setdefault(feat["properties"].get("land", "nl"), []).append(feat)
        laag_bestanden: dict[str, str] = {}
        for land, feats in per_land.items():
            pad = layers_dir / f"zones-{t}-{land}.geojson"
            pad.write_text(json.dumps(
                {"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
                encoding="utf-8")
            laag_bestanden[land] = pad.name
        aoi_only = all(set(f["properties"].get("ruleIds", ["FR-AOI-01"])) <= {"FR-AOI-01"}
                       for f in final)
        rapport = run_dir.parent / t / "report-xborder.html"
        rapport_pad = ""
        if rapport.is_file():  # alle tracks heten report-xborder.html → per track benoemen
            shutil.copy2(rapport, reports_dir / f"{t}.html")
            rapport_pad = f"reports/{t}.html"
        regels = sorted({r for f in final for r in f["properties"].get("ruleIds", [])})
        beschrijving = ("Eindzone = aanvraag-AOI (alleen FR-AOI-01): deze track heeft geen "
                        "ruimtelijke norm-operand — de waarde zit in de normtabellen van het "
                        "rapport. " if aoi_only else "")
        beschrijving += f"Regels: {', '.join(regels)}."
        if rapport_pad:
            beschrijving += f" Rapport: {rapport_pad}"
        scenario_groepen.append({
            "id": f"scenario-{t}", "parentId": "scenario",
            "title": f"Scenario: {t}" + (" (AOI-breed)" if aoi_only else ""),
            "isOpen": t == track,
        })
        for land, bestand in laag_bestanden.items():
            st = LAND_STIJL[land]
            scenario_lagen.append({
                "id": f"zones-{t}-{land}", "type": "geojson",
                "title": f"Zones {t} {'NL' if land == 'nl' else 'BE'}",
                "groupId": f"scenario-{t}",
                "defaultOn": t == track, "defaultAddToManager": True,
                "opacity": ZONE_OPACITY,
                "description": beschrijving,
                "settings": {"url": f"layers/{bestand}",
                             "style": {"fill": st["fill"], "stroke": st["stroke"]}},
            })

    ref_groepen, ref_lagen = _zeeland_referentielagen()
    bronnen_lagen = _scenario_bronnen(layers_dir)
    cfg = {
        "name": f"poc-nspd — NSPD {track}",
        "viewer": {
            "title": f"poc-nspd — NSPD {track}",
            "subTitle": "grensvergelijkende scan (plan 2026-10-14)",
            # Camera boven de Belgische kanaalzone, noordwaarts op Zelzate — dichtbij
            # genoeg voor de GRB-detailkaart en de 3D-gebouwen (bewezen 2026-10-16);
            # de "home"-knop brengt hier terug, uitzoomen geeft het districtsoverzicht.
            "startPosition": {"x": 3.80, "y": 51.155, "z": 4500, "heading": 0, "pitch": -45, "duration": 3},
        },
        "groups": [
            {"id": "achtergrond", "title": "Achtergrond (eigen)", "isOpen": True},
            {"id": "d3", "title": "Gebouwcontext (eigen)", "isOpen": True},
            {"id": "scenario", "title": "Scenario-zones (AI-pipeline)", "isOpen": True},
            {"id": "scenario-bronnen", "title": "Scenario-bronlagen (regel-operanden)", "isOpen": True},
            *scenario_groepen,
            *ref_groepen,
        ],
        "layers": [
            {"id": "bg-brt", "type": "wmts", "title": "BRT Achtergrondkaart (NL)", "groupId": "achtergrond",
             "isBackground": True, "defaultOn": True, "attribution": "PDOK", "defaultAddToManager": True,
             "settings": {"url": BRT_WMTS, "featureName": "standaard", "contentType": "image/png"}},
            # De Vlaamse luchtfoto komt via de referentielagen ("Luchtfoto Vlaanderen",
            # OFW-WMS); de eerdere eigen OMW-pin (featureName omwrgbmrvl) bestond niet.
            {"id": "bag3d", "type": "3dtiles", "title": "3D BAG LoD2.2 (NL-gebouwen)", "groupId": "d3",
             "defaultOn": True, "attribution": "3D BAG / TU Delft, CC-BY-4.0", "defaultAddToManager": True,
             "settings": {"url": BAG_3D, "enableHeightControl": True}},
            *bronnen_lagen,
            *scenario_lagen,
            *ref_lagen,
        ],
        # Leia verwacht tools als ARRAY van {id, enabled} met exacte tool-id's
        # (zie viewer/static/example.config.json); een object breekt de tool-init.
        # layerLibrary ontsluit de 50+ referentielagen die niet standaard aan staan.
        "tools": [{"id": "layerManager", "enabled": True},
                  {"id": "layerLibrary", "enabled": True},
                  {"id": "featureInfo", "enabled": True}],
    }
    # Fase-1-laag (taak 12, besluit "vlak"): GRB:ADP = administratieve PERCELEN,
    # géén gebouwen (ontdekt 2026-10-16 aan de CAPAKEY/CANU-attributen). Gebouwen
    # komen nu uit de referentielaag "3D Gebouwen België". Besluitdocument:
    # data/grb_extrusie_besluit.json; laagbestand via fetch_grb_layer.py.
    if (ROOT / "data" / "grb_extrusie_besluit.json").is_file():
        json.loads((ROOT / "data" / "grb_extrusie_besluit.json").read_text(encoding="utf-8"))
        cfg["layers"].append({
            "id": "grb-percelen",
            "type": "geojson",
            "title": "GRB percelen (BE, ADP, vlak)",
            "groupId": "d3",
            "defaultOn": False, "defaultAddToManager": True,
            "attribution": "GRB via Geopunt, vrije open data-modellicentie",
            "settings": {"url": "layers/grb-percelen-be.geojson"},
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
