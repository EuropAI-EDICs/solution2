# toolbox-sim/app/cip.py
"""EU LDT City Innovation Planner-sim: co-creatie-scenario's + contributions."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.guards import add_provenance, require_bearer


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim cip", docs_url=None, openapi_url=None)
    add_provenance(app, "cip")
    scenarios: dict[str, dict] = {}
    contributions: dict[str, list[dict]] = {}
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/scenarios")
    def list_scenarios(_: dict = Depends(require_bearer)):
        return {"total": len(scenarios), "data": [dict(s) for s in scenarios.values()]}

    @app.post("/scenarios", status_code=201)
    def create_scenario(payload: dict, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        scen = {"id": f"scen-{seq['n']}", "name": payload.get("name", f"scenario-{seq['n']}"), "contributions": 0}
        scenarios[scen["id"]] = scen
        contributions[scen["id"]] = []
        return scen

    @app.post("/scenarios/{scen_id}/contributions", status_code=201)
    def add_contribution(scen_id: str, payload: dict, _: dict = Depends(require_bearer)):
        if scen_id not in scenarios:
            return JSONResponse(status_code=404, content={"error": "scenario-not-found", "description": scen_id})
        seq["n"] += 1
        contrib = {"id": f"contrib-{seq['n']}", "author": payload.get("author", "anoniem"),
                   "text": payload.get("text", "")}
        contributions[scen_id].append(contrib)
        scenarios[scen_id]["contributions"] = len(contributions[scen_id])
        return contrib

    @app.get("/scenarios/{scen_id}/contributions")
    def list_contributions(scen_id: str, _: dict = Depends(require_bearer)):
        if scen_id not in scenarios:
            return JSONResponse(status_code=404, content={"error": "scenario-not-found", "description": scen_id})
        items = contributions.get(scen_id, [])
        return {"total": len(items), "data": items}

    return app
