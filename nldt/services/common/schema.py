from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

NLDT_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = NLDT_ROOT / "schemas"
RECIPES_DIR = NLDT_ROOT / "recipes"


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMAS_DIR / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_instance(instance: Any, schema_name: str) -> None:
    schema = load_schema(schema_name)
    Draft202012Validator(schema).validate(instance)


def load_recipe(recipe_id: str) -> dict[str, Any]:
    path = RECIPES_DIR / f"{recipe_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Recipe not found: {recipe_id}")
    with path.open(encoding="utf-8") as f:
        recipe = json.load(f)
    validate_instance(recipe, "recipe.schema.json")
    return recipe
