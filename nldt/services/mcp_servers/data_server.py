from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from services.adapters import data_platform

mcp = MCPServer("nldt-data-mcp")


@mcp.tool()
async def list_entities(
    entity_type: str,
    scope: str | None = None,
    geoproperty: str | None = None,
) -> str:
    """List NGSI-LD entities from Data Platform / broker."""
    entities = data_platform.list_entities(
        entity_type=entity_type,
        scope=scope,
        geoproperty=geoproperty,
    )
    return json.dumps(entities, indent=2)


@mcp.tool()
async def entities_to_geojson(
    entity_type: str,
    scope: str | None = None,
) -> str:
    """Fetch entities and convert to GeoJSON FeatureCollection."""
    from services.hybrid_bridge import fetch_ngsi_as_features

    fc = fetch_ngsi_as_features(entity_type, scope=scope)
    return json.dumps(fc, indent=2)


@mcp.tool()
async def list_scopes() -> str:
    """List JWT context-data and data-query scopes (EU LDT Data Platform)."""
    return json.dumps(data_platform.list_scopes(), indent=2)


@mcp.tool()
async def trino_query(
    sql: str,
    catalog: str | None = None,
    schema: str | None = None,
    row_limit: int | None = None,
) -> str:
    """Read-only SQL query via Trino (EU LDT dq). Row limit enforced."""
    result = data_platform.trino_query(
        sql,
        catalog=catalog,
        schema=schema,
        row_limit=row_limit,
    )
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def list_catalogs() -> str:
    """List Trino catalogs and schemas for planner hints."""
    return json.dumps(data_platform.list_catalogs(), indent=2)


@mcp.tool()
async def list_stream_tables(include_restricted: bool = False) -> str:
    """List CDC-backed lake stream tables (whitelist). Restricted hidden unless allowed."""
    from services.adapters import stream as stream_adapter

    return json.dumps(
        stream_adapter.list_stream_tables(include_restricted=include_restricted),
        indent=2,
    )


@mcp.tool()
async def query_stream_table(
    name: str,
    limit: int | None = None,
    include_restricted: bool = False,
) -> str:
    """Read-only query of a CDC-applied lake stream table (DuckDB/Parquet)."""
    from services.adapters import stream as stream_adapter

    return json.dumps(
        stream_adapter.query_stream_table(
            name, limit=limit, include_restricted=include_restricted
        ),
        indent=2,
        default=str,
    )


@mcp.tool()
async def get_freshness(name: str = "rijnland_peilen") -> str:
    """Freshness of a CDC-applied stream table (max measured_at / last apply)."""
    from services.adapters import stream as stream_adapter

    return json.dumps(stream_adapter.get_freshness(name), indent=2, default=str)


# --- read-only PoC-run-operatie (harness-unificatie M1) ------------------------

from services.process_adapter.poc_readops import inspect_geo_layer as _inspect_geo_layer  # noqa: E402


@mcp.tool()
async def inspect_geo_layer(run_id: str, layer: str) -> str:
    """Read-only: laag-metadata + zones van één zoneId binnen een canonieke PoC-run."""
    return json.dumps(_inspect_geo_layer(run_id, layer), indent=2, default=str)


# --- read-only leerstaat-operatie (decision-trail memory, retrieval v2) --------

from services.memory.store import load_trails  # noqa: E402


@mcp.tool()
async def list_decision_trails(
    status: str | None = None,
    learning_level: str | None = None,
    observation_type: str | None = None,
) -> str:
    """Read-only: decision trails (leerstaat) uit de semantic memory — optioneel gefilterd op status (open|handled), learning_level (operationeel|organisatie|institutioneel) of observation_type (journal_error|hitl_needs_human|ledger_reject|golden_drift)."""
    trails = load_trails()
    if status:
        trails = [t for t in trails if t["status"] == status]
    if learning_level:
        trails = [t for t in trails if t["learningLevel"] == learning_level]
    if observation_type:
        trails = [t for t in trails if t["observation"]["type"] == observation_type]
    return json.dumps({"count": len(trails), "trails": trails}, indent=2, default=str)


def main() -> None:
    if os.environ.get("NLDT_MCP_TRANSPORT", "stdio") == "streamable-http":
        from services.mcp_servers.http_transport import run_mcp_http

        run_mcp_http(mcp, 8092)
        return
    mcp.run()


if __name__ == "__main__":
    main()
