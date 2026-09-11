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
from pathlib import Path

ROOT = Path(__file__).resolve().parent

from rijnland import timeseries_report  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-year", type=int, default=2020)
    ap.add_argument("--to-year", type=int, default=2026)
    ap.add_argument("--parameter", default="CONCTTE|chloride|mg/l")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
