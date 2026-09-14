#!/usr/bin/env python3
"""Catalog + fetch static MapServer layers from Rijnland ArcGIS REST.

Source: https://rijnland.enl-mcs.nl/arcgis/rest/services

Writes:
  poc-rijnland/data/arcgis/catalog.json   — all services/layers + counts
  poc-rijnland/data/arcgis/layers/*.geojson — fetched layers (under --max-features)

Large layers (e.g. Watergang ~188k) are catalogued but skipped unless
--max-features is raised or --include NAME is passed.

Usage:
  PYTHONPATH=nldt nldt/.venv/bin/python poc-rijnland/scripts/fetch_arcgis_static.py --catalog-only
  PYTHONPATH=nldt nldt/.venv/bin/python poc-rijnland/scripts/fetch_arcgis_static.py --max-features 25000
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "arcgis"
BASE = "https://rijnland.enl-mcs.nl/arcgis/rest/services"
SKIP_NAMES = {"SampleWorldCities"}
USER_AGENT = "nLDT-rijnland-lake-fetch/1.0"


def _get_json(url: str, timeout: int = 90) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_services() -> list[str]:
    root = _get_json(f"{BASE}?f=json")
    names: list[str] = []
    for s in root.get("services") or []:
        if s.get("type") == "MapServer":
            names.append(s["name"])
    for folder in root.get("folders") or []:
        try:
            fd = _get_json(f"{BASE}/{folder}?f=json")
        except Exception:
            continue
        for s in fd.get("services") or []:
            if s.get("type") == "MapServer":
                names.append(s["name"])
    return sorted(set(names))


def safe_slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name.replace("/", "__"))


def build_catalog(*, sleep: float = 0.05) -> dict:
    services = list_services()
    entries = []
    for name in services:
        if name.split("/")[-1] in SKIP_NAMES or name in SKIP_NAMES:
            continue
        url = f"{BASE}/{name}/MapServer"
        try:
            meta = _get_json(f"{url}?f=json")
        except Exception as exc:
            entries.append({"name": name, "error": str(exc), "layers": []})
            continue
        layers_out = []
        for ly in meta.get("layers") or []:
            lid = ly.get("id")
            layer = {
                "id": lid,
                "name": ly.get("name"),
                "geometryType": ly.get("geometryType"),
                "count": None,
                "error": None,
            }
            try:
                q = _get_json(
                    f"{url}/{lid}/query?where=1%3D1&returnCountOnly=true&f=json"
                )
                layer["count"] = q.get("count")
            except Exception as exc:
                layer["error"] = str(exc)
            layers_out.append(layer)
            time.sleep(sleep)
        entries.append(
            {
                "name": name,
                "serviceUrl": url,
                "description": (meta.get("serviceDescription") or "")[:500],
                "layers": layers_out,
            }
        )
        time.sleep(sleep)
    return {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base": BASE,
        "serviceCount": len(entries),
        "services": entries,
    }


def fetch_layer_geojson(
    service_name: str,
    layer_id: int,
    *,
    out_path: Path,
    max_features: int,
    simplify_m: float | None,
    sleep: float,
) -> dict:
    """Stream features to disk to avoid OOM on large polygon layers."""
    url = f"{BASE}/{service_name}/MapServer/{layer_id}/query"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".partial")
    offset = 0
    count = 0
    truncated = False
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write('{"type":"FeatureCollection","features":[\n')
            first = True
            while True:
                params = {
                    "where": "1=1",
                    "outFields": "*",
                    "f": "geojson",
                    "outSR": "28992",
                    "resultRecordCount": "1000",
                    "resultOffset": str(offset),
                    "returnGeometry": "true",
                }
                if simplify_m is not None:
                    params["maxAllowableOffset"] = str(simplify_m)
                full = f"{url}?{urllib.parse.urlencode(params)}"
                try:
                    doc = _get_json(full, timeout=180)
                except urllib.error.HTTPError as exc:
                    tmp.unlink(missing_ok=True)
                    return {"ok": False, "error": f"HTTP {exc.code}", "features": count}
                except Exception as exc:
                    tmp.unlink(missing_ok=True)
                    return {"ok": False, "error": str(exc), "features": count}
                batch = doc.get("features") or []
                for feat in batch:
                    if count >= max_features:
                        truncated = True
                        break
                    if not first:
                        fh.write(",\n")
                    fh.write(json.dumps(feat, ensure_ascii=False, separators=(",", ":")))
                    first = False
                    count += 1
                if truncated or len(batch) < 1000:
                    break
                offset += 1000
                if offset % 10000 == 0:
                    print(f"    … {count} features", flush=True)
                time.sleep(sleep)
            props = {
                "source": "rijnland.enl-mcs.nl",
                "service": service_name,
                "layerId": layer_id,
                "fetchedAt": fetched_at,
                "crs": "EPSG:28992",
                "featureCount": count,
                "truncated": truncated,
                "simplify_m": simplify_m,
            }
            fh.write(
                '\n],"properties":'
                + json.dumps(props, ensure_ascii=False, separators=(",", ":"))
                + "}\n"
            )
        tmp.replace(out_path)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        return {"ok": False, "error": str(exc), "features": count}

    return {"ok": True, "features": count, "path": str(out_path), "truncated": truncated}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog-only", action="store_true")
    ap.add_argument("--reuse-catalog", action="store_true",
                    help="Reuse existing data/arcgis/catalog.json if present")
    ap.add_argument("--max-features", type=int, default=25_000,
                    help="Skip layers with count above this (default 25000)")
    ap.add_argument("--simplify-m", type=float, default=5.0,
                    help="maxAllowableOffset metres (default 5)")
    ap.add_argument("--include", action="append", default=[],
                    help="Force-include service name even if over max-features")
    ap.add_argument("--sleep", type=float, default=0.08)
    ap.add_argument("--limit", type=int, default=0, help="Max layers to fetch (0=all eligible)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    catalog_path = OUT / "catalog.json"
    if args.reuse_catalog and catalog_path.is_file():
        print(f"Reusing {catalog_path}")
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    else:
        print(f"Building catalog from {BASE} …")
        catalog = build_catalog(sleep=args.sleep)
        catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {catalog_path} ({catalog['serviceCount']} services)")

    if args.catalog_only:
        return 0

    include = set(args.include)
    fetched = 0
    skipped = 0
    errors = 0
    layers_dir = OUT / "layers"
    for svc in catalog["services"]:
        name = svc["name"]
        for ly in svc.get("layers") or []:
            count = ly.get("count")
            if count is None:
                skipped += 1
                continue
            if count == 0:
                skipped += 1
                continue
            force = name in include or name.split("/")[-1] in include
            if count > args.max_features and not force:
                skipped += 1
                continue
            slug = f"{safe_slug(name)}__L{ly['id']}"
            out = layers_dir / f"{slug}.28992.geojson"
            if out.is_file():
                print(f"skip existing {out.name}", flush=True)
                fetched += 1
                continue
            # Heavier simplify for large layers to keep disk/time sane.
            simplify = args.simplify_m
            if count > 100_000:
                simplify = max(simplify, 40.0)
            elif count > 50_000:
                simplify = max(simplify, 25.0)
            elif count > 25_000:
                simplify = max(simplify, 15.0)
            print(
                f"fetch {name}/{ly['id']} ({ly.get('name')}) "
                f"count={count} simplify={simplify} …",
                flush=True,
            )
            result = fetch_layer_geojson(
                name,
                int(ly["id"]),
                out_path=out,
                max_features=max(count, args.max_features) if force else args.max_features,
                simplify_m=simplify,
                sleep=args.sleep,
            )
            if result.get("ok"):
                print(f"  -> {result['features']} features", flush=True)
                fetched += 1
            else:
                print(f"  ERROR {result.get('error')}", flush=True)
                errors += 1
            if args.limit and fetched >= args.limit:
                print(f"limit {args.limit} reached")
                print(json.dumps({"fetched": fetched, "skipped": skipped, "errors": errors}))
                return 0
            time.sleep(args.sleep)

    summary = {"fetched": fetched, "skipped": skipped, "errors": errors, "out": str(OUT)}
    (OUT / "fetch-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
