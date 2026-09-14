from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.mcp_servers.catalog_server import mcp as catalog_mcp
from services.mcp_servers.http_transport import build_mcp_http_app

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}


@pytest.fixture
def http_client(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "mcp-tok")
    with TestClient(build_mcp_http_app(catalog_mcp)) as client:
        yield client


def test_mcp_http_rejects_anonymous(http_client):
    resp = http_client.post("/mcp", json=INIT)
    assert resp.status_code == 401


def test_mcp_http_authenticated_reaches_mcp_layer(http_client):
    resp = http_client.post(
        "/mcp",
        json=INIT,
        headers={"Authorization": "Bearer mcp-tok", "Accept": "application/json, text/event-stream"},
    )
    assert resp.status_code != 401  # 400/406/200 = reached MCP protocol layer
