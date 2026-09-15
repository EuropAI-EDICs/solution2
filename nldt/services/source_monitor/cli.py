"""CLI for source monitor (Kestra-friendly)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from services.source_monitor.run import run_monitor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="nLDT source monitor")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Probe registries and write a change report")
    run_p.add_argument("--mode", choices=["replay", "live"], default="replay")
    run_p.add_argument("--watchlist", type=Path, default=None)
    run_p.add_argument("--fixture-dir", type=Path, default=None)
    run_p.add_argument("--out-dir", type=Path, default=None)
    run_p.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)

    if args.cmd == "run":
        result = run_monitor(
            mode=args.mode,
            watchlist_path=args.watchlist,
            fixture_dir=args.fixture_dir,
            out_dir=args.out_dir,
            timeout=args.timeout,
        )
        print(json.dumps(result, indent=2))
        vr = (result.get("validationReport") or {}).get("verdict")
        if vr == "needs_human":
            return 2
        if result.get("status") != "ok":
            return 1
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
