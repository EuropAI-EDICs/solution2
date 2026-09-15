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


def load_recipe(recipe_id: str) -> dict[str, Any]:
    path = RECIPES_DIR / f"{recipe_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Recipe not found: {recipe_id}")
    with path.open(encoding="utf-8") as f:
        recipe = json.load(f)
    validate_instance(recipe, "recipe.schema.json")
    return recipe
