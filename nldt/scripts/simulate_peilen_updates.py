#!/usr/bin/env python3
"""Simulate peilen UPDATEs on OLTP to exercise CDC outbox (requires Postgres)."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.cdc import cdc_dsn, connect_psycopg, get_profile  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--n", type=int, default=5, help="Number of random stations to bump")
    ap.add_argument("--delta", type=float, default=0.01)
    args = ap.parse_args()
    profile = get_profile(args.profile)
    dsn = cdc_dsn(profile)
    if not dsn:
        print("CDC DSN not set", file=sys.stderr)
        return 2
    with connect_psycopg(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT peilgebied_id, waterstand_m FROM peilen_measurements")
            rows = cur.fetchall()
            if not rows:
                print("no rows — run seed_peilen_oltp.py first", file=sys.stderr)
                return 1
            sample = random.sample(rows, k=min(args.n, len(rows)))
            for peilgebied_id, waterstand_m in sample:
                cur.execute(
                    """
                    UPDATE peilen_measurements
                    SET waterstand_m = %s, measured_at = now(), updated_at = now(), source = 'simulate'
                    WHERE peilgebied_id = %s
                    """,
                    (float(waterstand_m) + args.delta, peilgebied_id),
                )
        conn.commit()
    print(json.dumps({"ok": True, "updated": len(sample)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
