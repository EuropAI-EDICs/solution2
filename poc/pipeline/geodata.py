#!/usr/bin/env python3
"""ArcGIS REST geo connector for the Utrecht wind-turbine opportunity-map PoC.

Track B, file 1 of 4 (geo connector). Loads the recon-validated source
registry (``poc/data/sources.json``, 71 entries, probe-evidenced 2026-08-30)
and fetches layers as GeoJSON FeatureCollections in EPSG:28992 (RD New, the
metric computation CRS), caching under::

    poc/data/cache/<sourceId>.28992.geojson   # computation (RD New, metric)
    poc/data/cache/<sourceId>.4326.geojson    # output twin (WGS84 / RFC 7946)

Server dialects, per the live recon findings:

* hosted ArcGIS Online (``services.arcgis.com/m4kxECHTi6Dj9hfa/...``):
  ``f=geojson`` + ``outSR=28992`` (crs member EPSG:28992), paging via
  ``resultOffset`` + ``orderByFields=<oid>``, maxRecordCount 2000, stop on
  ``exceededTransferLimit``.
* ``agrest.geodata-utrecht.nl``: ``f=json`` ONLY (``f=geojson`` -> HTTP 400),
  ``returnGeometry=true``, pages of 1000, esri ``rings`` converted
  client-side with orientation-adaptive shell/hole classification.

Politeness / robustness:

* custom User-Agent, one page in flight, small inter-page delay;
* cache-first: re-download only when the cache is absent, ``--refresh`` is
  set, or the query fingerprint (bbox / simplify) changed;
* ``bbox`` envelope filtering via the ArcGIS REST ``geometry`` +
  ``geometryType=esriGeometryEnvelope`` + ``inSR`` parameters (recon note:
  the server returns *un-clipped* geometries of intersecting features);
* optional ``--simplify-m`` -> ``maxAllowableOffset`` vertex simplification
  in outSR units (metres), for very large layers;
* clear ``GeoDataError`` on HTTP / ArcGIS-error / JSON failures.

No API keys are used or needed.

CLI::

    python3 poc/pipeline/geodata.py agrest-ov-gebied-windenergie \
        arcgis-et-wind-gebieden [--refresh] [--bbox xmin,ymin,xmax,ymax] \
        [--simplify-m 25] [--timeout 120]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from shapely.geometry import MultiPolygon, Polygon, mapping

try:  # pyproj is available per toolchain check; kept optional for parsing-only use
    from pyproj import Transformer
    from shapely.ops import transform as _shp_transform

    _RD_TO_WGS84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

    def _to_wgs84(geom):
        if geom is None or geom.is_empty:
            return geom
        return _shp_transform(
            lambda x, y, z=None: _RD_TO_WGS84.transform(x, y), geom
        )

except Exception:  # pragma: no cover - only hit on a broken toolchain
    _to_wgs84 = None

__all__ = [
    "GeoDataError",
    "USER_AGENT",
    "load_sources",
    "source_by_id",
    "fetch_layer",
    "esri_rings_to_geometry",
    "esri_feature_to_geojson",
    "feature_collection_to_wgs84",
    "main",
]

USER_AGENT = (
    "ldttoolbox-geoconnector/0.1 (wind-turbine opportunity-map PoC; "
    "cache-first, single-page politeness; open data of provincie Utrecht "
    "via geo-point.provincie-utrecht.nl)"
)

_MODULE_DIR = Path(__file__).resolve()
DEFAULT_SOURCES_PATH = _MODULE_DIR.parents[1] / "data" / "sources.json"
DEFAULT_CACHE_DIR = _MODULE_DIR.parents[1] / "data" / "cache"

PAGE_DELAY_S = 0.25
MAX_FEATURES_HARD_CAP = 500_000  # guard against runaway loops (~71 sources exist)


class GeoDataError(RuntimeError):
    """Raised for any registry / HTTP / protocol failure, with a clear message."""


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def load_sources(path=None) -> dict:
    """Load ``sources.json`` -> ``{sourceId: source-meta-dict}``.

    Tolerates missing optional fields per source; only ``id`` is required.
    """
    path = Path(path) if path is not None else DEFAULT_SOURCES_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError as exc:
        raise GeoDataError(f"sources registry not found at {path}") from exc
    except json.JSONDecodeError as exc:
        raise GeoDataError(f"sources registry {path} is not valid JSON: {exc}") from exc
    out = {}
    for src in doc.get("sources", []):
        sid = src.get("id")
        if sid:
            out[sid] = src
    if not out:
        raise GeoDataError(f"sources registry {path} contains no sources")
    return out


def source_by_id(source_id, sources=None, path=None) -> dict:
    if sources is None:
        sources = load_sources(path)
    try:
        return sources[source_id]
    except KeyError as exc:
        raise GeoDataError(
            f"unknown source id {source_id!r}; known ids: "
            + ", ".join(sorted(sources))
        ) from exc


# --------------------------------------------------------------------------- #
# esri JSON -> GeoJSON geometry conversion (orientation-adaptive)
# --------------------------------------------------------------------------- #

def _clean_ring(coords):
    pts = []
    for pt in coords or []:
        if pt is None or len(pt) < 2:
            continue
        pts.append((float(pt[0]), float(pt[1])))
    # drop a duplicated closing vertex before the degeneracy check
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def esri_rings_to_geometry(rings):
    """Convert an esri JSON ``geometry.rings`` list to a shapely geometry.

    Orientation-adaptive: esri JSON does not guarantee CW/CCW ring winding,
    so shells vs holes are classified geometrically (a ring properly inside
    another ring is a hole of its smallest containing shell). This is the
    conversion the recon flagged as required for agrest layers.

    Returns a shapely Polygon/MultiPolygon, or ``None`` for degenerate input.
    Invalid output (e.g. nested shells as served) is *not* repaired here —
    the engine owns repair + provenance recording.
    """
    if rings is None:
        return None
    if isinstance(rings, dict) and "curveRings" in rings:
        raise GeoDataError(
            "curveRings geometry is not supported by this connector "
            "(true curves cannot be losslessly converted to GeoJSON)"
        )
    ring_coords = []
    ring_polys = []
    for ring in rings:
        pts = _clean_ring(ring)
        if len(pts) < 3:
            continue
        p = Polygon(pts)
        if p.is_empty or p.area == 0.0:
            continue
        ring_coords.append(pts)
        ring_polys.append(p)
    if not ring_polys:
        return None
    if len(ring_polys) == 1:
        return ring_polys[0]

    # classify: parent[i] = index of the smallest ring that contains ring i;
    # containment depth parity then decides shell (even) vs hole (odd), so an
    # island inside a hole correctly becomes a shell of its own polygon.
    parent = [None] * len(ring_polys)
    for i, pi in enumerate(ring_polys):
        best, best_area = None, None
        for j, pj in enumerate(ring_polys):
            if i == j:
                continue
            try:
                inside = pi.within(pj)
            except Exception:  # invalid geometry -> envelope fallback
                inside = (
                    pi.bounds[0] >= pj.bounds[0]
                    and pi.bounds[1] >= pj.bounds[1]
                    and pi.bounds[2] <= pj.bounds[2]
                    and pi.bounds[3] <= pj.bounds[3]
                )
            if inside:
                area = pj.area
                if best is None or area < best_area:
                    best, best_area = j, area
        parent[i] = best

    depth = [None] * len(ring_polys)

    def _depth(i):
        if depth[i] is None:
            depth[i] = 0 if parent[i] is None else _depth(parent[i]) + 1
        return depth[i]

    parts = []
    for i in range(len(ring_polys)):
        if _depth(i) % 2 == 0:  # shell
            holes = [
                ring_coords[k]
                for k in range(len(ring_polys))
                if parent[k] == i and _depth(k) % 2 == 1
            ]
            parts.append(Polygon(ring_coords[i], holes))
    if not parts:  # cyclic containment degeneracy: fall back to flat union
        parts = ring_polys
    if len(parts) == 1:
        return parts[0]
    try:
        return MultiPolygon(
            [(p.exterior.coords, [h.coords for h in p.interiors]) for p in parts]
        )
    except Exception:
        from shapely.ops import unary_union

        return unary_union(parts)


def esri_feature_to_geojson(feature, index=None):
    """Convert one esri JSON feature (``attributes`` + ``geometry.rings``)."""
    attrs = dict(feature.get("attributes") or {})
    geom_in = feature.get("geometry")
    if geom_in is None:
        return None
    if "rings" in geom_in:
        geom = esri_rings_to_geometry(geom_in.get("rings"))
    elif "x" in geom_in and "y" in geom_in:
        from shapely.geometry import Point

        geom = Point(geom_in["x"], geom_in["y"])
    else:
        return None
    if geom is None or geom.is_empty:
        return None
    fid = attrs.get("OBJECTID", feature.get("objectId", index))
    return {"type": "Feature", "id": fid, "properties": attrs, "geometry": mapping(geom)}


def feature_collection_to_wgs84(fc):
    """Reproject a RD-New (28992) FeatureCollection dict to WGS84 (RFC 7946)."""
    if _to_wgs84 is None:
        raise GeoDataError("pyproj/shapely unavailable: cannot reproject to EPSG:4326")
    out_feats = []
    for f in fc.get("features", []):
        g = f.get("geometry")
        if g is None:
            continue
        from shapely.geometry import shape

        f2 = dict(f)
        f2["geometry"] = mapping(_to_wgs84(shape(g)))
        out_feats.append(f2)
    out = {
        "type": "FeatureCollection",
        "name": fc.get("name"),
        "features": out_feats,
        "properties": dict(fc.get("properties") or {}),
    }
    out["properties"]["crs"] = "OGC:CRS84/WGS84 (RFC 7946 default, no crs member)"
    return out


# --------------------------------------------------------------------------- #
# Query building & fetching
# --------------------------------------------------------------------------- #

def _oid_field(src):
    for key in ("queryTemplateParams",):
        params = src.get(key) or {}
        oid = params.get("oid") or params.get("orderByFields")
        if oid:
            return oid.split()[0].strip()
    for f in src.get("fields") or []:
        if f.get("type") == "esriFieldTypeOID":
            return f.get("name")
    return None


def _is_agrest(src):
    return "agrest" in (src.get("serviceUrl") or "")


def _wants_geojson(src):
    flag = src.get("geojsonFormatSupported")
    if flag is None:
        return not _is_agrest(src)  # default: hosted AGOL yes, agrest no
    return bool(flag)


def _page_size(src):
    mrc = src.get("maxRecordCount")
    if isinstance(mrc, (int, float)) and int(mrc) > 0:
        return int(mrc)
    return 1000 if _is_agrest(src) else 2000


def _bbox_str(bbox):
    if bbox is None:
        return None
    if isinstance(bbox, str):
        parts = [p.strip() for p in bbox.split(",")]
        if len(parts) != 4:
            raise GeoDataError(f"bbox must be 'xmin,ymin,xmax,ymax', got {bbox!r}")
        vals = [float(p) for p in parts]
    else:
        try:
            vals = [float(v) for v in bbox]
        except TypeError as exc:
            raise GeoDataError(f"bbox must have 4 numeric values, got {bbox!r}") from exc
        if len(vals) != 4:
            raise GeoDataError(f"bbox must have 4 values xmin,ymin,xmax,ymax, got {bbox!r}")
    if not (vals[0] < vals[2] and vals[1] < vals[3]):
        raise GeoDataError(f"bbox has zero/negative size: {vals}")
    return ",".join(repr(v) for v in vals)


def build_query_params(src, offset, bbox=None, simplify_m=None, where=None):
    """Build the REST query parameter set for one page (pure, testable)."""
    layer_id = src.get("layerId")
    if layer_id is None:
        raise GeoDataError(
            f"source {src.get('id')!r} has no layerId "
            "(unreachable/deleted service per recon) — cannot query"
        )
    use_geojson = _wants_geojson(src)
    params = {
        "where": where
        or (src.get("queryTemplateParams") or {}).get("where")
        or "1=1",
        "outFields": "*",
        "f": "geojson" if use_geojson else "json",
        "outSR": "28992",
        "resultRecordCount": _page_size(src),
        "resultOffset": offset,
        "returnGeometry": "true",
    }
    if use_geojson:  # hosted AGOL pagination contract (recon-verified)
        oid = _oid_field(src)
        if oid:
            params["orderByFields"] = oid
    bstr = _bbox_str(bbox)
    if bstr is not None:
        params.update(
            {
                "geometry": bstr,
                "geometryType": "esriGeometryEnvelope",
                "inSR": "28992",
            }
        )
    if simplify_m:
        try:
            sm = float(simplify_m)
        except (TypeError, ValueError) as exc:
            raise GeoDataError(f"simplify_m must be numeric, got {simplify_m!r}") from exc
        if sm <= 0:
            raise GeoDataError(f"simplify_m must be > 0, got {sm}")
        params["maxAllowableOffset"] = repr(sm)
    return params, use_geojson


def _query_url(src):
    layer_id = src.get("layerId")
    base = (src.get("serviceUrl") or "").rstrip("/")
    if not base:
        raise GeoDataError(f"source {src.get('id')!r} has no serviceUrl")
    return f"{base}/{layer_id}/query"


def _fetch_page(session, url, params, timeout):
    try:
        resp = session.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise GeoDataError(f"HTTP failure querying {url}: {exc}") from exc
    if resp.status_code != 200:
        snippet = resp.text[:300].replace("\n", " ")
        raise GeoDataError(
            f"HTTP {resp.status_code} from {resp.url} :: {snippet}"
        )
    try:
        body = resp.json()
    except ValueError as exc:
        raise GeoDataError(
            f"non-JSON response from {resp.url} "
            f"(possible truncation on very large pages): {exc}"
        ) from exc
    if isinstance(body, dict) and "error" in body:
        err = body["error"]
        raise GeoDataError(
            f"ArcGIS error from {url}: code={err.get('code')} "
            f"message={err.get('message')} details={err.get('details')}"
        )
    return body


def _fingerprint(bbox, simplify_m):
    return json.dumps(
        {"bbox": _bbox_str(bbox), "simplify_m": float(simplify_m) if simplify_m else None},
        sort_keys=True,
    )


# --------------------------------------------------------------------------- #
# Public fetch API
# --------------------------------------------------------------------------- #

def fetch_layer(
    source_id,
    bbox=None,
    *,
    refresh=False,
    sources=None,
    cache_dir=None,
    simplify_m=None,
    timeout=120,
    where=None,
    session=None,
):
    """Fetch one registry layer as a GeoJSON FeatureCollection in EPSG:28992.

    Cache-first: returns ``poc/data/cache/<source_id>.28992.geojson``
    immediately when present, unless ``refresh=True`` or the stored query
    fingerprint (bbox / simplify_m) differs from the current call — in that
    case the layer is re-downloaded and the cache overwritten. The WGS84
    twin ``<source_id>.4326.geojson`` is (re)generated locally whenever
    missing. Also writes provenance into the FeatureCollection's
    ``properties`` (sourceId, serviceUrl, layerId, lastChecked, where,
    fetchedAt, bbox, simplify, featureCount) so downstream engine provenance
    survives without the registry.

    ``bbox``: envelope filter ``xmin,ymin,xmax,ymax`` in EPSG:28992 (ArcGIS
    REST ``geometry``/``geometryType=esriGeometryEnvelope``/``inSR`` params).
    Recon caveat: returns full un-clipped geometries of intersecting
    features; the engine clips against the AOI anyway.
    """
    cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    path_rd = cache_dir / f"{source_id}.28992.geojson"
    path_wgs = cache_dir / f"{source_id}.4326.geojson"
    fp = _fingerprint(bbox, simplify_m)

    # cache-first: a valid cache is returned before even consulting the
    # registry (offline re-runs of the pipeline must not require the network)
    if path_rd.exists() and not refresh:
        try:
            cached = json.loads(path_rd.read_text(encoding="utf-8"))
            if (cached.get("properties") or {}).get("queryFingerprint") == fp:
                if not path_wgs.exists():
                    path_wgs.write_text(
                        json.dumps(feature_collection_to_wgs84(cached), ensure_ascii=False),
                        encoding="utf-8",
                    )
                return cached
            # fingerprint mismatch (bbox/simplify changed): fall through to refetch
        except (json.JSONDecodeError, OSError):
            pass  # corrupt cache: refetch

    src = source_by_id(source_id, sources=sources)

    if session is None:
        session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    url = _query_url(src)
    _, use_geojson = build_query_params(src, 0, bbox=bbox, simplify_m=simplify_m, where=where)
    offset, feats, pages = 0, [], 0
    expected = src.get("featureCount")
    while True:
        params, _ = build_query_params(src, offset, bbox=bbox, simplify_m=simplify_m, where=where)
        body = _fetch_page(session, url, params, timeout)
        raw = body.get("features", []) if isinstance(body, dict) else []
        for i, f in enumerate(raw):
            if use_geojson:
                if isinstance(f, dict) and f.get("geometry") is not None:
                    feats.append(f)
            else:
                gf = esri_feature_to_geojson(f, index=offset + i)
                if gf is not None:
                    feats.append(gf)
        pages += 1
        page_size = params["resultRecordCount"]
        got = len(raw)
        exceeded = bool(body.get("exceededTransferLimit")) if isinstance(body, dict) else False
        offset += got
        if got == 0 or (not exceeded and got < page_size):
            break
        if isinstance(expected, (int, float)) and expected > 0 and offset >= int(expected):
            break
        if len(feats) > MAX_FEATURES_HARD_CAP:
            raise GeoDataError(
                f"{source_id}: exceeded hard cap of {MAX_FEATURES_HARD_CAP} features; aborting"
            )
        time.sleep(PAGE_DELAY_S)

    props = dict(src.get("properties") or {})
    fc = {
        "type": "FeatureCollection",
        "name": source_id,
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": feats,
        "properties": {
            "sourceId": source_id,
            "title": src.get("title"),
            "serviceUrl": src.get("serviceUrl"),
            "layerId": src.get("layerId"),
            "role": src.get("role"),
            "authoritative": src.get("authoritative"),
            "licenseNote": src.get("licenseNote"),
            "lastChecked": src.get("lastChecked"),
            "where": (src.get("queryTemplateParams") or {}).get("where") or "1=1",
            "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "userAgent": USER_AGENT,
            "pages": pages,
            "featureCount": len(feats),
            "bbox": _bbox_str(bbox),
            "simplifyM": float(simplify_m) if simplify_m else None,
            "queryFingerprint": fp,
            **({"registryMeta": props} if props else {}),
        },
    }
    tmp = path_rd.with_suffix(".geojson.tmp")
    tmp.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path_rd)
    path_wgs.write_text(
        json.dumps(feature_collection_to_wgs84(fc), ensure_ascii=False), encoding="utf-8"
    )
    return fc


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fetch registry layers to poc/data/cache (EPSG:28992 + WGS84 twins)."
    )
    ap.add_argument("ids", nargs="+", help="source ids from poc/data/sources.json")
    ap.add_argument("--refresh", action="store_true", help="ignore existing cache")
    ap.add_argument("--bbox", help="xmin,ymin,xmax,ymax in EPSG:28992")
    ap.add_argument("--simplify-m", type=float, default=None, help="maxAllowableOffset (m)")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    ap.add_argument("--sources", default=str(DEFAULT_SOURCES_PATH))
    args = ap.parse_args(argv)

    sources = load_sources(args.sources)
    failures = 0
    for sid in args.ids:
        try:
            fc = fetch_layer(
                sid,
                bbox=args.bbox,
                refresh=args.refresh,
                sources=sources,
                cache_dir=Path(args.cache_dir),
                simplify_m=args.simplify_m,
                timeout=args.timeout,
            )
            p = fc.get("properties") or {}
            print(
                f"OK  {sid}: {p.get('featureCount')} features "
                f"({p.get('pages')} pages) -> {Path(args.cache_dir) / (sid + '.28992.geojson')}"
            )
        except GeoDataError as exc:
            failures += 1
            print(f"ERR {sid}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
