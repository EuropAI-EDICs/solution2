#!/usr/bin/env python3
"""PoC-3 fase 3: stroomgraad-fixtures uit Rijnlands openbare registratie.

Trede 1 van de flow-integratie ("legger-hydrauliek", geen rekenmodel):
haalt de drie lagen op waaruit een capaciteitsgewogen afwateringsgraaf
volgt — peilgebieden met streefpeilen (zwaartekracht-raster), gemalen
met hun bemaalde peilgebied en capaciteit (pomprichtingen), en de
primaire watergangen met dwarsprofiel en ruwheid (doorvoervermogen).

Wat publiek serveren: rijnland.enl-mcs.nl ArcGIS REST (RD-bronnen,
GeoJSON-uitvoer is WGS84). Watergangen worden gereduceerd tot
start/midden/eind per lijn: meer heeft de graaf niet nodig, en de
fixture blijft klein. Deterministisch offline hergebruik daarna.

Usage:
    nldt/.venv/bin/python poc-rijnland/scripts/fetch_flow.py           # fetch
    nldt/.venv/bin/python poc-rijnland/scripts/fetch_flow.py --dry-run # counts only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://rijnland.enl-mcs.nl/arcgis/rest/services"
OUT = Path(__file__).resolve().parents[1] / "data" / "flow"

LAYERS = {
    "peilgebieden": {
        "url": f"{BASE}/Peilgebied_praktijk_soort_gebied/MapServer/0",
        "fields": ("CODE,NAAM,SOORTAFWATERING,VASTPEIL,ZOMERPEIL,WINTERPEIL"),
    },
    "gemalen": {
        "url": f"{BASE}/Gemaal/MapServer/0",
        "fields": ("CODE,NAAM,FUNCTIEGEMAAL,CODEPEILGEBIEDPRAKTIJK,"
                   "MAXIMALECAPACITEIT,POLDERNAAM"),
    },
}

# primaire watergangen: CATEGORIEOPPWATERLICHAAM='primair' (15.2k van 188k)
WATERGANG_URL = f"{BASE}/Watergang_as/MapServer/0"
WATERGANG_FIELDS = ("CODE,NAAM,CATEGORIEOPPWATERLICHAAM,BREEDTE,WATERDIEPTE,"
                    "BODEMBREEDTE,TALUDHELLINGLINKS,TALUDHELLINGRECHTS,"
                    "RUWHEIDSWAARDELAAG,RUWHEIDSWAARDEHOOG")


def _get(url: str) -> bytes:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=90) as resp:
        return resp.read()


def fetch_geojson(url: str, fields: str, where: str = "1=1") -> list:
    features, offset = [], 0
    while True:
        doc = json.loads(_get(
            f"{url}/query?f=geojson&where={where.replace('=', '%3D')}"
            f"&outFields={fields}&resultRecordCount=1000&resultOffset={offset}"))
        batch = doc.get("features") or []
        features += batch
        if len(batch) < 1000:
            return features
        offset += 1000
        time.sleep(0.2)


def count(url: str, where: str = "1=1") -> int:
    return json.loads(_get(
        f"{url}/query?f=json&where={where.replace('=', '%3D')}"
        f"&returnCountOnly=true"))["count"]


def _line_points(geom: dict) -> list:
    """[start, midden, eind] van de langste lijn van (Multi)LineString."""
    lines = (geom["coordinates"] if geom["type"] == "LineString"
             else max(geom["coordinates"], key=len))
    mid = lines[len(lines) // 2]
    return [lines[0], mid, lines[-1]]


def simplify_fc(fc: dict, tolerance_m: float = 3.0) -> dict:
    """Verminder de puntdichtheid van polygonen (RD, shapely simplify).

    Peilgebieden komen met metersdichte vertices binnen (18,9 MB); voor
    cel-toewijzing en punt-in-polygon is 3 m ruim voldoende. Topologie
    per feature blijft bewaard (vereenvoudigen per losse feature)."""
    from pyproj import Transformer
    from shapely.geometry import shape, mapping
    from shapely.ops import transform as sh_transform

    to_rd = Transformer.from_crs(4326, 28992, always_xy=True)
    to_wgs = Transformer.from_crs(28992, 4326, always_xy=True)
    for f in fc["features"]:
        g = shape(f["geometry"])
        simp = sh_transform(to_rd.transform, g).simplify(tolerance_m)
        f["geometry"] = mapping(sh_transform(to_wgs.transform, simp))
    return fc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="alleen feature-aantallen tonen")
    args = ap.parse_args(argv)

    counts = {k: count(v["url"]) for k, v in LAYERS.items()}
    counts["watergangen_primair"] = count(WATERGANG_URL,
                                          "CATEGORIEOPPWATERLICHAAM='primair'")
    print("[flow] aantallen:", counts)
    if args.dry_run:
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {"source": BASE, "fetchedAt": now, "crs": "WGS84 (geojson-uitvoer)"}

    for name, spec in LAYERS.items():
        feats = fetch_geojson(spec["url"], spec["fields"])
        fc = simplify_fc({"type": "FeatureCollection", "features": feats}) \
            if name == "peilgebieden" \
            else {"type": "FeatureCollection", "features": feats}
        path = OUT / f"{name}.geojson"
        path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        meta[name] = {"n": len(feats), "bytes": path.stat().st_size}
        print(f"[flow] {name}: {len(feats)} features "
              f"({path.stat().st_size:,} bytes) -> {path}")

    rows = []
    for f in fetch_geojson(WATERGANG_URL, WATERGANG_FIELDS,
                           "CATEGORIEOPPWATERLICHAAM='primair'"):
        g = f.get("geometry") or {}
        if g.get("type") not in ("LineString", "MultiLineString"):
            continue
        rows.append({"a": f.get("properties") or {}, "p": _line_points(g)})
    path = OUT / "watergangen-primair.json"
    path.write_text(json.dumps({"rows": rows}, ensure_ascii=False),
                    encoding="utf-8")
    meta["watergangen_primair"] = {"n": len(rows),
                                   "bytes": path.stat().st_size}
    print(f"[flow] watergangen-primair: {len(rows)} rijen "
          f"({path.stat().st_size:,} bytes) -> {path}")

    (OUT / "flow-source.json").write_text(
        json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
