"""MCP-tool fetch_geo_layer via _run_poc_tool, offline (NLDT_OFFLINE=1)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))


def test_fetch_geo_layer_tool_offline_cache(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from services.mcp_servers import poc_server

    raw = asyncio.run(
        poc_server._run_poc_tool("fetch_geo_layer", {"source_id": "agrest-ov-gebied-windenergie"})
    )
    payload = json.loads(raw)
    assert payload["tool"] == "fetch_geo_layer"
    assert payload["processId"] == "fetch-geo-layer"
    assert payload["status"] == "successful"
    assert payload["outputs"]["summary"]["featureCount"] == 44
    assert payload["prov"]["startedAtTime"]
