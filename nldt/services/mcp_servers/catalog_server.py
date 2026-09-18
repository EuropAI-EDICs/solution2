from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from services.mcp_servers.headers import mcp_auth_headers

CATALOG_URL = os.environ.get("NLDT_CATALOG_URL", "http://localhost:8083")

mcp = MCPServer("nldt-catalog-mcp")


async def _get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{CATALOG_URL}{path}", headers=mcp_auth_headers())
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def search_records(
    q: str | None = None,
    record_type: str | None = None,
) -> str:
    """Search nLDT catalog records by query and optional type (process|recipe|asset|dataset|application)."""
    if os.environ.get("NLDT_OFFLINE") == "1":
        from services.catalog_adapter.seed import find_records

        features = find_records(q=q, record_type=record_type)
    else:
        data = await _get("/records")
        features = data.get("features", [])
        if q:
            ql = q.lower()
            features = [
                f
                for f in features
                if ql in f.get("title", "").lower()
                or ql in json.dumps(f.get("properties", {})).lower()
            ]
        if record_type:
            features = [f for f in features if f.get("type") == record_type]
    return json.dumps(features, indent=2)


@mcp.tool()
async def get_record(record_id: str) -> str:
    """Get a catalog record by id."""
    if os.environ.get("NLDT_OFFLINE") == "1":
        from services.catalog_adapter.seed import find_records

        for rec in find_records():
            if rec["id"] == record_id:
                return json.dumps(rec, indent=2)
        raise ValueError(f"Record not found: {record_id}")
    data = await _get(f"/records/{record_id}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def list_processes() -> str:
    """List process records in the catalog."""
    if os.environ.get("NLDT_OFFLINE") == "1":
        from services.catalog_adapter.seed import find_records

        items = find_records(record_type="process")
        return json.dumps({"processes": items}, indent=2)
    data = await _get("/processes")
    return json.dumps(data, indent=2)


@mcp.tool()
async def search_lake_datasets(
    poc: str | None = None,
    zone: str | None = None,
    accessClass: str | None = None,
    q: str | None = None,
    include_restricted: bool = False,
) -> str:
    """Discover PoC data lake datasets. Restricted assets filtered unless include_restricted=true."""
    from services.catalog_adapter.seed import find_lake_datasets

    features = find_lake_datasets(
        poc=poc,
        zone=zone,
        access_class=accessClass,
        q=q,
        include_restricted=include_restricted,
    )
    return json.dumps(features, indent=2)


@mcp.tool()
async def search_lake_elasticsearch(
    q: str,
    poc: str | None = None,
    kind: str | None = None,
    variable: str | None = None,
    size: int = 20,
) -> str:
    """Full-text lake discovery via Elasticsearch (or in-memory mock). kinds: dataset|timeseries_series|scenario_gold."""
    from services.elasticsearch import search_lake

    hits = search_lake(q, poc=poc, kind=kind, variable=variable, size=size)
    return json.dumps(hits, indent=2)


@mcp.tool()
async def get_lake_manifest(
    record_id: str | None = None,
    lake_uri: str | None = None,
    include_restricted: bool = False,
) -> str:
    """Get lake inventory manifest (lakeUri, sha256, accessClass). Provide record_id or lake_uri."""
    from services.catalog_adapter.seed import get_lake_manifest as _get_manifest

    manifest = _get_manifest(
        record_id=record_id,
        lake_uri=lake_uri,
        include_restricted=include_restricted,
    )
    if manifest is None:
        return json.dumps({"error": "not_found_or_restricted"}, indent=2)
    return json.dumps(manifest, indent=2)


@mcp.tool()
async def list_poc_capabilities() -> str:
    """List PoC processes and recipes (tags poc-*) for scenario/QA orchestration."""
    from services.catalog_adapter.seed import find_poc_capabilities

    return json.dumps(find_poc_capabilities(), indent=2)


def main() -> None:
    if os.environ.get("NLDT_MCP_TRANSPORT", "stdio") == "streamable-http":
        from services.mcp_servers.http_transport import run_mcp_http

        run_mcp_http(mcp, 8090)
        return
    mcp.run()


if __name__ == "__main__":
    main()
