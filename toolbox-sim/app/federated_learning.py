# toolbox-sim/app/federated_learning.py
"""EU LDT Federated Learning-sim: rounds met deterministische gemeente-aggregaten."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.guards import add_provenance, require_bearer


def _aggregate(peilen_instances: list[dict] | None, tag: str) -> dict:
    if peilen_instances:
        values = [float(i["value"]) for i in peilen_instances]
        return {"mean_waterstand_m": round(sum(values) / len(values), 3), "n_peilgebieden": len(values)}
    return {"mean_waterstand_m": 0.0, "n_peilgebieden": 0, "syntheticSeed": True, "seed": str(sum(map(ord, tag)))}


def create_app(peilen_instances: list[dict] | None) -> FastAPI:
    app = FastAPI(title="toolbox-sim federated-learning", docs_url=None, openapi_url=None)
    add_provenance(app, "federated-learning")
    rounds: dict[str, dict] = {}
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/rounds", status_code=201)
    def create_round(payload: dict, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        rid = f"round-{seq['n']}"
        rounds[rid] = {"id": rid, "name": payload.get("name", rid), "participants": []}
        return rounds[rid]

    @app.post("/rounds/{rid}/updates")
    def submit_update(rid: str, payload: dict, _: dict = Depends(require_bearer)):
        rnd = rounds.get(rid)
        if rnd is None:
            return JSONResponse(status_code=404, content={"error": "round-not-found", "description": rid})
        municipality = payload.get("municipality", f"muni-{len(rnd['participants']) + 1}")
        if municipality not in rnd["participants"]:
            rnd["participants"].append(municipality)
        return {"round": rid, "municipality": municipality, "metric": _aggregate(peilen_instances, municipality)}

    @app.get("/rounds/{rid}/result")
    def result(rid: str, _: dict = Depends(require_bearer)):
        rnd = rounds.get(rid)
        if rnd is None:
            return JSONResponse(status_code=404, content={"error": "round-not-found", "description": rid})
        aggregate = _aggregate(peilen_instances, "|".join(rnd["participants"]) or rid)
        return {"round": rid, "participants": len(rnd["participants"]), "aggregate": aggregate}

    return app
