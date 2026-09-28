#!/usr/bin/env python3
"""Bronsonderzoek-continueiteitsprobe voor de MiniGIM-bronnen (PoC-5).

Probeert elke geregistreerde bron in ``data/sources.json`` met één kleine,
sleutelloze live query en schrijft het bewijs naar
``data/probe_evidence_<ts>.json`` (zelfde patroon als poc/data/probe_services.py).
Geen enkele probe muteert data; bedoeld voor de source-monitor-continueiteit.

Uitvoeren:
    nldt/.venv/bin/python poc-minigim/data/probe_minigim.py
    nldt/.venv/bin/python poc-minigim/data/probe_minigim.py --quiet   # alleen exit code
Exit 0 = alle bronnen gezond; 1 = minstens één bron wijkt af.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent
RD = "http://www.opengis.net/def/crs/EPSG/0/28992"
# proef-bbox: Breda-west (klein, goedkoop, altijd gevuld)
BBOX = "120500,390500,122500,392500"
UA = {"User-Agent": "ldt-toolbox-poc-minigim/1.0 (broncontrole)"}


def _get(url: str, timeout: int = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def _probe_source(src: dict) -> dict:
    proto = src["protocol"]
    if proto == "ogc-api-features":
        base = src["baseUrl"].rstrip("/")
        coll = (src.get("collections") or [""])[0]
        url = (
            f"{base}/collections/{coll}/items?f=json&limit=1"
            f"&bbox-crs={RD}&crs={RD}&bbox={BBOX}"
            if coll
            else f"{base}/collections?f=json"
        )
    elif proto == "wfs2":
        base = src["baseUrl"].rstrip("/")
        tn = (src.get("typeNames") or [src.get("typeName") or ""])[0]
        url = (
            f"{base}?service=WFS&version=2.0.0&request=GetFeature&typenames={tn}"
            f"&outputFormat=geojson&srsName=urn:ogc:def:crs:EPSG::28992&count=1"
            f"&bbox=120000,389000,126000,394000"
        )
    elif proto == "arcgis-rest":
        url = (
            f"{src['serviceUrl'].rstrip('/')}/{src.get('layerId', 0)}/query"
            f"?f=geojson&outSR=28992&where=1%3D1&resultRecordCount=1"
        )
    else:
        return {"id": src["id"], "ok": False, "error": f"onbekend protocol {proto}"}

    try:
        status, body = _get(url)
        doc = json.loads(body)
        n = len(doc.get("features", [])) if isinstance(doc, dict) else 0
        # WFS/OGC-api levert GeoJSON met features (kan legitiem 0 zijn buiten bbox),
        # ArcGIS ook; collections-endpoint heeft geen features-key
        healthy = status == 200 and (isinstance(doc, (dict, list)))
        return {
            "id": src["id"],
            "ok": healthy,
            "httpStatus": status,
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "sampleFeatures": n,
            "url": url,
        }
    except Exception as exc:  # noqa: BLE001 — probe wil elke fout vangen
        return {"id": src["id"], "ok": False, "error": f"{type(exc).__name__}: {exc}", "url": url}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    registry = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    results = [_probe_source(s) for s in registry["sources"]]
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = {
        "probedAt": ts,
        "bbox": BBOX,
        "results": results,
        "allOk": all(r["ok"] for r in results),
    }
    out = DATA / f"probe_evidence_{ts}.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    if not args.quiet:
        for r in results:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['id']:32} {r.get('error', r.get('httpStatus', ''))}")
        print(f"bewijs: {out}")
    return 0 if evidence["allOk"] else 1


if __name__ == "__main__":
    sys.exit(main())
