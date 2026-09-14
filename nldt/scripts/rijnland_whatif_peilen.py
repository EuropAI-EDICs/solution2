#!/usr/bin/env python3
"""CLI: Rijnland peilen what-if → CDC lake → report (+ peil-conflict replay)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.rijnland_whatif import DEFAULT_ARCHIVE, run_whatif  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", type=Path, help="Scenario JSON file")
    ap.add_argument("--delta-m", type=float, help="Quick scenario: add metres to peilen")
    ap.add_argument("--layer", default="boezem", help="polders|boezem|all")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--id", default="boezem-plus5cm")
    ap.add_argument("--title", default=None)
    ap.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-lake", action="store_true", help="Skip CDC bronze/silver apply")
    ap.add_argument("--no-conflict", action="store_true")
    args = ap.parse_args()

    if args.scenario:
        scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
        if args.limit is not None:
            scenario["limit"] = args.limit
        if args.layer:
            scenario.setdefault("layer", args.layer)
    elif args.delta_m is not None:
        scenario = {
            "id": args.id,
            "title": args.title or f"What-if: {args.layer} {args.delta_m:+} m",
            "description": "Synthetic peilen shift for Rijnland simulation via CDC lake pipeline",
            "delta_m": args.delta_m,
            "layer": args.layer,
            "limit": args.limit,
        }
    else:
        print("Provide --scenario or --delta-m", file=sys.stderr)
        return 2

    result = run_whatif(
        scenario,
        archive_path=args.archive,
        out_dir=args.out,
        apply_to_lake=not args.no_lake,
        attach_conflict_replay=not args.no_conflict,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
