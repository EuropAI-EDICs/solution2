"""Landelijke context/scenario-basis bronnen — cache-first fetchers.

Rollen (zie poc/data/sources.json): 'context' (rapportage, nooit zone-bepalend)
en 'scenario-basis' (onderbouwt basis.dataGrounding van een hypothetical).
Cache: poc/data/cache/national/<cache_name>; offline replays via cache of
fixture-transport. Geen enkele functie hier schrijft juridische claims.

Live-pinning (plan-2 task 4, stap 1, 2026-10-14): de verwachte CBS
OData-tabellen bestaan niet (meer) — een volledige scan van de StatLine-
catalogus (5983 tabellen, filter op Title geverifieerd werkend) bevat geen
enkele 'vierkant'/'100m'/'landgebruik'-titel; 84583NED blijkt "Kerncijfers
wijken en buurten 2019". De opvolgers zijn PDOK OGC API's:

- Kerncijfers per vierkant (100m): https://api.pdok.nl/cbs/
  vierkantstatistieken100m/ogc/v1, collectie ``vierkant100`` (CBS
  Vierkantstatistieken 100m, jaargang 2024). Cel-kolom: ``crs28992res100m``,
  formaat "E1300N4400" = RD-hoek (130000, 440000), cel 100x100 m. Jaartal
  via CQL2-filter (``jaarcode=2024``); bbox-filter server-side in RD.
- Landgebruik: https://api.pdok.nl/cbs/landuse/ogc/v1, collectie
  ``existinglanduse`` (CBS Existing Land Use, INSPIRE geharmoniseerd,
  BBG2017). Er is géén 100m-vierkant-tabel meer; de features zijn
  geometry-zware vectoren — deze fetcher houdt alleen de properties vast.

Daarom paging over OGC API Features (``links`` met rel="next") in plaats
van OData TypedDataSet. Legacy CBS-celcodes ("b13004400") blijven leesbaar.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "national"

# In plan-2 task 4 stap 1 live gepinde waarden; hier bijgewerkt houden.
CBS_ODATA = "https://opendata.cbs.nl/ODataApi/odata"  # statline OData (geen vierkant-tabellen meer)
CBS_GRID_SERVICE = "https://api.pdok.nl/cbs/vierkantstatistieken100m/ogc/v1"
CBS_GRID_DATASET = "vierkant100"        # CBS Vierkantstatistieken 100m, collectie-id
CBS_GRID_FILTER = "jaarcode=2024"       # laatste jaargang in de dienst (CQL2)
CBS_LANDUSE_SERVICE = "https://api.pdok.nl/cbs/landuse/ogc/v1"
CBS_LANDUSE_DATASET = "existinglanduse"  # INSPIRE Existing Land Use (BBG2017)
SOURCE_BY_CACHE = {
    "test-grid.json": "cbs-grid-kerncijfers-100m",  # test-fixture
    "cbs-grid-kerncijfers-100m.json": "cbs-grid-kerncijfers-100m",
    "cbs-landgebruik-100m.json": "cbs-landgebruik-100m",
}

Transport = Callable[[str], dict]

# Utrecht AOI in RD (EPSG:28992), gelijk aan de request-AOI van de poc
UTRECHT_BBOX_RD = (130_000.0, 440_000.0, 160_000.0, 470_000.0)

_RD_CRS = "http://www.opengis.net/def/crs/EPSG/0/28992"
_OGC_PAGE_LIMIT = "1000"
_MAX_OGC_PAGES = 5000  # cyclus-bewaking op rel="next"

# live celcode 'E1300N4400' (x/100, y/100); 1-4 cijfers per deel getolereerd
_CELL_EN_RE = re.compile(r"^E(\d{1,4})N(\d{1,4})$")


def _default_transport(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "nLDT-toolbox-poc/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def _cell_rd(key: str) -> tuple[float, float] | None:
    """CBS 100m-celcode → RD-middelpunt (x+50, y+50).

    Live formaat 'E1300N4400' (hoek = x*100, y*100 in meters). Legacy
    formaat 'b13004400' ('b' + x-m/100 + y-m/100) blijft leesbaar voor
    oudere CBS-caches. Onbekende codes → None.
    """
    m = _CELL_EN_RE.match(key)
    if m:
        x = int(m.group(1)) * 100
        y = int(m.group(2)) * 100
        return (x + 50.0, y + 50.0)
    if key.startswith("b") and key[1:].isdigit() and len(key[1:]) == 8:
        x = int(key[1:5]) * 100
        y = int(key[5:9]) * 100
        return (x + 50.0, y + 50.0)
    return None


def record_in_utrecht_bbox(rec: dict, cell_key: str = "crs28992res100m") -> bool:
    xy = _cell_rd(str(rec.get(cell_key, "")))
    if xy is None:
        return False
    x0, y0, x1, y1 = UTRECHT_BBOX_RD
    return x0 <= xy[0] <= x1 and y0 <= xy[1] <= y1


def fetch_cbs_dataset(
    *,
    dataset_id: str,
    cache_name: str,
    refresh: bool = False,
    transport: Transport | None = None,
    cell_column: str | None = "crs28992res100m",
    service_url: str = CBS_GRID_SERVICE,
    cql_filter: str | None = None,
) -> dict:
    """Paged OGC-API-Features-download, gefilterd op de Utrecht-bbox.

    De bbox staat server-side in de request (RD); met ``cell_column``
    komt daar een exact client-side cel-middenpunt-filter bij. Zonder
    ``cell_column`` (bijv. landgebruik, geen celcodes) blijven alle
    records van de server-bbox staan. Records zijn feature-properties;
    geometry wordt niet vastgehouden (100m-cellen zijn reconstrueerbaar
    uit de celcode). Cache-first via ``poc/data/cache/national/``.
    """
    t = transport or _default_transport
    cache = CACHE / cache_name
    if cache.is_file() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))
    params = {
        "f": "json",
        "limit": _OGC_PAGE_LIMIT,
        "bbox": ",".join(f"{v:g}" for v in UTRECHT_BBOX_RD),
        "bbox-crs": _RD_CRS,
        "crs": _RD_CRS,
    }
    if cql_filter:
        params["filter"] = cql_filter
    url: str | None = (
        f"{service_url}/collections/{dataset_id}/items?"
        + urllib.parse.urlencode(params)
    )
    records: list[dict] = []
    pages = 0
    while url:
        page = t(url)
        for feat in page.get("features", []):
            props = dict(feat.get("properties") or {})
            if cell_column is None or record_in_utrecht_bbox(props, cell_column):
                records.append(props)
        url = next(
            (
                link.get("href")
                for link in page.get("links", [])
                if link.get("rel") == "next"
            ),
            None,
        )
        pages += 1
        if pages > _MAX_OGC_PAGES:
            raise RuntimeError(f"te veel OGC-API-pagina's ({_MAX_OGC_PAGES}); paging lijkt niet te eindigen")
    payload = {
        "sourceId": SOURCE_BY_CACHE.get(cache_name, cache_name),
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": records,
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def fetch_kerncijfers(refresh: bool = False, transport: Transport | None = None) -> dict:
    """Kerncijfers per vierkant (100m), jaargang 2024, Utrecht-bbox."""
    return fetch_cbs_dataset(
        dataset_id=CBS_GRID_DATASET,
        cache_name="cbs-grid-kerncijfers-100m.json",
        refresh=refresh,
        transport=transport,
        cell_column="crs28992res100m",
        service_url=CBS_GRID_SERVICE,
        cql_filter=CBS_GRID_FILTER,
    )


def fetch_landgebruik(refresh: bool = False, transport: Transport | None = None) -> dict:
    """Landgebruik-context (PDOK existinglanduse, INSPIRE/BBG2017).

    Let op: geometry-zware bron — alleen feature-properties komen in de
    cache; er is geen 100m-vierkant-tabel meer (zie module-docstring).
    """
    assert CBS_LANDUSE_DATASET, "dataset-id pinnen (plan-2 task 4 stap 1)"
    return fetch_cbs_dataset(
        dataset_id=CBS_LANDUSE_DATASET,
        cache_name="cbs-landgebruik-100m.json",
        refresh=refresh,
        transport=transport,
        cell_column=None,  # geen celcodes in deze bron; bbox al server-side
        service_url=CBS_LANDUSE_SERVICE,
    )
