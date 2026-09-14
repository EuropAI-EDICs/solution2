from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from services.adapters.keycloak_auth import auth_headers, is_configured as keycloak_configured

PV_BASE_URL = os.environ.get("NLDT_PV_BASE_URL", "").rstrip("/")
MOCK = os.environ.get("NLDT_PV_MOCK", "true").lower() in ("1", "true", "yes")
EXPORT_PUBLIC_BASE = os.environ.get(
    "NLDT_EXPORT_PUBLIC_BASE", "http://localhost:8084/exports"
)


def available() -> bool:
    return bool(PV_BASE_URL) or MOCK


def _api(path: str) -> str:
    base = PV_BASE_URL.rstrip("/")
    if base.endswith("/api"):
        return f"{base}/{path.lstrip('/')}"
    return f"{base}/api/{path.lstrip('/')}"


def create_data_source(
    *,
    name: str,
    url: str,
    token: str | None = None,
) -> dict[str, Any]:
    if MOCK and not PV_BASE_URL:
        return {"id": f"mock-ds-{uuid4().hex[:8]}", "name": name, "mock": True}

    payload = {
        "name": name,
        "sourceConfiguration": {"type": "EXTERNAL", "url": url, "headers": []},
        "securityConfiguration": {"type": "OTHER", "headers": []},
    }
    headers = {"Content-Type": "application/json", **auth_headers(token)}
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(_api("dataSources"), json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def create_data_layer(
    *,
    name: str,
    data_source_id: str,
    layer_type: str = "SCENARIO",
    token: str | None = None,
) -> dict[str, Any]:
    if MOCK and not PV_BASE_URL:
        return {
            "id": f"mock-dl-{uuid4().hex[:8]}",
            "name": name,
            "dataSource": data_source_id,
            "mock": True,
        }

    payload = {
        "name": name,
        "dataSource": data_source_id,
        "type": layer_type,
        "configuration": {},
    }
    headers = {"Content-Type": "application/json", **auth_headers(token)}
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(_api("dataLayers"), json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def register_geojson_layer(
    *,
    geojson: dict[str, Any],
    name: str,
    export_store: Path,
    token: str | None = None,
) -> dict[str, Any]:
    """
    Publish GeoJSON to export store, create P&V dataSource + dataLayer.
    Returns registration metadata including public GeoJSON URL.
    """
    export_store.mkdir(parents=True, exist_ok=True)
    export_id = f"{name.replace(' ', '-').lower()}-{uuid4().hex[:8]}"
    export_path = export_store / f"{export_id}.geojson"
    export_path.write_text(json.dumps(geojson), encoding="utf-8")
    public_url = f"{EXPORT_PUBLIC_BASE.rstrip('/')}/{export_id}.geojson"

    ds = create_data_source(name=f"{name}-source", url=public_url, token=token)
    dl = create_data_layer(
        name=name,
        data_source_id=ds["id"],
        layer_type="SCENARIO",
        token=token,
    )
    return {
        "exportId": export_id,
        "geoJsonUrl": public_url,
        "dataSource": ds,
        "dataLayer": dl,
        "playVisualiseUrl": f"{PV_BASE_URL or 'http://localhost:pv'}/api/dataLayers/{dl['id']}",
        "mock": ds.get("mock", False),
    }
