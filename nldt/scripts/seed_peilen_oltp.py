#!/usr/bin/env python3
"""Seed peilen_measurements OLTP from restricted bronze peilen.json (CDC upstream)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.cdc import cdc_dsn, connect_psycopg, get_profile  # noqa: E402

WORKSPACE = ROOT.parent
DEFAULT_PEILEN = WORKSPACE / "poc-rijnland" / "data" / "peilen" / "peilen.json"


def _stations_from_peilen(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    stations = data.get("stations") or {}
    rows = []
    for sid, meta in stations.items():
        latest = meta.get("latest") or {}
        value = latest.get("value")
        if value is None:
            continue
        fetched = latest.get("fetchedAt") or datetime.now(timezone.utc).isoformat()
        rows.append(
            {
                "peilgebied_id": sid,
                "waterstand_m": float(value),
                "measured_at": fetched,
                "source": "bronze-seed",
            }
        )
    return rows


def seed(dsn: str, peilen_path: Path, *, limit: int | None = None) -> dict:
    rows = _stations_from_peilen(peilen_path)
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        raise SystemExit(f"no stations with latest values in {peilen_path}")

    with connect_psycopg(dsn) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO peilen_measurements (peilgebied_id, waterstand_m, measured_at, source, updated_at)
                    VALUES (%(peilgebied_id)s, %(waterstand_m)s, %(measured_at)s::timestamptz, %(source)s, now())
                    ON CONFLICT (peilgebied_id) DO UPDATE SET
                      waterstand_m = EXCLUDED.waterstand_m,
                      measured_at = EXCLUDED.measured_at,
                      source = EXCLUDED.source,
                      updated_at = now()
                    """,
                    row,
                )
        conn.commit()
    return {"seeded": len(rows), "path": str(peilen_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--peilen", type=Path, default=DEFAULT_PEILEN)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    profile = get_profile(args.profile)
    dsn = cdc_dsn(profile)
    if not dsn:
        print("NLDT_CDC_SOURCE_URL / profile DSN not set", file=sys.stderr)
        return 2
    result = seed(dsn, args.peilen, limit=args.limit)
    print(json.dumps({"ok": True, "profile": profile["name"], **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
