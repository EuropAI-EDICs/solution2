# toolbox-sim/app/ucs.py
"""EU LDT Use Cases & Scenarios-sim: experiment-trigger = canonieke replay."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class TriggerIn(BaseModel):
    processId: str
    inputs: dict = {}


def create_app(processes: dict) -> FastAPI:
    app = FastAPI(title="toolbox-sim ucs", docs_url=None, openapi_url=None)
    add_provenance(app, "ucs")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/v1/experiments/trigger-process")
    def trigger(payload: TriggerIn, _: dict = Depends(require_bearer)):
        entry = processes.get(payload.processId)
        if entry is None:
            # Afwijking plan (taak-4/8-precedent): top-level {"error": ...} teruggeven;
            # HTTPException-detail wordt in {"detail": ...} gewrapped, test asserteert r.json()["error"].
            return JSONResponse(status_code=404, content={"error": "process-not-found", "description": payload.processId})
        return {
            "outputs": entry["outputs"],
            "provenance": f"sim-replay://canonical/{entry['runId']}",
        }

    return app
