# toolbox-sim/app/integrated_environment.py
"""EU LDT Integrated Environment-sim: portal-aggregatie, OGC-Records-vorm, metrics."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Response

from app.guards import add_provenance, require_bearer


def create_app(solutions: list[dict], inventory_path: Path | None) -> FastAPI:
    app = FastAPI(title="toolbox-sim integrated-environment", docs_url=None, openapi_url=None)
    add_provenance(app, "integrated-environment")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/solutions")
    def list_solutions(_: dict = Depends(require_bearer)):
        return {"total": len(solutions), "data": [dict(s) for s in solutions]}

    @app.get("/catalogue")
    def catalogue(_: dict = Depends(require_bearer)):
        datasets = []
        if inventory_path is not None and inventory_path.exists():
            inv = json.loads(inventory_path.read_text())
            datasets = [
                {"id": d.get("id"), "poc": d.get("poc"), "zone": d.get("zone"),
                 "lakeUri": d.get("lakeUri"), "license": d.get("license")}
                for d in inv.get("datasets", [])
            ]
        return {"type": "Catalogue", "total": len(datasets), "data": datasets}

    @app.get("/metrics")
    def metrics(_: dict = Depends(require_bearer)):
        lines = [f"solutions_total {len(solutions)}"]
        for s in solutions:
            lines.append(f'solution_up{{name="{s.get("name", "?")}"}} 1')
        return Response(content="\n".join(lines) + "\n", media_type="text/plain")

    return app
