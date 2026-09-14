from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from services.common.auth import require_bearer
from services.common.telemetry import init_telemetry, span
from services.process_adapter.handlers import describe_process, list_processes
from services.process_adapter.jobs import create_job, get_job, job_results

app = FastAPI(
    title="nLDT Process Adapter", version="1.0.0", dependencies=[Depends(require_bearer)]
)


class ExecutionRequest(BaseModel):
    inputs: dict[str, Any]
    backend: str = "local"
    response: str = "document"


@app.get("/")
def landing() -> dict[str, Any]:
    return {
        "title": "nLDT OGC API Processes Adapter",
        "description": "Hybrid process facade (local + UCS stub)",
        "links": [
            {"rel": "processes", "href": "/processes"},
            {"rel": "conformance", "href": "/conformance"},
        ],
    }


@app.get("/conformance")
def conformance() -> dict[str, Any]:
    return {
        "conformsTo": [
            "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/core",
        ]
    }


@app.get("/processes")
def processes() -> dict[str, Any]:
    return {"processes": list_processes()}


@app.get("/processes/{process_id}")
def process_description(process_id: str) -> dict[str, Any]:
    try:
        return describe_process(process_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/processes/{process_id}/execution")
def execute(process_id: str, body: ExecutionRequest, request: Request) -> dict[str, Any]:
    init_telemetry("nldt-process-adapter")
    try:
        describe_process(process_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    wallet_claims = getattr(request.state, "wallet_claims", None)
    with span("process.execute", {"process.id": process_id, "backend": body.backend}):
        job = create_job(
            process_id,
            body.inputs,
            backend=body.backend,
            **({"actor": {"executor": wallet_claims}} if wallet_claims else {}),
        )
    return job


@app.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "jobId": job["jobId"],
        "status": job["status"],
        "processId": job["processId"],
        "links": job["links"],
    }


@app.get("/jobs/{job_id}/results")
def results(job_id: str) -> dict[str, Any]:
    res = job_results(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="job not found")
    return res


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_PROCESS_PORT", "8082"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
