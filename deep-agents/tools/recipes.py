"""Recipe tools backed by the nLDT cookbook (../nldt/recipes/*.json).

Docstrings double as the tool descriptions the deep agent sees.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import journal

REPO_ROOT = Path(__file__).resolve().parents[2]
RECIPES_DIR = Path(os.environ.get("NLDT_RECIPES_DIR", REPO_ROOT / "nldt" / "recipes"))


def list_recipes() -> list[dict[str, Any]]:
    """List the available nLDT recipes with id, title and tags (tags name the POC each recipe belongs to)."""
    recipes = []
    for path in sorted(RECIPES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        recipes.append(
            {
                "id": data.get("id", path.stem),
                "title": data.get("title"),
                "tags": data.get("tags", []),
                "requiredProcesses": data.get("requiredProcesses", []),
            }
        )
    journal.append("tool_call", "agent", f"list_recipes() → {len(recipes)} recipes")
    return recipes


def get_recipe(recipe_id: str) -> dict[str, Any]:
    """Load the full definition of one nLDT recipe: steps, inputs, outputs, required processes and risk level."""
    path = RECIPES_DIR / f"{recipe_id}.json"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in RECIPES_DIR.glob("*.json")))
        raise FileNotFoundError(f"Unknown recipe '{recipe_id}'. Available: {available}")
    recipe = json.loads(path.read_text(encoding="utf-8"))
    journal.append(
        "tool_call", "agent", f"get_recipe('{recipe_id}') → {len(recipe.get('steps', []))} step(s)"
    )
    return recipe
