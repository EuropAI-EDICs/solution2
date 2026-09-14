#!/usr/bin/env python3
"""Sync PoC filesystem assets into the nLDT data lake (fs or S3/MinIO)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.lake.sync import run_sync, write_sync_report  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--poc",
        action="append",
        dest="pocs",
        choices=["utrecht", "breda", "eindhoven", "rijnland"],
        help="PoC to sync (repeatable). Default: utrecht + breda",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args()
    summary = run_sync(pocs=args.pocs, dry_run=args.dry_run)
    path = write_sync_report(summary, args.report)
    print(
        json.dumps(
            {
                "count": summary["count"],
                "uploaded": summary["uploaded"],
                "skipped": summary["skipped"],
                "report": str(path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
