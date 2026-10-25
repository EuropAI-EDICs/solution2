"""Contextpagina's per uitdaging — zelfstandige Leaflet-pagina's.

Voor elke uitdaging uit ``poc/scenarios/uitdagingen.json`` wordt één pagina
geschreven: de control-zone van de featured run (juridisch) plus
contextlagen (netcongestie, RCE, RWS/ProRail, CBS) die expliciet in de
legenda dragen: *context — geen juridische zone*. De pagina's zijn
besluit-ondersteuning, nooit een juridisch advies.

Twee bewuste afwijkingen van het oorspronkelijke plan-briefje:

1. **Uitvoermap.** De pagina's gaan naar ``nldt/simulation/`` (en niet naar
   ``deep-agents/runs/``): het dashboard laadt ``simulationPages`` via
   ``/simulation/<pad>`` en ``live_server`` serveert dat pad uitsluitend uit
   ``nldt/simulation``; ``deep-agents/runs/`` is bovendien gitignored.
   ``nldt/simulation`` is wel in git — de pagina's zijn dus reproduceerbaar
   én direct gelinkt vanaf het dashboard.
2. **CBS-grid als statusregel.** De 100m-kerncijfers-cache bevat ~18k
   cellen zonder geometrie (alleen celcodes/kenmerken). Een puntwolk van
   18k cirkels is onpraktisch en de geometrie is niet bewaard; de cache-
   status (aantal cellen) staat daarom als legenda-regel op de pagina in
   plaats van als overlay. Idem voor landgebruik (kenmerken zonder
   geometrie) en DINO (endpoint niet gepind).

Alle lagen zijn *cache-waarnemend*: ontbrekende caches worden nooit
opgehaald (geen netwerk) maar gemeld in de legenda. Geometrieën worden
geclipt op de Utrecht-AOI, vereenvoudigd (Douglas-Peucker) en gereprojecteerd
naar WGS84 — uitsluitend voor weergave. Dat geldt ook voor de control-zone
(10 m-tolerantie); de juridische geometrie zelf blijft onaangetast in de
run-map (``poc/scenario-runs/<run>/scenarios/CONTROL.geojson``).
"""

from __future__ import annotations

import html as _html
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyproj import Transformer  # noqa: E402

from pipeline import national_data as nd  # noqa: E402
from pipeline.scenario_labels import (  # noqa: E402
    BASELINE_VERSCHIL,
    final_only_fc,
    scenario_kleur,
    scenario_kort,
    scenario_verschil,
)

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "nldt" / "simulation"  # dashboard serveert /simulation/ hieruit
SCENARIO_RUNS = REPO / "poc" / "scenario-runs"
BASELINE_KLEUR = "#145a32"

UITDAGINGEN = json.loads(
    (REPO / "poc" / "scenarios" / "uitdagingen.json").read_text(encoding="utf-8"))

AOI_RD = nd.UTRECHT_BBOX_RD  # (130000, 440000, 160000, 470000) — weergave-uitknip

LEGE_FC = '{"type": "FeatureCollection", "features": []}'

_TO_RD = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
_TO_WGS = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)


# --------------------------------------------------------------------------- #
# Geometrie-hulpen — clip op de AOI (RD), Douglas-Peucker, RD↔WGS84
# --------------------------------------------------------------------------- #

def _map_coords(coords: Any, fn) -> Any:
    """Roept ``fn`` op elke positie (diepte-3-lijst) in een coordinate-boom."""
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        return fn(coords)
    return [_map_coords(c, fn) for c in coords]


def _segment_in_bbox(a: list, b: list, bbox: tuple) -> tuple | None:
    """Liang-Barsky: zichtbaar interval (t0, t1) van segment a→b in de bbox."""
    x0, y0, x1, y1 = bbox
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return None
                t0 = max(t0, r)
            else:
                if r < t0:
                    return None
                t1 = min(t1, r)
    if t1 <= t0:
        return None  # raakt hooguit een hoek: niets zichtbaars
    return t0, t1


def _lerp(a: list, b: list, t: float) -> list:
    return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]


def _clip_paths(paths: list, bbox: tuple) -> list:
    """Knipt lijnpaden op de bbox; levert 0..n nieuwe paden (>= 2 punten)."""
    uit: list[list] = []
    for pts in paths:
        cur: list = []
        for i in range(len(pts) - 1):
            seg = _segment_in_bbox(pts[i], pts[i + 1], bbox)
            if seg is None:
                if len(cur) >= 2:
                    uit.append(cur)
                cur = []
                continue
            t0, t1 = seg
            p_in, p_out = _lerp(pts[i], pts[i + 1], t0), _lerp(pts[i], pts[i + 1], t1)
            if cur and abs(cur[-1][0] - p_in[0]) < 1e-9 and abs(cur[-1][1] - p_in[1]) < 1e-9:
                cur.append(p_out)
            else:
                if len(cur) >= 2:
                    uit.append(cur)
                cur = [p_in, p_out]
        if len(cur) >= 2:
            uit.append(cur)
    return uit


def _clip_ring(ring: list, bbox: tuple) -> list:
    """Sutherland-Hodgman: knipt een (gesloten) ring op de convexe bbox."""
    x0, y0, x1, y1 = bbox

    def inter_v(a: list, b: list, x: float) -> list:
        t = (x - a[0]) / (b[0] - a[0])
        return [x, a[1] + t * (b[1] - a[1])]

    def inter_h(a: list, b: list, y: float) -> list:
        t = (y - a[1]) / (b[1] - a[1])
        return [a[0] + t * (b[0] - a[0]), y]

    pts = ring
    for inside, cross in (
        (lambda p: p[0] >= x0, lambda a, b: inter_v(a, b, x0)),
        (lambda p: p[0] <= x1, lambda a, b: inter_v(a, b, x1)),
        (lambda p: p[1] >= y0, lambda a, b: inter_h(a, b, y0)),
        (lambda p: p[1] <= y1, lambda a, b: inter_h(a, b, y1)),
    ):
        if len(pts) < 3:
            return []
        uit: list = []
        for i in range(len(pts)):
            cur, prev = pts[i], pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    uit.append(cross(prev, cur))
                uit.append(cur)
            elif inside(prev):
                uit.append(cross(prev, cur))
        pts = uit
    return pts if len(pts) >= 3 else []


def _douglas_peucker(points: list, eps: float) -> list:
    """Iteratieve Douglas-Peucker (diepte-bewust: geen recursielimiet)."""
    n = len(points)
    if n < 3:
        return list(points)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = points[i][0], points[i][1]
        bx, by = points[j][0], points[j][1]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        dmax, imax = -1.0, -1
        for k in range(i + 1, j):
            px, py = points[k][0], points[k][1]
            if seg2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > dmax:
                dmax, imax = d, k
        if dmax > eps:
            keep[imax] = True
            stack.append((i, imax))
            stack.append((imax, j))
    return [points[k] for k in range(n) if keep[k]]


def _vereenvoudig_ring(ring: list, eps: float) -> list | None:
    """Gesloten ring → geclipt, vereenvoudigd, opnieuw gesloten — of None."""
    ring = _clip_ring(ring, AOI_RD)
    if len(ring) < 4:  # gesloten: minimaal driehoek
        return None
    open_ring = _douglas_peucker(ring[:-1], eps)
    if len(open_ring) < 3:
        return None
    return [*open_ring, list(open_ring[0])]


def _clip_simplify(gtype: str, coords: Any, eps: float) -> tuple[str, Any] | None:
    """Geometry → (type, RD-coordinaten) geclipt+vereenvoudigd, of None."""
    if gtype == "Point":
        x0, y0, x1, y1 = AOI_RD
        if x0 <= coords[0] <= x1 and y0 <= coords[1] <= y1:
            return "Point", coords
        return None
    if gtype == "MultiPoint":
        x0, y0, x1, y1 = AOI_RD
        gehouden = [p for p in coords if x0 <= p[0] <= x1 and y0 <= p[1] <= y1]
        return ("MultiPoint", gehouden) if gehouden else None
    if gtype in ("LineString", "MultiLineString"):
        paden = _clip_paths([coords] if gtype == "LineString" else coords, AOI_RD)
        paden = [_douglas_peucker(p, eps) for p in paden]
        paden = [p for p in paden if len(p) >= 2]
        if not paden:
            return None
        if len(paden) == 1:
            return "LineString", paden[0]
        return "MultiLineString", paden
    if gtype == "Polygon":
        ringen = [_vereenvoudig_ring(r, eps) for r in coords]
        if not ringen or ringen[0] is None:
            return None
        return "Polygon", [r for r in ringen if r is not None]
    if gtype == "MultiPolygon":
        polys = []
        for poly in coords:
            ringen = [_vereenvoudig_ring(r, eps) for r in poly]
            if ringen and ringen[0] is not None:
                polys.append([r for r in ringen if r is not None])
        return ("MultiPolygon", polys) if polys else None
    return None  # onbekend type: liever weglaten dan de pagina breken


def prepare_fc(
    fc: dict,
    *,
    crs: str = "rd",
    tolerance_m: float = 10,
    keep: list[str] | None = None,
) -> dict:
    """FeatureCollection → WGS84-FC geclipt op de Utrecht-AOI, vereenvoudigd.

    ``crs`` is het CRS van de *invoer* ("rd" of "wgs84"); uitvoer is altijd
    WGS84 (EPSG:4326), afgerond op 5 decimalen (~1 m). ``keep`` is een
    property-whitelist (popup/legenda); None = alles overnemen. Features
    zonder geometrie of volledig buiten de AOI vervallen.
    """
    if str(crs).lower() not in ("rd", "wgs84"):
        raise ValueError(f"onbekend invoer-CRS {crs!r} — gebruik 'rd' of 'wgs84'")
    wgs_in = str(crs).lower() == "wgs84"
    feats_uit: list[dict] = []
    for feat in (fc.get("features", []) if isinstance(fc, dict) else []):
        geom = feat.get("geometry")
        if not geom or not geom.get("coordinates"):
            continue
        coords = geom["coordinates"]
        if wgs_in:
            coords = _map_coords(
                coords, lambda p: list(_TO_RD.transform(p[0], p[1])[:2]))
        geprepareerd = _clip_simplify(geom["type"], coords, tolerance_m)
        if geprepareerd is None:
            continue
        nieuw_type, nieuwe_coords = geprepareerd

        def _naar_wgs(p):  # RD → WGS84, 5 decimalen (~1 m): compact en sub-pixel
            lon, lat = _TO_WGS.transform(p[0], p[1])[:2]
            return [round(lon, 5), round(lat, 5)]

        uit_coords = _map_coords(nieuwe_coords, _naar_wgs)
        props = feat.get("properties") or {}
        if keep is not None:
            props = {k: props[k] for k in keep if k in props}
        feats_uit.append({"type": "Feature", "properties": props,
                          "geometry": {"type": nieuw_type, "coordinates": uit_coords}})
    return {"type": "FeatureCollection", "features": feats_uit}


# --------------------------------------------------------------------------- #
# Contextlagen — cache-waarnemend, per uitdaging; nooit netwerk
# --------------------------------------------------------------------------- #

def _laag(naam: str, kleur: str, *, geojson: str = "", status: str = "",
          **extra: Any) -> dict:
    laag = {"name": naam, "color": kleur, "geojson": geojson,
            "status": status, "legal": False}
    laag.update(extra)
    return laag


def _dag(iso: Any) -> str:
    return str(iso)[:10] if iso else ""


def _objecten_status(n: int, dag: str = "") -> str:
    woord = "object" if n == 1 else "objecten"
    return f"{n} {woord} uit cache" + (f" ({dag})" if dag else "")


def _lees_cache(cache_name: str) -> dict | None:
    """Leest een nationale cache; None als hij ontbreekt of onleesbaar is."""
    pad = nd.CACHE / cache_name
    if not pad.is_file():
        return None
    try:
        data = json.loads(pad.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _laag_netcongestie() -> dict:
    naam, kleur = "Netcongestie (context)", "#c0392b"
    try:
        payload = nd.load_netcongestie()
    except FileNotFoundError:
        return _laag(naam, kleur, status=(
            "cache ontbreekt — download volgens poc/data/sources.json "
            "(netbeheerder-netcongestie)"))
    fc = prepare_fc(payload["records"], crs="wgs84", tolerance_m=25,
                    keep=["afname", "voedingsgebied_naam", "RNB", "wachtrij_afname"])
    return _laag(
        naam, kleur,
        geojson=json.dumps(fc, ensure_ascii=False),
        status=_objecten_status(len(fc["features"]), _dag(payload.get("retrieved"))),
        styleBy={"prop": "afname",
                 "palette": {"0": "#27ae60", "1": "#f39c12",
                             "2": "#e67e22", "3": "#c0392b"}},
        popup=["afname", "voedingsgebied_naam", "wachtrij_afname"])


def _wfs_laag(naam: str, kleur: str, cache_name: str, *, keep: list[str],
              popup: list[str], tolerance_m: float = 10) -> dict:
    payload = _lees_cache(cache_name)
    if payload is None:
        return _laag(naam, kleur, status=(
            f"cache ontbreekt ({cache_name}) — haal via "
            f"national_data.fetch_wfs of leg de fixture aan"))
    fc = prepare_fc(payload["records"], crs="rd", tolerance_m=tolerance_m, keep=keep)
    return _laag(naam, kleur,
                 geojson=json.dumps(fc, ensure_ascii=False),
                 status=_objecten_status(len(fc["features"]), _dag(payload.get("retrieved"))),
                 popup=popup)


def _laag_rijksmonumenten() -> dict:
    return _wfs_laag(
        "Rijksmonumenten (context)", "#8e44ad", "rce-monumenten.json",
        keep=["rijksmonument_nummer", "hoofdcategorie", "subcategorie"],
        popup=["rijksmonument_nummer", "hoofdcategorie"])


def _laag_archeologie() -> dict:
    return _wfs_laag(
        "Archeologie — AMK 2014 (context)", "#d35400", "rce-iam-archeologie.json",
        keep=["monumentnummer", "toponiem", "kwaliteitswaarde"],
        popup=["monumentnummer", "kwaliteitswaarde"], tolerance_m=25)


def _laag_rws_wegen() -> dict:
    return _wfs_laag(
        "RWS wegen (context)", "#7f8c8d", "rws-nwb-wegen.json",
        keep=["wegnummer", "wegbehsrt"], popup=["wegnummer"], tolerance_m=15)


def _laag_spoor() -> dict:
    return _wfs_laag(
        "Spoorlijnen ProRail (context)", "#2c3e50", "prorail-spoor.json",
        keep=["geocodeNaam"], popup=["geocodeNaam"], tolerance_m=10)


def _laag_cbs_grid() -> dict:
    """Grid-besluit: 18k cellen gaan niet als puntwolk de pagina op."""
    naam, kleur = "CBS 100m-kerncijfers (context)", "#2980b9"
    payload = _lees_cache("cbs-grid-kerncijfers-100m.json")
    if payload is None:
        return _laag(naam, kleur, status=(
            "niet in de cache (CBS Vierkantstatistieken 100m via PDOK)"))
    n = len(payload.get("records", []))
    return _laag(naam, kleur, status=(
        f"cache aanwezig ({n:,} cellen)".replace(",", ".")
        + " — niet op de kaart (18k+ puntwolk onpraktisch; legenda-status)"))


def _laag_landgebruik() -> dict:
    naam, kleur = "CBS landgebruik (context)", "#16a085"
    payload = _lees_cache("cbs-landgebruik-100m.json")
    if payload is None:
        return _laag(naam, kleur, status=(
            "niet in de cache (CBS Existing Land Use via PDOK)"))
    n = len(payload.get("records", []))
    return _laag(naam, kleur, status=(
        f"cache aanwezig ({n:,} records)".replace(",", ".")
        + " — niet op de kaart (cache bewaart alleen kenmerken, geen geometrie)"))


def _laag_dino() -> dict:
    return _laag("DINO ondergrond (context)", "#f39c12", status=(
        "endpoint niet gepind — DINOloket biedt geen open WFS meer "
        "(zie poc/data/sources.json)"))


_LAGEN = {
    "netcongestie": _laag_netcongestie,
    "rce-monumenten": _laag_rijksmonumenten,
    "rce-iam-archeologie": _laag_archeologie,
    "rws-nwb-wegen": _laag_rws_wegen,
    "prorail-spoor": _laag_spoor,
    "cbs-grid": _laag_cbs_grid,
    "cbs-landgebruik": _laag_landgebruik,
    "dino-ondergrond": _laag_dino,
}

_LAGEN_PER_UITDAGING: dict[str, list[str]] = {
    "energietransitie": ["netcongestie", "cbs-grid"],
    "wonen-werken": ["rce-monumenten", "cbs-grid"],
    "water-bodem": ["rce-iam-archeologie", "dino-ondergrond", "cbs-grid"],
    "landschap-infra": ["rce-monumenten", "prorail-spoor", "rws-nwb-wegen", "cbs-grid"],
    "landelijk-gebied": ["rce-monumenten", "cbs-landgebruik", "cbs-grid"],
}


def context_layers(uitdaging_id: str) -> list[dict[str, Any]]:
    """Contextlagen die bij een uitdaging horen (cache-waarnemend).

    Elke geconfigureerde bron komt terug, als tekenbare laag (``geojson``
    gevuld) óf als statusregel (``geojson == ""``, ``status`` gevuld).
    Ontbrekende caches worden gemeld, nooit opgehaald.
    """
    return [_LAGEN[bron]() for bron in _LAGEN_PER_UITDAGING.get(uitdaging_id, [])]


def split_layers(layers: list[dict[str, Any]]) -> tuple[list, list]:
    """Deelt lagen in tekenbare overlays en legenda-statusregels."""
    tekenbaar = [l for l in layers if l.get("geojson")]
    statusregels = [l for l in layers if not l.get("geojson")]
    return tekenbaar, statusregels


# --------------------------------------------------------------------------- #
# Pagina-rendering — geen .format over de template (accolades in CSS/JS)
# --------------------------------------------------------------------------- #

_CSS = (
    "body{margin:0;font-family:sans-serif}#map{height:100vh}"
    ".legend{position:absolute;top:10px;right:10px;z-index:1100;background:#fff;"
    "padding:10px 12px;max-width:420px;max-height:92vh;overflow:auto;"
    "font-size:12px;line-height:1.45;box-shadow:0 1px 6px rgba(0,0,0,.3)}"
    ".legend label{display:block;cursor:pointer;margin:2px 0}"
    ".legend .sw{display:inline-block;width:10px;height:10px;margin-right:4px;"
    "vertical-align:middle}"
    ".legend .note{margin-bottom:6px}"
    ".legend .sect{margin-top:8px;font-weight:700;color:#222}"
    ".legend .track{margin-top:6px;color:#555;font-size:11px}"
    ".legend .srcstatus{margin-top:4px;color:#555}"
    ".legend .runid{margin-top:6px;color:#777}"
    ".legend .disclaimer{margin-top:8px;border-top:1px solid #ddd;"
    "padding-top:6px;color:#444}"
)

_JS_BASIS = """
const map = L.map('map').setView([52.08, 5.12], 9);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {attribution: '&copy; OpenStreetMap-bijdragers'}).addTo(map);
function toggleLayer(id, on) {
  var l = window[id];
  if (!l) { return; }
  if (on) { l.addTo(map); } else { map.removeLayer(l); }
}
function zonePopup(titel, verschil) {
  return function () {
    var t = '<b>' + titel + '</b>';
    if (verschil) { t += '<br>' + verschil; }
    return t;
  };
}
function layerPopup(name, fields) {
  return function (layer) {
    var p = (layer.feature && layer.feature.properties) || {};
    var rows = '';
    (fields || []).forEach(function (k) {
      rows += '<br>' + k + ': ' + (p[k] === undefined ? '' : p[k]);
    });
    return '<b>' + name + '</b><br>context — geen juridische zone' + rows;
  };
}
"""


def _js(waarde: Any) -> str:
    """JSON voor in een <script>-blok; '</' ge-escaped (breekt de pagina niet)."""
    return json.dumps(waarde, ensure_ascii=False).replace("</", "<\\/")


def _zone_geojson(pad: Path) -> str | None:
    """WGS84-FC voor weergave (vereenvoudigd); None als bestand ontbreekt.

    Alleen de final-kanszone — anders tekent de inclusion-stap de hele provincie.
    """
    if not pad.is_file():
        return None
    try:
        fc = json.loads(pad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    fc = final_only_fc(fc)
    # Geen areaKm2 in popup/properties — alleen id/ruleIds voor traceerbaarheid.
    prepared = prepare_fc(fc, crs="wgs84", tolerance_m=10,
                          keep=["id", "ruleIds", "operation"])
    if not prepared.get("features"):
        return None
    return json.dumps(prepared, ensure_ascii=False)


def scenario_sweep_layers(uitdaging: dict) -> list[dict[str, Any]]:
    """Baseline + scenario-varianten per track — met NL éénregel-verschil.

    Baseline staat standaard aan; varianten uit (aanvinken = verschil op de kaart).
    """
    lagen: list[dict[str, Any]] = []
    for track in uitdaging.get("tracks") or []:
        run_id = UITDAGINGEN["scenarioRuns"].get(track)
        if not run_id:
            continue
        bron = SCENARIO_RUNS / run_id
        rapport_pad = bron / "scenario-report.json"
        control_gj = _zone_geojson(bron / "scenarios" / "CONTROL.geojson")
        if control_gj:
            lagen.append({
                "track": track,
                "name": f"{track}: baseline (huidige regels)",
                "verschil": BASELINE_VERSCHIL,
                "color": BASELINE_KLEUR,
                "geojson": control_gj,
                "defaultOn": True,
                "isBaseline": True,
                "run_id": run_id,
            })
        if not rapport_pad.is_file():
            continue
        try:
            rapport = json.loads(rapport_pad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for i, s in enumerate(rapport.get("scenarios") or []):
            geo = bron / str(s.get("geometryFile") or "")
            gj = _zone_geojson(geo)
            if not gj:
                continue
            delta = float(s.get("deltaVsControlKm2") or 0)
            verschil = scenario_verschil(s)
            lagen.append({
                "track": track,
                "name": f"{track}: {scenario_kort(s)}",
                "verschil": verschil,
                "color": scenario_kleur(i, delta),
                "geojson": gj,
                "defaultOn": False,
                "isBaseline": False,
                "run_id": run_id,
                "scenarioId": str(s.get("scenarioId") or ""),
            })
    return lagen


def render_html(titel: str, control_geojson: str, layers: list[dict[str, Any]],
                run_id: str | None = None,
                *,
                sweep_layers: list[dict[str, Any]] | None = None) -> str:
    """Render één zelfstandige Leaflet-pagina (sweep + context-overlays).

    ``control_geojson`` blijft de fallback-baseline wanneer ``sweep_layers``
    leeg is (tests / ontbrekende runs). Met sweep: elke laag heeft een
    éénregel-``verschil`` in legenda + popup — geen km².
    """
    esc = lambda s: _html.escape(str(s), quote=True)  # noqa: E731
    tekenbaar, statusregels = split_layers(layers)
    sweep = list(sweep_layers or [])
    try:
        control_fc = json.loads(control_geojson) if control_geojson else {}
    except ValueError:
        control_fc = {}
    heeft_control = bool(isinstance(control_fc, dict) and control_fc.get("features"))
    # Als sweep baselines bevat, geen aparte legacy control-laag tekenen.
    if sweep:
        heeft_control = False

    legend: list[str] = [
        '<div class="note">Zet scenario\'s aan naast de baseline om het '
        '<b>verschil</b> op de kaart te zien. Contextlagen zijn <b>geen '
        'juridische zone</b>.</div>'
    ]
    if sweep:
        legend.append('<div class="sect">Scenario-sweep</div>')
        laatste_track = None
        for i, s in enumerate(sweep):
            if s.get("track") != laatste_track:
                laatste_track = s.get("track")
                legend.append(f'<div class="track">{esc(laatste_track)}</div>')
            checked = " checked" if s.get("defaultOn") else ""
            legend.append(
                f'<label><input type="checkbox"{checked} '
                f'onchange="toggleLayer(\'sweep{i}\', this.checked)"> '
                f'<span class="sw" style="background:{s["color"]}"></span> '
                f'{esc(s["name"])}</label>')
    elif heeft_control:
        legend.append('<div class="sect">Scenario-sweep</div>')
        legend.append('<label><input type="checkbox" checked '
                      'onchange="toggleLayer(\'lyrControl\', this.checked)"> '
                      '<span class="sw" style="background:#145a32"></span> '
                      'baseline (huidige regels)</label>')
    else:
        legend.append('<div class="srcstatus">geen baseline-zone voor deze pagina'
                      '</div>')

    legend.append('<div class="sect">Context</div>')
    for i, l in enumerate(tekenbaar):
        status_bit = f' <small>({esc(l["status"])})</small>' if l.get("status") else ""
        legend.append(
            f'<label><input type="checkbox" checked '
            f'onchange="toggleLayer(\'overlay{i}\', this.checked)"> '
            f'<span class="sw" style="background:{l["color"]}"></span> '
            f'{esc(l["name"])} — context, geen juridische zone{status_bit}</label>')
    for l in statusregels:
        legend.append(
            f'<div class="srcstatus"><span class="sw" '
            f'style="background:{l["color"]}"></span> '
            f'{esc(l["name"])} — {esc(l["status"])}</div>')
    run_ids = sorted({s["run_id"] for s in sweep if s.get("run_id")})
    if not run_ids and run_id:
        run_ids = [run_id]
    runline = (f'<div class="runid">runs: {esc(", ".join(run_ids))}</div>'
               if run_ids else "")
    disclaimer = (
        '<div class="disclaimer">Besluit-ondersteuning — geen juridisch advies. '
        'Contextlagen zijn referentie-materiaal; geometrieën zijn vereenvoudigd '
        'voor weergave.</div>')

    js: list[str] = [_JS_BASIS]
    if heeft_control:
        js.append("var control = " + control_geojson.replace("</", "<\\/") + ";")
        js.append(
            'var lyrControl = L.geoJSON(control, '
            '{style: {color: "#145a32", weight: 2, fillOpacity: 0.05}}).addTo(map);')
        js.append('lyrControl.bindPopup(zonePopup('
                  + _js("baseline (huidige regels)") + ", "
                  + _js(BASELINE_VERSCHIL) + "));")
    for i, s in enumerate(sweep):
        nr = str(i)
        kleur = _js(s["color"])
        js.append("var sweepData" + nr + " = " + s["geojson"].replace("</", "<\\/") + ";")
        opacity = "0.08" if s.get("isBaseline") else "0.22"
        weight = "2" if s.get("isBaseline") else "2"
        add = ".addTo(map)" if s.get("defaultOn") else ""
        js.append(
            "var sweep" + nr + " = L.geoJSON(sweepData" + nr + ", {"
            "style: {color: " + kleur + ", weight: " + weight + ", "
            "fillColor: " + kleur + ", fillOpacity: " + opacity + "}})"
            + add + ";")
        js.append("sweep" + nr + ".bindPopup(zonePopup("
                  + _js(s["name"]) + ", " + _js(s.get("verschil") or "") + "));")
    for i, l in enumerate(tekenbaar):
        kleur = _js(l["color"])
        nr = str(i)
        js.append("var data" + nr + " = " + l["geojson"].replace("</", "<\\/") + ";")
        if l.get("styleBy"):
            prop = _js(l["styleBy"]["prop"])
            js.append("var pal" + nr + " = " + _js(l["styleBy"]["palette"]) + ";")
            keuze = ("var v = (f.properties || {})[" + prop + "]; "
                     "var c = pal" + nr + "[String(v)] || " + kleur + "; ")
            js.append("var overlay" + nr + " = L.geoJSON(data" + nr + ", {"
                      "style: function (f) { " + keuze +
                      "return {color: c, weight: 2, fillOpacity: 0.15}; },"
                      "pointToLayer: function (f, ll) { " + keuze +
                      "return L.circleMarker(ll, {radius: 5, color: c, weight: 1, "
                      "fillOpacity: 0.6}); }});")
        else:
            js.append("var overlay" + nr + " = L.geoJSON(data" + nr + ", {"
                      "style: {color: " + kleur + ", weight: 2, dashArray: '5 5', "
                      "fillOpacity: 0.15},"
                      "pointToLayer: function (f, ll) { return L.circleMarker(ll, "
                      "{radius: 4, color: " + kleur + ", weight: 1, "
                      "fillOpacity: 0.6}); }});")
        js.append("overlay" + nr + ".addTo(map);")
        js.append("overlay" + nr + ".bindPopup(layerPopup(" + _js(l["name"]) +
                  ", " + _js(l.get("popup") or []) + "));")

    return ('<!DOCTYPE html>\n<html lang="nl"><head><meta charset="utf-8">'
            '<title>Utrecht context — ' + esc(titel) + '</title>\n'
            '<link rel="stylesheet" '
            'href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>\n'
            '<style>' + _CSS + '</style></head>\n<body>\n'
            '<div id="map"></div>\n'
            '<div class="legend"><b>' + esc(titel) + '</b>' + runline + '\n'
            + "\n".join(legend) + "\n" + disclaimer + '</div>\n'
            '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">'
            '</script>\n<script>\n'
            + "\n".join(js) + "\n</script>\n</body></html>\n")


# --------------------------------------------------------------------------- #
# Generatie — één pagina per uitdaging, waar het dashboard ze vindt
# --------------------------------------------------------------------------- #

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for uit in UITDAGINGEN["uitdagingen"]:
        sweep = scenario_sweep_layers(uit)
        # Fallback control (eerste baseline) voor tests / lege sweep.
        control = next((s["geojson"] for s in sweep if s.get("isBaseline")), LEGE_FC)
        run_id = next((s["run_id"] for s in sweep if s.get("run_id")), None)
        pagina = render_html(
            uit["titel"], control, context_layers(uit["id"]),
            run_id=run_id, sweep_layers=sweep)
        uit_pad = OUT_DIR / f"utrecht-context-{uit['id']}.html"
        uit_pad.write_text(pagina, encoding="utf-8")
        print(uit_pad, f"({len(sweep)} sweep-lagen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
