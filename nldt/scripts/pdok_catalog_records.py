#!/usr/bin/env python3
"""DCAT-AP-NL-records voor de PDOK-bronnen van poc-nspd → lake catalog/dcat/.

Leest poc-nspd/data/sources.json (alle ``ogc-api``-bronnen op api.pdok.nl) en
de als-ontvangen PDOK-catalogus (poc-nspd/data/bronze/pdok-catalog/<stamp>/
index.json, via data/probe_pdok_catalog.py) en schrijft per bron één
DCAT-record naar ``catalog/dcat/<sourceId>.json`` — dezelfde vorm als de
DONL-harvest (services/donl_harvest/dcat_map.py), met ``nldt:poc = nspd``.

Distributies: altijd een ``DataService`` (OGC API Features items-URL); voor
gedownloade lagen (``fetched`` in de registry) ook de silver-tweeling
(28992/4326) als ``Download`` met lake-URI en de bronze-pagina's als
``prov:wasDerivedFrom``. Service-only bronnen krijgen een DataService-manifest
onder ``silver/nspd/services/<sourceId>/manifest.json`` (DONL-conventie: geen
blinde dump van omvangrijke diensten).

Run (vanaf nldt/):  PYTHONPATH=. python scripts/pdok_catalog_records.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.donl_harvest.dcat_map import DCAT_CONTEXT, _lang_value  # noqa: E402
from services.lake import get_lake_client  # noqa: E402

POC_NSPD = ROOT.parent / "poc-nspd"
REGISTRY = POC_NSPD / "data" / "sources.json"
CATALOG_BRONZE = POC_NSPD / "data" / "bronze" / "pdok-catalog"
PDOK_API = "https://api.pdok.nl/"
PDOK_TERMS = "https://www.pdok.nl/voorwaarden"

PUBLISHERS = {
    "rvo": ("Rijksdienst voor Ondernemend Nederland (RVO)", "rvo"),
    "hwh": ("Het Waterschapshuis (HWH)", "hwh"),
    "rws": ("Rijkswaterstaat (RWS)", "rws"),
    "kadaster": ("Kadaster", "kadaster"),
    "lv": ("Kadaster (Landelijke Voorziening)", "kadaster-lv"),
    "cbs": ("Centraal Bureau voor de Statistiek (CBS)", "cbs"),
    "rce": ("Rijksdienst voor het Cultureel Erfgoed (RCE)", "rce"),
    "ienw": ("Ministerie van Infrastructuur en Waterstaat (IenW)", "ienw"),
    "prorail": ("ProRail", "prorail"),
    "tno": ("TNO Geologische Dienst Nederland", "tno"),
    "rioned": ("Stichting RIONED", "rioned"),
}


def _latest_catalog() -> tuple[dict[str, dict[str, Any]], str | None]:
    """{api-root-href → api-entry} uit de jongste bronze-snapshot + stamp."""
    snaps = sorted(CATALOG_BRONZE.glob("*/index.json")) if CATALOG_BRONZE.is_dir() else []
    if not snaps:
        return {}, None
    idx = json.loads(snaps[-1].read_text(encoding="utf-8"))
    by_root: dict[str, dict[str, Any]] = {}
    for api in idx.get("apis") or []:
        for link in api.get("links") or []:
            if link.get("rel") == "root":
                by_root[link["href"].rstrip("/")] = api
    return by_root, snaps[-1].parent.name


def _publisher(service_url: str) -> dict[str, Any]:
    org = service_url.replace(PDOK_API, "").split("/", 1)[0]
    name, ident = PUBLISHERS.get(org, (f"PDOK-aanbieder '{org}'", org))
    return {"@type": "foaf:Organization", "foaf:name": name, "dcterms:identifier": ident}


def build_record(src: dict[str, Any], api: dict[str, Any] | None, *, lake_uri_for, now: str) -> dict[str, Any]:
    sid = src["id"]
    service = src["serviceUrl"].rstrip("/")
    collection = src.get("collection")
    items_url = f"{service}/collections/{collection}/items?f=json" if collection else service
    fetched = src.get("fetched") or {}
    dists: list[dict[str, Any]] = [{
        "@type": "dcat:Distribution",
        "dcterms:identifier": f"{sid}:ogcapi-features",
        "dcterms:title": _lang_value(f"{src.get('title')} — OGC API Features ({collection})"),
        "dcat:accessURL": items_url,
        "dcterms:format": "OGC API - Features",
        "dcat:mediaType": "application/geo+json",
        "nldt:distributionType": "DataService",
        "dcat:accessService": {
            "@type": "dcat:DataService",
            "dcterms:title": _lang_value(api.get("title") if api else src.get("title")),
            "dcat:endpointURL": service,
            "dcat:endpointDescription": f"{service}/api",
            "dcterms:format": "OGC API - Features",
            "dcterms:conformsTo": "http://www.opengis.net/spec/ogcapi-features-1/1.0",
        },
    }]
    silver_keys: list[str] = []
    cache = POC_NSPD / "data" / "cache"
    rd_cache = cache / f"{sid}.28992.geojson"
    national_cache = cache / "national" / f"{sid}.json"
    if rd_cache.is_file():
        # silver-tweeling aanwezig (fetch_pdok_layers.py of eerdere pipeline-fetch)
        if not fetched.get("featureCount"):
            try:
                props = json.loads(rd_cache.read_text(encoding="utf-8")).get("properties") or {}
                fetched = {**fetched, "featureCount": props.get("featureCount"), "at": props.get("fetchedAt")}
            except (json.JSONDecodeError, OSError):
                pass
        for crs in ("28992", "4326"):
            key = f"silver/nspd/geo/{sid}.{crs}.geojson"
            silver_keys.append(key)
            dists.append({
                "@type": "dcat:Distribution",
                "dcterms:identifier": f"{sid}:silver-{crs}",
                "dcterms:title": _lang_value(f"{sid}.{crs}.geojson (NSPD-bbox, EPSG:{crs})"),
                "dcat:accessURL": lake_uri_for(key),
                "dcterms:format": "GeoJSON",
                "dcat:mediaType": "application/geo+json",
                "nldt:distributionType": "Download",
                "nldt:zone": "silver",
                "nldt:crs": f"EPSG:{crs}",
                "nldt:featureCount": fetched.get("featureCount"),
            })
    elif national_cache.is_file():
        # properties-only context-cache (pipeline/national_data.py)
        key = f"silver/nspd/geo/national/{sid}.json"
        silver_keys.append(key)
        dists.append({
            "@type": "dcat:Distribution",
            "dcterms:identifier": f"{sid}:silver-properties",
            "dcterms:title": _lang_value(f"{sid}.json (NSPD-bbox, alleen properties)"),
            "dcat:accessURL": lake_uri_for(key),
            "dcterms:format": "JSON",
            "dcat:mediaType": "application/json",
            "nldt:distributionType": "Download",
            "nldt:zone": "silver",
        })
    rec: dict[str, Any] = {
        "@context": DCAT_CONTEXT,
        "@type": "dcat:Dataset",
        "dcterms:identifier": sid,
        "dcterms:title": _lang_value(src.get("title")),
        "dcterms:description": _lang_value(
            (api or {}).get("description") or src.get("note") or src.get("title")
        ),
        "dcterms:modified": now,
        "dcterms:license": PDOK_TERMS,
        "nldt:licenseNote": src.get("licenseNote")
        or "PDOK open data; exacte licentie (CC0 / CC-BY 4.0) per dataset op pdok.nl — niet per dataset geverifieerd",
        "dcat:keyword": sorted({*((api or {}).get("keywords") or []), *(src.get("tracks") or []), "NSPD", "North Sea Port"}),
        "dcat:landingPage": service,
        "dcat:distribution": dists,
        "dcterms:publisher": _publisher(service),
        "dcterms:spatial": {
            "@type": "dcterms:Location",
            "dcat:bbox": "POLYGON((3.45 51.02, 3.88 51.02, 3.88 51.48, 3.45 51.48, 3.45 51.02))",
            "nldt:bboxNote": "NSPD-werkkader (poc-nspd/bbox.py), WGS84",
        },
        "prov:wasDerivedFrom": items_url,
        "nldt:hadPrimarySource": "api.pdok.nl",
        "nldt:poc": "nspd",
        "nldt:zone": "catalog",
        "nldt:accessClass": "open",
        "nldt:retrievedAt": fetched.get("at") or src.get("lastChecked"),
        "nldt:role": src.get("role"),
        "nldt:tracks": src.get("tracks"),
        "nldt:jurisdictie": src.get("jurisdictie"),
        "nldt:fetchPolicy": src.get("fetchPolicy") or "cache",
        "nldt:probeEvidence": src.get("probeEvidence"),
        "nldt:registryUri": lake_uri_for("silver/nspd/meta/sources.json"),
        "nldt:distributionSummary": {
            "total": len(dists),
            "download": len(silver_keys),
            "dataService": 1,
        },
    }
    if src.get("axisOrder"):
        rec["nldt:axisOrder"] = src["axisOrder"]
    if silver_keys:
        rec["nldt:lakeUri"] = lake_uri_for(silver_keys[0])
        if fetched.get("bronze"):
            rel = fetched["bronze"].replace("data/bronze/", "")  # pdok/<sid>/<stamp>
            rec["nldt:bronzeUri"] = lake_uri_for(f"bronze/nspd/{rel}/")
    else:
        rec["nldt:serviceManifestUri"] = lake_uri_for(f"silver/nspd/services/{sid}/manifest.json")
        rec["nldt:lakeUri"] = rec["nldt:serviceManifestUri"]
    return rec


def service_manifest(src: dict[str, Any], rec: dict[str, Any], now: str) -> dict[str, Any]:
    return {
        "@type": "dcat:DataService",
        "datasetId": src["id"],
        "title": src.get("title"),
        "endpointURL": src["serviceUrl"].rstrip("/"),
        "collection": src.get("collection"),
        "itemsURL": rec["prov:wasDerivedFrom"],
        "format": "OGC API - Features",
        "fetchPolicy": src.get("fetchPolicy"),
        "note": src.get("note"),
        "generatedAt": now,
        "nldt:poc": "nspd",
        "nldt:zone": "silver",
        "nldt:accessClass": "open",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    pdok = [s for s in doc.get("sources", [])
            if s.get("endpointType") == "ogc-api" and (s.get("serviceUrl") or "").startswith(PDOK_API)]
    by_root, catalog_stamp = _latest_catalog()
    client = get_lake_client()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written = []
    for src in pdok:
        api = by_root.get(src["serviceUrl"].rstrip("/"))
        rec = build_record(src, api, lake_uri_for=client.uri_for, now=now)
        if catalog_stamp:
            rec["nldt:catalogSnapshotUri"] = client.uri_for(f"bronze/nspd/pdok-catalog/{catalog_stamp}/index.json")
        key = f"catalog/dcat/{src['id']}.json"
        body = json.dumps(rec, ensure_ascii=False, indent=2).encode("utf-8")
        out = {"id": src["id"], "key": key, "inCatalog": api is not None,
               "fetched": "nldt:serviceManifestUri" not in rec}
        if not args.dry_run:
            client.put_bytes(key, body, content_type="application/ld+json")
            if not out["fetched"]:
                mkey = f"silver/nspd/services/{src['id']}/manifest.json"
                client.put_bytes(mkey, json.dumps(service_manifest(src, rec, now), ensure_ascii=False, indent=2).encode("utf-8"),
                                 content_type="application/json")
                out["manifest"] = mkey
        written.append(out)
    print(json.dumps({"count": len(written), "dryRun": args.dry_run, "catalogSnapshot": catalog_stamp,
                      "withoutCatalogEntry": [w["id"] for w in written if not w["inCatalog"]],
                      "serviceOnly": [w["id"] for w in written if not w["fetched"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
