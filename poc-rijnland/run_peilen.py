#!/usr/bin/env python3
"""PoC-3 fase 2d: waterpeilen-tijdreeks (polders + boezem, mNAP).

Renders the growing peil archive (``data/peilen/peilen.json``, seeded by
``scripts/fetch_peilen.py`` — Rijnland exposes only current values plus a
~12-day chart window, so the archive starts at first fetch and grows with
every re-run) as one offline page in the timeseries style: station
selector, daily median per station with min–max band, mediaan-polders and
mediaan-boezem aggregates, and a play cursor.

Usage:
    nldt/.venv/bin/python poc-rijnland/run_peilen.py
    nldt/.venv/bin/python poc-rijnland/run_peilen.py --refresh   # her-fetch eerst
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POC_ROOT = ROOT.parent / "poc"
for _p in (str(ROOT), str(POC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rijnland import hexmap_time, timeseries_report  # noqa: E402

ARCHIVE = ROOT / "data" / "peilen" / "peilen.json"

#: aggregates shown first in the selector
AGG_POLDERS = "AGGREGAAT|mediaan-polders|mNAP"
AGG_BOEZEM = "AGGREGAAT|mediaan-boezem|mNAP"


def build_fixture(archive: dict) -> dict:
    """Archive → timeseries fixture (rows keyed per day, y = mNAP)."""
    series: dict = {}
    labels: dict = {}
    per_layer_days: dict = {"polders": {}, "boezem": {}}

    for fid, rec in (archive.get("stations") or {}).items():
        rows = []
        for day, d in sorted((rec.get("days") or {}).items()):
            rows.append({"ym": day, "n": d["n"], "nLocations": 1,
                         "median": d["median"],
                         "p25": d["min"], "p75": d["max"]})
        if not rows:
            continue
        series[fid] = rows
        labels[fid] = (f"{rec.get('name') or fid} "
                       f"({rec.get('layer')})")
        for r in rows:
            per_layer_days.setdefault(rec.get("layer", "polders"), {}
                                      ).setdefault(r["ym"], []
                                                   ).append(r["median"])

    for agg_key, layer, label in ((AGG_POLDERS, "polders", "Mediaan alle polderstations"),
                                  (AGG_BOEZEM, "boezem", "Mediaan alle boezemstations")):
        days = per_layer_days.get(layer) or {}
        rows = []
        for day, vals in sorted(days.items()):
            if len(vals) < 5:
                continue  # te weinig stations die dag
            qs = statistics.quantiles(vals, n=4)
            rows.append({"ym": day, "n": len(vals), "nLocations": len(vals),
                         "median": round(statistics.median(vals), 4),
                         "p25": round(qs[0], 4), "p75": round(qs[2], 4)})
        if rows:
            series[agg_key] = rows
            labels[agg_key] = label
    return {"series": series, "labels": labels,
            "rawRowsPerYear": {"2026": sum(len(v) for v in series.values())}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch stations first (grows the archive)")
    ap.add_argument("--no-animate", action="store_true",
                    help="skip the animated hex map (hexmap-peilen-tijd.html)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.refresh or not ARCHIVE.is_file():
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "fetch_peilen.py")],
            check=False)
        if r.returncode != 0 and not ARCHIVE.is_file():
            raise SystemExit("[peilen] fetch failed and no archive present")

    archive = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    fixture = build_fixture(archive)
    if not fixture["series"]:
        raise SystemExit("[peilen] archive has no series")

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out or ROOT / "runs" / f"{ts}-peilen"
    out_dir.mkdir(parents=True, exist_ok=True)

    n_stations = len([k for k in fixture["series"] if not k.startswith("AGG")])
    default = AGG_POLDERS if AGG_POLDERS in fixture["series"] \
        else sorted(fixture["series"])[0]
    first = min(r["ym"] for s in fixture["series"].values() for r in s)
    last = max(r["ym"] for s in fixture["series"].values() for r in s)

    def _nl(iso: str) -> str:
        d = _dt.date.fromisoformat(iso)
        return f"{d.day} {_dt.date(2000, d.month, 1).strftime('%b')} {d.year}"
    html = timeseries_report.render_timeseries(
        fixture,
        title="Waterpeilen Rijnland — polders & boezem (mNAP)",
        default_parameter=default,
        labels=fixture["labels"],
        subtitle_override=(f"venster {_nl(first)} t/m {_nl(last)} · "
                           f"{n_stations} stations · archief groeit per "
                           "her-fetch (±12 dagen per run)"),
        show_season=False,
        out_path=out_dir / "peilen.html")
    (out_dir / "peilen.json").write_text(json.dumps({
        "archive": str(ARCHIVE.relative_to(ROOT)),
        "stations": n_stations,
        "window": [first, last],
        "lastFetchedAt": archive.get("lastFetchedAt"),
        "computedBy": "poc-rijnland-peilen/0.1",
    }, indent=1) + "\n", encoding="utf-8")
    print(f"[peilen] {out_dir / 'peilen.html'} ({len(html):,} bytes; "
          f"{n_stations} stations, venster {first} … {last})")

    if not args.no_animate:
        try:
            from pipeline import h3step

            days_all = sorted({d for r in archive["stations"].values()
                               for d in (r.get("days") or {})})
            locs = []
            devs_all = []
            for rec in archive["stations"].values():
                days = rec.get("days") or {}
                if not days:
                    continue
                med = statistics.median([d["median"] for d in days.values()])
                values = [round((days[d]["median"] - med) * 100.0, 1)
                          if d in days else None for d in days_all]
                devs_all += [v for v in values if v is not None]
                locs.append({"x": rec["x"], "y": rec["y"], "values": values})
            scale = statistics.quantiles([abs(v) for v in devs_all],
                                         n=10)[-1] or 1.0
            bundle = hexmap_time.build_cell_steps(
                locations=locs, resolution=8,
                call=lambda pid, inputs: h3step.call(pid, inputs))
            if bundle:
                steps = [_dt.date.fromisoformat(d).strftime("%d %b")
                         for d in days_all]
                anim = hexmap_time.render_hexmap_time(
                    bundle, steps=steps,
                    title=("Waterpeil-afwijking per cel t.o.v. mediane peil "
                           f"(cm) — {steps[0]} t/m {steps[-1]}"),
                    value_label="Afwijking t.o.v. mediane peil (cm)",
                    unit="cm",
                    vmin=-scale, vmax=scale,
                    stops=[(0.0, "Ver lager (droger)"),
                           (0.5, "Op mediaan"),
                           (1.0, "Ver hoger (natter)")],
                    out_path=out_dir / "hexmap-peilen-tijd.html")
                print(f"[peilen] {out_dir / 'hexmap-peilen-tijd.html'} "
                      f"({len(anim):,} bytes, {bundle['nSteps']} dagen)")
        except Exception as exc:  # animatie is decision support
            print(f"[peilen] WARNING hexmap-animatie overgeslagen: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
