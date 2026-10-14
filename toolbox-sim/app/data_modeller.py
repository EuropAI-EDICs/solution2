# toolbox-sim/app/data_modeller.py
"""EU LDT Data Modeller-sim: model-registry (seeded uit nldt/schemas) + jsonschema-validatie."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, Response

from app.guards import add_provenance, require_bearer


def create_app(schemas: dict[str, dict]) -> FastAPI:
    app = FastAPI(title="toolbox-sim data-modeller", docs_url=None, openapi_url=None)
    add_provenance(app, "data-modeller")
    models: dict[str, dict] = {name: dict(s) for name, s in schemas.items()}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/models")
    def list_models(_: dict = Depends(require_bearer)):
        return {"data": sorted(models)}

    @app.post("/models", status_code=201)
    def create_model(payload: dict, _: dict = Depends(require_bearer)):
        name = payload.get("name") or ""
        schema = payload.get("schema")
        if not name or not isinstance(schema, dict):
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "name en schema (object) zijn vereist"})
        models[name] = schema
        return Response(status_code=201, headers={"Location": f"/models/{name}"})

    @app.delete("/models/{name}", status_code=204)
    def delete_model(name: str, _: dict = Depends(require_bearer)):
        models.pop(name, None)
        return Response(status_code=204)

    @app.post("/models/{name}/validate")
    def validate(name: str, instance: dict, _: dict = Depends(require_bearer)):
        schema = models.get(name)
        if schema is None:
            return JSONResponse(status_code=404, content={"error": "model-not-found", "description": name})
        import jsonschema

        try:
            jsonschema.Draft202012Validator(schema).validate(instance)
            return {"valid": True, "findings": []}
        except jsonschema.ValidationError as exc:
            return {"valid": False, "findings": [{"path": list(exc.absolute_path), "message": exc.message}]}

    return app
