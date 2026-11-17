#!/usr/bin/env python3
"""veenendaal-spoorzone-scan — deterministische gebiedscheck Spoorzone Veenendaal.

Voeding: docs/USE_CASE_VEENENDAAL_SPOORZONE.md (Use Case Canvas) ·
data/gebied.json (werkgrens + doelen uit het Toekomstbeeld juni 2025).

Doctrine (GENAI_SEAMS): de rekenlaag beslist — elk getal in de rapportage is
herleidbaar naar bron-URL + query-parameters + sha256 (manifest.json naast
deze run). Stdlib + requests; geen shapely: vlakoppervlaktes via de
schoenlaced formule op EPSG:28992-coördinaten (meters, planair).

Werkgrens: gebied.json biedt òf een GeoJSON-polygon (`werkgrens.geojson_rd`,
assengrens-vormig, o.a. zandloper) òf een bbox (`werkgrens.bbox_rd`). De engine
rekent op wat gebied.json biedt: bij een polygon wordt elke ring ge-earcut naar
driehoeken (binnen-disjunct) en clippen we vlakken per driehoek met
Sutherland–Hodgman — oppervlaktemeetkundig exact ook bij concave grenzen.

Poorten: V0 structuur · V1 geometrie-sanity · V2 bronkoppeling per indicator ·
V3 tweede, onafhankelijk geïmplementeerde aggregatiepassage over de cache.

Gebruik:  python3 run.py [--refresh]
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CACHE = DATA / "cache"
RUNS = ROOT / "runs"

CRS = "http://www.opengis.net/def/crs/EPSG/0/28992"
BAG_BASE = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections"
BGT_BASE = "https://api.pdok.nl/lv/bgt/ogc/v1/collections"
PAGE_CAP = 120
PAGE_PAUSE = 0.05

# pand-statussen die (nog) niet als bestaande bouwmassa gelden
NIET_BESTAAND = {"Pand gesloopt", "Niet gerealiseerd pand"}

BOUWJAAR_BUCKETS = [("<1965", 0, 1965), ("1965-1984", 1965, 1985),
                    ("1985-1999", 1985, 2000), ("2000-2019", 2000, 2020),
                    ("≥2020", 2020, 10_000)]

# BGT-collection → indicator-key in de rapportage ('spoor' is lijngeometrie in BGT v1)
BGT_LAGEN = {
    "begroeidterreindeel": "begroeid_terrein_ha",
    "onbegroeidterreindeel": "onbegroeid_terrein_ha",
    "waterdeel": "waterdeel_ha",
    "spoor": "spoorlijn_km",
    "vegetatieobject_punt": "vegetatieobject_punt",
    "vegetatieobject_vlak": "vegetatie_vlak_ha",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- ophalen (cache-first)

def fetch_paged(base: str, collection: str, params: dict, refresh: bool = False,
                cache_key: str | None = None) -> tuple[list, dict]:
    """Haalt alle pagina's van een OGC-API Features-collection; cache-first.
    Naast de cache wordt een sidecar-meta (fetchedAt, params, sha256) bewaard,
    zodat het bevraagtijdstip ook bij hergebruik in het manifest terechtkomt."""
    CACHE.mkdir(parents=True, exist_ok=True)
    naam = cache_key or collection
    cache_path = CACHE / f"{naam}.geojson"
    meta_path = CACHE / f"{naam}.meta.json"
    if cache_path.exists() and meta_path.exists() and not refresh:
        meta = json.loads(meta_path.read_text())
        doc = json.loads(cache_path.read_text())
        meta.update({"cached": True, "featureCount": len(doc["features"])})
        return doc["features"], meta

    url = f"{base}/{collection}/items"
    features: list = []
    pages = 0
    t0 = time.time()
    while url and pages < PAGE_CAP:
        resp = requests.get(url, params=params if pages == 0 else None, timeout=90)
        resp.raise_for_status()
        doc = resp.json()
        if doc.get("type") != "FeatureCollection" or not isinstance(doc.get("features"), list):
            raise ValueError(f"V0-fout {collection}: geen FeatureCollection")
        features.extend(doc["features"])
        pages += 1
        url = next((l["href"] for l in doc.get("links", []) if l.get("rel") == "next"), None)
        time.sleep(PAGE_PAUSE)
    if pages >= PAGE_CAP:
        raise RuntimeError(f"{collection}: page-cap ({PAGE_CAP}) geraakt — verbreed of chunk de bbox")

    cache_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    meta = {
        "collection": collection, "cached": False, "pages": pages,
        "featureCount": len(features), "sha256": sha256_file(cache_path),
        "fetchedAt": utcnow(), "duur_s": round(time.time() - t0, 1),
        "url": f"{base}/{collection}/items", "params": params,
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return features, meta


def _feature_sleutel(f: dict) -> str:
    p = f.get("properties") or {}
    return (p.get("identificatie") or p.get("lokaal_id") or f.get("id")
            or json.dumps(f.get("geometry"), sort_keys=True)[:64])


def fetch_venster(base: str, collection: str, params: dict, venster: tuple,
                  refresh: bool = False) -> tuple[list, dict]:
    """Haalt een collection op binnen het fetch-venster en cacheert de samengevoegde,
    gededupliceerde set onder de canonieke collectienaam. Het venster wordt 2×2
    getegeld: PDOK (BAG v2) geeft bij grotere vensters betrouwbaar HTTP 500 diep in
    de cursor-paginering — per tegel blijft elke pagineringsketen kort genoeg.
    Overlap op de tegelnaden verdwijnt via de feature-sleutel (identificatie/lokaal_id)."""
    cache_path = CACHE / f"{collection}.geojson"
    meta_path = CACHE / f"{collection}.meta.json"
    if cache_path.exists() and meta_path.exists() and not refresh:
        meta = json.loads(meta_path.read_text())
        doc = json.loads(cache_path.read_text())
        meta.update({"cached": True, "featureCount": len(doc["features"])})
        return doc["features"], meta

    minx, miny, maxx, maxy = venster
    xs = [minx, (minx + maxx) / 2, maxx]
    ys = [miny, (miny + maxy) / 2, maxy]
    alle: dict = {}
    tile_metas = []
    t0 = time.time()
    for i in range(2):
        for j in range(2):
            tile = (xs[i], ys[j], xs[i + 1], ys[j + 1])
            tparams = {**params, "bbox": ",".join(str(round(v, 1)) for v in tile)}
            feats, meta = fetch_paged(base, collection, tparams, refresh=True,
                                      cache_key=f"{collection}.tile{i}{j}")
            meta["tile_bbox"] = [round(v, 1) for v in tile]
            tile_metas.append(meta)
            for f in feats:
                alle[_feature_sleutel(f)] = f
    features = list(alle.values())
    cache_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    meta = {
        "collection": collection, "cached": False,
        "pages": sum(m["pages"] for m in tile_metas),
        "featureCount": len(features), "sha256": sha256_file(cache_path),
        "fetchedAt": tile_metas[0]["fetchedAt"] if tile_metas else utcnow(),
        "duur_s": round(time.time() - t0, 1),
        "url": f"{base}/{collection}/items", "params": params,
        "tiles": tile_metas,
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return features, meta


# ---------------------------------------------------------------- geometrie (schoenlac, RD-meters)

def ring_area(ring: list) -> float:
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def polygon_area(poly: list) -> float:
    if not poly:
        return 0.0
    area = abs(ring_area(poly[0]))
    for hole in poly[1:]:
        area -= abs(ring_area(hole))
    return area


def feature_area(geom: dict) -> float:
    if geom is None:
        return 0.0
    t = geom.get("type")
    if t == "Polygon":
        return polygon_area(geom.get("coordinates", []))
    if t == "MultiPolygon":
        return sum(polygon_area(p) for p in geom.get("coordinates", []))
    return 0.0  # punten/lijnen: geen vlakoppervlak


def ring_centroid(ring: list) -> tuple[float, float]:
    """Zwaartepunt van een gesloten ring via de schoenlac-vorm; degeneraat → puntgemiddelde."""
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    if len(pts) < 3:
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    a = ring_area(pts + [pts[0]])  # ring_area verwacht een gesloten ring
    if abs(a) < 1e-9:
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    cx = cy = 0.0
    for p, q in zip(pts, pts[1:] + pts[:1]):
        f = p[0] * q[1] - q[0] * p[1]
        cx += (p[0] + q[0]) * f
        cy += (p[1] + q[1]) * f
    return (cx / (6 * a), cy / (6 * a))


def feature_centroid(geom: dict):
    """Zwaartepunt: punt-features zijn zichzelf; vlakken volgen de grootste buitenring."""
    if geom is None:
        return None
    t = geom.get("type")
    if t == "Point":
        return tuple(geom["coordinates"][:2])
    rings = None
    if t == "Polygon":
        rings = [geom["coordinates"][0]]
    elif t == "MultiPolygon":
        rings = [p[0] for p in geom["coordinates"]]
    if not rings:
        return None
    grootste = max(rings, key=lambda r: abs(ring_area(r)))
    return ring_centroid(grootste)


def point_in_ring(x: float, y: float, ring: list) -> bool:
    """Ray casting (even-oneven); punten exact op de rand zijn meetkundig verwaarloosbaar."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


# ----------------------- earcut-triangulatie (concave polygonen, stdlib-poort)

def _streep_herhaalde_punten(pts: list) -> list:
    """Vouwt opeenvolgende (vrijwel) identieke punten ineen — een dubbel hoekpunt
    maakt de collineaire schoonmaak blind en vreet dan het echte hoekpunt op."""
    out = [pts[0]]
    for p in pts[1:]:
        q = out[-1]
        if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6:
            continue
        out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out = out[:-1]
    return out


def _streep_collineaire_punten(pts: list) -> list:
    """Verwijdert hoekpunten die (vrijwel) exact op het segment tussen hun buren
    liggen — collineaire resterende punten zijn voor earcut onverwijderbaar en
    kunnen bovendien diagnosegoute oren blokkeren."""
    changed = True
    while changed and len(pts) > 3:
        changed = False
        out = []
        n = len(pts)
        for i in range(n):
            a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            tussen = (min(a[0], c[0]) - 1e-9 <= b[0] <= max(a[0], c[0]) + 1e-9
                      and min(a[1], c[1]) - 1e-9 <= b[1] <= max(a[1], c[1]) + 1e-9)
            if abs(cross) < 1e-7 and tussen:
                changed = True
                continue
            out.append(b)
        pts = out
    return pts


def earcut(ring: list) -> list:
    """Trianguleert een simpele polygon-ring (open of gesloten) naar binnen-disjuncte
    driehoeken [(a, b, c), ...] — poort van het klassieke ear-clipping-algoritme
    (kaaskuren: alleen strikt convexe oren; blokkeerders gelden ook óp de rand).
    Zelfcheck bij de som: laad_werkgrens verifieert Σ driehoeksoppervlaktes."""
    pts = [list(p) for p in ring]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return []
    pts = _streep_collineaire_punten(_streep_herhaalde_punten(pts))
    if len(pts) < 3:
        return []
    # orientatie op de gesloten ring bepalen (ring_area verwacht sluitpunt)
    if ring_area(pts + [pts[0]]) < 0:
        pts.reverse()
    n = len(pts)
    prev_ = [n - 1] + list(range(n - 1))
    next_ = list(range(1, n)) + [0]
    triangles: list = []
    resterend, i, beurt = n, 0, 0
    while resterend > 2 and beurt < 4 * n:
        beurt += 1
        a, b, c = pts[prev_[i]], pts[i], pts[next_[i]]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if cross > 1e-9:  # alleen strikt convexe oren (collineair slaat over)
            oor = True
            p = next_[i]
            for _ in range(resterend - 3):
                p = next_[p]
                q = pts[p]
                # blokkeerders gelden ook óp de oor-rand: een diagonaal die
                # exact door een ander hoekpunt loopt mag niet geknipt worden
                if p not in (prev_[i], i, next_[i]) and _punt_in_of_op_driehoek(q, a, b, c):
                    oor = False
                    break
            if oor:
                triangles.append((a, b, c))
                next_[prev_[i]] = next_[i]
                prev_[next_[i]] = prev_[i]
                resterend -= 1
                i = prev_[i]
                continue
        i = next_[i]
    return triangles


def _punt_in_of_op_driehoek(p, a, b, c) -> bool:
    """In of op de rand van driehoek abc (alle drie kruisproducten gelijkzinnig)."""
    eps = -1e-7
    d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    d2 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0])
    d3 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0])
    return d1 >= eps and d2 >= eps and d3 >= eps


# ------------------------------------------------- clippen naar de werkgrens (bbox = (minx,miny,maxx,maxy))
# De API's leveren objecten die de bbox *snijden* met volledige geometrie; voor
# oppervlakte-indicatoren clippen we elke ring met Sutherland–Hodgman tegen de
# rechthoek (convex clipper → oppervlaktemeetkundig exact, ook bij concave ringen).

def clip_halfplane(pts: list, axis: int, bound: float, keep_ge: bool) -> list:
    out: list = []
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        vp = p[axis] - bound
        vq = q[axis] - bound
        pin = (vp >= 0) if keep_ge else (vp <= 0)
        qin = (vq >= 0) if keep_ge else (vq <= 0)
        if pin:
            out.append(p)
        if pin != qin:
            t = vp / (vp - vq)
            out.append([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])])
    if out:
        out.append(out[0])
    return out


def ring_area_in_bbox(ring: list, bbox: tuple) -> float:
    pts = ring
    for axis, bound, keep_ge in [(0, bbox[0], True), (0, bbox[2], False),
                                 (1, bbox[1], True), (1, bbox[3], False)]:
        pts = clip_halfplane(pts, axis, bound, keep_ge)
        if not pts:
            return 0.0
    return abs(ring_area(pts))


def polygon_area_in_bbox(poly: list, bbox: tuple) -> float:
    if not poly:
        return 0.0
    area = ring_area_in_bbox(poly[0], bbox)
    for hole in poly[1:]:
        area -= ring_area_in_bbox(hole, bbox)
    return max(area, 0.0)


def feature_area_in_bbox(geom: dict, bbox: tuple) -> float:
    if geom is None:
        return 0.0
    t = geom.get("type")
    if t == "Polygon":
        return polygon_area_in_bbox(geom.get("coordinates", []), bbox)
    if t == "MultiPolygon":
        return sum(polygon_area_in_bbox(p, bbox) for p in geom.get("coordinates", []))
    return 0.0


def seg_len_in_rect(p: list, q: list, bbox: tuple) -> float:
    """Lengte van het deel van segment p→q binnen de bbox (Liang–Barsky)."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pi, di, lo, hi in ((p[0], dx, bbox[0], bbox[2]), (p[1], dy, bbox[1], bbox[3])):
        if di == 0:
            if pi < lo or pi > hi:
                return 0.0
        else:
            a, b = (lo - pi) / di, (hi - pi) / di
            if a > b:
                a, b = b, a
            t0, t1 = max(t0, a), min(t1, b)
    if t0 >= t1:
        return 0.0
    return ((dx * (t1 - t0)) ** 2 + (dy * (t1 - t0)) ** 2) ** 0.5


def lijn_len_in_bbox(geom: dict, bbox: tuple) -> float:
    if geom is None or geom.get("type") not in ("LineString", "MultiLineString"):
        return 0.0
    lines = ([geom["coordinates"]] if geom["type"] == "LineString"
             else geom["coordinates"])
    return sum(
        seg_len_in_rect(a, b, bbox)
        for line in lines for a, b in zip(line, line[1:])
    )


# ---------------- clippen naar een algemene (concave) werkgrens-polygon -------
# Strategie: de werkgrens-ring wordt eenmalig ge-earcut naar binnen-disjuncte
# driehoeken; een subject-ring wordt per driehoek met Sutherland–Hodgman tegen
# de drie halfvlakken geclipt. Omdat de driehoeken elkaar niet overlappen is de
# som over de driehoeken exact voor concave grenzen.

def clip_ring_halfplane(pts: list, a: list, b: list) -> list:
    """Houdt het deel van ring pts (gesloten) links van de gerichte lijn a→b."""
    if not pts:
        return []
    out: list = []
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        vp = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        vq = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
        pin, qin = vp >= 0, vq >= 0
        if pin:
            out.append(p)
        if pin != qin and vp != vq:
            t = vp / (vp - vq)
            out.append([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])])
    if out:
        out.append(out[0])
    return out


def ring_area_in_triangle(ring: list, tri: tuple) -> float:
    pts = ring
    for a, b in zip(tri, tri[1:] + tri[:1]):
        pts = clip_ring_halfplane(pts, a, b)
        if not pts:
            return 0.0
    return abs(ring_area(pts))


def ring_area_in_triangles(ring: list, triangles: list) -> float:
    return sum(ring_area_in_triangle(ring, tri) for tri in triangles)


def polygon_area_in_triangles(poly: list, triangles: list) -> float:
    if not poly:
        return 0.0
    area = ring_area_in_triangles(poly[0], triangles)
    for hole in poly[1:]:
        area -= ring_area_in_triangles(hole, triangles)
    return max(area, 0.0)


def feature_area_in_triangles(geom: dict, triangles: list) -> float:
    if geom is None or not triangles:
        return 0.0
    t = geom.get("type")
    if t == "Polygon":
        return polygon_area_in_triangles(geom.get("coordinates", []), triangles)
    if t == "MultiPolygon":
        return sum(polygon_area_in_triangles(p, triangles) for p in geom.get("coordinates", []))
    return 0.0


def seg_len_in_polygons(p: list, q: list, rings: list) -> float:
    """Lengte van p→q binnen de union van de (simpele) rings — parameterdoorsnede:
    snijpunten met alle randen verzamelen, middelpunten van de intervallen toetsen."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        return 0.0
    ts = {0.0, 1.0}
    for ring in rings:
        for a, b in zip(ring, ring[1:]):
            ex, ey = b[0] - a[0], b[1] - a[1]
            den = dx * ey - dy * ex
            if den == 0:
                continue
            t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
            u = ((a[0] - p[0]) * dy - (a[1] - p[1]) * dx) / den
            if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
                ts.add(t)
    tsl = sorted(ts)
    binnen = 0.0
    for t0, t1 in zip(tsl, tsl[1:]):
        if t1 - t0 <= 1e-12:
            continue
        tm = (t0 + t1) / 2
        if any(point_in_ring(p[0] + tm * dx, p[1] + tm * dy, ring) for ring in rings):
            binnen += (t1 - t0) * (dx * dx + dy * dy) ** 0.5
    return binnen


def lijn_len_in_polygons(geom: dict, rings: list) -> float:
    if geom is None or geom.get("type") not in ("LineString", "MultiLineString"):
        return 0.0
    lines = ([geom["coordinates"]] if geom["type"] == "LineString"
             else geom["coordinates"])
    return sum(
        seg_len_in_polygons(a, b, rings)
        for line in lines for a, b in zip(line, line[1:])
    )


# -------------------------------------------- werkgrens-lader (polygon of bbox)

def laad_werkgrens(wg: dict) -> dict:
    """Normaliseert gebied.json→werkgrens naar: mode, fetch-bbox, oppervlakte en
    — bij polygon-modus — driehoeken (voor vlak-clip) en buitenringen (punt/lijn)."""
    if "geojson_rd" in wg:
        g = wg["geojson_rd"]
        # normaliseer naar: lijst polygonen, elke polygon = [buitenring, gaten...]
        polys = ([g["coordinates"]] if g.get("type") == "Polygon"
                 else list(g["coordinates"]))
        triangles = [tri for poly in polys for tri in earcut(poly[0])]
        area_m2 = sum(0.5 * abs(
            (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
            for a, b, c in triangles)
        # zelfcheck: driehoekssom ≈ schoenlac-som (earcut-falen → harde fout)
        schoenlac = sum(abs(ring_area(poly[0])) - sum(abs(ring_area(h)) for h in poly[1:])
                        for poly in polys)
        if abs(area_m2 - schoenlac) > 1e-4 * max(schoenlac, 1.0):
            raise ValueError(
                f"werkgrens-polygon: earcut-som {area_m2:.1f} m² ≠ schoenlac {schoenlac:.1f} m²")
        ringen = [poly[0] for poly in polys]
        xs = [c[0] for ring in ringen for c in ring]
        ys = [c[1] for ring in ringen for c in ring]
        return {"mode": "polygon", "polygonen": polys, "driehoeken": triangles,
                "buitenringen": ringen, "area_m2": area_m2,
                "bbox": (min(xs), min(ys), max(xs), max(ys))}
    bbox = tuple(wg["bbox_rd"])
    return {"mode": "bbox", "polygonen": None, "driehoeken": None,
            "buitenringen": None,
            "area_m2": (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),
            "bbox": bbox}


def grens_area_in(geom: dict, grens: dict) -> float:
    """Vlakoppervlak (m²) van geom binnen de werkgrens — mode-afhankelijk."""
    if grens["mode"] == "polygon":
        return feature_area_in_triangles(geom, grens["driehoeken"])
    return feature_area_in_bbox(geom, grens["bbox"])


def grens_lijn_km(geom: dict, grens: dict) -> float:
    if grens["mode"] == "polygon":
        return lijn_len_in_polygons(geom, grens["buitenringen"]) / 1000
    return lijn_len_in_bbox(geom, grens["bbox"]) / 1000


def grens_bevat_zwaartepunt(geom: dict, grens: dict) -> bool:
    c = feature_centroid(geom)
    if c is None:
        return False
    if grens["mode"] == "polygon":
        return any(point_in_ring(c[0], c[1], ring) for ring in grens["buitenringen"])
    b = grens["bbox"]
    return b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3]


def bgt_actueel(features: list) -> list:
    """Versie-deduplice: BGT v1 levert ook historische versies. Per lokaal_id
    blijft de versie met lege eind_registratie (actueel); is er geen actuele
    versie, dan bestaat het object niet meer en valt het weg. Bij meerdere
    actieve versies wint de laatste tijdstip_registratie."""
    actueel: dict = {}
    for f in features:
        p = f.get("properties", {})
        lid = p.get("lokaal_id")
        if p.get("eind_registratie") not in (None, ""):
            continue
        ts = p.get("tijdstip_registratie") or ""
        if lid not in actueel or ts > actueel[lid][0]:
            actueel[lid] = (ts, f)
    return [f for _, f in actueel.values()]


# ---------------------------------------------------------------- indicatoren (1e implementatie)

def bag_indicatoren(features: list, grens: dict) -> dict:
    bestaand, verwijderd = [], 0
    for f in features:
        if f.get("properties", {}).get("status") in NIET_BESTAAND:
            verwijderd += 1
        else:
            bestaand.append(f)

    # panden horen bij het gebied als hun zwaartepunt binnen de werkgrens ligt
    bestaand = [f for f in bestaand if grens_bevat_zwaartepunt(f.get("geometry"), grens)]

    woningen_vbo = 0
    panden_met_woonfunctie = 0
    vloer_m2 = 0.0
    ge2020 = 0
    buckets = {label: 0 for label, _, _ in BOUWJAAR_BUCKETS}
    for f in bestaand:
        p = f.get("properties", {})
        gd = p.get("gebruiksdoel") or ""
        if "woonfunctie" in gd:
            panden_met_woonfunctie += 1
            woningen_vbo += p.get("aantal_verblijfsobjecten") or 0
        vloer_m2 += grens_area_in(f.get("geometry"), grens)
        bj = p.get("bouwjaar")
        if isinstance(bj, int):
            if bj >= 2020:
                ge2020 += 1
            for label, lo, hi in BOUWJAAR_BUCKETS:
                if lo <= bj < hi:
                    buckets[label] += 1
                    break

    return {
        "panden_bestand": len(bestaand),
        "panden_verwijderd_status": verwijderd,
        "woningen_verblijfsobjecten_proxy": woningen_vbo,
        "panden_met_woonfunctie": panden_met_woonfunctie,
        "pand_vloeroppervlak_m2": round(vloer_m2),
        "panden_bouwjaar_vanaf_2020": ge2020,
        "bouwjaar_buckets": buckets,
    }


def bgt_indicatoren(features: list, key: str, grens: dict):
    actueel = bgt_actueel(features)
    if key.endswith("_punt"):
        return sum(1 for f in actueel if grens_bevat_zwaartepunt(f.get("geometry"), grens))
    if key == "spoorlijn_km":
        return round(sum(grens_lijn_km(f.get("geometry"), grens) for f in actueel), 1)
    return round(sum(grens_area_in(f.get("geometry"), grens) for f in actueel) / 10_000, 2)  # ha


# ---------------------------------------------------------------- V3: tweede, onafhankelijke passage

def v3_herberekening(indicatoren: dict, grens: dict) -> tuple[bool, str]:
    """Opnieuw aggregeren vanuit de cachebestanden met een apart geschreven
    implementatie (generator-based, ander loop-patroon); waakt tegen
    aggregatie-bugs. De oppervlaktemeetkunde (schoenlac + werkgrens-clip) is gedeeld
    en wordt door de V1-sanity gedekt."""
    def iter_features(name):
        doc = json.loads((CACHE / name).read_text())
        yield from doc["features"]

    pand = sum(
        1 for f in iter_features("pand.geojson")
        if f["properties"].get("status") not in NIET_BESTAAND
        and grens_bevat_zwaartepunt(f.get("geometry"), grens)
    )
    ge2020 = sum(
        1 for f in iter_features("pand.geojson")
        if f["properties"].get("status") not in NIET_BESTAAND
        and grens_bevat_zwaartepunt(f.get("geometry"), grens)
        and isinstance(f["properties"].get("bouwjaar"), int)
        and f["properties"]["bouwjaar"] >= 2020
    )
    groen_ha = round(sum(
        grens_area_in(f.get("geometry"), grens)
        for f in bgt_actueel(list(iter_features("begroeidterreindeel.geojson")))
    ) / 10_000, 2)
    vlak_totaal_ha = sum(
        indicatoren[k] for k in
        ["begroeid_terrein_ha", "onbegroeid_terrein_ha", "waterdeel_ha"]
    )
    opp_ha = grens["area_m2"] / 10_000

    checks = [
        (pand == indicatoren["panden_bestand"], f"panden {pand} vs {indicatoren['panden_bestand']}"),
        (ge2020 == indicatoren["panden_bouwjaar_vanaf_2020"],
         f"bouwjaar≥2020 {ge2020} vs {indicatoren['panden_bouwjaar_vanaf_2020']}"),
        (groen_ha == indicatoren["begroeid_terrein_ha"],
         f"groen {groen_ha} vs {indicatoren['begroeid_terrein_ha']}"),
        (vlak_totaal_ha <= opp_ha * 1.02,
         f"vlaktotalen {round(vlak_totaal_ha, 1)} ha ≤ werkgrens {round(opp_ha, 1)} ha (+2%)"),
    ]
    return all(c for c, _ in checks), "; ".join(m for _, m in checks)


# ---------------------------------------------------------------- rapport

def doelvergelijking(ind: dict, doelen: dict, opp_ha: float, nu_jaar: int) -> list:
    verwacht = round((nu_jaar - doelen["programma_start"]) * doelen["woningen_per_jaar_gemiddeld"])
    return [
        ("Wonen", f"~{doelen['woningen_nieuw_feiten_tabel']} nieuw (p.14; inleiding p.3 noemt "
                  f"~{doelen['woningen_tot_2040_inleiding']})",
         f"{ind['woningen_verblijfsobjecten_proxy']} bestaand (vbo-proxy) → groei ≈ "
         f"{round(doelen['woningen_nieuw_feiten_tabel'] / max(ind['woningen_verblijfsobjecten_proxy'], 1), 1)}×"),
        ("Bouwtempo", f"{doelen['woningen_per_jaar_gemiddeld']} woningen/jaar sinds {doelen['programma_start']}",
         f"verwacht tot {nu_jaar}: ~{verwacht}; proxy gerealiseerd: {ind['panden_bouwjaar_vanaf_2020']} "
         f"nieuwe pánden (pand ≠ woning, indicatief)"),
        ("Groen", f"> {doelen['groen_ha_minimum']} ha",
         f"huidig begroeid terrein: {ind['begroeid_terrein_ha']} ha "
         f"(+ vegetatievlak {ind['vegetatie_vlak_ha']} ha)"),
        ("Werken", f"~{doelen['arbeidsplaatsen_nieuw']} nieuwe arbeidsplaatsen",
         "arbeidsplaatsen niet rechtstreeks meetbaar in BAG/BGT (open seam: bron met banenregistratie)"),
        ("Dichtheid", f"stedelijk; basishoogte {doelen['woongebouwen_basishoogte_lagen']} lagen, "
                      f"accenten {doelen['woongebouwen_accenten_lagen']}",
         f"huidig: {round(ind['woningen_verblijfsobjecten_proxy'] / (opp_ha / 100))} woningen/km²; "
         f"na realisatie: ~{round((ind['woningen_verblijfsobjecten_proxy'] + doelen['woningen_nieuw_feiten_tabel']) / (opp_ha / 100))}"),
    ]


def schrijf_rapport(run_dir: Path, gebied: dict, ind: dict, vergelijking: list,
                    v1: list, v3: tuple, run_id: str, grens: dict) -> None:
    bron = gebied["bron"]
    wg = gebied["werkgrens"]
    vloer = f"{ind['pand_vloeroppervlak_m2']:,}".replace(",", ".")
    if grens["mode"] == "polygon":
        n_punten = sum(len(r) - 1 for r in grens["buitenringen"])
        grens_regel = (f"**Werkgrens:** {wg['type']} — GeoJSON-polygon RD ({n_punten} hoekpunten, "
                       f"{len(grens['buitenringen'])} ring, ≈{grens['area_m2'] / 10_000:.1f} ha; "
                       f"fetch-venster bbox {wg['bbox_rd']}). {wg['afleiding']}")
    else:
        grens_regel = (f"**Werkgrens:** {wg['type']} — bbox RD {wg['bbox_rd']} "
                       f"({wg['breedte_m']}×{wg['hoogte_m']} m ≈ "
                       f"{wg['opp_ha']} ha). {wg['afleiding']}")
    regels = [
        f"# Gebiedscheck Spoorzone Veenendaal — {run_id}",
        "",
        f"*Run {utcnow()} · engine `poc-veenendaal/run.py` · doctrine: rekenlaag beslist, mens beslist.*",
        "",
        f"**Brongebiedsdocument:** [{bron['naam']}]({bron['url']}) (geraadpleegd {bron['geraadpleegd']}).",
        "",
        grens_regel,
        "",
        "## Huidige stand (deterministisch uit BAG/BGT; per bron URL+sha256 in `manifest.json`)",
        "",
        "| Indicator | Waarde | Bron |",
        "|---|---:|---|",
        f"| Panden bestand (excl. gesloopt/niet gerealiseerd) | {ind['panden_bestand']} | BAG pand |",
        f"| — panden met status gesloopt/niet gerealiseerd | {ind['panden_verwijderd_status']} | BAG pand |",
        f"| Panden met woonfunctie | {ind['panden_met_woonfunctie']} | BAG pand |",
        f"| Woningen (som verblijfsobjecten op woonpanden; proxy) | {ind['woningen_verblijfsobjecten_proxy']} | BAG pand |",
        f"| Pand-vloeroppervlak binnen werkgrens (grondvlak, som) | {vloer} m² | BAG pand |",
        f"| Panden met bouwjaar ≥ 2020 | {ind['panden_bouwjaar_vanaf_2020']} | BAG pand |",
        f"| Begroeid terrein binnen werkgrens | {ind['begroeid_terrein_ha']} ha | BGT |",
        f"| Onbegroeid (verhard) terrein binnen werkgrens | {ind['onbegroeid_terrein_ha']} ha | BGT |",
        f"| Water binnen werkgrens | {ind['waterdeel_ha']} ha | BGT |",
        f"| Spoorlijn binnen werkgrens | {ind['spoorlijn_km']} km | BGT |",
        f"| Bomen (vegetatieobject punt) | {ind['vegetatieobject_punt']} | BGT |",
        f"| Vegetatievlak binnen werkgrens | {ind['vegetatie_vlak_ha']} ha | BGT |",
        "",
        "**Bouwjaar-verdeling (bestaande panden):** "
        + " · ".join(f"{k}: {v}" for k, v in ind["bouwjaar_buckets"].items()),
        "",
        "## Doelvergelijking (toekomstbeeld ↔ gemeten)",
        "",
        "| Onderwerp | Doel (Toekomstbeeld) | Stand/kader |",
        "|---|---|---|",
    ]
    regels += [f"| {o} | {d} | {s} |" for o, d, s in vergelijking]
    regels += [
        "",
        "## Kwaliteitspoorten",
        "",
        "- **V0 structuur**: alle responses FeatureCollection; featureCounts per bron in manifest.",
        f"- **V1 geometrie-sanity**: {'geen afwijkingen' if not v1 else 'WAARSCHUWINGEN: ' + '; '.join(v1)}.",
        "- **V2 bronherleidbaarheid**: elke indicator verwijst naar collection+URL in manifest.json (sha256 vast).",
        f"- **V3 herberekening (tweede implementatie over cache)**: {'PASS' if v3[0] else 'FAIL'} — {v3[1]}.",
        "",
        "## Beperkingen & vervolg",
        "",
        "- Werkgrens is een provisionele polygon op de assengrenzen uit het Toekomstbeeld",
        "  (Grift/spoor/Rondwegen; zandloper-vorm) — geen juridische plangrens; cijfers zijn",
        "  indicatief tot de officiële gebiedsgrens beschikbaar is (open item, USE_CASE Annex B).",
        "- Panden horen bij het gebied als hun zwaartepunt binnen de werkgrens ligt;",
        "  panden die de rand snijden tellen dus niet mee.",
        "- Woningen zijn een proxy (som `aantal_verblijfsobjecten` op panden met woonfunctie); panden ≠ woningen.",
        "- Bouwjaar ≥ 2020 omvat ook vervangingsbouw; geen uitsplitsing sloop/nieuw zonder historische BAG.",
        "- Volgende stap volgens canvas: omgevingswet-toets (DSO/IMRO) en ontwerpvarianten (nLDT Plane B/D).",
        "",
        "*Manifest: `manifest.json` · indicatoren: `indicators.json` · cache: `data/cache/`.*",
    ]
    (run_dir / "report.md").write_text("\n".join(regels))


# ---------------------------------------------------------------- main

def main(refresh: bool = False) -> int:
    gebied = json.loads((DATA / "gebied.json").read_text())
    grens = laad_werkgrens(gebied["werkgrens"])
    bbox = ",".join(str(round(v)) for v in grens["bbox"])
    params = {"bbox": bbox, "bbox-crs": CRS, "crs": CRS}
    bag_params = {**params, "limit": 400}
    bgt_params = {**params, "limit": 500}

    print("→ ophalen BAG pand …")
    pand, m_pand = fetch_venster(BAG_BASE, "pand", bag_params, grens["bbox"], refresh)
    print(f"  {m_pand['featureCount']} panden")
    indicatoren = bag_indicatoren(pand, grens)
    manifests = [m_pand]

    for coll, key in BGT_LAGEN.items():
        print(f"→ ophalen BGT {coll} …")
        feats, m = fetch_venster(BGT_BASE, coll, bgt_params, grens["bbox"], refresh)
        indicatoren[key] = bgt_indicatoren(feats, key, grens)
        manifests.append(m)
        print(f"  {m['featureCount']} objecten → {key} = {indicatoren[key]}")

    # V1: geclipte vlaktotalen mogen de werkgrens niet overschrijden (met kleine marge)
    v1 = []
    grens_opp = grens["area_m2"]
    for key in ["begroeid_terrein_ha", "onbegroeid_terrein_ha", "waterdeel_ha", "vegetatie_vlak_ha"]:
        if key in indicatoren and indicatoren[key] * 10_000 > grens_opp * 1.05:
            v1.append(f"{key} = {indicatoren[key]} ha overschrijdt de werkgrens")

    v3 = v3_herberekening(indicatoren, grens)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-gebiedscheck"
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    vergelijking = doelvergelijking(indicatoren, gebied["doelen_uit_toekomstbeeld"],
                                    grens_opp / 10_000,
                                    datetime.now(timezone.utc).year)
    manifest = {"runId": run_id, "geraadpleegdOp": utcnow(), "crs": CRS,
                "werkgrens": {**gebied["werkgrens"],
                              "modus": grens["mode"],
                              "fetch_bbox_rd": [round(v, 1) for v in grens["bbox"]],
                              "opp_ha_herberekend": round(grens_opp / 10_000, 2)},
                "bronnen": manifests}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (run_dir / "indicators.json").write_text(json.dumps(indicatoren, indent=2, ensure_ascii=False))
    schrijf_rapport(run_dir, gebied, indicatoren, vergelijking, v1, v3, run_id, grens)

    print(f"\n✓ run {run_id}")
    print(f"  panden bestand: {indicatoren['panden_bestand']} | woningen-proxy: "
          f"{indicatoren['woningen_verblijfsobjecten_proxy']} | groen: {indicatoren['begroeid_terrein_ha']} ha")
    print(f"  V3: {'PASS' if v3[0] else 'FAIL'} | rapport: {run_dir / 'report.md'}")
    return 0 if v3[0] and not v1 else (2 if not v3[0] else 1)


if __name__ == "__main__":
    sys.exit(main(refresh="--refresh" in sys.argv))
