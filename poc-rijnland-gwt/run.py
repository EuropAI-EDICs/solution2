#!/usr/bin/env python3
"""PoC-6 Rijnland GWT digital twin (Morales 2023 framework, MVP).

Sensor positions + rainfall → per-logger decision-tree depth forecast →
Waterpump ON/OFF triggers with gemaal advice → animated H3 twin map +
single-file report. Reuses PoC-1 ``pipeline`` (geodata, h3step) and the
PoC-3 ``hexmap_time`` bridge. See
docs/superpowers/specs/2026-10-13-rijnland-gwt-digital-twin-design.md.
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
POC_RIJNLAND = ROOT.parent / "poc-rijnland"
for p in (str(ROOT), str(POC_ROOT), str(POC_RIJNLAND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from gwt import archive as gwt_archive  # noqa: E402
from gwt import predict, rain as gwt_rain, report as gwt_report  # noqa: E402
from gwt import sensors, triggers  # noqa: E402
from pipeline import geodata, h3step  # noqa: E402 — PoC-1
from rijnland import hexmap_time  # noqa: E402 — PoC-3 bridge

SOURCES_PATH = ROOT / "data" / "sources.json"
CACHE_DIR = ROOT / "data" / "cache"
RAIN_CACHE_DIR = ROOT / "data" / "rain"
ARCHIVE_PATH = ROOT / "data" / "gwt" / "gwt.json"

# Leiden / Haarlemmermeer demo slice (PoC-3 default); --full for everything.
DEFAULT_BBOX = "90000,455000,105000,470000"
FULL_BBOX = "85000,445000,135000,485000"

MVP_QUESTION = (
    "Where will the groundwater table in the Rijnland beheergebied cross "
    "drought/ingress thresholds in the coming days — and which gemaal "
    "action (aan / uit / vasthouden) is advised?")

HISTORY_STEPS = 30  # animated map: this many history days + the forecast


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None,
                    help="output directory (default: poc-rijnland-gwt/runs/<ts>)")
    ap.add_argument("--bbox", default=DEFAULT_BBOX,
                    help="xmin,ymin,xmax,ymax in EPSG:28992 "
                         f"(default demo slice {DEFAULT_BBOX})")
    ap.add_argument("--full", action="store_true",
                    help="fetch entire Rijnland layers (rain on the full-area grid)")
    ap.add_argument("--refresh", action="store_true", help="re-fetch geo layers")
    ap.add_argument("--refresh-rain", action="store_true",
                    help="re-download open-meteo precipitation")
    ap.add_argument("--reseed", action="store_true",
                    help="regenerate the seeded GWT archive (formula change)")
    ap.add_argument("--no-h3", action="store_true", help="skip the animated hex map")
    ap.add_argument("--h3-resolution", type=int, default=7, choices=range(0, 16),
                    metavar="{0..15}",
                    help="H3 resolution for the twin map (default 7 ≈ 1.2 km; "
                         "the demo-slice loggers form a thin corridor)")
    ap.add_argument("--days", type=int, default=90,
                    help="archive/history window in days (default 90)")
    ap.add_argument("--forecast-days", type=int, default=5)
    ap.add_argument("--rain-scenario-mm", type=float, default=None,
                    help="what-if: flat cloudburst (mm) replacing day +1 forecast rain")
    ap.add_argument("--ingress-depth", type=float, default=0.4,
                    help="depth <= this (m -mv) → WaterpumpON (default 0.4)")
    ap.add_argument("--drought-depth", type=float, default=1.2,
                    help="depth >= this (m -mv) → WaterpumpOFF + vasthouden (default 1.2)")
    ap.add_argument("--gemaal-radius-m", type=float, default=2500.0,
                    help="nearest-gemaal match radius; beyond it = action gap")
    ap.add_argument("--timeout", type=int, default=180)
    return ap


def dump_json(path: Path, doc: dict, *, indent: int = 1) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=indent) + "\n",
                    encoding="utf-8")


def _mean_depth_by_date(forecasts_by_code: dict) -> dict:
    by_date: dict = {}
    for fc in forecasts_by_code.values():
        for step in fc.get("forecast", []):
            by_date.setdefault(step["date"], []).append(step["depth"])
    return {d: round(statistics.mean([v for v in vs if v is not None]), 3)
            for d, vs in by_date.items() if any(v is not None for v in vs)}


def _merge_day_summary(cmd_days: list, mean_by_date: dict) -> list:
    return [{**d, "meanDepth": mean_by_date.get(d["date"])} for d in cmd_days]


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{ts}-gwt-twin"
    out_dir = Path(args.out) if args.out else ROOT / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    bbox = FULL_BBOX if args.full else args.bbox
    bbox_vals = [float(v) for v in bbox.split(",")]
    rain_bbox = [float(v) for v in (FULL_BBOX if args.full else bbox).split(",")]

    print(f"[poc-rijnland-gwt] {run_id} -> {out_dir}")
    sources = geodata.load_sources(SOURCES_PATH)
    # loggers: attribute-mode fetch (service returns NULL geometry for them)
    loggers_fc = sensors.fetch_layer_attrs(
        "rijnland-logger-grondwater", sources=sources, cache_dir=CACHE_DIR,
        bbox=None if args.full else bbox_vals, refresh=args.refresh,
        timeout=args.timeout)
    gemalen_fc = geodata.fetch_layer(
        "rijnland-gemaal", bbox=bbox_vals, refresh=args.refresh,
        sources=sources, cache_dir=CACHE_DIR, timeout=args.timeout)
    loggers = sensors.parse_loggers(loggers_fc)
    gemalen = sensors.parse_points(gemalen_fc)
    print(f"[poc-rijnland-gwt] loggers={len(loggers)} gemalen={len(gemalen)}")

    rain = gwt_rain.fetch_rain(rain_bbox, days_back=args.days,
                               forecast_days=args.forecast_days,
                               cache_dir=RAIN_CACHE_DIR,
                               refresh=args.refresh_rain,
                               timeout=min(args.timeout, 90))
    dump_json(out_dir / "rain.json", rain)
    past_dates = sorted((rain.get("past") or {}).keys())[-args.days:]
    fc_dates = sorted((rain.get("forecast") or {}).keys())[:args.forecast_days]
    if not past_dates or len(fc_dates) < args.forecast_days:
        print("[poc-rijnland-gwt] open-meteo returned too few days",
              file=sys.stderr)
        return 2
    past_rain = rain["past"]

    arch = gwt_archive.load_or_seed(ARCHIVE_PATH, loggers, past_rain,
                                    past_dates, reseed=args.reseed)
    # scope the run to the fetched (AOI) loggers, not the whole archive
    loggers_by_code = {code: arch["loggers"][code]
                       for code in (str(lg["code"]) for lg in loggers)
                       if code in arch["loggers"]}

    forecasts_by_code: dict = {}
    scenario_by_code: dict = {}
    backtests: list = []
    for code, entry in sorted(loggers_by_code.items()):
        depths = [entry.get("days", {}).get(d, {}).get("depth")
                  for d in past_dates]
        rains = [float(past_rain.get(d) or 0.0) for d in past_dates]
        if sum(1 for v in depths if v is not None) < predict.MIN_ROWS:
            continue
        forecasts_by_code[code] = predict.forecast_logger(
            past_dates, depths, rains, fc_dates,
            [float((rain.get("forecast") or {}).get(d) or 0.0)
             for d in fc_dates])
        if args.rain_scenario_mm:
            scenario_by_code[code] = predict.forecast_logger(
                past_dates, depths, rains, fc_dates,
                [float((rain.get("forecast") or {}).get(d) or 0.0)
                 for d in fc_dates],
                scenario_mm=args.rain_scenario_mm)
        bt = predict.backtest_logger(past_dates, depths, rains)
        if bt.get("available"):
            backtests.append({"code": code, **bt})
    print(f"[poc-rijnland-gwt] forecasts={len(forecasts_by_code)} "
          f"backtests={len(backtests)}")

    commands, cmd_summary = triggers.build_commands(
        forecasts_by_code, loggers_by_code, gemalen,
        ingress=args.ingress_depth, drought=args.drought_depth,
        radius_m=args.gemaal_radius_m)
    dump_json(out_dir / "commands.json",
              {"version": "poc-rijnland-gwt-commands/0.1", "runId": run_id,
               "thresholds": {"ingress": args.ingress_depth,
                              "drought": args.drought_depth},
               "gemaalRadiusM": args.gemaal_radius_m,
               "commands": commands, "summary": cmd_summary})
    dump_json(out_dir / "forecast.json",
              {"runId": run_id, "unit": "m-onder-maaiveld",
               "forecastDates": fc_dates, "forecasts": forecasts_by_code})

    mean_by_date = _mean_depth_by_date(forecasts_by_code)

    run_doc: dict = {
        "runId": run_id,
        "generatedAt": ts,
        "mvpQuestion": MVP_QUESTION,
        "bbox": None if args.full else bbox,
        "nLoggers": len(forecasts_by_code),
        "nGemalen": len(gemalen),
        "forecastDates": fc_dates,
        "forecastSummary": {"days": _merge_day_summary(
            cmd_summary["days"], mean_by_date)},
        "commandSummary": cmd_summary,
        "backtests": backtests,
        "commands": commands,
        "seedFormula": arch.get("seedFormula"),
    }

    scenario_doc = None
    if args.rain_scenario_mm:
        scen_commands, scen_summary = triggers.build_commands(
            scenario_by_code, loggers_by_code, gemalen,
            ingress=args.ingress_depth, drought=args.drought_depth,
            radius_m=args.gemaal_radius_m)
        dump_json(out_dir / "commands-scenario.json",
                  {"runId": run_id, "scenarioMm": args.rain_scenario_mm,
                   "commands": scen_commands, "summary": scen_summary})
        scen_mean = _mean_depth_by_date(scenario_by_code)
        scenario_doc = {
            "commandSummary": {"days": _merge_day_summary(
                scen_summary["days"], scen_mean)},
            "commands": scen_commands,
        }
        run_doc["scenario"] = scenario_doc
        run_doc["scenarioMm"] = args.rain_scenario_mm

    hexmap_name = None
    if not args.no_h3:
        def _h3_call(process_id, inputs):
            return h3step.call(process_id, inputs, refresh=args.refresh)

        try:
            import h3 as h3py

            steps = past_dates[-HISTORY_STEPS:] + fc_dates
            locations = []
            for code, entry in loggers_by_code.items():
                values = [entry.get("days", {}).get(d, {}).get("depth")
                          for d in steps]
                locations.append({"x": entry["x"], "y": entry["y"],
                                  "values": values})
            # Logger→cell directly (h3.latlng_to_cell): the demo-slice
            # loggers form a thin polder corridor, so the PoC-3
            # hull-restricted join collapsed to ~2 res-8 cells and dropped
            # 16 loggers. The bridge stays in for cell geometries.
            n_steps = max(len(l["values"]) for l in locations)
            per_cell: dict = {}
            for loc in locations:
                lat, lon = hexmap_time._to_wgs(loc["x"], loc["y"])
                cell = h3py.latlng_to_cell(lat, lon, args.h3_resolution)
                slots = per_cell.setdefault(cell, [[] for _ in range(n_steps)])
                for t, v in enumerate(loc["values"]):
                    if v is not None:
                        slots[t].append(float(v))
            values = {c: [round(statistics.median(s), 4) if s else None
                          for s in slots]
                      for c, slots in per_cell.items()}
            cells_fc = _h3_call("h3-cells-to-geojson",
                                {"cells": sorted(per_cell)})["features"]
            bundle = {"cells_fc": cells_fc, "values": values,
                      "nSteps": n_steps}
            if bundle["values"]:
                hexmap_name = "gwt-twin-hexmap.html"
                hexmap_time.render_hexmap_time(
                    bundle, steps=steps,
                    title=f"Rijnland GWT twin — {run_id} "
                          f"(rood = ondiep / indringingsrisico)",
                    value_label="Grondwaterdiepte", unit="m -mv",
                    vmin=gwt_archive.DEPTH_MIN, vmax=gwt_archive.DEPTH_MAX,
                    invert=True, out_path=out_dir / hexmap_name)
                run_doc["nCells"] = len(bundle["values"])
        except Exception as exc:  # decision support only
            run_doc.setdefault("degradations", []).append(
                {"kind": "h3-error", "message": str(exc)[:400]})
    run_doc["hexmapName"] = hexmap_name

    dump_json(out_dir / "gwt-twin-report.json", run_doc)
    (out_dir / "gwt-twin-report.html").write_text(
        gwt_report.render_report(run_doc), encoding="utf-8")

    n_on = cmd_summary.get("days", [{}])[-1].get("WaterpumpON", 0) \
        if cmd_summary.get("days") else 0
    print(f"[poc-rijnland-gwt] commands={cmd_summary['totalCommands']} "
          f"gaps={cmd_summary['totalGaps']} ON(last day)={n_on} "
          f"hexmap={hexmap_name or 'skipped'}")
    print(f"[poc-rijnland-gwt] report -> {out_dir / 'gwt-twin-report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
