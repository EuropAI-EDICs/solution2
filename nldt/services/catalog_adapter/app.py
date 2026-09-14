from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from services.catalog_adapter.marketplace import fetch_marketplace_assets
from services.catalog_adapter.seed import find_records, seed_records
from services.common.auth import require_bearer
from services.common.schema import load_recipe
from services.marketplace_publish import publish_recipe

app = FastAPI(
    title="nLDT Catalog Adapter", version="1.0.0", dependencies=[Depends(require_bearer)]
)


def _all_records() -> list[dict[str, Any]]:
    return seed_records() + fetch_marketplace_assets()


@app.get("/")
def landing() -> dict[str, Any]:
    return {
        "title": "nLDT OGC API Records Catalog",
        "description": "AppStore catalog (seed + optional Marketplace Agent)",
        "links": [
            {"rel": "records", "href": "/records"},
            {"rel": "conformance", "href": "/conformance"},
        ],
    }


@app.get("/conformance")
def conformance() -> dict[str, Any]:
    return {
        "conformsTo": [
            "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
        ]
    }


@app.get("/records")
def records(
    q: str | None = Query(None),
    type: str | None = Query(None, alias="type"),
) -> dict[str, Any]:
    items = find_records(q=q, record_type=type)
    mp = fetch_marketplace_assets()
    if type == "asset" or type is None:
        if q:
            q_lower = q.lower()
            mp = [r for r in mp if q_lower in r.get("title", "").lower()]
        if type == "asset":
            items = mp
        elif type is None:
            items = items + mp
    return {
        "type": "FeatureCollection",
        "features": items,
        "numberMatched": len(items),
        "links": [{"rel": "self", "href": "/records"}],
    }


@app.get("/records/{record_id}")
def get_record(record_id: str) -> dict[str, Any]:
    for rec in _all_records():
        if rec["id"] == record_id:
            return rec
    raise HTTPException(status_code=404, detail="record not found")


@app.get("/processes")
def list_processes() -> dict[str, Any]:
    items = find_records(record_type="process")
    return {"processes": items}


class PublishRecipeRequest(BaseModel):
    recipeId: str
    categories: list[str] | None = None
    licence: str = "EUPL-1.2"


@app.post("/publish/recipe")
def publish_recipe_to_marketplace(body: PublishRecipeRequest) -> dict[str, Any]:
    try:
        recipe = load_recipe(body.recipeId)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = publish_recipe(recipe, categories=body.categories, licence=body.licence)
    return {"recipeId": body.recipeId, **result}


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_CATALOG_PORT", "8083"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
