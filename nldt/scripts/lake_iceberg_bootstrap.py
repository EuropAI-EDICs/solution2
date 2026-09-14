#!/usr/bin/env python3
"""Bootstrap Iceberg/DuckDB warehouse from lake-inventory.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.lake.iceberg import bootstrap_inventory_iceberg  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--force", action="store_true")
    p.add_argument("--inventory", type=Path, default=None)
    args = p.parse_args()
    meta = bootstrap_inventory_iceberg(inventory_path=args.inventory, force=args.force)
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
