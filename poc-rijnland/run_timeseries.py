#!/usr/bin/env python3
"""PoC-3 fase 2c: tijdreeks gemeten waterkwaliteit 2020–2026.

Renders the monthly WKP fixture as one interactive offline HTML page:
maandmediaan + P25–P75-band, 12-maands trend, seizoenscyclus en een
afspeel-cursor over de tijd. See rijnland/timeseries_report.py.

Usage:
    nldt/.venv/bin/python poc-rijnland/run_timeseries.py
    nldt/.venv/bin/python poc-rijnland/run_timeseries.py --parameter 'VERZDGGD|zuurstof|%'
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POC_ROOT = ROOT.parent / "poc"
for _p in (str(ROOT), str(POC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rijnland import hexmap_time, timeseries_report  # noqa: E402
from rijnland.water_quality import NORMS  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-year", type=int, default=2020)
    ap.add_argument("--to-year", type=int, default=2026)
    ap.add_argument("--parameter", default="CONCTTE|chloride|mg/l")
    ap.add_argument("--no-animate", action="store_true",
                    help="skip the animated hex map (hexmap-tijd.html)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    fixture_path = (ROOT / "data" / "wkp" /
                    f"waterkwaliteit-monthly-{args.from_year}-{args.to_year}.json")
    if not fixture_path.is_file():
        raise SystemExit(
            f"[ts] fixture missing: {fixture_path}\n"
            f"[ts] run: nldt/.venv/bin/python poc-rijnland/scripts/fetch_wkp.py "
            f"--monthly --from-year {args.from_year} --to-year {args.to_year}")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out or ROOT / "runs" / f"{ts}-timeseries"
    out_dir.mkdir(parents=True, exist_ok=True)

    html = timeseries_report.render_timeseries(
        fixture,
        title=f"Waterkwaliteit Rijnland {args.from_year}–{args.to_year}",
        default_parameter=args.parameter,
        out_path=out_dir / "timeseries.html")
    (out_dir / "timeseries.json").write_text(
        json.dumps({"fixture": fixture_path.name,
                    "defaultParameter": args.parameter,
                    "computedBy": timeseries_report.TS_VERSION,
                    "bytesHtml": len(html)}, indent=1) + "\n",
        encoding="utf-8")
    print(f"[ts] {out_dir / 'timeseries.html'} ({len(html):,} bytes, "
          f"default {args.parameter})")

    if not args.no_animate:
        try:
            from pipeline import h3step

            per_loc = (fixture.get("perLocation") or {}).get(args.parameter)
            months = fixture.get("months") or []
            if not per_loc or not months:
                raise ValueError("geen per-locatie maandseries in de fixture")
            locs = [{"x": l["x"], "y": l["y"], "values": l["values"]}
                    for l in per_loc.values()]
            vals = [v for l in locs for v in l["values"] if v is not None]
            qs = statistics.quantiles(vals, n=10)
            bundle = hexmap_time.build_cell_steps(
                locations=locs, resolution=8,
                call=lambda pid, inputs: h3step.call(pid, inputs))
            if bundle:
                steps = [_dt.date(int(m[:4]), int(m[5:7]), 1).strftime("%b %Y")
                         for m in months]
                norm = NORMS.get(args.parameter, {})
                anim = hexmap_time.render_hexmap_time(
                    bundle, steps=steps,
                    title=(f"{norm.get('label', args.parameter)} per cel, "
                           f"per maand {months[0][:4]}–{months[-1][:4]}"),
                    value_label=norm.get("label", args.parameter),
                    unit=args.parameter.split("|")[-1],
                    vmin=qs[0], vmax=qs[-1],
                    invert=norm.get("worse") == "low",
                    stops=[(0.0, "Gunstigste kwart van gemeten bereik"),
                           (0.5, "Midden van gemeten bereik"),
                           (1.0, "Ongunstigste kwart van gemeten bereik")],
                    out_path=out_dir / "hexmap-tijd.html")
                (out_dir / "hexmap-tijd.json").write_text(json.dumps({
                    "parameter": args.parameter,
                    "cells": len(bundle["values"]),
                    "steps": len(steps),
                    "scale": [qs[0], qs[-1]],
                }, indent=1) + "\n", encoding="utf-8")
                print(f"[ts] {out_dir / 'hexmap-tijd.html'} "
                      f"({len(anim):,} bytes, {bundle['nSteps']} stappen)")
        except Exception as exc:  # animatie is decision support
            print(f"[ts] WARNING hexmap-animatie overgeslagen: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
