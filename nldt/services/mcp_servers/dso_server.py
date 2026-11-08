"""nldt-dso-mcp — façade over de dso-kb-processen (spec 2026-11-07).

Zelfde transport/auth als de zusterservers (:8090–8093); streamable-http
draait op :8094. Tools spiegelen de processen 1:1; responses volgen het
poc-server-patroon {tool, processId, jobId, status, outputs, prov}.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from services.mcp_servers.client import PROCESS_URL
from services.mcp_servers.headers import mcp_auth_headers
from services.mcp_servers.dso_tools import DSO_TOOLS

mcp = MCPServer("nldt-dso-mcp")


async def _execute_remote(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{PROCESS_URL.rstrip('/')}/processes/{process_id}/execution",
            json={"inputs": inputs, "backend": "local"},
            headers=mcp_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()


def _execute_local(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    from services.process_adapter import jobs as job_store

    return job_store.create_job(process_id, inputs, backend="local")


async def _run_dso_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    spec = DSO_TOOLS.get(tool_name)
    if spec is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    inputs = {k: v for k, v in arguments.items() if v is not None}
    if os.environ.get("NLDT_OFFLINE") == "1":
        result = _execute_local(spec["process_id"], inputs)
    else:
        result = await _execute_remote(spec["process_id"], inputs)
    payload = {
        "tool": tool_name,
        "processId": spec["process_id"],
        "jobId": result.get("jobId"),
        "status": result.get("status"),
        "outputs": result.get("outputs"),
        "prov": result.get("prov"),
    }
    return json.dumps(payload, indent=2, default=str)


@mcp.tool(name="dso_kb_overview", description=DSO_TOOLS["dso_kb_overview"]["description"])
async def dso_kb_overview() -> str:
    return await _run_dso_tool("dso_kb_overview", {})


@mcp.tool(name="dso_kb_annotations", description=DSO_TOOLS["dso_kb_annotations"]["description"])
async def dso_kb_annotations(
    instrument: str,
    locatie: str | None = None,
    artikel: str | None = None,
    detail: bool = False,
    maxItems: int = 100,
) -> str:
    return await _run_dso_tool(
        "dso_kb_annotations",
        {"instrument": instrument, "locatie": locatie, "artikel": artikel,
         "detail": detail, "maxItems": maxItems},
    )


@mcp.tool(name="dso_kb_document_structure", description=DSO_TOOLS["dso_kb_document_structure"]["description"])
async def dso_kb_document_structure(
    instrument: str,
    locatie: str | None = None,
    wIdPrefix: str | None = None,
    maxItems: int = 100,
) -> str:
    return await _run_dso_tool(
        "dso_kb_document_structure",
        {"instrument": instrument, "locatie": locatie, "wIdPrefix": wIdPrefix, "maxItems": maxItems},
    )


@mcp.tool(name="dso_kb_tpod", description=DSO_TOOLS["dso_kb_tpod"]["description"])
async def dso_kb_tpod(instrument: str, locatie: str | None = None) -> str:
    return await _run_dso_tool("dso_kb_tpod", {"instrument": instrument, "locatie": locatie})


@mcp.tool(name="dso_kb_toets", description=DSO_TOOLS["dso_kb_toets"]["description"])
async def dso_kb_toets(
    instrument: str,
    locatie: str | None = None,
    artikel: str | None = None,
) -> str:
    return await _run_dso_tool(
        "dso_kb_toets", {"instrument": instrument, "locatie": locatie, "artikel": artikel}
    )


@mcp.tool(name="dso_kb_overlap", description=DSO_TOOLS["dso_kb_overlap"]["description"])
async def dso_kb_overlap(
    instrument: str,
    locatie: str | None = None,
    status: str | None = None,
    pagina: int = 1,
) -> str:
    return await _run_dso_tool(
        "dso_kb_overlap",
        {"instrument": instrument, "locatie": locatie, "status": status, "pagina": pagina},
    )


@mcp.tool(name="dso_kb_gios", description=DSO_TOOLS["dso_kb_gios"]["description"])
async def dso_kb_gios(
    instrument: str,
    locatie: str | None = None,
    identificatie: str | None = None,
) -> str:
    return await _run_dso_tool(
        "dso_kb_gios",
        {"instrument": instrument, "locatie": locatie, "identificatie": identificatie},
    )


@mcp.tool(name="dso_kb_point_in_gio", description=DSO_TOOLS["dso_kb_point_in_gio"]["description"])
async def dso_kb_point_in_gio(
    instrument: str,
    x: float,
    y: float,
    identificatie: str | None = None,
) -> str:
    return await _run_dso_tool(
        "dso_kb_point_in_gio",
        {"instrument": instrument, "x": x, "y": y, "identificatie": identificatie},
    )


@mcp.tool(name="dso_kb_refresh", description=DSO_TOOLS["dso_kb_refresh"]["description"])
async def dso_kb_refresh(
    instrument: str,
    locatie: str | None = None,
    metTpod: bool = True,
) -> str:
    return await _run_dso_tool(
        "dso_kb_refresh", {"instrument": instrument, "locatie": locatie, "metTpod": metTpod}
    )


def main() -> None:
    if os.environ.get("NLDT_MCP_TRANSPORT", "stdio") == "streamable-http":
        from services.mcp_servers.http_transport import run_mcp_http

        run_mcp_http(mcp, 8094)
        return
    mcp.run()


if __name__ == "__main__":
    main()
