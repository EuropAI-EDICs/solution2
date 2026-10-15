# toolbox-sim/app/ucs.py
"""EU LDT UCS-sim: experiment-trigger (canonieke replay) + authoring + model-executie."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class TriggerIn(BaseModel):
    processId: str
    inputs: dict = {}
    experimentId: str | None = None


class ExperimentIn(BaseModel):
    name: str
    recipeId: str


def create_app(processes: dict, recipes: dict | None = None, ground=None) -> FastAPI:
    app = FastAPI(title="toolbox-sim ucs", docs_url=None, openapi_url=None)
    add_provenance(app, "ucs")
    experiments: dict[str, dict] = {}
    counter = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/v1/experiments", status_code=201)
    def create_experiment(payload: ExperimentIn, _: dict = Depends(require_bearer)):
        recipe = (recipes or {}).get(payload.recipeId)
        if recipe is None:
            return JSONResponse(status_code=404, content={"error": "recipe-not-found", "description": payload.recipeId})
        counter["n"] += 1
        exp = {
            "id": f"exp-{counter['n']}",
            "name": payload.name,
            "recipeId": payload.recipeId,
            "recipeTitle": recipe.get("title", payload.recipeId),
            "runs": [],
        }
        experiments[exp["id"]] = exp
        return exp

    @app.get("/api/v1/experiments")
    def list_experiments(_: dict = Depends(require_bearer)):
        return {"data": [dict(e) for e in experiments.values()]}

    @app.get("/api/v1/experiments/{exp_id}")
    def get_experiment(exp_id: str, _: dict = Depends(require_bearer)):
        exp = experiments.get(exp_id)
        if exp is None:
            return JSONResponse(status_code=404, content={"error": "experiment-not-found", "description": exp_id})
        return exp

    @app.post("/api/v1/experiments/trigger-process")
    def trigger(payload: TriggerIn, _: dict = Depends(require_bearer)):
        from app import algorithms

        if payload.processId in algorithms.MODEL_IDS:
            if ground is None:
                return JSONResponse(status_code=503, content={"error": "missing-ground", "description": "ground niet geladen"})
            try:
                result = algorithms.run_model(payload.processId, payload.inputs, ground)
            except algorithms.MissingGround as exc:
                return JSONResponse(status_code=503, content={"error": "missing-ground", "description": exc.need})
            except algorithms.BadInput as exc:
                return JSONResponse(status_code=422, content={"error": "bad-input", "description": str(exc)})
        else:
            entry = processes.get(payload.processId)
            if entry is None:
                # Afwijking plan (taak-4/8-precedent): top-level {"error": ...};
                # HTTPException-detail wordt in {"detail": ...} gewrapped.
                return JSONResponse(status_code=404, content={"error": "process-not-found", "description": payload.processId})
            result = {
                "outputs": entry["outputs"],
                "provenance": f"sim-replay://canonical/{entry['runId']}",
            }
        exp = experiments.get(payload.experimentId or "")
        if exp is not None:
            exp["runs"].append({"processId": payload.processId, "inputs": payload.inputs})
        return result

    return app
