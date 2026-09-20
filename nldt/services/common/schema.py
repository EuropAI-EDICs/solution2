from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

NLDT_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = NLDT_ROOT / "schemas"
POC_SCHEMAS_DIR = SCHEMAS_DIR / "poc"
RECIPES_DIR = NLDT_ROOT / "recipes"
# Cookbook metadata that lives next to recipes but is not a Recipe document.
NON_RECIPE_STEMS = frozenset({"edic-asset-map"})


def load_schema(name: str) -> dict[str, Any]:
    """Load a JSON Schema by file name.

    Resolution order:
    1. ``nldt/schemas/<name>``
    2. ``nldt/schemas/poc/<name>`` (Phase 5.0 contract bridge; may be a symlink)
    3. ``nldt/schemas/poc/<basename>`` when ``name`` is ``poc/<basename>``
    """
    candidates = [
        SCHEMAS_DIR / name,
        POC_SCHEMAS_DIR / Path(name).name,
    ]
    if name.startswith("poc/"):
        candidates.insert(0, SCHEMAS_DIR / name)
    for path in candidates:
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"Schema not found: {name} (searched {[str(c) for c in candidates]})")


def validate_instance(instance: Any, schema_name: str) -> None:
    schema = load_schema(schema_name)
    Draft202012Validator(schema).validate(instance)


def is_recipe_id(recipe_id: str) -> bool:
    return recipe_id not in NON_RECIPE_STEMS


def list_recipe_ids() -> list[str]:
    return sorted(
        p.stem
        for p in RECIPES_DIR.glob("*.json")
        if is_recipe_id(p.stem)
    )


def load_edic_asset_map() -> dict[str, Any]:
    path = RECIPES_DIR / "edic-asset-map.json"
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    validate_instance(payload, "edic-asset-map.schema.json")
    return payload


def edic_entry_for_recipe(recipe_id: str) -> dict[str, Any] | None:
    payload = load_edic_asset_map()
    wanted = f"recipe:{recipe_id}"
    for asset in payload.get("assets", []):
        if asset.get("id") == wanted:
            return asset
    return None


def load_recipe(recipe_id: str) -> dict[str, Any]:
    if not is_recipe_id(recipe_id):
        raise FileNotFoundError(f"Recipe not found: {recipe_id}")
    path = RECIPES_DIR / f"{recipe_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Recipe not found: {recipe_id}")
    with path.open(encoding="utf-8") as f:
        recipe = json.load(f)
    validate_instance(recipe, "recipe.schema.json")
    return recipe
