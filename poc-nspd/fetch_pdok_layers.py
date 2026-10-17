#!/usr/bin/env python3
"""PDOK-lagen uit de registry ophalen → data/cache (28992 + 4326) + data/bronze.

Haalt alle registry-bronnen met ``fetchPolicy: "cache"`` (PDOK OGC API
Features, gepind 2026-10-16 via data/probe_pdok_catalog.py) binnen de
NSPD-bbox op via ``pipeline.geodata.fetch_layer`` (cache-first, rel=next-
paging, axisOrder-correctie). Elke pagina gaat als-ontvangen naar
``data/bronze/pdok/<sourceId>/<retrievedAt>/page-NNNN.json`` (+ manifest met
sha256) — de lake-bronze-laag; de cache is de silver-laag (dual CRS). Beide
mappen zijn git-ignored; ``nldt/scripts/lake_sync.py --poc nspd`` zet ze in
de nldt-datalake.

Schrijft per bron een ``fetched``-blok terug in data/sources.json
(featureCount/pages/bronze-pad) als fetch-bewijs naast het probe-bewijs.

Run (vanaf poc-nspd/):  .venv/bin/python fetch_pdok_layers.py [--refresh] [--ids a b]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bbox import nspd_bbox_rd  # noqa: E402
from pipeline import geodata  # noqa: E402

REGISTRY = ROOT / "data" / "sources.json"
BRONZE = ROOT / "data" / "bronze" / "pdok"


class _BronzeSink:
    """Schrijft ruwe pagina's weg en verzamelt het manifest."""

    def __init__(self, sid: str, src: dict, stamp: str) -> None:
        self.dir = BRONZE / sid / stamp
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pages: list[dict] = []
        self.manifest = {
            "sourceId": sid,
            "serviceUrl": src.get("serviceUrl"),
            "collection": src.get("collection"),
            "axisOrder": src.get("axisOrder") or "lonlat",
            "retrievedAt": stamp,
            "userAgent": geodata.USER_AGENT,
            "zone": "bronze",
            "note": "as-received OGC API Features pages (f=json), unmodified bytes",
        }

    def __call__(self, i: int, url: str, content: bytes) -> None:
        name = f"page-{i + 1:04d}.json"
        (self.dir / name).write_bytes(content)
        self.pages.append({"file": name, "url": url, "bytes": len(content),
                           "sha256": hashlib.sha256(content).hexdigest()})

    def close(self) -> Path:
        self.manifest["pages"] = self.pages
        p = self.dir / "manifest.json"
        p.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        return self.dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refresh", action="store_true", help="cache negeren en opnieuw downloaden")
    ap.add_argument("--ids", nargs="*", help="alleen deze source-ids (default: alle fetchPolicy=cache)")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args(argv)

    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in doc["sources"]}
    wanted = args.ids or [sid for sid, s in sources.items()
                          if s.get("fetchPolicy") == "cache" and s.get("endpointType") == "ogc-api"]
    bbox = nspd_bbox_rd()
    failures = 0
    for sid in wanted:
        src = sources[sid]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        sink = _BronzeSink(sid, src, stamp)
        t0 = time.time()
        try:
            fc = geodata.fetch_layer(sid, bbox=bbox, refresh=args.refresh, sources=sources,
                                     timeout=args.timeout, raw_sink=sink)
        except geodata.GeoDataError as exc:
            failures += 1
            print(f"ERR {sid}: {exc}", file=sys.stderr)
            continue
        p = fc.get("properties") or {}
        downloaded = bool(sink.pages)
        if downloaded:
            bronze_dir = sink.close()
            src["fetched"] = {
                "at": stamp, "featureCount": p.get("featureCount"), "pages": p.get("pages"),
                "bronze": str(bronze_dir.relative_to(ROOT)),
                "cache": f"data/cache/{sid}.28992.geojson",
            }
        else:  # cache-hit: lege bronze-map opruimen
            try:
                sink.dir.rmdir()
                if not any(sink.dir.parent.iterdir()):
                    sink.dir.parent.rmdir()
            except OSError:
                pass
        print(f"OK  {sid}: {p.get('featureCount')} features / {p.get('pages')} pagina's "
              f"({'download' if downloaded else 'cache-hit'}, {time.time() - t0:.1f}s)")

    REGISTRY.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
