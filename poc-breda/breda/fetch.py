"""Fetch-laag van de Breda vijf-waardenscan.

Twee dialecten:

- ArcGIS REST (gemeente Breda: services-eu1.arcgis.com + geo.breda.nl) —
  hergebruikt ``poc.pipeline.geodata.fetch_layer`` (cache-first, RD + WGS84
  twins, provenance in de FeatureCollection-properties).
- CBS WFS 2.0 (PDOK wijkenbuurten 2024) — eigen fetcher met hetzelfde
  cache/provenance-contract: ``<id>.28992.geojson`` + ``<id>.4326.geojson``
  in ``poc-breda/data/cache/``.

Beide zijn sleutelloos en schrijven nooit giswerk weg: een falende laag
wordt als ``None`` geretourneerd en door de orchestrator als degradatie
geregistreerd.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from pipeline import geodata  # noqa: E402  — PoC-1

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "data" / "sources.json"
CACHE_DIR = ROOT / "data" / "cache"

USER_AGENT = "ldt-toolbox-poc4-breda/0.1 (contact: github.com/marc-minnee)"
PAGE_SIZE = 250  # WFS count-cap van PDOK-GoMapserver ligt laag; veilige paginagrootte
PAGE_DELAY_S = 0.4
MAX_PAGES = 100  # Breda 2024 = 56 buurten in 11 wijken (recon 13-9-2026, filter-query)

# PDOK-GoMapserver-quirk (recon 13-9-2026): cql_filter wordt genegeerd; de
# combinatie bbox+startIndex heeft een instabiele sorteervolgorde (overlappende
# windows missen features). De standaard OGC-XML ``filter`` op gemeentenaam
# werkt wél exact: 1 pagina, 56 buurten, geverifieerd tegen de wijkenlaag (11).
OGC_FILTER = (
    "<Filter><PropertyIsEqualTo><PropertyName>gemeentenaam</PropertyName>"
    "<Literal>Breda</Literal></PropertyIsEqualTo></Filter>"
)


class FetchError(RuntimeError):
    """Netwerk- of protocolfout bij het ophalen van één laag."""


def load_sources(path: Path = SOURCES_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cbs_config(sources: dict | None = None) -> dict:
    src = sources if sources is not None else load_sources()
    return src["cbsWfs"]


def _bbox_str(bbox) -> str:
    if isinstance(bbox, str):
        parts = [p.strip() for p in bbox.split(",")]
        if len(parts) != 4:
            raise FetchError(f"bbox moet 'xmin,ymin,xmax,ymax' (RD) zijn, kreeg {bbox!r}")
        vals = [float(p) for p in parts]
    else:
        vals = [float(v) for v in bbox]
    if len(vals) != 4 or not (vals[0] < vals[2] and vals[1] < vals[3]):
        raise FetchError(f"bbox moet 'xmin,ymin,xmax,ymax' (RD) zijn, kreeg {bbox!r}")
    return ",".join(repr(v) for v in vals)


def fetch_cbs_buurten(
    bbox,
    *,
    refresh: bool = False,
    sources: dict | None = None,
    cache_dir: Path = CACHE_DIR,
    timeout: int = 90,
    session: requests.Session | None = None,
) -> dict:
    """Haal CBS-buurtvlakken (+statistiek) van gemeente Breda als GeoJSON (RD).

    Server-side gefilterd via de standaard OGC-XML ``filter`` op
    ``gemeentenaam='Breda'``; client-side dubbelgecheckt op dezelfde waarde.
    Sentinels blijven raw in de cache staan — opschonen doet
    :mod:`breda.indicators` (raw bewaren = herleidbaar herberekenen).
    """
    cfg = cbs_config(sources)
    source_id = cfg["id"]
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path_rd = cache_dir / f"{source_id}.28992.geojson"
    path_wgs = cache_dir / f"{source_id}.4326.geojson"
    fp = {"filter": "gemeentenaam=Breda", "ogc": True}

    if path_rd.exists() and not refresh:
        try:
            cached = json.loads(path_rd.read_text(encoding="utf-8"))
            if (cached.get("properties") or {}).get("queryFingerprint") == fp:
                if not path_wgs.exists():
                    path_wgs.write_text(
                        json.dumps(
                            geodata.feature_collection_to_wgs84(cached),
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                return cached
        except (json.JSONDecodeError, OSError):
            pass  # corrupte cache: opnieuw ophalen

    if session is None:
        session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typenames": cfg["typeName"],
        "outputFormat": cfg["outputFormat"],
        "srsName": "urn:ogc:def:crs:EPSG::28992",
        "filter": OGC_FILTER,
    }
    feats: list[dict] = []
    pages = 0
    start = 0
    while True:
        params = dict(params_base, count=PAGE_SIZE, startIndex=start)
        resp = session.get(cfg["baseUrl"], params=params, timeout=timeout)
        if resp.status_code != 200:
            raise FetchError(
                f"{source_id}: WFS GetFeature HTTP {resp.status_code} "
                f"bij startIndex={start}"
            )
        try:
            body = resp.json()
        except ValueError as exc:
            raise FetchError(f"{source_id}: WFS-antwoord is geen JSON: {exc}") from exc
        raw = body.get("features", [])
        kept = [
            f
            for f in raw
            if (f.get("properties") or {}).get("gemeentenaam") == cfg["gemeenteFilter"]
        ]
        feats.extend(kept)
        pages += 1
        start += len(raw)
        if len(raw) < PAGE_SIZE:
            break
        if pages >= MAX_PAGES:
            raise FetchError(f"{source_id}: meer dan {MAX_PAGES} pagina's — afgebroken")
        time.sleep(PAGE_DELAY_S)

    fc = {
        "type": "FeatureCollection",
        "name": source_id,
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": feats,
        "properties": {
            "sourceId": source_id,
            "title": cfg["title"],
            "serviceUrl": cfg["baseUrl"],
            "layerId": cfg["typeName"],
            "role": cfg["role"],
            "authoritative": cfg["authoritative"],
            "licenseNote": cfg["licenseNote"],
            "lastChecked": cfg.get("lastChecked"),
            "where": "OGC-XML-filter gemeentenaam='Breda' (cql_filter genegeerd door "
                     "PDOK-GoMapserver; bbox+startIndex instabiel — recon 2026-09-13)",
            "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "userAgent": USER_AGENT,
            "pages": pages,
            "featureCount": len(feats),
            "bbox": _bbox_str(bbox) if bbox else None,
            "simplifyM": None,
            "queryFingerprint": fp,
        },
    }
    tmp = path_rd.with_suffix(".geojson.tmp")
    tmp.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path_rd)
    path_wgs.write_text(
        json.dumps(geodata.feature_collection_to_wgs84(fc), ensure_ascii=False),
        encoding="utf-8",
    )
    return fc


def _patch_max_record_count(src_entry, session, timeout):
    """Zet de actuele maxRecordCount uit de service-metadata in de registry-entry.

    Les uit de canonieke run: Bomen heeft maxRecordCount=1000 terwijl het
    register 2000 vroeg — GeoJSON-paging stopte toen stil na 1 pagina
    (1.000 van 117.012 bomen). Live-metadata is de bron van waarheid; bij
    falen (offline replay) geldt de registerwaarde als fallback.
    """
    url = f"{src_entry['serviceUrl'].rstrip('/')}/{src_entry['layerId']}?f=json"
    try:
        resp = session.get(url, timeout=timeout)
        info = resp.json()
        mrc = info.get("maxRecordCount")
        if isinstance(mrc, int) and mrc > 0:
            src_entry["maxRecordCount"] = mrc
    except Exception:
        pass  # offline replay / metadata onbereikbaar: registerval blijft staan


def fetch_all(
    *,
    refresh: bool = False,
    sources: dict | None = None,
    cache_dir: Path = CACHE_DIR,
    timeout: int = 120,
    include_bomen: bool = True,
) -> dict:
    """Haal alle lagen op; geeft ``(layers, degradations)``-vorm terug via dict.

    Volgorde: eerst de gemeentegrens (bepaalt de bbox voor al het andere),
    dan CBS-buurtén en de Breda-lagen met die bbox. Elke laag die faalt
    (netwerk/wijziging) komt als ``None`` in het resultaat met een
    degradatiemelding — de orchestrator registreert dat in validation.json.
    """
    src = sources if sources is not None else load_sources()
    # geodata.fetch_layer(sources=…) verwacht {sourceId: meta} (zoals
    # pipeline.geodata.load_sources() oplevert), niet het registry-bestand zelf.
    arcgis_registry = {s["id"]: s for s in src.get("sources", [])}
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    layers: dict[str, dict | None] = {}
    degradations: list[dict] = []

    def _get(source_id: str, bbox=None, **kw) -> dict | None:
        entry = dict(arcgis_registry[source_id])
        _patch_max_record_count(entry, session, timeout)
        try:
            return geodata.fetch_layer(
                source_id,
                bbox=bbox,
                refresh=refresh,
                sources={source_id: entry},
                cache_dir=cache_dir,
                simplify_m=kw.pop("simplify_m", None),
                timeout=timeout,
                session=session,
            )
        except Exception as exc:  # bewust breed: elke falende laag is een degradatie
            degradations.append(
                {"sourceId": source_id, "error": f"{type(exc).__name__}: {exc}"}
            )
            return None

    layers["gemeentegrens"] = _get("breda-gemeentegrens")
    bbox = None
    if layers["gemeentegrens"]:
        geoms = [f["geometry"] for f in layers["gemeentegrens"]["features"] if f.get("geometry")]
        if geoms:
            try:
                from shapely.ops import unary_union

                g = unary_union(
                    [shape for shape in _iter_shapes(geoms)]
                )
                minx, miny, maxx, maxy = g.bounds
                # kleine marge zodat buurten op de rand niet door afronding vallen
                marge = 250.0
                bbox = (
                    repr(minx - marge),
                    repr(miny - marge),
                    repr(maxx + marge),
                    repr(maxy + marge),
                )
                bbox = ",".join(bbox)
            except Exception as exc:
                degradations.append(
                    {
                        "sourceId": "breda-gemeentegrens",
                        "error": f"bbox-afleiding mislukt ({exc}) — lagen zonder bbox",
                    }
                )
    if bbox is None:
        # recon-fallback: gemeente Breda-bbox (RD), royaal
        bbox = "106000,392000,133000,421000"

    try:
        layers["buurten"] = fetch_cbs_buurten(
            bbox, refresh=refresh, sources=src, cache_dir=cache_dir, timeout=timeout
        )
    except Exception as exc:
        layers["buurten"] = None
        degradations.append(
            {"sourceId": "cbs-buurten-2024", "error": f"{type(exc).__name__}: {exc}"}
        )

    for key, sid in (
        ("wijkdeals", "breda-wijkdeals"),
        ("hoofdgroenstructuur", "breda-hoofdgroenstructuur"),
        ("verharding", "breda-verharding"),
        ("kansenkaart", "breda-kansenkaart"),
    ):
        layers[key] = _get(sid, bbox=bbox)

    if include_bomen:
        layers["bomen"] = _get("breda-bomen", bbox=bbox)
    else:
        layers["bomen"] = None
        degradations.append(
            {"sourceId": "breda-bomen", "error": "skipped (include_bomen=False)"}
        )

    return {"layers": layers, "degradations": degradations, "bbox": bbox}


def _iter_shapes(geoms):
    from shapely.geometry import shape as _shape

    for g in geoms:
        if isinstance(g, dict):
            yield _shape(g)
