# toolbox-sim/app/data_platform.py
"""EU LDT Data Platform-sim: NGSI-LD-broker (+ UCS-proxyvariant; Trino in Task 8)."""
from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response

from app.guards import add_provenance, provenance_detail, require_bearer


def create_broker_app(
    *,
    entities_by_tenant: dict[str, list[dict]],
    provenance_by_tenant: dict[str, str],
    include_proxy: bool = False,
    include_trino: bool = False,
) -> FastAPI:
    app = FastAPI(title="toolbox-sim data-platform", docs_url=None, openapi_url=None)
    add_provenance(app, "data-platform")
    store: dict[str, dict[str, dict]] = {
        tenant: {e["id"]: e for e in entities} for tenant, entities in entities_by_tenant.items()
    }

    def _tenant(x_tenant: str) -> dict[str, dict]:
        return store.setdefault(x_tenant, {})

    def _prov(x_tenant: str) -> dict:
        return provenance_detail(provenance_by_tenant.get(x_tenant, "toolbox-sim/data-platform"))

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/ngsi-ld/v1/entities")
    def list_entities(
        request: Request,
        type: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"),
        _: dict = Depends(require_bearer),
    ):
        tenant = _tenant(x_tenant)
        entities = list(tenant.values())
        if type:
            entities = [e for e in entities if e.get("type") == type]
        entities.sort(key=lambda e: e["id"])
        return Response(
            content=json.dumps(entities[:limit], separators=(",", ":")),
            media_type="application/json",
            headers=_prov(x_tenant),
        )

    @app.get("/ngsi-ld/v1/entities/{entity_id}")
    def get_entity(entity_id: str, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        entity = _tenant(x_tenant).get(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail={"error": "NotFound", "description": entity_id})
        return Response(
            content=json.dumps(entity, separators=(",", ":")),
            media_type="application/json",
            headers=_prov(x_tenant),
        )

    @app.post("/ngsi-ld/v1/entityOperations/upsert", status_code=204)
    def upsert(batch: list[dict], x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        tenant = _tenant(x_tenant)
        for entity in batch:
            tenant[entity["id"]] = entity

    if include_proxy:

        @app.get("/api/v1/data-platform/entities")
        def proxy_list(
            type: str | None = Query(default=None),
            scope: str | None = Query(default=None),
            limit: int = Query(default=100, ge=1, le=1000),
            x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"),
            _: dict = Depends(require_bearer),
        ):
            tenant = _tenant(x_tenant)
            entities = list(tenant.values())
            if type:
                entities = [e for e in entities if e.get("type") == type]
            entities.sort(key=lambda e: e["id"])
            return {"data": entities[:limit]}

        @app.get("/api/v1/data-platform/entities/{entity_id}")
        def proxy_get(entity_id: str, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
            entity = _tenant(x_tenant).get(entity_id)
            if entity is None:
                raise HTTPException(status_code=404, detail={"error": "NotFound", "description": entity_id})
            return {"data": entity}

    return app
