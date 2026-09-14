#!/usr/bin/env python3
"""Apply bronze CDC Parquet batches → silver peilen_latest via DuckDB MERGE."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.cdc import bronze_cdc_dir, get_profile, silver_peilen_path  # noqa: E402
from services.lake import DEFAULT_BUCKET, duckdb_connect, fs_root  # noqa: E402


def list_batches(cdc_dir: Path, *, since_state: Path) -> list[Path]:
    applied: set[str] = set()
    if since_state.is_file():
        applied = set(json.loads(since_state.read_text(encoding="utf-8")).get("applied") or [])
    files = sorted(cdc_dir.glob("*.parquet"))
    return [p for p in files if p.name not in applied]


def apply_batches(batches: list[Path], silver_path: Path) -> dict:
    if not batches:
        return {"applied": 0, "silver": str(silver_path)}

    silver_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb_connect(readonly=False)
    # Target table (create if missing)
    if silver_path.is_file():
        con.execute(
            f"""
            CREATE OR REPLACE TABLE peilen_latest AS
            SELECT * FROM read_parquet('{silver_path.as_posix()}')
            """
        )
    else:
        con.execute(
            """
            CREATE TABLE peilen_latest (
              peilgebied_id VARCHAR PRIMARY KEY,
              waterstand_m DOUBLE,
              measured_at TIMESTAMP,
              source VARCHAR,
              cdc_lsn BIGINT,
              applied_at TIMESTAMP
            )
            """
        )

    for batch in batches:
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE cdc_batch AS
            SELECT * FROM read_parquet('{batch.as_posix()}')
            """
        )
        # Deletes
        con.execute(
            """
            DELETE FROM peilen_latest
            WHERE peilgebied_id IN (
              SELECT peilgebied_id FROM cdc_batch WHERE op = 'D'
            )
            """
        )
        # Upserts (I/U): last event per peilgebied_id in batch wins
        con.execute(
            """
            CREATE OR REPLACE TEMP TABLE cdc_upsert AS
            SELECT * EXCLUDE (rn) FROM (
              SELECT
                peilgebied_id,
                waterstand_m,
                measured_at,
                source,
                cdc_lsn,
                ROW_NUMBER() OVER (
                  PARTITION BY peilgebied_id ORDER BY cdc_lsn DESC
                ) AS rn
              FROM cdc_batch
              WHERE op IN ('I', 'U')
            ) t WHERE rn = 1
            """
        )
        con.execute(
            """
            DELETE FROM peilen_latest
            WHERE peilgebied_id IN (SELECT peilgebied_id FROM cdc_upsert)
            """
        )
        con.execute(
            """
            INSERT INTO peilen_latest
            SELECT
              peilgebied_id,
              waterstand_m,
              measured_at,
              source,
              cdc_lsn,
              now() AS applied_at
            FROM cdc_upsert
            """
        )

    con.execute(f"COPY peilen_latest TO '{silver_path.as_posix()}' (FORMAT PARQUET)")
    # Also mirror under iceberg/mirrors for dbt
    mirror = fs_root() / DEFAULT_BUCKET / "iceberg" / "mirrors" / "rijnland_peilen_latest.parquet"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY peilen_latest TO '{mirror.as_posix()}' (FORMAT PARQUET)")
    n = con.execute("SELECT count(*) FROM peilen_latest").fetchone()[0]
    return {
        "applied": len(batches),
        "batches": [p.name for p in batches],
        "rows": n,
        "silver": str(silver_path),
        "mirror": str(mirror),
        "appliedAt": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=None)
    args = ap.parse_args()
    profile = get_profile(args.profile)
    poc = profile.get("poc") or "rijnland"
    cdc_dir = bronze_cdc_dir(poc)
    silver = silver_peilen_path(poc)
    state_path = ROOT / "data" / "cdc-apply-state.json"

    batches = list_batches(cdc_dir, since_state=state_path)
    result = apply_batches(batches, silver)
    if batches:
        state = {"applied": []}
        if state_path.is_file():
            state = json.loads(state_path.read_text(encoding="utf-8"))
        applied = set(state.get("applied") or [])
        applied.update(p.name for p in batches)
        state["applied"] = sorted(applied)
        state["last"] = result
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
