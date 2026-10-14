# toolbox-sim/app/ai_notebook.py
"""EU LDT AI Notebook-sim: notebook-sessies + deterministische pipeline-runs over de lake-inventaris."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.guards import add_provenance, require_bearer


def create_app(lake_root: Path | None) -> FastAPI:
    app = FastAPI(title="toolbox-sim ai-notebook", docs_url=None, openapi_url=None)
    add_provenance(app, "ai-notebook")
    notebooks: dict[str, dict] = {}
    runs: dict[str, dict] = {}
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/notebooks", status_code=201)
    def create_notebook(payload: dict, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        nb = {"id": f"nb-{seq['n']}", "name": payload.get("name", f"notebook-{seq['n']}")}
        notebooks[nb["id"]] = nb
        return nb

    @app.post("/pipelines/runs", status_code=201)
    def run_pipeline(payload: dict, _: dict = Depends(require_bearer)):
        nb = notebooks.get(payload.get("notebookId") or "")
        if nb is None:
            return JSONResponse(status_code=404, content={"error": "notebook-not-found", "description": payload.get("notebookId")})
        seq["n"] += 1
        rid = f"run-{seq['n']}"
        inventory = 0
        if lake_root is not None:
            inv = lake_root / "catalog" / "inventory.parquet"
            mirrors = lake_root / "iceberg" / "mirrors" / "inventory.parquet"
            count_path = mirrors if mirrors.exists() else inv
            if count_path.exists():
                import duckdb

                inventory = duckdb.connect().execute(
                    f"SELECT count(*) FROM read_parquet('{count_path.as_posix()}')"
                ).fetchone()[0]
        run = {
            "id": rid, "notebookId": nb["id"], "pipeline": payload.get("pipeline", "inventory-count"),
            "state": "SUCCEEDED" if inventory else "NO_GROUND",
            "outputs": {"inventoryDatasets": inventory, "lakeRoot": str(lake_root or "")},
            "provenance": "lake://nldt-poc-lake/iceberg/mirrors/inventory.parquet",
        }
        runs[rid] = run
        return run

    @app.get("/pipelines/runs/{rid}")
    def get_run(rid: str, _: dict = Depends(require_bearer)):
        run = runs.get(rid)
        if run is None:
            return JSONResponse(status_code=404, content={"error": "run-not-found", "description": rid})
        return run

    return app
