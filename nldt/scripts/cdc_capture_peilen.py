#!/usr/bin/env python3
"""Capture peilen CDC outbox → bronze Parquet batches for the lake pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.cdc import (  # noqa: E402
    bronze_cdc_dir,
    cdc_dsn,
    connect_psycopg,
    get_profile,
    load_watermarks,
    save_watermarks,
)


def _write_batch(rows: list[dict], out_dir: Path) -> Path:
    import duckdb

    out_dir.mkdir(parents=True, exist_ok=True)
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = out_dir / f"{batch_id}.parquet"
    jl = out_dir / f"{batch_id}.jsonl"
    with jl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, default=str) + "\n")
    con = duckdb.connect()
    con.execute(
        f"COPY (SELECT * FROM read_json_auto('{jl.as_posix()}')) "
        f"TO '{dest.as_posix()}' (FORMAT PARQUET)"
    )
    jl.unlink(missing_ok=True)
    return dest


def capture_from_outbox(dsn: str, *, after_lsn: int, limit: int = 10000) -> tuple[list[dict], int]:
    with connect_psycopg(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT cdc_lsn, op, peilgebied_id, waterstand_m,
                       measured_at, source, captured_at
                FROM peilen_cdc_outbox
                WHERE cdc_lsn > %s
                ORDER BY cdc_lsn
                LIMIT %s
                """,
                (after_lsn, limit),
            )
            cols = [d.name for d in cur.description]
            rows = []
            max_lsn = after_lsn
            for tup in cur.fetchall():
                row = dict(zip(cols, tup))
                max_lsn = max(max_lsn, int(row["cdc_lsn"]))
                for k in ("measured_at", "captured_at"):
                    if row.get(k) is not None:
                        row[k] = row[k].isoformat()
                rows.append(row)
    return rows, max_lsn


def capture_fixture(peilen_path: Path) -> list[dict]:
    """Offline CDC-shaped batch from bronze peilen.json (no Postgres)."""
    data = json.loads(peilen_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for i, (sid, meta) in enumerate(sorted((data.get("stations") or {}).items()), start=1):
        latest = meta.get("latest") or {}
        if latest.get("value") is None:
            continue
        rows.append(
            {
                "cdc_lsn": i,
                "op": "I",
                "peilgebied_id": sid,
                "waterstand_m": float(latest["value"]),
                "measured_at": latest.get("fetchedAt") or now,
                "source": "fixture",
                "captured_at": now,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--fixture", type=Path, help="Offline: peilen.json → bronze batch")
    ap.add_argument("--limit", type=int, default=10000)
    args = ap.parse_args()

    profile = get_profile(args.profile)
    poc = profile.get("poc") or "rijnland"
    out_dir = bronze_cdc_dir(poc)

    if args.fixture:
        rows = capture_fixture(args.fixture)
        dest = _write_batch(rows, out_dir)
        print(json.dumps({"ok": True, "mode": "fixture", "rows": len(rows), "path": str(dest)}, indent=2))
        return 0

    dsn = cdc_dsn(profile)
    if not dsn:
        print("CDC DSN not configured (use --fixture for offline)", file=sys.stderr)
        return 2

    marks = load_watermarks()
    key = f"{profile['name']}:peilen"
    after = int(marks.get(key, 0))
    rows, max_lsn = capture_from_outbox(dsn, after_lsn=after, limit=args.limit)
    if not rows:
        print(json.dumps({"ok": True, "mode": "outbox", "rows": 0, "after_lsn": after}, indent=2))
        return 0

    dest = _write_batch(rows, out_dir)
    marks[key] = max_lsn
    save_watermarks(marks)
    print(
        json.dumps(
            {
                "ok": True,
                "mode": "outbox",
                "rows": len(rows),
                "path": str(dest),
                "watermark": max_lsn,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
