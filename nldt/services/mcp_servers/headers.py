"""Outbound auth headers for MCP servers calling gated nLDT services (BK-1)."""

from __future__ import annotations

import os


def mcp_auth_headers() -> dict[str, str]:
    static = os.environ.get("NLDT_MCP_BEARER_TOKEN", "").strip()
    if static:
        return {"Authorization": f"Bearer {static}"}
    from services.adapters.keycloak_auth import auth_headers

    return auth_headers()
