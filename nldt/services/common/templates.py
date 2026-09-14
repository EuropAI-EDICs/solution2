from __future__ import annotations

import re
from typing import Any

_TEMPLATE = re.compile(r"\$\{(recipe\.inputs\.[^}]+|steps\.[^}]+)\}")


def resolve_templates(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        match = _TEMPLATE.fullmatch(value.strip())
        if match:
            return _lookup(match.group(1), context)
        return value
    if isinstance(value, list):
        return [resolve_templates(v, context) for v in value]
    if isinstance(value, dict):
        return {k: resolve_templates(v, context) for k, v in value.items()}
    return value


def _lookup(path: str, context: dict[str, Any]) -> Any:
    if path.startswith("recipe.inputs."):
        key = path.split(".", 2)[2]
        return context["recipe"]["inputs"].get(key)
    if path.startswith("steps."):
        _, step_id, _, output_key = path.split(".", 3)
        return context["steps"][step_id]["outputs"][output_key]
    raise KeyError(f"Unknown template path: {path}")
