# toolbox-sim/app/dataspace_ready.py
"""EU LDT Data Space Ready-sim: EDC-connectorstub (Management v3 + flow v2)."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, Response

from app.guards import add_provenance, require_bearer


def create_app(offers: list[dict], lake_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="toolbox-sim dataspace-ready", docs_url=None, openapi_url=None)
    add_provenance(app, "dataspace-ready")
    offers_by_uid = {o["uid"]: o for o in offers}
    assets: dict[str, dict] = {}
    policies: dict[str, dict] = {}
    contract_defs: dict[str, dict] = {}
    negotiations: dict[str, dict] = {}
    transfers: dict[str, dict] = {}
    seq = {"n": 0}

    def _next(prefix: str) -> str:
        seq["n"] += 1
        return f"{prefix}-sim-{seq['n']}"

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/v3/policydefinitions", status_code=201)
    def create_policy(policy: dict, _: dict = Depends(require_bearer)):
        pid = policy.get("@id") or _next("policy")
        policies[pid] = {**policy, "@id": pid}
        return Response(status_code=201, headers={"Location": f"/v3/policydefinitions/{pid}"})

    @app.post("/v3/assets", status_code=201)
    def create_asset(asset: dict, _: dict = Depends(require_bearer)):
        aid = asset.get("@id") or _next("asset")
        assets[aid] = {**asset, "@id": aid}
        return Response(status_code=201, headers={"Location": f"/v3/assets/{aid}"})

    @app.post("/v3/contractdefinitions", status_code=201)
    def create_contract_definition(definition: dict, _: dict = Depends(require_bearer)):
        cid = definition.get("@id") or _next("contract")
        contract_defs[cid] = {**definition, "@id": cid}
        return Response(status_code=201, headers={"Location": f"/v3/contractdefinitions/{cid}"})

    @app.post("/v2/catalog/request")
    def catalog_request(payload: dict, _: dict = Depends(require_bearer)):
        return {
            "@type": "cat:Catalog",
            "offers": [
                {"uid": o["uid"], "datasetId": o.get("datasetId"), "lakeUri": o.get("lakeUri"),
                 "accessClass": o.get("accessClass"), "license": o.get("license")}
                for o in offers
            ],
        }

    @app.post("/v2/contractnegotiations", status_code=201)
    def create_negotiation(payload: dict, _: dict = Depends(require_bearer)):
        offer = offers_by_uid.get(payload.get("offerUid") or "")
        if offer is None:
            return JSONResponse(status_code=404, content={"error": "offer-not-found", "description": payload.get("offerUid")})
        nid = _next("cn")
        negotiations[nid] = {"id": nid, "offerUid": offer["uid"], "state": "REQUESTED"}
        return negotiations[nid]

    @app.get("/v2/contractnegotiations/{nid}")
    def get_negotiation(nid: str, _: dict = Depends(require_bearer)):
        cn = negotiations.get(nid)
        if cn is None:
            return JSONResponse(status_code=404, content={"error": "negotiation-not-found", "description": nid})
        # deterministische state-machine: eerste read bevestigt
        cn["state"] = "CONFIRMED"
        return cn

    @app.post("/v2/transferprocesses", status_code=201)
    def create_transfer(payload: dict, _: dict = Depends(require_bearer)):
        offer = offers_by_uid.get(payload.get("offerUid") or "")
        if offer is None:
            return JSONResponse(status_code=404, content={"error": "offer-not-found", "description": payload.get("offerUid")})
        tid = _next("tp")
        local = ""
        if lake_root is not None and offer.get("lakeUri", "").startswith("lake://"):
            local = str(lake_root / offer["lakeUri"].removeprefix("lake://nldt-poc-lake/"))
        transfers[tid] = {"id": tid, "offerUid": offer["uid"], "state": "STARTED",
                          "destination": local, "negotiationId": payload.get("negotiationId")}
        return transfers[tid]

    @app.get("/v2/transferprocesses/{tid}")
    def get_transfer(tid: str, _: dict = Depends(require_bearer)):
        tp = transfers.get(tid)
        if tp is None:
            return JSONResponse(status_code=404, content={"error": "transfer-not-found", "description": tid})
        # deterministische state-machine: eerste read rondt de overdracht af
        tp["state"] = "COMPLETED"
        return tp

    return app
