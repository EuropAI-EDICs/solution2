"""PoC MCP aliases — thin façade over process-mcp for scenario + QA tools."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from services.mcp_servers.client import PROCESS_URL
from services.mcp_servers.poc_tools import POC_TOOLS

mcp = MCPServer("nldt-poc-mcp")


async def _execute_remote(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{PROCESS_URL.rstrip('/')}/processes/{process_id}/execution",
            json={"inputs": inputs, "backend": "local"},
        )
        resp.raise_for_status()
        return resp.json()


def _execute_local(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    from services.process_adapter import jobs as job_store

    return job_store.create_job(process_id, inputs, backend="local")


async def _run_poc_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    spec = POC_TOOLS.get(tool_name)
    if spec is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    process_id = spec["process_id"]
    inputs = {k: v for k, v in arguments.items() if v is not None}
    if os.environ.get("NLDT_OFFLINE") == "1":
        result = _execute_local(process_id, inputs)
    else:
        result = await _execute_remote(process_id, inputs)
    payload = {
        "tool": tool_name,
        "processId": process_id,
        "jobId": result.get("jobId"),
        "status": result.get("status"),
        "outputs": result.get("outputs"),
        "prov": result.get("prov"),
    }
    return json.dumps(payload, indent=2, default=str)


@mcp.tool(name="run_opportunity_map", description=POC_TOOLS["run_opportunity_map"]["description"])
async def run_opportunity_map(
    mode: str = "replay",
    useCase: str | None = None,
    runDir: str | None = None,
) -> str:
    return await _run_poc_tool(
        "run_opportunity_map",
        {"mode": mode, "useCase": useCase, "runDir": runDir},
    )


@mcp.tool(name="propose_scenarios", description=POC_TOOLS["propose_scenarios"]["description"])
async def propose_scenarios(
    baselineRunDir: str,
    author: str = "auto",
    maxScenarios: int = 10,
) -> str:
    return await _run_poc_tool(
        "propose_scenarios",
        {"baselineRunDir": baselineRunDir, "author": author, "maxScenarios": maxScenarios},
    )


@mcp.tool(name="run_scenario_sweep", description=POC_TOOLS["run_scenario_sweep"]["description"])
async def run_scenario_sweep(
    useCase: str,
    baselineRunDir: str | None = None,
    author: str | None = None,
    scenarioSetPath: str | None = None,
    outDir: str | None = None,
    noH3: bool = True,
) -> str:
    return await _run_poc_tool(
        "run_scenario_sweep",
        {
            "useCase": useCase,
            "baselineRunDir": baselineRunDir,
            "author": author,
            "scenarioSetPath": scenarioSetPath,
            "outDir": outDir,
            "noH3": noH3,
        },
    )


@mcp.tool(name="ask_scan", description=POC_TOOLS["ask_scan"]["description"])
async def ask_scan(
    question: str,
    runDir: str | None = None,
    asker: str = "auto",
) -> str:
    return await _run_poc_tool(
        "ask_scan",
        {"question": question, "runDir": runDir, "asker": asker},
    )


@mcp.tool(name="run_value_scan", description=POC_TOOLS["run_value_scan"]["description"])
async def run_value_scan(
    mode: str = "replay",
    runDir: str | None = None,
) -> str:
    return await _run_poc_tool("run_value_scan", {"mode": mode, "runDir": runDir})


@mcp.tool(name="run_crosstrack", description=POC_TOOLS["run_crosstrack"]["description"])
async def run_crosstrack(
    mode: str = "replay",
    runDir: str | None = None,
    outDir: str | None = None,
) -> str:
    return await _run_poc_tool(
        "run_crosstrack",
        {"mode": mode, "runDir": runDir, "outDir": outDir},
    )


@mcp.tool(name="run_peil_conflict", description=POC_TOOLS["run_peil_conflict"]["description"])
async def run_peil_conflict(
    mode: str = "replay",
    runDir: str | None = None,
    outDir: str | None = None,
    bbox: str | None = None,
    noH3: bool | None = None,
) -> str:
    return await _run_poc_tool(
        "run_peil_conflict",
        {"mode": mode, "runDir": runDir, "outDir": outDir, "bbox": bbox, "noH3": noH3},
    )


@mcp.tool(
    name="run_peil_conflict_live",
    description=POC_TOOLS["run_peil_conflict_live"]["description"],
)
async def run_peil_conflict_live(
    mode: str = "replay",
    runDir: str | None = None,
) -> str:
    return await _run_poc_tool(
        "run_peil_conflict_live",
        {"mode": mode, "runDir": runDir},
    )


@mcp.tool(name="run_peil_whatif", description=POC_TOOLS["run_peil_whatif"]["description"])
async def run_peil_whatif(
    delta_m: float,
    layer: str = "boezem",
    limit: int | None = None,
    scenarioId: str = "whatif",
    applyToLake: bool = True,
) -> str:
    return await _run_poc_tool(
        "run_peil_whatif",
        {
            "delta_m": delta_m,
            "layer": layer,
            "limit": limit,
            "scenarioId": scenarioId,
            "applyToLake": applyToLake,
        },
    )


@mcp.tool(name="run_bp2op_transform", description=POC_TOOLS["run_bp2op_transform"]["description"])
async def run_bp2op_transform(
    mode: str = "replay",
    useCase: str = "eindhoven",
    runDir: str | None = None,
    outDir: str | None = None,
) -> str:
    return await _run_poc_tool(
        "run_bp2op_transform",
        {"mode": mode, "useCase": useCase, "runDir": runDir, "outDir": outDir},
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
