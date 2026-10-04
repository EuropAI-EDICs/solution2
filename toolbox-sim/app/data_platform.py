# toolbox-sim/app/data_platform.py
"""EU LDT Data Platform-sim: NGSI-LD-broker (+ UCS-proxyvariant; Trino in Task 8)."""
from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

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

    if include_trino:
        import re

        from pathlib import Path

        tables = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "trino" / "tables.json").read_text())
        statements: dict[str, list[list]] = {}
        statement_seq = {"n": 0}

        def _first_page(request: Request, columns: list[str], rows: list[list]) -> dict:
            # Trino-draadgedrag (taak-14-contract, gevangen door de live adaptertest):
            # de POST levert kolommen + continuation-URI; de rijen volgen pas op de
            # nextUri-pagina. Clients (zoals de nldt-trino-adapter) lezen data
            # uitsluitend via nextUri-polling en negeren eerste-pagina-data.
            statement_seq["n"] += 1
            statement_id = f"statement-sim-{statement_seq['n']}"
            statements[statement_id] = rows
            next_uri = str(request.url.replace(path=f"/v1/statement/next/{statement_id}", query=""))
            return {
                "id": statement_id,
                "stats": {},
                "columns": [{"name": c, "type": "varchar"} for c in columns],
                "nextUri": next_uri,
            }

        @app.post("/v1/statement")
        async def statement(request: Request, _: dict = Depends(require_bearer)):
            sql = (await request.body()).decode("utf-8", "replace").strip()
            normalized = " ".join(sql.lower().split())
            if re.match(r"^(insert|update|delete|drop|create|alter|truncate)\b", normalized):
                # Afwijking plan (taak-4-precedent): top-level {"error": ...} teruggeven;
                # HTTPException-detail wordt in {"detail": ...} gewrapped, tests asserten r.json()["error"].
                return JSONResponse(status_code=403, content={"error": "write-forbidden"})
            m = re.match(r"^show schemas from (\w+)$", normalized)
            if m:
                catalog = tables["catalogs"].get(m.group(1))
                if catalog is None:
                    raise HTTPException(status_code=404, detail={"error": "catalog-not-found"})
                return _first_page(request, ["Schema"], [[s] for s in sorted(catalog)])
            m = re.match(r"^show tables from (\w+)\.(\w+)$", normalized)
            if m:
                schema = tables["catalogs"].get(m.group(1), {}).get(m.group(2))
                if schema is None:
                    raise HTTPException(status_code=404, detail={"error": "schema-not-found"})
                return _first_page(request, ["Table"], [[t] for t in sorted(schema)])
            m = re.match(r"^select \* from (\w+)\.(\w+)\.(\w+)(?: limit (\d+))?$", normalized)
            if m:
                table = tables["catalogs"].get(m.group(1), {}).get(m.group(2), {}).get(m.group(3))
                if table is None:
                    raise HTTPException(status_code=404, detail={"error": "table-not-found"})
                rows = [list(r) for r in table["rows"]]
                if m.group(4):
                    rows = rows[: int(m.group(4))]
                return _first_page(request, table["columns"], rows)
            # Idem afwijking: top-level error-body i.v.m. het testcontract.
            return JSONResponse(
                status_code=400,
                content={
                    "error": "unsupported-statement",
                    "error_description": "stub ondersteunt SHOW SCHEMAS FROM, SHOW TABLES FROM <cat>.<sch> en SELECT * FROM ... [LIMIT n]",
                },
            )

        @app.get("/v1/statement/next/{statement_id}")
        def statement_next(statement_id: str, _: dict = Depends(require_bearer)):
            rows = statements.pop(statement_id, None)
            if rows is None:
                raise HTTPException(status_code=404, detail={"error": "statementNotFound", "description": statement_id})
            return {"id": statement_id, "stats": {}, "data": rows, "nextUri": None}

    return app
