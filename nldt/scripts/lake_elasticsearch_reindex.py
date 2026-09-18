#!/usr/bin/env python3
"""Reindex lake inventory + timeseries + gold scenarios into Elasticsearch (or mock)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NLDT_ROOT))

from services.elasticsearch.indexer import reindex  # noqa: E402


def main() -> int:
    result = reindex()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
