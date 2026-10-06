"""MCP-client: het ENIGE kanaal van de agents naar nldt-capabiliteit (M1).

Harness-doctrine: de agent vraagt operaties aan; de harness (nldt-servers)
houdt credentials, gates en provenance. Geen stille fallback — een
onbereikbare server is een expliciete fout voor het agent-antwoord.

Gebouwd direct op de mcp-SDK 2.x (dezelfde pin als nldt; langchain-mcp-
adapters vereist mcp<2 en is daarmee incompatibel). Een tool-aanroep opent
een korte streamable-HTTP-sessie (initialize + call_tool per keer) — simpel
en robuust voor het PoC-verkeersniveau. Lokaal draait auth standaard op
`off` (NLDT_AUTH_MODE); bij een actieve bearer-gate wordt hier client-side
header-configuratie toegevoegd.
"""
from __future__ import annotations

import os
from typing import Any

from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import Field, create_model

_JSON_TYPES = {"string": str, "integer": int, "number": float, "boolean": bool}


def build_client_config(nldt_base: str | None = None) -> dict[str, dict[str, str]]:
    base = (nldt_base or os.environ.get("NLDT_MCP_BASE", "http://localhost")).rstrip("/")
    return {
        "nldt-catalog": {"transport": "streamable_http", "url": f"{base}:8090/mcp"},
        "nldt-process": {"transport": "streamable_http", "url": f"{base}:8091/mcp"},
        "nldt-data": {"transport": "streamable_http", "url": f"{base}:8092/mcp"},
        "nldt-poc": {"transport": "streamable_http", "url": f"{base}:8093/mcp"},
    }


def _args_model(tool_name: str, schema: dict[str, Any]):
    """JSON-schema → pydantic-model voor StructuredTool (str/int/float/bool/list/dict)."""
    fields: dict[str, Any] = {}
    required = set(schema.get("required", []))
    for prop, spec in (schema.get("properties") or {}).items():
        kind = spec.get("type", "string")
        py_type = {"array": list, "object": dict}.get(kind, _JSON_TYPES.get(kind, str))
        if prop in required:
            fields[prop] = (py_type, Field(..., description=spec.get("description")))
        else:
            fields[prop] = (py_type | None, Field(None, description=spec.get("description")))
    if not fields:
        return None
    return create_model(f"{tool_name}_args", **fields)


async def _with_session(url: str, action):
    async with streamable_http_client(url) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            return await action(session)


def _content_text(result: Any) -> str:
    parts = [getattr(block, "text", None) for block in getattr(result, "content", [])]
    return "\n".join(p for p in parts if p) or "(leeg resultaat)"


def _build_tool(url: str, server_name: str, name: str, description: str, schema: dict[str, Any]) -> StructuredTool:
    label = f"[{server_name}] {description or name}"

    async def _call(**kwargs: Any) -> str:
        async def action(session: ClientSession):
            return await session.call_tool(name, kwargs)

        return _content_text(await _with_session(url, action))

    return StructuredTool(
        name=name,
        description=label,
        args_schema=_args_model(name, schema),
        coroutine=_call,
    )


async def _list_tools(url: str) -> list[tuple[str, str, dict[str, Any]]]:
    async def action(session: ClientSession):
        listed = await session.list_tools()
        # mcp 2.x gebruikt snake_case (input_schema); 1.x camelCase.
        schema = lambda t: getattr(t, "input_schema", None) or getattr(t, "inputSchema", {}) or {}
        return [(t.name, t.description or "", schema(t)) for t in listed.tools]

    return await _with_session(url, action)


async def load_mcp_tools() -> list:
    tools: list = []
    for server_name, entry in build_client_config().items():
        url = entry["url"]
        try:
            discovered = await _list_tools(url)
        except Exception as exc:
            raise RuntimeError(
                f"nldt MCP-server '{server_name}' onbereikbaar op {url}: {exc}"
            ) from exc
        for name, description, schema in discovered:
            tools.append(_build_tool(url, server_name, name, description, schema))
    return tools
