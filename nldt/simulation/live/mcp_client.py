"""Echte MCP-client over streamable-http tegen de eigen loopback-mounts.

Elke call opent een korte sessie (initialize → call_tool) — robuust voor de
demo, geen sessie-hergebruik tussen stappen.
"""

from __future__ import annotations

from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# De SDK-cap op één SSE-event is 1 MB (DEFAULT_MAX_SSE_EVENT_SIZE) — te klein
# voor de inline-lagen: de utrecht-chain haalt zones.geojson (7,4 MB) op en
# het JSON-RPC-antwoord spiegelt de payload (text + structuredContent), zodat
# het event ~15 MB is (gemeten). Loopback tegen de eigen mounts = vertrouwd;
# 64 MB dekt het slechtste geval binnen de run_artifact-cap (10 MB artifact
# ≈ 20 MB event) met ruime marge.
_MAX_SSE_EVENT_SIZE = 64 * 1024 * 1024


class McpToolError(RuntimeError):
    pass


class McpLoopbackClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def call_tool(self, server: str, tool: str, args: dict[str, Any]) -> str:
        url = f"{self.base_url}/mcp/{server}/mcp"
        async with streamable_http_client(url, max_sse_event_size=_MAX_SSE_EVENT_SIZE) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, args)
        if getattr(result, "isError", False):
            raise McpToolError(f"{server}.{tool} mislukt: {result.content}")
        for block in result.content or []:
            text = getattr(block, "text", None)
            if text is not None:
                return text
        raise McpToolError(f"{server}.{tool}: geen tekst-resultaat")
