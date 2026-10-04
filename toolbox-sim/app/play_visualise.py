# toolbox-sim/app/play_visualise.py
"""EU LDT Play & Visualise-sim: dataSources + dataLayers (SCENARIO)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class SourceConfiguration(BaseModel):
    type: str
    url: str
    headers: list = []


class SecurityConfiguration(BaseModel):
    type: str
    headers: list = []


class DataSourceIn(BaseModel):
    name: str
    sourceConfiguration: SourceConfiguration
    securityConfiguration: SecurityConfiguration


class DataLayerIn(BaseModel):
    name: str
    dataSource: str
    type: str
    configuration: dict = {}


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim play-visualise", docs_url=None, openapi_url=None)
    add_provenance(app, "play-visualise")
    data_sources: dict[str, dict] = {}
    data_layers: dict[str, dict] = {}
    counter = {"n": 0}

    def _next(prefix: str) -> str:
        counter["n"] += 1
        return f"{prefix}-{counter['n']}"

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/dataSources")
    def create_data_source(payload: DataSourceIn, _: dict = Depends(require_bearer)):
        ds_id = _next("ds")
        data_sources[ds_id] = payload.model_dump()
        data_sources[ds_id]["id"] = ds_id
        return data_sources[ds_id]

    @app.post("/api/dataLayers")
    def create_data_layer(payload: DataLayerIn, _: dict = Depends(require_bearer)):
        if payload.dataSource not in data_sources:
            raise HTTPException(status_code=404, detail={"error": "dataSourceNotFound", "description": payload.dataSource})
        dl_id = _next("dl")
        data_layers[dl_id] = payload.model_dump()
        data_layers[dl_id]["id"] = dl_id
        return data_layers[dl_id]

    @app.get("/api/dataLayers/{dl_id}")
    def get_data_layer(dl_id: str, _: dict = Depends(require_bearer)):
        if dl_id not in data_layers:
            raise HTTPException(status_code=404, detail={"error": "dataLayerNotFound", "description": dl_id})
        return data_layers[dl_id]

    return app
