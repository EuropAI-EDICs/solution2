# toolbox-sim/app/marketplace.py
"""EU LDT Marketplace Agent-sim: upload + publish met offering-id."""
from __future__ import annotations

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class PublishIn(BaseModel):
    name: str
    description: str
    categories: list[str]
    licence: str = "EUPL-1.2"


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim marketplace", docs_url=None, openapi_url=None)
    add_provenance(app, "marketplace")
    assets: dict[str, dict] = {}
    counter = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/v1/agent/assets")
    async def upload(file: UploadFile = File(...), _: dict = Depends(require_bearer)):
        counter["n"] += 1
        asset_id = f"asset-{counter['n']}"
        assets[asset_id] = {"id": asset_id, "fileName": file.filename, "size": len(await file.read()), "status": "uploaded"}
        return {"id": asset_id}

    @app.post("/api/v1/agent/assets/{asset_id}/publish")
    def publish(asset_id: str, payload: PublishIn, _: dict = Depends(require_bearer)):
        asset = assets.get(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail={"error": "assetNotFound", "description": asset_id})
        asset.update(
            status="published",
            name=payload.name,
            description=payload.description,
            categories=payload.categories,
            licence=payload.licence,
            publishState={"offering_id": f"sim-offering-{asset_id}"},
        )
        return asset

    @app.get("/api/v1/agent/assets")
    def listing(_: dict = Depends(require_bearer)):
        return {"data": [dict(a) for a in assets.values()]}

    return app
