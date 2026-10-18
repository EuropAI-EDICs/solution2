"""Live probe van de gebruikte Utrecht-bronnen (nspd-port fase 2).

Leest de registry, kiest de bronnen die in een layers.json-manifest voorkomen
of role scenario-basis hebben, en probeert elk: ArcGIS-count (agrest/hub),
OGC-API/WFS-head (nationale bronnen), of "document" (skip). Schrijft
probe-sources-<datum>.json als NSPD-stijl evidence. Lees-only: raakt geen
caches. Run: cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 data/probe_sources.py
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
POC = HERE.parent
AOI = {"type": "Polygon", "coordinates": [[[130000, 440000], [160000, 440000],
      [160000, 470000], [130000, 470000], [130000, 440000]]]}


def _arcgis_count(entry: dict) -> int | None:
    url = f"{entry['serviceUrl']}/{entry.get('layerId', 0)}/query?f=json&where=1%3D1&returnCountOnly=true"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return int(json.loads(r.read().decode("utf-8")).get("count"))
    except Exception as exc:  # bewust breed: de probe registreert, faalt nooit
        return None if not isinstance(exc, KeyboardInterrupt) else None


def main() -> int:
    reg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    used: set[str] = set()
    for run in sorted((POC / "runs").glob("*/layers.json")):
        for laag in json.loads(run.read_text(encoding="utf-8")).values():
            sid = laag.get("aliasSourceId")
            if sid:
                used.add(sid)
    for it in reg["sources"]:
        if it.get("role") == "scenario-basis":
            used.add(it["id"])
    by_id = {it["id"]: it for it in reg["sources"]}
    out = {"datum": date.today().isoformat(), "aoi": AOI, "bronnen": []}
    for sid in sorted(used):
        it = by_id.get(sid)
        if not it or "serviceUrl" not in it:
            out["bronnen"].append({"id": sid, "role": it.get("role") if it else None,
                                   "bereikbaar": False, "featureCount": None,
                                   "fout": "geen serviceUrl (document/AOI)"})
            continue
        count = _arcgis_count(it) if "arcgis" in it["serviceUrl"] or "agrest" in it["serviceUrl"] else None
        out["bronnen"].append({"id": sid, "role": it.get("role"),
                               "bereikbaar": count is not None,
                               "featureCount": count})
    path = HERE / f"probe-sources-{date.today().isoformat()}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_ok = sum(1 for b in out["bronnen"] if b["bereikbaar"])
    print(f"probe {path.name}: {n_ok}/{len(out['bronnen'])} bereikbaar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
