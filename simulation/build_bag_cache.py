#!/usr/bin/env python3
"""Build simulation/bag-cache.json — bebouwing in de PoC-1-eindzones (BAG).

One build-time sweep through the Clappform OGC Digital Twin API
(https://api.ogc-digital-twin.clappform.com, OGC API - Processes):

  1. the union bbox of the three canonical final zones is tiled (0.1° grid);
  2. per tile the process `bag-panden-fetch` runs (PDOK BAG WFS, key-vrij,
     1000/request, 20000/execution); truncated tiles subdivide (max depth 3);
  3. every pand (GeoJSON incl. geometry) is projected to RD New (EPSG:28992)
     and intersected with each track's final zone — same contract as the
     API's own `plot-bag-overlap` step (overlap measured in RD New);
  4. aggregates only are cached per track: pand-count, bouwjaar-known count,
     decade histogram. No pand geometries are kept — the simulation page
     stays single-file/offline; it embeds the numbers, not the buildings.

Run:   nldt/.venv/bin/python simulation/build_bag_cache.py   (~3–8 min, network)
Then:  nldt/.venv/bin/python simulation/build_simulation.py  (embeds the cache)
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shp_transform, unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
API = "https://api.ogc-digital-twin.clappform.com"
OUT = HERE / "bag-cache.json"

TRACKS = {
    "wind": ROOT / "poc" / "runs" / "20260830T113234Z-wind",
    "zon": ROOT / "poc" / "runs" / "20260830T142439Z-zon",
    "bos": ROOT / "poc" / "runs" / "20260830T142446Z-bos",
}
TILE = 0.1          # startgrootte (graden) — ~7.7×5.6 km
PAGE = 1000         # PDOK-paginagrootte; API-paging boven één pagina is onbetrouwbaar
PDOK = "https://service.pdok.nl/lv/bag/wfs/v2_0"


def post(path: str, payload: dict, tries: int = 3) -> dict:
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(tries):
        req = urllib.request.Request(
            API + path, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == tries - 1:
                raise
            print(f"  retry {attempt + 1} na fout {e} — {path}")
            time.sleep(4 * (attempt + 1))


def _pdok_hits(bbox: list) -> int:
    """Aantal panden in de tile volgens PDOK zelf (resultType=hits, lat/lon-volgorde)."""
    q = (f"{PDOK}?service=WFS&version=2.0.0&request=GetFeature&typeNames=bag:pand"
         f"&resultType=hits&bbox={bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]},"
         f"urn:ogc:def:crs:EPSG::4326")
    with urllib.request.urlopen(q, timeout=60) as r:
        xml = r.read().decode("utf-8", "replace")
    m = re.search(r'numberMatched="(\d+)"', xml)
    return int(m.group(1)) if m else -1


def _pdok_page(bbox: list, start: int) -> list:
    q = (f"{PDOK}?service=WFS&version=2.0.0&request=GetFeature&typeNames=bag:pand"
         f"&outputFormat=json&count={PAGE}&startIndex={start}"
         f"&bbox={bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]},"
         f"urn:ogc:def:crs:EPSG::4326")
    with urllib.request.urlopen(q, timeout=120) as r:
        d = json.load(r)
    return d.get("features") or []


def fetch_direct(bbox: list, hits: int, depth: int = 0) -> list:
    """Tile rechtstreeks via PDOK met correcte paging (geometrie in EPSG:28992).
    PDOK kapt paging af na ~50.000 features per query (400 'typename') — bij die
    cap splitst de tile in kwadranten die elk onder de cap blijven."""
    out, start = [], 0
    while start < hits:
        try:
            page = _pdok_page(bbox, start)
        except urllib.error.HTTPError as e:
            e.read()
            if start >= 50000 and depth < 4:
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                subs = ([bbox[0], bbox[1], cx, cy], [cx, bbox[1], bbox[2], cy],
                        [bbox[0], cy, cx, bbox[3]], [cx, cy, bbox[2], bbox[3]])
                print(f"    paging-cap bij start={start} → {bbox} opsplitsen (depth {depth + 1})")
                for sub in subs:
                    out += fetch_direct(sub, _pdok_hits(sub), depth + 1)
                return out
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(3)
            page = _pdok_page(bbox, start)
        out += page
        start += PAGE
        time.sleep(0.15)
        if len(page) < PAGE:
            break
    return out


def fetch_tile(bbox: list, depth: int = 0, stats: dict | None = None) -> list:
    """Alle panden in een tile (geometrie genormaliseerd naar WGS84). De OGC-DT
    API is betrouwbaar onder één pagina (<1000); daarboven breekt zijn
    paging-lus af (gemeten: 994 t.o.v. 87.776 werkelijk op een Utrecht-stad-
    tile) — die tiles komen rechtstreeks van PDOK, geometrie teruggeprojecteerd."""
    if stats is None:
        stats = {"tiles": 0, "direct": 0, "apiBug": 0}
    stats["tiles"] += 1
    res = post("/processes/bag-panden-fetch/execution",
               {"inputs": {"bbox": bbox}})
    bag = res.get("bag_buildings") or {}
    val = bag.get("value")
    feats = val if isinstance(val, list) else (val or {}).get("features") or []
    meta = (res.get("bag_query") or {}).get("value") or {}
    truncated = bool(meta.get("truncated"))
    n_api = len(feats)

    if n_api >= 900 or truncated:   # API geeft ~994 bij breakende paging — altijd controleren
        hits = _pdok_hits(bbox)
        if hits > n_api or truncated:
            stats["direct"] += 1
            stats["apiBug"] += int(hits > n_api)
            if depth == 0:
                print(f"  tile {bbox}: API gaf {n_api}, PDOK zegt {hits} "
                      f"(paging-bug) → PDOK-direct")
            back = Transformer.from_crs(28992, 4326, always_xy=True).transform
            out = []
            for f in fetch_direct(bbox, max(hits, n_api)):
                g = f.get("geometry")
                if g:
                    try:
                        f["geometry"] = shp_transform(back, shape(g)).__geo_interface__
                    except Exception:
                        f["geometry"] = None
                out.append(f)
            return out
    return feats


def main() -> int:
    # ---- finale zones laden + gezamenlijke bbox
    zones_final = {}
    bounds = []
    for track, run in TRACKS.items():
        zs = json.loads((run / "zones.json").read_text(encoding="utf-8"))
        zs = zs if isinstance(zs, list) else zs.get("zones", zs)
        final = next(z for z in zs if z["id"].startswith("ZR-final"))
        g = shape(final["geometry"]["payload"])
        zones_final[track] = g
        bounds.append(g.bounds)
    x0 = min(b[0] for b in bounds); y0 = min(b[1] for b in bounds)
    x1 = max(b[2] for b in bounds); y1 = max(b[3] for b in bounds)
    print(f"unie-bbox: [{x0:.3f},{y0:.3f},{x1:.3f},{y1:.3f}]")

    # ---- tegelen + panden ophalen (één campagne voor alle tracks)
    tx = int((x1 - x0) / TILE) + 1
    ty = int((y1 - y0) / TILE) + 1
    print(f"grid: {tx}×{ty} = {tx * ty} tegels van {TILE}°")
    stats = {"tiles": 0, "direct": 0, "apiBug": 0}
    panden = {}
    for ix in range(tx):
        for iy in range(ty):
            bbox = [round(x0 + ix * TILE, 4), round(y0 + iy * TILE, 4),
                    round(min(x0 + (ix + 1) * TILE, x1), 4), round(min(y0 + (iy + 1) * TILE, y1), 4)]
            feats = fetch_tile(bbox, 0, stats)
            for f in feats:
                pid = (f.get("properties") or {}).get("identificatie") or f.get("id")
                if pid and pid not in panden:
                    panden[pid] = f
        print(f"  kolom {ix + 1}/{tx} — {len(panden)} unieke panden")

    print(f"totaal {len(panden)} unieke panden — {stats['tiles']} tiles: "
          f"{stats['tiles'] - stats['direct']}× via de OGC-DT API, "
          f"{stats['direct']}× PDOK-direct (waarvan {stats['apiBug']} aantoonbaar "
          f"paging-bug in bag-panden-fetch)")

    # ---- per track: pand in eindzone? (RD New, zelfde contract als plot-bag-overlap)
    fwd = Transformer.from_crs(4326, 28992, always_xy=True).transform
    zones_rd = {t: shp_transform(fwd, g) for t, g in zones_final.items()}
    tracks_out = {}
    for track, g_rd in zones_rd.items():
        n = known = 0
        hist: dict[str, int] = {}
        for pid, f in panden.items():
            geom = f.get("geometry")
            if not geom:
                continue
            try:
                p = shp_transform(fwd, shape(geom))
            except Exception:
                continue
            if not p.intersects(g_rd):
                continue
            # pand telt als zijn centroïde in de zone ligt (of >50% overlap)
            if not g_rd.contains(p.centroid) and p.intersection(g_rd).area < 0.5 * p.area:
                continue
            n += 1
            bj = (f.get("properties") or {}).get("bouwjaar") or f.get("properties", {}).get("begindatum")
            if isinstance(bj, int) and bj > 1000:
                known += 1
                dec = f"{bj // 10 * 10}"
                hist[dec] = hist.get(dec, 0) + 1
        tracks_out[track] = {
            "n": n, "bouwjaarBekend": known,
            "hist": {k: hist[k] for k in sorted(hist)},
        }
        print(f"  {track}: {n} panden in eindzone ({known} met bouwjaar)")

    out = {
        "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {
            "api": API,
            "process": "bag-panden-fetch (OGC API - Processes)",
            "upstream": "PDOK BAG WFS v2_0 — bag:pand, key-vrij",
            "projectie": "overlap in RD New (EPSG:28992), pand telt bij centroïde in zone of ≥50% overlap",
            "apiCalls": stats["tiles"], "tilesDirectPdok": stats["direct"],
            "tilesApiPagingBug": stats["apiBug"],
            "fetchedUnique": len(panden),
        },
        "tracks": tracks_out,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"schreef {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
