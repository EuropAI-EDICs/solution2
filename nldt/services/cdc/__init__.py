"""CDC helpers for nLDT lake pipeline (Postgres outbox → bronze → silver)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from services.lake import DEFAULT_BUCKET, NLDT_ROOT, fs_root

PROFILES_PATH = NLDT_ROOT / "data" / "stream-cdc-profiles.json"
STREAM_VIEWS_PATH = NLDT_ROOT / "data" / "stream-views.json"
WATERMARK_PATH = NLDT_ROOT / "data" / "cdc-watermarks.json"


def load_profiles() -> dict[str, Any]:
    return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))


def get_profile(name: str | None = None) -> dict[str, Any]:
    data = load_profiles()
    key = name or os.environ.get("NLDT_CDC_PROFILE") or data.get("defaultProfile") or "local-compose"
    profiles = data.get("profiles") or {}
    if key not in profiles:
        raise KeyError(f"unknown CDC profile: {key}")
    return {"name": key, **profiles[key]}


def cdc_dsn(profile: dict[str, Any] | None = None) -> str:
    profile = profile or get_profile()
    env_name = profile.get("dsnEnv") or "NLDT_CDC_SOURCE_URL"
    return os.environ.get(env_name) or profile.get("defaultDsn") or ""


def bronze_cdc_dir(poc: str = "rijnland") -> Path:
    return fs_root() / DEFAULT_BUCKET / "bronze" / poc / "cdc" / "peilen"


def silver_peilen_path(poc: str = "rijnland") -> Path:
    return fs_root() / DEFAULT_BUCKET / "silver" / poc / "peilen_latest" / "peilen_latest.parquet"


def load_watermarks() -> dict[str, Any]:
    if WATERMARK_PATH.is_file():
        return json.loads(WATERMARK_PATH.read_text(encoding="utf-8"))
    return {}


def save_watermarks(data: dict[str, Any]) -> None:
    WATERMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATERMARK_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_stream_views(*, include_restricted: bool = False) -> list[dict[str, Any]]:
    if not STREAM_VIEWS_PATH.is_file():
        return []
    tables = json.loads(STREAM_VIEWS_PATH.read_text(encoding="utf-8")).get("tables") or []
    if include_restricted:
        return tables
    return [t for t in tables if (t.get("accessClass") or "internal") != "restricted"]


def connect_psycopg(dsn: str):
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg required for CDC (pip install psycopg[binary])") from exc
    return psycopg.connect(dsn)
