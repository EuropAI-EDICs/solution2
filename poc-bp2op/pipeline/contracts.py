"""Contract layer: load + validate artifacts against poc-bp2op/schemas (the V0 gate)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import jsonschema

POC_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = POC_ROOT / "schemas"

_SCHEMA_NAMES = {
    "conversion-request": "conversion-request.schema.json",
    "bron-regel": "bron-regel.schema.json",
    "doel-regel": "doel-regel.schema.json",
    "kennisbank-pair": "kennisbank-pair.schema.json",
    "omzettabel-row": "omzettabel-row.schema.json",
    "coverage-report": "coverage-report.schema.json",
    "validation-report": "validation-report.schema.json",
}


@lru_cache(maxsize=None)
def _schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / _SCHEMA_NAMES[name]
    return json.loads(path.read_text(encoding="utf-8"))


class ContractError(ValueError):
    """V0 gate failure: artifact does not satisfy its schema."""


def validate(name: str, instance: Any) -> None:
    """Validate one artifact against its schema; raise ContractError with all errors listed."""
    try:
        jsonschema.validate(instance=instance, schema=_schema(name))
    except jsonschema.ValidationError as exc:  # first error, plus the tree for completeness
        errors = sorted(jsonschema.Draft202012Validator(_schema(name)).iter_errors(instance), key=lambda e: list(e.path))
        detail = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5]) or exc.message
        raise ContractError(f"{name} V0 failure: {detail}") from exc


def validate_many(name: str, instances: List[Any]) -> None:
    for i, inst in enumerate(instances):
        try:
            validate(name, inst)
        except ContractError as exc:
            raise ContractError(f"instance[{i}] {exc}") from exc


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
