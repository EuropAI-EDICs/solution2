from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException

from services.common.auth import require_bearer
from services.common.schema import list_recipe_ids, load_recipe

app = FastAPI(title="nLDT Cookbook", version="1.0.0", dependencies=[Depends(require_bearer)])

COOKBOOK_BASE = os.environ.get("NLDT_COOKBOOK_URL", "http://localhost:8081")


@app.get("/")
def landing() -> dict[str, Any]:
    return {
        "title": "nLDT Cookbook Service",
        "description": "Recipe definitions for Digital Twin as a Service",
        "links": [{"rel": "recipes", "href": "/recipes"}],
    }


@app.get("/recipes")
def list_recipes() -> dict[str, Any]:
    return {
        "recipes": [
            {
                "id": rid,
                "href": f"/recipes/{rid}",
                "cookbookUri": f"{COOKBOOK_BASE}/recipes/{rid}",
            }
            for rid in list_recipe_ids()
        ]
    }


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: str) -> dict[str, Any]:
    try:
        recipe = load_recipe(recipe_id)
        recipe["cookbookUri"] = f"{COOKBOOK_BASE}/recipes/{recipe_id}"
        return recipe
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_COOKBOOK_PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
