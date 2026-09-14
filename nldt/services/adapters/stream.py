"""Query CDC-applied lake stream tables (DuckDB) + freshness — no OLTP access."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.cdc import (
    STREAM_VIEWS_PATH,
    load_stream_views,
    silver_peilen_path,
)
from services.lake import DEFAULT_BUCKET, NLDT_ROOT, duckdb_connect, fs_root

ALLOW_RESTRICTED = os.environ.get("NLDT_STREAM_ALLOW_RESTRICTED", "").lower() in (
    "1",
    "true",
    "yes",
)
ROW_LIMIT = int(os.environ.get("NLDT_STREAM_ROW_LIMIT", "100"))


def list_stream_tables(*, include_restricted: bool | None = None) -> list[dict[str, Any]]:
    allow = ALLOW_RESTRICTED if include_restricted is None else include_restricted
    return load_stream_views(include_restricted=allow)


def _resolve_table(name: str, *, include_restricted: bool) -> dict[str, Any]:
    tables = load_stream_views(include_restricted=True)
    for t in tables:
        if t.get("name") == name:
            if (t.get("accessClass") == "restricted") and not include_restricted:
                raise PermissionError(f"restricted stream table: {name}")
            return t
    raise KeyError(f"unknown stream table: {name}")


def _local_path_for(table: dict[str, Any]) -> Path:
    key = table.get("lakeKey") or ""
    path = fs_root() / DEFAULT_BUCKET / key
    if path.is_file():
        return path
    # Fallback known silver path
    if table.get("name") == "rijnland_peilen":
        return silver_peilen_path(table.get("poc") or "rijnland")
    return path


def query_stream_table(
    name: str,
    *,
    limit: int | None = None,
    include_restricted: bool | None = None,
) -> dict[str, Any]:
    allow = ALLOW_RESTRICTED if include_restricted is None else include_restricted
    table = _resolve_table(name, include_restricted=allow)
    path = _local_path_for(table)
    if not path.is_file():
        return {
            "name": name,
            "columns": [],
            "rows": [],
            "rowCount": 0,
            "error": f"table not materialized: {path}",
        }
    lim = min(limit or ROW_LIMIT, ROW_LIMIT)
    con = duckdb_connect()
    cur = con.execute(
        f"SELECT * FROM read_parquet('{path.as_posix()}') LIMIT {int(lim)}"
    )
    cols = [d[0] for d in cur.description]
    rows = [list(r) for r in cur.fetchall()]
    return {
        "name": name,
        "accessClass": table.get("accessClass"),
        "lakeUri": table.get("lakeUri"),
        "columns": cols,
        "rows": rows,
        "rowCount": len(rows),
    }


def get_freshness(name: str = "rijnland_peilen") -> dict[str, Any]:
    allow = ALLOW_RESTRICTED
    try:
        table = _resolve_table(name, include_restricted=allow)
    except PermissionError:
        return {"name": name, "error": "restricted", "freshness_seconds": None}
    path = _local_path_for(table)
    apply_state = NLDT_ROOT / "data" / "cdc-apply-state.json"
    last_apply = None
    if apply_state.is_file():
        last_apply = (json.loads(apply_state.read_text(encoding="utf-8")).get("last") or {}).get(
            "appliedAt"
        )
    max_measured = None
    if path.is_file():
        con = duckdb_connect()
        try:
            max_measured = con.execute(
                f"SELECT max(measured_at) FROM read_parquet('{path.as_posix()}')"
            ).fetchone()[0]
        except Exception:
            max_measured = None
    freshness_seconds = None
    if max_measured is not None:
        if hasattr(max_measured, "timestamp"):
            freshness_seconds = (
                datetime.now(timezone.utc) - max_measured.replace(tzinfo=timezone.utc)
            ).total_seconds()
        else:
            try:
                dt = datetime.fromisoformat(str(max_measured).replace("Z", "+00:00"))
                freshness_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
            except Exception:
                freshness_seconds = None
    return {
        "name": name,
        "path": str(path) if path else None,
        "exists": path.is_file() if path else False,
        "max_measured_at": str(max_measured) if max_measured is not None else None,
        "last_apply_at": last_apply,
        "freshness_seconds": freshness_seconds,
        "streamViewsConfig": str(STREAM_VIEWS_PATH),
    }
