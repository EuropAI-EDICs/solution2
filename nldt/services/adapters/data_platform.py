from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import httpx

from services.adapters.keycloak_auth import auth_headers, is_configured as keycloak_configured

NGSI_LD_URL = os.environ.get("NLDT_NGSI_LD_URL", "").rstrip("/")
DATA_PLATFORM_URL = os.environ.get("NLDT_DATA_PLATFORM_URL", "").rstrip("/")
TRINO_URL = os.environ.get("NLDT_TRINO_URL", "https://dq.ldt.local").rstrip("/")
NGSI_TENANT = os.environ.get("NLDT_NGSI_TENANT", os.environ.get("NGSILD-Tenant", "ldt"))
MOCK = os.environ.get("NLDT_DATA_PLATFORM_MOCK", "true").lower() in ("1", "true", "yes")
TRINO_ROW_LIMIT = int(os.environ.get("NLDT_TRINO_ROW_LIMIT", "100"))
TRINO_TIMEOUT_S = float(os.environ.get("NLDT_TRINO_TIMEOUT_S", "30"))


def available() -> bool:
    return bool(NGSI_LD_URL or DATA_PLATFORM_URL) or MOCK


def list_entities(
    *,
    entity_type: str,
    scope: str | None = None,
    geoproperty: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if MOCK and not NGSI_LD_URL and not DATA_PLATFORM_URL:
        return _mock_entities(entity_type)

    if DATA_PLATFORM_URL:
        return _list_via_ucs_proxy(entity_type, scope, geoproperty, limit)
    return _list_via_broker(entity_type, geoproperty, limit)


def get_entity(entity_id: str, *, scope: str | None = None) -> dict[str, Any]:
    if MOCK and not NGSI_LD_URL and not DATA_PLATFORM_URL:
        return {"id": entity_id, "type": "MockEntity", "mock": True}

    if DATA_PLATFORM_URL:
        params: dict[str, str] = {"scope": scope or "urn:ngsi-ld:scope:default"}
        headers = auth_headers()
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{DATA_PLATFORM_URL}/api/v1/data-platform/entities/{entity_id}",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            body = resp.json()
            return body.get("data", body)

    headers = {"NGSILD-Tenant": NGSI_TENANT, **auth_headers()}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{NGSI_LD_URL}/ngsi-ld/v1/entities/{entity_id}",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


def entities_to_geojson(entities: list[dict[str, Any]]) -> dict[str, Any]:
    features = []
    for ent in entities:
        geom = _extract_geometry(ent)
        if not geom:
            continue
        features.append(
            {
                "type": "Feature",
                "id": ent.get("id"),
                "properties": {"type": ent.get("type"), "source": "ngsi-ld"},
                "geometry": geom,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _list_via_broker(
    entity_type: str, geoproperty: str | None, limit: int
) -> list[dict[str, Any]]:
    if not NGSI_LD_URL:
        raise RuntimeError("NLDT_NGSI_LD_URL not configured")
    params: dict[str, Any] = {"type": entity_type, "limit": limit}
    if geoproperty:
        params["geoproperty"] = geoproperty
    headers = {"NGSILD-Tenant": NGSI_TENANT, **auth_headers()}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{NGSI_LD_URL}/ngsi-ld/v1/entities", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("entities", [])


def _list_via_ucs_proxy(
    entity_type: str,
    scope: str | None,
    geoproperty: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "scope": scope or "urn:ngsi-ld:scope:default",
        "type": entity_type,
        "limit": limit,
    }
    if geoproperty:
        params["geoproperty"] = geoproperty
    headers = auth_headers()
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{DATA_PLATFORM_URL}/api/v1/data-platform/entities",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data", body)
        if isinstance(data, dict) and "entities" in data:
            return data["entities"]
        return data if isinstance(data, list) else []


def _extract_geometry(entity: dict[str, Any]) -> dict[str, Any] | None:
    for key, val in entity.items():
        if key in ("id", "type", "@context"):
            continue
        if isinstance(val, dict) and val.get("type") == "GeoProperty":
            return val.get("value")
        if isinstance(val, dict) and val.get("type") in ("Point", "Polygon", "MultiPolygon", "LineString"):
            return val
    loc = entity.get("location")
    if isinstance(loc, dict) and loc.get("type") == "GeoProperty":
        return loc.get("value")
    return None


def _mock_entities(entity_type: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"urn:ngsi-ld:{entity_type}:mock-001",
            "type": entity_type,
            "location": {
                "type": "GeoProperty",
                "value": {"type": "Point", "coordinates": [5.12, 52.09]},
            },
            "mock": True,
        }
    ]


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


def list_scopes(*, token: str | None = None) -> list[dict[str, str]]:
    """Extract context-data and data-query scopes from JWT groups."""
    if MOCK and not keycloak_configured() and not token:
        return [
            {"scope": "urn:ngsi-ld:scope:default", "role": "User", "plane": "context-data"},
            {"scope": "timescaledb", "role": "User", "plane": "data-query"},
        ]
    tok = token
    if not tok and is_configured():
        from services.adapters.keycloak_auth import get_service_token

        tok = get_service_token()
    if not tok:
        return []
    payload = _decode_jwt_payload(tok)
    groups = payload.get("groups") or []
    scopes: list[dict[str, str]] = []
    for group in groups:
        g = str(group)
        if g.startswith("/context-data/"):
            parts = g.strip("/").split("/")
            if len(parts) >= 3:
                scopes.append(
                    {"scope": parts[1], "role": parts[2], "plane": "context-data"}
                )
        elif g.startswith("/data-query/"):
            parts = g.strip("/").split("/")
            if len(parts) >= 3:
                scopes.append(
                    {"scope": parts[1], "role": parts[2], "plane": "data-query"}
                )
    return scopes


def _assert_readonly_sql(sql: str) -> None:
    normalized = re.sub(r"\s+", " ", sql.strip().lower())
    if not normalized.startswith("select") and not normalized.startswith("show") and not normalized.startswith("describe"):
        raise ValueError("Only read-only SELECT/SHOW/DESCRIBE queries are allowed")
    forbidden = (" insert ", " update ", " delete ", " drop ", " create ", " alter ", " truncate ")
    padded = f" {normalized} "
    for word in forbidden:
        if word in padded:
            raise ValueError(f"Forbidden SQL keyword in query: {word.strip()}")


def trino_query(
    sql: str,
    *,
    catalog: str | None = None,
    schema: str | None = None,
    row_limit: int | None = None,
) -> dict[str, Any]:
    """Execute read-only SQL against Trino (EU LDT Data Platform dq)."""
    _assert_readonly_sql(sql)
    limit = row_limit if row_limit is not None else TRINO_ROW_LIMIT
    if MOCK and not os.environ.get("NLDT_TRINO_URL"):
        return {
            "columns": ["catalog", "schema", "table"],
            "rows": [["timescaledb", "public", "mock_table"]],
            "rowCount": 1,
            "mock": True,
        }

    headers = {
        "X-Trino-User": os.environ.get("NLDT_TRINO_USER", "nldt-agent"),
        **auth_headers(),
    }
    if catalog:
        headers["X-Trino-Catalog"] = catalog
    if schema:
        headers["X-Trino-Schema"] = schema

    with httpx.Client(timeout=TRINO_TIMEOUT_S, verify=False) as client:
        resp = client.post(
            f"{TRINO_URL}/v1/statement",
            content=sql,
            headers={**headers, "Content-Type": "text/plain"},
        )
        resp.raise_for_status()
        body = resp.json()
        columns = [c.get("name") for c in body.get("columns") or []]
        rows: list[list[Any]] = []
        next_uri = body.get("nextUri")
        while next_uri and len(rows) < limit:
            poll = client.get(next_uri, headers=headers)
            poll.raise_for_status()
            chunk = poll.json()
            for row in chunk.get("data") or []:
                rows.append(row)
                if len(rows) >= limit:
                    break
            next_uri = chunk.get("nextUri") if len(rows) < limit else None
        return {"columns": columns, "rows": rows[:limit], "rowCount": len(rows[:limit])}


def list_catalogs() -> list[dict[str, Any]]:
    """List Trino catalogs and schemas (planner hints)."""
    if MOCK and not os.environ.get("NLDT_TRINO_URL"):
        return [
            {"catalog": "timescaledb", "schemas": ["public", "mtvalencia"]},
            {"catalog": "hive", "schemas": ["default"]},
        ]
    result = trino_query("SHOW SCHEMAS FROM timescaledb", row_limit=50)
    schemas = [row[0] if row else "" for row in result.get("rows") or []]
    catalogs = [{"catalog": "timescaledb", "schemas": schemas}]
    try:
        hive = trino_query("SHOW SCHEMAS FROM hive", row_limit=50)
        catalogs.append(
            {
                "catalog": "hive",
                "schemas": [row[0] if row else "" for row in hive.get("rows") or []],
            }
        )
    except Exception:
        pass
    return catalogs
