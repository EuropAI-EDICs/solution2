"""Streamable-HTTP transport for nLDT MCP servers behind the shared bearer gate.

Dockerised clients (n8n/OpenWebUI in GovChat-NL) cannot spawn stdio servers;
NLDT_MCP_TRANSPORT=streamable-http serves the same MCPServer over HTTP.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.mcpserver import MCPServer


def build_mcp_http_app(server: MCPServer, host: str | None = None) -> Any:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from starlette.requests import Request

    from services.common.auth import require_bearer

    # Forward the bind host to the SDK: loopback keeps the SDK's
    # DNS-rebinding allowlist (loopback-only Host headers), while a
    # non-loopback bind such as 0.0.0.0 (Docker clients reaching us via
    # host.docker.internal) leaves the allowlist off so their Host headers
    # reach the mounted MCP app, which sits behind our own bearer gate.
    bind_host = host if host is not None else os.environ.get("NLDT_MCP_HTTP_HOST", "127.0.0.1")
    mcp_app = server.streamable_http_app(host=bind_host)  # POST /mcp; creates the session manager

    @asynccontextmanager
    async def _lifespan(app: Any) -> Any:
        # Mounted sub-apps never receive ASGI lifespan events, so the MCP
        # session manager (exposed by MCPServer for exactly this FastAPI
        # mounting case) must be started from the parent app's lifespan.
        async with server.session_manager.run():
            yield

    app: Any = FastAPI(title=f"{server.name}-http", version="1.0.0", lifespan=_lifespan)

    @app.middleware("http")
    async def _bearer_gate(request: Request, call_next: Any) -> Any:
        # FastAPI dependency injection does not cover mounted ASGI apps,
        # so the shared bearer gate runs as middleware in front of the
        # mounted MCP app (same 401/WWW-Authenticate shape as the services).
        try:
            await require_bearer(request)
        except HTTPException as exc:
            return JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers=exc.headers,
            )
        return await call_next(request)

    app.mount("/", mcp_app)
    return app


def run_mcp_http(server: MCPServer, default_port: int) -> None:
    import uvicorn

    host = os.environ.get("NLDT_MCP_HTTP_HOST", "127.0.0.1")
    uvicorn.run(
        build_mcp_http_app(server, host=host),
        host=host,
        port=int(os.environ.get("NLDT_MCP_HTTP_PORT", str(default_port))),
    )
