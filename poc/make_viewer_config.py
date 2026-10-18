"""Utrecht-PoC run-output → Leia-config (NSPD-patroon, make_viewer_config.py van
poc-nspd geport). Genereert deep-agents/viewer-utrecht/: de Leia-build met een
Utrecht-config (achtergrondkaart, 3D-gebouwcontext, scenario-zones per
uitdaging, what-if-runs, landelijke bronlagen) — Lagenbeheer met aan/uit per
groep en laag, opstart-schoon (alleen basiskaarten aan).

Run: cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 make_viewer_config.py
Kijk: http://127.0.0.1:8765/viewer-utrecht/index.html
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SCENARIO_RUNS = ROOT / "scenario-runs"
UITDAGINGEN = ROOT / "scenarios" / "uitdagingen.json"
ALIASES = ROOT / "tracks" / "_zone-aliases.json"
NATIONAL = ROOT / "data" / "cache" / "national"
# De Leia-build (poc-nspd/viewer/build) is voor ROOT-hosting gebouwd
# (APP_URL gebakken op http://localhost:8010): alle app-fetches resolven daar
# naartoe via <base href>. De Utrecht-viewer is dus een SUBMAP van die build
# (config.json + layers/), geserveerd door de draaiende NSPD-server op 8010 —
# zelfde origin, geen CORS, en laag-URL's zijn root-absoluut (/utrecht/...).
OUT = REPO / "poc-nspd" / "viewer" / "build" / "utrecht"
URL_PREFIX = "/utrecht"
BRT_WMTS = "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0?"
BAG_3D = "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json"

# Leia (geojson-layer.ts): vul-transparantie komt uitsluitend uit laag-opacity;
# een hex-alpha wordt door withAlpha() overschreven. Zie NSPD-variant.
ZONE_OPACITY = 20

CONTROL_STIJL = {"fill": "#5e5c64", "stroke": "#3d3846"}
# scenario-kleuren per richting (NSPD-conventie): groen = ruimte erbij,
# rood = ruimte eraf
TRACK_STIJL = {
    "wind": ("#1a5fb4", "#0f3d73"), "zon": ("#e5a50a", "#8f6a06"),
    "bos": ("#26a269", "#155e3f"), "water": ("#1c71d8", "#124a8f"),
    "bodem": ("#813d9c", "#4e2560"), "mobiliteit": ("#986a44", "#5c3f28"),
    "landschap": ("#8c564b", "#4e2f28"), "landbouw": ("#e78a4e", "#8a5124"),
    "wonen": ("#3584e4", "#1b58a8"), "werken": ("#f6d32d", "#8a7517"),
    "recreatie": ("#33d17a", "#1e7a48"), "biomassa": ("#ff7800", "#994800"),
    "energietoets": ("#f66151", "#93410c"),
}


def _uitdaging_featured() -> list[dict]:
    """[{uitdaging: {id, titel}, track, run_id}] uit het curation-contract."""
    uj = json.loads(UITDAGINGEN.read_text(encoding="utf-8"))
    per: dict[str, dict] = {}
    for uit in uj["uitdagingen"]:
        for track in uit["tracks"]:
            run_id = uj["scenarioRuns"].get(track)
            if run_id:
                per[track] = {"uitdaging": uit, "track": track, "run_id": run_id}
    volgorde = [t for u in uj["uitdagingen"] for t in u["tracks"]]
    return sorted(per.values(), key=lambda x: volgorde.index(x["track"]))


def _scenario_groep_en_lagen(layers_dir: Path) -> tuple[list[dict], list[dict]]:
    """Per uitdaging een subgroep met CONTROL + scenario-lagen (delta in titel,
    kleur per track). Opstart: alles uit — Lagenbeheer is de bediening."""
    groepen: list[dict] = []
    lagen: list[dict] = []
    for item in _uitdaging_featured():
        track, run_id = item["track"], item["run_id"]
        bron = SCENARIO_RUNS / run_id
        rapport_pad = bron / "scenario-report.json"
        if not rapport_pad.is_file():
            continue
        rapport = json.loads(rapport_pad.read_text(encoding="utf-8"))
        gid = f"scenario-{track}"
        groepen.append({"id": gid, "parentId": "scenario",
                        "title": f"Uitdaging: {item['uitdaging']['titel']} — {track}",
                        "isOpen": False})
        control_km2 = float((rapport.get("control") or {}).get("finalAreaKm2") or 0)
        control = bron / "scenarios" / "CONTROL.geojson"
        if control.is_file():
            shutil.copy2(control, layers_dir / f"zones-{track}-CONTROL.geojson")
            lagen.append({
                "id": f"zones-{track}-CONTROL", "type": "geojson",
                "title": f"CONTROL {track} ({control_km2:.1f} km²)".replace(".", ","),
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": 15,
                "description": "Reproductie van de baseline-zone door de scenario-"
                               "engine; alle deltas zijn t.o.v. deze laag gemeten.",
                "settings": {"url": f"{URL_PREFIX}/layers/zones-{track}-CONTROL.geojson",
                             "style": CONTROL_STIJL},
            })
        fill, stroke = TRACK_STIJL.get(track, ("#c64600", "#7a2b00"))
        for s in rapport.get("scenarios", []):
            geo = bron / str(s.get("geometryFile") or "")
            if not geo.is_file():
                continue
            scid = str(s.get("scenarioId") or Path(geo).stem)
            delta = float(s.get("deltaVsControlKm2") or 0)
            kleur = "#1a7f37" if delta >= 0 else "#c01c28"
            shutil.copy2(geo, layers_dir / f"zones-{track}-{scid}.geojson")
            basis_type = str((s.get("basis") or {}).get("type") or "")
            lagen.append({
                "id": f"zones-{track}-{scid}", "type": "geojson",
                "title": f"{scid} (Δ {delta:+.1f} km²)".replace(".", ","),
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": ZONE_OPACITY,
                "description": (f"{s.get('name', '')} — basis: {basis_type}; "
                                f"delta t.o.v. control {delta:+.1f} km² "
                                f"(IoU {float(s.get('iouVsControl') or 0):.2f})."),
                "settings": {"url": f"{URL_PREFIX}/layers/zones-{track}-{scid}.geojson",
                             "style": {"fill": kleur, "stroke": kleur}},
            })
    return groepen, lagen


def _whatif_groep_en_lagen(layers_dir: Path) -> tuple[list[dict], list[dict]]:
    """De data-gegronde what-ifs (fase 3): *-whatif-sets met add_zone_rule."""
    groepen: list[dict] = []
    lagen: list[dict] = []
    for rapport_pad in sorted(SCENARIO_RUNS.glob("*-whatif/scenario-report.json")):
        try:
            rapport = json.loads(rapport_pad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rapport.get("verdict") != "pass":
            continue
        usecase = rapport_pad.parent.name.removesuffix("-whatif")
        gid = f"whatif-{usecase}"
        groepen.append({"id": gid, "parentId": "whatif",
                        "title": f"What-if: {usecase}", "isOpen": False})
        bron = rapport_pad.parent
        control_km2 = float((rapport.get("control") or {}).get("finalAreaKm2") or 0)
        control = bron / "scenarios" / "CONTROL.geojson"
        if control.is_file():
            shutil.copy2(control, layers_dir / f"whatif-{usecase}-CONTROL.geojson")
            lagen.append({
                "id": f"whatif-{usecase}-CONTROL", "type": "geojson",
                "title": f"CONTROL ({control_km2:.1f} km²)".replace(".", ","),
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": 15,
                "description": "Reproductie van de baseline-zone door de scenario-"
                               "engine; alle deltas zijn t.o.v. deze laag gemeten.",
                "settings": {"url": f"{URL_PREFIX}/layers/whatif-{usecase}-CONTROL.geojson",
                             "style": CONTROL_STIJL},
            })
        for s in rapport.get("scenarios", []):
            geo = bron / str(s.get("geometryFile") or "")
            if not geo.is_file():
                continue
            scid = str(s.get("scenarioId") or Path(geo).stem)
            delta = float(s.get("deltaVsControlKm2") or 0)
            kleur = "#1a7f37" if delta >= 0 else "#c01c28"
            shutil.copy2(geo, layers_dir / f"whatif-{usecase}-{scid}.geojson")
            dg = (s.get("basis") or {}).get("dataGrounding") or {}
            lagen.append({
                "id": f"whatif-{usecase}-{scid}", "type": "geojson",
                "title": f"{scid} (Δ {delta:+.1f} km²)".replace(".", ","),
                "groupId": gid, "defaultOn": False, "defaultAddToManager": True,
                "opacity": 25,
                "description": (f"{s.get('name', '')} — data-gegrond what-if "
                                f"(bron: {dg.get('sourceId', '?')}); delta t.o.v. "
                                f"control {delta:+.1f} km²."),
                "settings": {"url": f"{URL_PREFIX}/layers/whatif-{usecase}-{scid}.geojson",
                             "style": {"fill": kleur, "stroke": kleur}},
            })
    return groepen, lagen


#: de nationale caches met geometrie (plan 2); RD-caches gaan naar WGS84 en
#: worden boven 2 MB display-gesimplificeerd (5 m) — zelfde patroon als NSPD.
_BRON_KEUZES = [
    ("netcongestie", "Netcongestie voedingsgebieden (Landelijke Capaciteitskaart)",
     "#a51d2d", "#620e14", "scenario-basis voor energietoets en de what-ifs; "
     "afnamecodes 0-3 (3 = tekort met wachtrij)."),
    ("rce-monumenten", "Rijksmonumenten (RCE)", "#8c564b", "#4e2f28",
     "punten; erfgoed-context bij wonen/landschap."),
    ("rce-iam-archeologie", "Archeologische monumenten (AMK-2014)", "#b5835a", "#614434",
     "substituut voor IAM (geen open WMS); erfgoed-context."),
    ("nwb-wegvakken", "NWB-wegvakken (RWS)", "#17becf", "#0b5f66",
     "wegennet-context bij mobiliteit."),
    ("prorail-spoor", "Spoorlijnen (ProRail)", "#984ea3", "#4c1547",
     "spoor-context bij mobiliteit."),
]


def _eerste_coord(fc: dict) -> float | None:
    """Eerste x-coördinaat, diep genest (Point t/m MultiPolygon)."""
    def dig(c):
        while isinstance(c, (list, tuple)) and c and isinstance(c[0], (list, tuple)):
            c = c[0]
        return c[0] if isinstance(c, (list, tuple)) and c else None

    for f in fc.get("features", []):
        g = f.get("geometry") or {}
        x = dig(g.get("coordinates"))
        if x is not None:
            return float(x)
    return None


def _bron_lagen(layers_dir: Path) -> list[dict]:
    sys_path = str(ROOT)
    if sys_path not in __import__("sys").path:
        __import__("sys").path.insert(0, sys_path)
    from pipeline.geodata import feature_collection_to_wgs84
    from shapely.geometry import mapping, shape

    aliases = json.loads(ALIASES.read_text(encoding="utf-8"))
    lagen: list[dict] = []
    for zone_id, titel, fill, stroke, uitleg in _BRON_KEUZES:
        alias = aliases.get(zone_id) or {}
        bron = ROOT / alias.get("cachePath", "")
        if not bron.is_file():
            print(f"[bronnen] {zone_id} overgeslagen: cache ontbreekt ({bron})")
            continue
        doel = layers_dir / f"bron-{zone_id}.geojson"
        if not doel.is_file():
            try:
                fc = json.loads(bron.read_text(encoding="utf-8"))
                fc = fc.get("records", fc)
                if bron.stat().st_size > 2_000_000:
                    for f in fc.get("features", []):
                        g = f.get("geometry")
                        if g:
                            f["geometry"] = mapping(shape(g).simplify(5.0, preserve_topology=True))
                if fc.get("features"):
                    x = _eerste_coord(fc)
                    if x is not None and abs(x) > 180:  # RD → WGS84
                        fc = feature_collection_to_wgs84(fc)
                fc["properties"] = {"viewerNote": "display-kopie van de nationale "
                                    "pipeline-cache; autoritatieve geometrie: de cache zelf"}
                doel.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
            except Exception as exc:  # nooit crashen: laag overslaan
                print(f"[bronnen] {zone_id} overgeslagen: {exc}")
                continue
        lagen.append({
            "id": f"bron-{zone_id}", "type": "geojson",
            "title": titel, "groupId": "bronnen",
            "defaultOn": False, "defaultAddToManager": True, "opacity": 55,
            "attribution": "landelijke open bronnen (plan 2 data-kalibratie)",
            "description": f"{uitleg} Rol: {alias.get('role', 'context')}.",
            "settings": {"url": f"{URL_PREFIX}/layers/bron-{zone_id}.geojson",
                         "style": {"fill": fill, "stroke": stroke}},
        })
    return lagen


def main() -> int:
    layers_dir = OUT / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    # geen Leia-kopie nodig: de root (../index.html, ../_app, ../Cesium) doet al het werk

    scenario_groepen, scenario_lagen = _scenario_groep_en_lagen(layers_dir)
    whatif_groepen, whatif_lagen = _whatif_groep_en_lagen(layers_dir)
    bron_lagen = _bron_lagen(layers_dir)

    cfg = {
        "name": "ldttoolbox — Utrecht-PoC",
        "viewer": {
            "title": "Utrecht-PoC — waar kan ik wat?",
            "subTitle": "5 uitdagingen × 13 tracks × 3 scenario's (+ what-ifs), "
                        "elke claim geciteerd uit de Omgevingsverordening",
            "startPosition": {"x": 5.12, "y": 52.08, "z": 45000,
                              "heading": 0, "pitch": -45, "duration": 3},
        },
        "groups": [
            {"id": "achtergrond", "title": "Achtergrond", "isOpen": True},
            {"id": "d3", "title": "Gebouwcontext (3D BAG)", "isOpen": True},
            {"id": "scenario", "title": "Scenario-zones per uitdaging", "isOpen": True},
            *scenario_groepen,
            {"id": "whatif", "title": "What-if scenario's (data-gegrond)",
             "isOpen": bool(whatif_groepen)},
            *whatif_groepen,
            {"id": "bronnen", "title": "Landelijke bronlagen (kalibratie plan 2)",
             "isOpen": False},
        ],
        "layers": [
            {"id": "bg-brt", "type": "wmts", "title": "BRT Achtergrondkaart (NL)",
             "groupId": "achtergrond", "isBackground": True, "defaultOn": True,
             "attribution": "PDOK", "defaultAddToManager": True,
             "settings": {"url": BRT_WMTS, "featureName": "standaard",
                          "contentType": "image/png"}},
            # 3D BAG staat bewust standaard UIT: de tileset crashte de Cesium-
            # renderloop bij opstart (bisect 2026-10-18, [object Object]); als
            # schakelaar in Lagenbeheer probeert hij opnieuw bij het aanzetten.
            {"id": "bag3d", "type": "3dtiles", "title": "3D BAG LoD2.2 (NL-gebouwen)",
             "groupId": "d3", "defaultOn": False, "attribution": "3D BAG / TU Delft, CC-BY-4.0",
             "defaultAddToManager": True,
             "description": "3D-gebouwcontext; bij crash de schakelaar weer uit — "
                            "de tileset faalt soms afhankelijk van net/werkgeheugen.",
             "settings": {"url": BAG_3D, "enableHeightControl": True}},
            *scenario_lagen,
            *whatif_lagen,
            *bron_lagen,
        ],
        "tools": [{"id": "layerManager", "enabled": True},
                  {"id": "layerLibrary", "enabled": True},
                  {"id": "featureInfo", "enabled": True}],
    }
    # Opstart-schone kaart (NSPD-conventie): alléén de basiskaarten staan aan;
    # alles thematische staat één klik weg in Lagenbeheer.
    for laag in cfg["layers"]:
        if laag["id"] != "bg-brt":
            laag["defaultOn"] = False

    (OUT / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Leia-config: {OUT / 'config.json'} "
          f"({len(cfg['layers'])} lagen, {len(cfg['groups'])} groepen)")
    print("kijk op: http://localhost:8010/index.html?config=/utrecht/config.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
