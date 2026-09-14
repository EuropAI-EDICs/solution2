from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.common.schema import validate_instance
from services.context3d.export_import import export_from_execution, import_context, load_context, save_context

NLDT_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_STORE = NLDT_ROOT / "data" / "context3d"
EXPORT_STORE = NLDT_ROOT / "data" / "exports"

app = FastAPI(title="nLDT Web 3D Context Service", version="1.0.0")


class ExportRequest(BaseModel):
    execution: dict[str, Any]
    runId: str | None = None
    title: str | None = None


class ImportRequest(BaseModel):
    document: dict[str, Any]


@app.get("/")
def landing() -> dict[str, Any]:
    return {
        "title": "Web 3D Context import/export",
        "links": [{"rel": "export", "href": "/export"}, {"rel": "contexts", "href": "/contexts"}],
    }


@app.post("/export")
def export_context(body: ExportRequest) -> dict[str, Any]:
    doc = export_from_execution(body.execution, run_id=body.runId, title=body.title)
    validate_instance(doc, "web3d-context.schema.json")
    path = save_context(doc, CONTEXT_STORE)
    return {"document": doc, "storedAt": str(path)}


@app.post("/import")
def import_context_endpoint(body: ImportRequest) -> dict[str, Any]:
    validate_instance(body.document, "web3d-context.schema.json")
    try:
        parsed = import_context(body.document)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return parsed


@app.get("/contexts")
def list_contexts() -> dict[str, Any]:
    if not CONTEXT_STORE.exists():
        return {"contexts": []}
    items = sorted(CONTEXT_STORE.glob("*.json"))
    return {"contexts": [{"id": p.stem, "path": str(p)} for p in items]}


@app.get("/contexts/{context_id}")
def get_context(context_id: str) -> dict[str, Any]:
    path = CONTEXT_STORE / f"{context_id}.json"
    if not path.exists():
        path = CONTEXT_STORE / f"context-{context_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="context not found")
    return load_context(path)


class GeoJsonExportBody(BaseModel):
    geojson: dict[str, Any]


@app.post("/exports")
def store_export(body: GeoJsonExportBody) -> dict[str, Any]:
    from uuid import uuid4

    export_id = uuid4().hex[:12]
    EXPORT_STORE.mkdir(parents=True, exist_ok=True)
    path = EXPORT_STORE / f"{export_id}.geojson"
    import json

    path.write_text(json.dumps(body.geojson), encoding="utf-8")
    return {"exportId": export_id, "href": f"/exports/{export_id}.geojson"}


@app.get("/exports/{export_id}.geojson")
def get_export(export_id: str) -> JSONResponse:
    path = EXPORT_STORE / f"{export_id}.geojson"
    if not path.exists():
        raise HTTPException(status_code=404, detail="export not found")
    import json

    return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_CONTEXT3D_PORT", "8084"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
