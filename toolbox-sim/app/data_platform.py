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
    temporal: dict | None = None,
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

    subscriptions: dict[str, dict] = {}
    subscription_notifications: dict[str, list[dict]] = {}
    registrations: dict[str, dict] = {}
    id_seq = {"n": 0}
    clock_seq = {"n": 0}

    def _sim_clock() -> str:
        # sim-klok: vaste basis + teller → deterministisch, monotoon, ISO-8601 Z
        clock_seq["n"] += 1
        total = clock_seq["n"]
        hh, rest = divmod(total, 3600)
        mm, ss = divmod(rest, 60)
        return f"2026-01-01T{hh:02d}:{mm:02d}:{ss:02d}Z"

    def _next_urn(prefix: str) -> str:
        id_seq["n"] += 1
        return f"urn:ngsi-ld:{prefix}:sim-{id_seq['n']}"

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

    @app.post("/ngsi-ld/v1/subscriptions/", status_code=201)
    def create_subscription(subscription: dict, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        if subscription.get("type") != "Subscription" or "entities" not in subscription or "notification" not in subscription:
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "Subscription vereist type, entities en notification"})
        sid = _next_urn("Subscription")
        subscriptions[sid] = {**subscription, "id": sid, "status": "active"}
        return Response(status_code=201, headers={"Location": f"/ngsi-ld/v1/subscriptions/{sid}"})

    @app.get("/ngsi-ld/v1/subscriptions/")
    def list_subscriptions(_: dict = Depends(require_bearer)):
        return [dict(s) for s in subscriptions.values()]

    @app.get("/ngsi-ld/v1/subscriptions/{sid}")
    def get_subscription(sid: str, _: dict = Depends(require_bearer)):
        sub = subscriptions.get(sid)
        if sub is None:
            # Taak-4-precedent: top-level {"error": ...} teruggeven; HTTPException-detail
            # wordt in {"detail": ...} gewrapped, tests asserten r.json()["error"].
            return JSONResponse(status_code=404, content={"error": "NotFound", "description": sid})
        return sub

    @app.delete("/ngsi-ld/v1/subscriptions/{sid}", status_code=204)
    def delete_subscription(sid: str, _: dict = Depends(require_bearer)):
        subscriptions.pop(sid, None)
        subscription_notifications.pop(sid, None)
        return Response(status_code=204)

    @app.post("/ngsi-ld/v1/subscriptions/{sid}/notify")
    def trigger_notify(sid: str, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        sub = subscriptions.get(sid)
        if sub is None:
            # Taak-4-precedent: top-level {"error": ...} teruggeven; HTTPException-detail
            # wordt in {"detail": ...} gewrapped, tests asserten r.json()["error"].
            return JSONResponse(status_code=404, content={"error": "NotFound", "description": sid})
        watched = [(e.get("id"), e.get("type")) for e in sub.get("entities", [])]
        tenant = _tenant(x_tenant)
        matched = [
            e for e in tenant.values()
            if any((wid and e.get("id") == wid) or (wtype and e.get("type") == wtype) for wid, wtype in watched)
        ]
        payload = {
            "subscriptionId": sid,
            "notifiedAt": _sim_clock(),
            "data": matched,
        }
        subscription_notifications.setdefault(sid, []).append(payload)
        return payload

    @app.get("/ngsi-ld/v1/subscriptions/{sid}/notifications")
    def list_subscription_notifications(sid: str, _: dict = Depends(require_bearer)):
        if sid not in subscriptions:
            # Taak-4-precedent: top-level {"error": ...} teruggeven; HTTPException-detail
            # wordt in {"detail": ...} gewrapped, tests asserten r.json()["error"].
            return JSONResponse(status_code=404, content={"error": "NotFound", "description": sid})
        return {"data": subscription_notifications.get(sid, [])}

    @app.post("/ngsi-ld/v1/registrations/", status_code=201)
    def create_registration(registration: dict, _: dict = Depends(require_bearer)):
        if registration.get("type") != "ContextSourceRegistration" or "endpoint" not in registration:
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "ContextSourceRegistration vereist type en endpoint"})
        rid = _next_urn("ContextSourceRegistration")
        registrations[rid] = {**registration, "id": rid, "status": "active"}
        return Response(status_code=201, headers={"Location": f"/ngsi-ld/v1/registrations/{rid}"})

    @app.get("/ngsi-ld/v1/registrations/")
    def list_registrations(_: dict = Depends(require_bearer)):
        return [dict(r) for r in registrations.values()]

    @app.delete("/ngsi-ld/v1/registrations/{rid}", status_code=204)
    def delete_registration(rid: str, _: dict = Depends(require_bearer)):
        registrations.pop(rid, None)
        return Response(status_code=204)

    @app.get("/ngsi-ld/v1/temporal/entities/{entity_id}")
    def temporal_entity(
        entity_id: str,
        timerel: str = Query(...),
        time: str = Query(...),
        endTime: str | None = Query(default=None),
        time_property: str = Query(default="observedAt", alias="time_property"),
        _: dict = Depends(require_bearer),
    ):
        entity = (temporal or {}).get(entity_id)
        if entity is None:
            # Taak-4-precedent: top-level {"error": ...} teruggeven; HTTPException-detail
            # wordt in {"detail": ...} gewrapped en de test asserteert r.json()["error"].
            return JSONResponse(status_code=404, content={"error": "NotFound", "description": entity_id})
        if timerel not in ("before", "after", "between"):
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "timerel is before|after|between"})
        if timerel == "between" and not endTime:
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "timerel=between vereist endTime"})

        def _keep(instance: dict) -> bool:
            stamp = str(instance.get(time_property, ""))
            if timerel == "before":
                return stamp <= time
            if timerel == "after":
                return stamp >= time
            return time <= stamp <= (endTime or "")

        instances = [i for i in entity.get("instances", []) if _keep(i)]
        body = {k: v for k, v in entity.items() if k not in ("instances", "attribute")}
        body[entity["attribute"]] = [{"type": "Property", "instances": instances}]
        return body

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
