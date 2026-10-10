#!/usr/bin/env python3
"""Exporteer de Rijnland-peilen als H3-hexagon-flow voor het live-dashboard.

Leest het peil-archief (``data/peilen/peilen.json``), bouwt via de engine-
eigen bridge (``hexmap_time.build_cell_steps`` + de stroomgraaf-graaf) de
per-cel-per-dag afwijking t.o.v. de mediane peil, en schrijft
``hex-flow.json`` voor het dashboard:

  { steps: [daglabels], cells_fc: FeatureCollection, values: {cel: [cm,…]},
    derived: {cel: {…}}, cellPg: {cel: {naam, peil}}, meta: {…} }

Ontbrekende dagwaarden worden lineair geïnterpoleerd (data-aanvulling);
de vlag ``interpolated`` markeert per cel welke stappen aangevuld zijn.

Run: ``python rijnland_hex_export.py --out <hex-flow.json>`` (cwd = poc-rijnland,
d.w.z. via de tool in ``tools/poc_live.py``).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "poc-rijnland"
for p in (str(ROOT.parent / "poc"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from rijnland import flow as flow_mod          # noqa: E402
from rijnland import hexmap_time               # noqa: E402
from rijnland.hexmap_time import _to_wgs       # noqa: E402
from shapely.geometry import mapping, shape    # noqa: E402
from shapely.ops import unary_union            # noqa: E402
# h3step leeft in poc/pipeline en wordt pas ná de sys.path-insert geïmporteerd
from pipeline import h3step                    # noqa: E402


def _interpolate(values: list[float | None]) -> list[float | None]:
    """Lineair opvullen van None-gaten tussen bekende waarden (randen blijven None)."""
    out = list(values)
    n = len(out)
    i = 0
    while i < n:
        if out[i] is not None:
            i += 1
            continue
        j = i
        while j < n and out[j] is None:
            j += 1
        if i > 0 and j < n:                      # beide kanten bekend → interpoleer
            left, right = out[i - 1], out[j]
            for k in range(i, j):
                f = (k - i + 1) / (j - i + 1)
                out[k] = round(left + (right - left) * f, 4)
        i = j
    return out


def build_hex_flow(archive_path: Path, with_flow: bool = True) -> dict:
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    days_all = sorted({d for r in archive["stations"].values()
                       for d in (r.get("days") or {})})
    locs = []
    for rec in archive["stations"].values():
        days = rec.get("days") or {}
        if not days:
            continue
        med = statistics.median([d["median"] for d in days.values()])
        values = [round((days[d]["median"] - med) * 100.0, 1) if d in days else None
                  for d in days_all]
        locs.append({"x": rec["x"], "y": rec["y"], "values": values,
                     "name": rec.get("name"), "classification": rec.get("classification"),
                     "layer": rec.get("layer")})

    bundle = hexmap_time.build_cell_steps(
        locations=locs, resolution=8,
        call=lambda pid, inputs: h3step.call(pid, inputs))
    if not bundle:
        raise SystemExit("geen cel-bundel: h3-bridge of locaties ontbreken")

    # stations per cel: zelfde join als de bridge, nu met namen en classificatie
    pts_wgs = [_to_wgs(l["x"], l["y"]) for l in locs]
    points_fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"i": i},
         "geometry": {"type": "Point", "coordinates": [round(x, 6), round(y, 6)]}}
        for i, (x, y) in enumerate(pts_wgs)]}
    hull = unary_union([shape(f["geometry"]) for f in points_fc["features"]]).convex_hull
    hull_fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": mapping(hull)}]}
    join = h3step.call("h3-spatial-join-points",
                       {"points": points_fc, "polygon": hull_fc,
                        "resolution": 8})["join"]
    st_cell = {r["index"]: r["cell"] for r in join.get("perPoint", [])
               if r.get("inCells")}
    from collections import Counter
    cell_stations = Counter(st_cell.values())
    cell_station_name = {}
    for i, cell in st_cell.items():
        nm = locs[i].get("name")
        if nm and cell not in cell_station_name:
            cell_station_name[cell] = nm

    values = {cell: _interpolate(series)
              for cell, series in bundle["values"].items()}

    derived, cell_pg = {}, {}
    if with_flow:
        try:
            from rijnland import flow as flow_mod

            fx = flow_mod.load_fixtures()
            graph = flow_mod.build_flow_graph(
                peilgebieden_fc=fx["peilgebieden"],
                gemalen_fc=fx["gemalen"],
                watergangen=fx["watergangen"],
                resolution=8,
                call=lambda pid, inputs: h3step.call(pid, inputs))
            if graph:
                derived = flow_mod.derive_values(graph, bundle["values"])
                for cell in bundle["values"]:
                    pg = graph["cellPg"].get(cell)
                    if pg:
                        node = graph["nodes"][pg]
                        cell_pg[cell] = {"name": node["name"], "peil": node["peil"]}
        except Exception as exc:                     # stroomgraad is decision support
            print(f"[hex-flow] WARNING stroomgraad overgeslagen: {exc}", file=sys.stderr)

    # per-cel statistieken (op de geïnterpoleerde reeks)
    cell_meta = {}
    for cell, series in values.items():
        known = [v for v in series if v is not None]
        meta_cell = {
            "stations": cell_stations.get(cell, 0),
            "stationExample": cell_station_name.get(cell),
            "mean": round(statistics.mean(known), 1) if known else None,
            "min": round(min(known), 1) if known else None,
            "max": round(max(known), 1) if known else None,
            "trend": round(known[-1] - known[0], 1) if len(known) >= 2 else None,
            "derived": cell in derived,
        }
        pg = cell_pg.get(cell)
        if pg:
            meta_cell["peilgebied"] = pg.get("name")
            meta_cell["peil"] = pg.get("peil")
        cell_meta[cell] = meta_cell

    # per-dag tellingen: hoeveel cellen zitten ver van hun mediane peil
    day_stats = []
    for d_i, d in enumerate(days_all):
        lows, highs, known_vals = 0, 0, []
        worst_low, worst_high = None, None
        for cell, series in values.items():
            v = series[d_i]
            if v is None:
                continue
            known_vals.append(v)
            if v <= -2:
                lows += 1
                if worst_low is None or v < worst_low["v"]:
                    worst_low = {"cell": cell, "v": v}
            elif v >= 2:
                highs += 1
                if worst_high is None or v > worst_high["v"]:
                    worst_high = {"cell": cell, "v": v}
        day_stats.append({
            "date": d,
            "nLager": lows, "nHoger": highs,
            "nNear": len(known_vals) - lows - highs,
            "meanDev": round(statistics.mean(known_vals), 1) if known_vals else None,
            "mostLager": worst_low, "mostHoger": worst_high,
        })

    steps = [d[5:] for d in days_all]                # MM-DD leesbaar kort
    return {
        "steps": steps,
        "cells_fc": bundle["cells_fc"],
        "values": values,
        "interpolated": {cell: [v is None for v in series]
                          for cell, series in bundle["values"].items()},
        "derived": derived,
        "cellPg": cell_pg,
        "cellMeta": cell_meta,
        "dayStats": day_stats,
        "meta": {
            "unit": "cm t.o.v. mediane peil",
            "nStations": len(locs),
            "nCells": len(bundle["values"]),
            "nDerived": len(derived),
            "window": [days_all[0], days_all[-1]],
            "nearBandCm": 2,
            "stops": "rood = lager/droger · blauw = hoger/natter",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", default=str(ROOT / "data" / "peilen" / "peilen.json"))
    ap.add_argument("--out", required=True, help="pad voor hex-flow.json")
    ap.add_argument("--no-flow", action="store_true", help="stroomgraaf-afleiding overslaan")
    args = ap.parse_args()
    flow = build_hex_flow(Path(args.archive), with_flow=not args.no_flow)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(flow, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[hex-flow] {out} — {flow['meta']['nCells']} cellen, "
          f"{flow['meta']['nStations']} stations, {len(flow['steps'])} dagen, "
          f"{flow['meta']['nDerived']} afgeleide cellen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
