"""CLI for DONL harvest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from services.donl_harvest.harvest import DEFAULT_WATCHLIST, harvest_datasets, harvest_watchlist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harvest data.overheid.nl into nLDT data lake")
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=DEFAULT_WATCHLIST,
        help="Path to donl-watchlist.json",
    )
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        help="Explicit CKAN package id (repeatable)",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Skip downloading file distributions",
    )
    parser.add_argument(
        "--max-download-mb",
        type=int,
        default=50,
        help="Max bytes per downloadable distribution",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write harvest summary JSON to path",
    )
    args = parser.parse_args(argv)

    max_bytes = args.max_download_mb * 1024 * 1024 if args.max_download_mb else None
    if args.packages:
        summary = harvest_datasets(
            args.packages,
            download_files=not args.metadata_only,
            max_download_bytes=max_bytes,
        )
    else:
        summary = harvest_watchlist(
            args.watchlist,
            download_files=not args.metadata_only,
            max_download_bytes=max_bytes,
        )

    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary.get("errorCount", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
