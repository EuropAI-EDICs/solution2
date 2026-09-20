#!/usr/bin/env python3
"""Fetch actual water levels (polders + boezem, mNAP) into a growing archive.

Rijnland exposes measured peilen only as *current* values (AGOL live layers)
plus a fixed ~12-day chart window per station (HydroNET watercontrolroom).
Retro history is not openly served, so this script snapshots what IS open:
every station's latest value and its 12-day series, aggregated to daily
stats and merged into ``data/peilen/peilen.json``. Re-run it (e.g. weekly)
to grow the archive forward.

Usage:
    nldt/.venv/bin/python poc-rijnland/scripts/fetch_peilen.py            # fetch + merge
    nldt/.venv/bin/python poc-rijnland/scripts/fetch_peilen.py --dry-run  # station list only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import statistics
from pathlib import Path
from urllib.request import Request, urlopen

AGOL = "https://services1.arcgis.com/KXsJqtRt2xEqyDWx/arcgis/rest/services"
LAYERS = {
    "polders": f"{AGOL}/eb7225ec-7287-4ad8-8d8a-b0ed6163e136/FeatureServer/0",
    "boezem": f"{AGOL}/953f7293-123f-4c5c-a277-47fd7ed84bec/FeatureServer/0",
}
OUT = Path(__file__).resolve().parents[1] / "data" / "peilen" / "peilen.json"

_POINT_RE = re.compile(r'\{\s*"y":\s*(-?[\d.]+),\s*"x":\s*([\d.]+)\s*\}')


def _get(url: str) -> bytes:
    req = Request(url, headers={"Accept": "application/json,text/html"})
    with urlopen(req, timeout=60) as resp:
        return resp.read()


def parse_chart_series(html: str) -> list:
    """Extract the embedded Highcharts points [{"y":…, "x": epoch-ms}]."""
    return [{"y": float(y), "x": float(x)}
            for y, x in _POINT_RE.findall(html)]


def daily_stats(points: list) -> dict:
    """Per-UTC-day {n, median, min, max} from epoch-ms points."""
    per_day: dict = {}
    for p in points:
        day = _dt.datetime.fromtimestamp(
            p["x"] / 1000.0, _dt.timezone.utc).strftime("%Y-%m-%d")
        per_day.setdefault(day, []).append(p["y"])
    return {
        day: {"n": len(v),
              "median": round(statistics.median(v), 4),
              "min": round(min(v), 4),
              "max": round(max(v), 4)}
        for day, v in sorted(per_day.items())
    }


def fetch_stations() -> list:
    stations = []
    for layer, url in LAYERS.items():
        offset = 0
        while True:
            doc = json.loads(_get(
                f"{url}/query?where=1%3D1&outFields=*&f=geojson"
                f"&resultRecordCount=200&resultOffset={offset}"))
            feats = doc.get("features") or []
            for f in feats:
                p = f.get("properties") or {}
                if not p.get("chartUrl"):
                    continue
                coord = (f.get("geometry") or {}).get("coordinates") or [None, None]
                stations.append({
                    "fid": p.get("featureIdentifier") or p.get("name"),
                    "name": p.get("name") or "",
                    "classification": p.get("classification") or "",
                    "value": p.get("value"),
                    "x": coord[0], "y": coord[1],
                    "chartUrl": p["chartUrl"],
                    "layer": layer,
                })
            if len(feats) < 200:
                break
            offset += 200
    return [s for s in stations if s["fid"]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="list stations without fetching charts")
    args = ap.parse_args()

    stations = fetch_stations()
    print(f"[peilen] {len(stations)} stations "
          f"({sum(1 for s in stations if s['layer'] == 'polders')} polders, "
          f"{sum(1 for s in stations if s['layer'] == 'boezem')} boezem)")
    if args.dry_run:
        for s in stations[:5]:
            print("  ", s["layer"], s["fid"], s["name"][:50])
        return 0

    archive = {}
    if OUT.is_file():
        archive = json.loads(OUT.read_text(encoding="utf-8"))
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = archive.setdefault("stations", {})
    archive.update({
        "source": "Rijnland AGOL live layers + HydroNET watercontrolroom "
                  "efsserviceprovider chart endpoint (~12-day window)",
        "layers": LAYERS,
        "unit": "mNAP",
        "lastFetchedAt": now,
    })

    n_points = 0
    for i, s in enumerate(stations, 1):
        try:
            html = _get(s["chartUrl"]).decode("utf-8", "replace")
            points = parse_chart_series(html)
            n_points += len(points)
            rec = records.setdefault(s["fid"], {})
            rec.update({
                "name": s["name"], "classification": s["classification"],
                "layer": s["layer"], "x": s["x"], "y": s["y"],
                "unit": "mNAP",
                "latest": {"value": s["value"], "fetchedAt": now},
            })
            days = rec.setdefault("days", {})
            days.update(daily_stats(points))
        except Exception as exc:  # one station failing must not kill the run
            print(f"[peilen] WARN {s['fid']}: {type(exc).__name__}: {exc}")
        if i % 40 == 0:
            print(f"[peilen] {i}/{len(stations)} stations…", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(archive, ensure_ascii=False), encoding="utf-8")
    n_days = sum(len(r.get("days", {})) for r in records.values())
    print(f"[peilen] {OUT}: {len(records)} stations, {n_points} raw points "
          f"-> {n_days} station-days archived")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
