from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from services.mcp_servers.client import PROCESS_URL

mcp = MCPServer("nldt-process-mcp")


async def _request(method: str, path: str, json_body: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=120.0) as client:
        url = f"{PROCESS_URL.rstrip('/')}{path}"
        if method == "GET":
            resp = await client.get(url)
        else:
            resp = await client.post(url, json=json_body)
        resp.raise_for_status()
        return resp.json()


def _execute_local(process_id: str, inputs: dict[str, Any], backend: str) -> dict[str, Any]:
    from services.process_adapter import jobs as job_store

    return job_store.create_job(process_id, inputs, backend=backend)


@mcp.tool()
async def describe_process(process_id: str) -> str:
    """Get OGC API Processes description for a process id."""
    if os.environ.get("NLDT_OFFLINE") == "1":
        from services.process_adapter.handlers import describe_process as _describe

        return json.dumps(_describe(process_id), indent=2)
    data = await _request("GET", f"/processes/{process_id}")
    return json.dumps(data, indent=2)


@mcp.tool()
async def execute_process(
    process_id: str,
    inputs: dict[str, Any],
    backend: str = "local",
) -> str:
    """Execute a process with inputs."""
    if os.environ.get("NLDT_OFFLINE") == "1":
        data = _execute_local(process_id, inputs, backend)
    else:
        data = await _request(
            "POST",
            f"/processes/{process_id}/execution",
            {"inputs": inputs, "backend": backend},
        )
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
async def get_job_status(job_id: str) -> str:
    """Poll job status and results."""
    if os.environ.get("NLDT_OFFLINE") == "1":
        from services.process_adapter import jobs as job_store

        payload = {
            "status": job_store.get_job(job_id),
            "results": job_store.job_results(job_id),
        }
        return json.dumps(payload, indent=2, default=str)
    status = await _request("GET", f"/jobs/{job_id}")
    results = await _request("GET", f"/jobs/{job_id}/results")
    return json.dumps({"status": status, "results": results}, indent=2, default=str)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
