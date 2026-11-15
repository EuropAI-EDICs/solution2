"""Echte MCP-client over streamable-http tegen de eigen loopback-mounts.

Elke call opent een korte sessie (initialize → call_tool) — robuust voor de
demo, geen sessie-hergebruik tussen stappen.
"""

from __future__ import annotations

from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class McpToolError(RuntimeError):
    pass


class McpLoopbackClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def call_tool(self, server: str, tool: str, args: dict[str, Any]) -> str:
        url = f"{self.base_url}/mcp/{server}/mcp"
        async with streamable_http_client(url) as (read, write):
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
