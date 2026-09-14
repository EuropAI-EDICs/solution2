from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.mcp_servers.catalog_server import mcp as catalog_mcp
from services.mcp_servers.http_transport import build_mcp_http_app

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}

# Port-carrying loopback base_url so the Host header ("127.0.0.1:9999")
# passes the SDK transport-security loopback allowlist ("127.0.0.1:*"
# requires a port; a portless base_url leaves Host "127.0.0.1" -> 421).
LOOPBACK_BASE_URL = "http://127.0.0.1:9999"


@pytest.fixture
def http_client(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "mcp-tok")
    with TestClient(build_mcp_http_app(catalog_mcp), base_url=LOOPBACK_BASE_URL) as client:
        yield client


def test_mcp_http_rejects_anonymous(http_client):
    resp = http_client.post("/mcp", json=INIT)
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_mcp_http_open_by_default(monkeypatch):
    monkeypatch.delenv("NLDT_AUTH_MODE", raising=False)
    with TestClient(build_mcp_http_app(catalog_mcp), base_url=LOOPBACK_BASE_URL) as client:
        resp = client.post("/mcp", json=INIT)
    assert resp.status_code != 401  # auth off: bearer gate passes through


def test_mcp_http_authenticated_reaches_mcp_layer(http_client):
    resp = http_client.post(
        "/mcp",
        json=INIT,
        headers={"Authorization": "Bearer mcp-tok", "Accept": "application/json, text/event-stream"},
    )
    # Host passes the SDK allowlist; 200 = MCP protocol layer answered
    # (SSE body may still carry a JSON-RPC error for the minimal INIT).
    assert resp.status_code == 200
