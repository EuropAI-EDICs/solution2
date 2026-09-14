from __future__ import annotations

import asyncio

from services.mcp_servers.headers import mcp_auth_headers


def test_static_token_preferred(monkeypatch):
    monkeypatch.setenv("NLDT_MCP_BEARER_TOKEN", "mcp-tok")
    assert mcp_auth_headers() == {"Authorization": "Bearer mcp-tok"}


def test_no_config_returns_empty(monkeypatch):
    monkeypatch.delenv("NLDT_MCP_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("KEYCLOAK_URL", raising=False)
    monkeypatch.delenv("KEYCLOAK_HOST", raising=False)
    assert mcp_auth_headers() == {}


def test_process_server_request_sends_header(monkeypatch):
    monkeypatch.setenv("NLDT_MCP_BEARER_TOKEN", "mcp-tok")
    from services.mcp_servers import process_server

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResp()

    monkeypatch.setattr(process_server.httpx, "AsyncClient", FakeClient)
    out = asyncio.run(process_server._request("POST", "/jobs/x", {"a": 1}))
    assert out == {"ok": True}
    assert captured["headers"]["Authorization"] == "Bearer mcp-tok"


def test_catalog_server_get_sends_header(monkeypatch):
    monkeypatch.setenv("NLDT_MCP_BEARER_TOKEN", "mcp-tok")
    from services.mcp_servers import catalog_server

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"features": []}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, headers=None):
            captured["headers"] = headers
            return FakeResp()

    monkeypatch.setattr(catalog_server.httpx, "AsyncClient", FakeClient)
    out = asyncio.run(catalog_server._get("/records"))
    assert out == {"features": []}
    assert captured["headers"]["Authorization"] == "Bearer mcp-tok"
