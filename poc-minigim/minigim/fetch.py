"""Sleutelloze open-bron fetchers voor de MiniGIM-gebiedscheck (PoC-5).

Drie protocollen (recon 2026-09-21, zie data/sources.json):
  - ogc-api-features : api.pdok.nl/…/ogc/v1, f=json + bbox-crs/crs=EPSG/0/28992, cursor-paginering via next-link (géén offset/startIndex)
  - wfs2             : service.pdok.nl, outputFormat=geojson + srsName=urn…28992, paginering count/startIndex; OGC-XML-filter URL-encoded
  - arcgis-rest      : f=geojson + outSR=28992 + resultOffset (geo.breda.nl: geen paginering)

Cache-first: elke laag wordt als <key>.28992.geojson onder data/cache opgeslagen
met een queryFingerprint (zelfde patroon als poc/poc-breda). Fetches zijn
nooit fataal voor de run: een falende laag wordt als not-delivered gelogd.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
CACHE = DATA / "cache"
USER_AGENT = "ldt-toolbox-poc-minigim/1.0 (MiniGIM gebiedscheck)"
PAGE_SIZE = 500
MAX_PAGES = 200
PAGE_DELAY_S = 0.15
RD_CRS = "http://www.opengis.net/def/crs/EPSG/0/28992"
OGC_FILTER_BREDA = (
    "<Filter><PropertyIsEqualTo><PropertyName>gemeentenaam</PropertyName>"
    "<Literal>Breda</Literal></PropertyIsEqualTo></Filter>"
)


class FetchError(RuntimeError):
    """Netwerk- of protocolfout bij het ophalen van één laag."""


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cache_key(source_id: str, fingerprint: str) -> Path:
    # filters (CBS OGC-XML) en bbox'en hashen naar een korte slug — leesbaar
    # en veilig als bestandsnaam
    readable = re.sub(r"[^a-zA-Z0-9_-]+", "-", fingerprint.split(";")[1] if ";" in fingerprint else fingerprint)[:60].strip("-")
    digest = hashlib.sha256(fingerprint.encode()).hexdigest()[:10]
    return CACHE / f"{source_id}__{readable}-{digest}.28992.geojson"


def _bbox_str(bbox) -> str:
    return ",".join(f"{v:.0f}" for v in bbox)


def load_aoi(path: Path):
    """Laadt de plangrens als GeoJSON FeatureCollection (RD-geometrie).

    Ondersteunt FeatureCollection/Feature/geometry in EPSG:28992 (crs-member of
    RD-coordinategrootte) of EPSG:4326 (via pyproj omgezet).
    """
    import shapely.geometry as sg

    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("type") == "FeatureCollection":
        feats = doc["features"]
    elif doc.get("type") == "Feature":
        feats = [doc]
    else:
        feats = [{"type": "Feature", "properties": {}, "geometry": doc}]

    crs_name = ""
    if isinstance(doc.get("crs"), dict):
        crs_name = json.dumps(doc["crs"]).upper()
    coords = list(sg.shape(feats[0]["geometry"]).bounds)
    is_rd = "28992" in crs_name or (len(coords) == 4 and coords[0] > 100000)

    fc = {"type": "FeatureCollection", "features": feats}
    if not is_rd:
        from pyproj import Transformer
        from shapely.ops import transform as shp_transform

        tr = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
        out = []
        for f in feats:
            g = shp_transform(lambda x, y, z=None: tr.transform(x, y), sg.shape(f["geometry"]))
            out.append({**f, "geometry": json.loads(json.dumps(g.__geo_interface__))})
        fc["features"] = out
    fc["crs"] = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}}
    return fc, _sha256(path.read_bytes())


# --------------------------------------------------------------------------- #
# protocol-fetchers (elke geeft (features, manifest) — manifest = prov-bewijs)
# --------------------------------------------------------------------------- #

def _fetch_ogc_api(base: str, collection: str, bbox=None, limit: int | None = None) -> tuple[list, dict]:
    """OGC API Features met cursor-paginering via de server-'next'-link.

    PDOK's OGC-API-implementatie accepteert géén offset/startIndex — de enige
    geldige paginering is de ondoorzichtige cursor-URL uit de next-link
    (recon 2026-09-21).
    """
    base = base.rstrip("/")
    pages, feats, urls = 0, [], []
    url = f"{base}/collections/{collection}/items?f=json&limit={limit or PAGE_SIZE}&crs={RD_CRS}"
    if bbox:
        url += f"&bbox-crs={RD_CRS}&bbox={_bbox_str(bbox)}"
    while True:
        pages += 1
        if pages > MAX_PAGES:
            raise FetchError(f"ogc-api {collection}: >{MAX_PAGES} pagina's")
        urls.append(url)
        doc = json.loads(_get(url))
        feats.extend(doc.get("features", []))
        nxt = next((l.get("href") for l in (doc.get("links") or []) if l.get("rel") == "next"), None)
        if not nxt or not doc.get("features"):
            break
        url = nxt
        time.sleep(PAGE_DELAY_S)
    return feats, {"protocol": "ogc-api-features", "urls": urls, "pages": pages}


def _fetch_wfs(base: str, type_name: str, bbox=None, ogc_filter: str | None = None) -> tuple[list, dict]:
    pages, feats, urls = 0, [], []
    start = 0
    base = base.rstrip("/")
    filter_q = urllib.parse.quote(ogc_filter) if ogc_filter else None
    while True:
        pages += 1
        if pages > MAX_PAGES:
            raise FetchError(f"wfs {type_name}: >{MAX_PAGES} pagina's")
        url = (
            f"{base}?service=WFS&version=2.0.0&request=GetFeature"
            f"&typenames={type_name}&outputFormat=geojson"
            f"&srsName=urn:ogc:def:crs:EPSG::28992&count={PAGE_SIZE}&startIndex={start}"
        )
        if filter_q:
            url += f"&filter={filter_q}"
        elif bbox:
            url += f"&bbox={_bbox_str(bbox)},urn:ogc:def:crs:EPSG::28992"
        urls.append(url)
        doc = json.loads(_get(url))
        page = doc.get("features", [])
        feats.extend(page)
        if len(page) < PAGE_SIZE:
            break
        start += len(page)
        time.sleep(PAGE_DELAY_S)
    return feats, {"protocol": "wfs2", "urls": urls, "pages": pages}


def _fetch_arcgis(service_url: str, layer_id: int, paginate: bool = True) -> tuple[list, dict]:
    pages, feats, urls = 0, [], []
    offset = 0
    base = f"{service_url.rstrip('/')}/{layer_id}/query"
    while True:
        pages += 1
        if pages > MAX_PAGES:
            raise FetchError(f"arcgis {base}: >{MAX_PAGES} pagina's")
        url = f"{base}?f=geojson&outSR=28992&where=1%3D1&resultRecordCount={PAGE_SIZE}"
        if paginate and offset:
            url += f"&resultOffset={offset}"
        elif not paginate:
            url = f"{base}?f=geojson&outSR=28992&where=1%3D1&resultRecordCount=2000"
        urls.append(url)
        doc = json.loads(_get(url))
        page = doc.get("features", [])
        feats.extend(page)
        if not paginate or len(page) < PAGE_SIZE:
            break
        offset += len(page)
        time.sleep(PAGE_DELAY_S)
    return feats, {"protocol": "arcgis-rest", "urls": urls, "pages": pages, "bytesHint": len(feats)}


# --------------------------------------------------------------------------- #
# publieke cache-first laag-API
# --------------------------------------------------------------------------- #

def fetch_layer(source: dict, bbox=None, refresh: bool = False, cbs_filter: str | None = None):
    """Haalt één laag op (cache-first) en geeft (FeatureCollection, manifest).

    cbs_filter: OGC-XML filter voor de CBS-WFS (poc-breda mechanics).
    """
    proto = source["protocol"]
    fp_parts = [proto]
    if proto == "ogc-api-features":
        coll = (source.get("collections") or [""])[0]
        fp_parts += [coll, _bbox_str(bbox) if bbox else "all"]
    elif proto == "wfs2":
        tn = (source.get("typeNames") or [source.get("typeName") or ""])[0]
        fp_parts += [tn, cbs_filter or (_bbox_str(bbox) if bbox else "all")]
    elif proto == "arcgis-rest":
        fp_parts += [source["id"], "full"]
    fingerprint = ";".join(fp_parts)
    cache_path = _cache_key(source["id"], fingerprint)

    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if (cached.get("properties") or {}).get("queryFingerprint") == fingerprint:
            return cached, cached["properties"]["manifest"]

    if proto == "ogc-api-features":
        coll = (source.get("collections") or [""])[0]
        if not coll:
            # collections-overzicht (aanwezigheidschecks)
            url = f"{source['baseUrl'].rstrip('/')}/collections?f=json"
            body = _get(url)
            doc = json.loads(body)
            manifest = {
                "protocol": "ogc-api-features",
                "urls": [url],
                "pages": 1,
                "fetchedAt": _now_iso(),
                "sha256": [_sha256(body)],
                "featureCount": 0,
                "note": "collections-overzicht",
            }
            fc = {
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
                "features": [],
                "properties": {"queryFingerprint": fingerprint, "manifest": manifest, "collections": [c["id"] for c in doc.get("collections", [])]},
            }
            return fc, manifest
        feats, m = _fetch_ogc_api(source["baseUrl"], coll, bbox=bbox)
    elif proto == "wfs2":
        tn = (source.get("typeNames") or [source.get("typeName") or ""])[0]
        feats, m = _fetch_wfs(source["baseUrl"], tn, bbox=bbox, ogc_filter=cbs_filter)
    elif proto == "arcgis-rest":
        paginate = source.get("paginationSupported", True)
        feats, m = _fetch_arcgis(source["serviceUrl"], source.get("layerId", 0), paginate=paginate)
    else:
        raise FetchError(f"onbekend protocol {proto} voor {source['id']}")

    # raw bodies zijn al weg; sha over geserialiseerde features (herleidbaar)
    payload = json.dumps(feats, ensure_ascii=False, sort_keys=True).encode()
    manifest = {
        **m,
        "fetchedAt": _now_iso(),
        "sha256": [_sha256(payload)],
        "featureCount": len(feats),
        "sourceId": source["id"],
    }
    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
        "features": feats,
        "properties": {"queryFingerprint": fingerprint, "manifest": manifest},
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(fc, ensure_ascii=False) + "\n", encoding="utf-8")
    return fc, manifest
