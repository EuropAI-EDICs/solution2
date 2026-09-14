from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.common.auth import require_bearer

app = FastAPI(title="nLDT A2A Agent", version="1.0.0", dependencies=[Depends(require_bearer)])

AGENT_URL = os.environ.get("NLDT_A2A_URL", "http://localhost:8085/a2a")


def agent_card() -> dict[str, Any]:
    return {
        "name": "nldt-orchestrator",
        "description": "Generic nLDT digital twin orchestrator — recipe discovery and execution",
        "url": AGENT_URL,
        "version": "1.0.0",
        "protocolVersion": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "skills": [
            {
                "id": "execute-recipe",
                "name": "Execute nLDT recipe",
                "description": "Discover and run an nLDT recipe via OGC Processes",
                "tags": ["nldt", "digital-twin", "ogc-processes"],
            },
            {
                "id": "export-3d-context",
                "name": "Export Web 3D Context",
                "description": "Export recipe results as Web3DContext document",
                "tags": ["visualization", "3d-context"],
            },
        ],
        "authentication": {
            "schemes": ["bearer"],
            "note": "EU LDT Identity Management (Keycloak) in production",
        },
    }


class A2ATask(BaseModel):
    skillId: str = Field(..., description="Skill to invoke")
    message: str = Field(..., description="Task description / NL request")
    recipeId: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    autoApproveHitl: bool = False


class A2ATaskResult(BaseModel):
    taskId: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


@app.get("/")
def root() -> dict[str, Any]:
    return {"agentCard": agent_card(), "links": [{"rel": "agent-card", "href": "/agent-card"}]}


@app.get("/agent-card")
def get_agent_card() -> dict[str, Any]:
    return agent_card()


@app.post("/tasks", response_model=A2ATaskResult)
def receive_task(body: A2ATask) -> A2ATaskResult:
    task_id = str(uuid4())
    if body.skillId == "execute-recipe":
        return _execute_recipe_task(task_id, body)
    if body.skillId == "export-3d-context":
        return _export_context_task(task_id, body)
    raise HTTPException(status_code=400, detail=f"unknown skill: {body.skillId}")


def _execute_recipe_task(task_id: str, body: A2ATask) -> A2ATaskResult:
    from agents.orchestrator.graph import build_graph

    if not body.recipeId:
        return A2ATaskResult(taskId=task_id, status="failed", error="recipeId required")

    os.environ.setdefault("NLDT_OFFLINE", "1")
    app_graph = build_graph()
    run_id = task_id[:8]
    try:
        result = app_graph.invoke(
            {
                "run_id": run_id,
                "natural_language_request": body.message,
                "recipe_id": body.recipeId,
                "resolved_inputs": body.inputs,
                "auto_approve_hitl": body.autoApproveHitl,
            },
            config={"configurable": {"thread_id": run_id}},
        )
    except Exception as exc:
        return A2ATaskResult(taskId=task_id, status="failed", error=str(exc))

    if result.get("error"):
        return A2ATaskResult(taskId=task_id, status="failed", error=result["error"])
    return A2ATaskResult(
        taskId=task_id,
        status="completed",
        result={
            "execution": result.get("execution"),
            "validationReport": result.get("validation_report"),
            "explanation": result.get("explanation"),
        },
    )


def _export_context_task(task_id: str, body: A2ATask) -> A2ATaskResult:
    from services.common.schema import validate_instance
    from services.context3d.export_import import export_from_execution

    execution = body.inputs.get("execution")
    if not execution:
        return A2ATaskResult(taskId=task_id, status="failed", error="inputs.execution required")
    try:
        doc = export_from_execution(execution, run_id=task_id[:8], title=body.message)
        validate_instance(doc, "web3d-context.schema.json")
    except Exception as exc:
        return A2ATaskResult(taskId=task_id, status="failed", error=str(exc))
    return A2ATaskResult(taskId=task_id, status="completed", result={"web3dContext": doc})


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_A2A_PORT", "8085"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
