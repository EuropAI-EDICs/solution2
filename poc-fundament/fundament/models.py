"""Modelregister: computation-modellen + hun transports (BB13-patroon).

Het register declareert welke transports een model heeft (OGC API
Processes, A2A Agent Card, MCP, in-process); de conformance-tests bewijzen
dat de gerefereerde transports werkelijk bestaan (processId in de
process-adapter, agent-id in de a2a-catalogus) — het register claimt niets
wat de repo niet waarmaakt.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "modelregister.schema.json"


class ModelRegistryError(RuntimeError):
    """Modelregister ongeldig tegen het schema, of dubbele model-ids."""


def load_model_registry(path: Path) -> dict:
    """Leest het register, valideert tegen het schema; luide faal."""
    import jsonschema

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(p) for p in exc.absolute_path) or "<top>"
        raise ModelRegistryError(f"{Path(path).name}: {where}: {exc.message[:300]}") from exc
    ids = [m["id"] for m in doc["models"]]
    if len(ids) != len(set(ids)):
        raise ModelRegistryError("dubbele model-ids in het register")
    return doc


def model_by_id(registry: dict, model_id: str) -> dict:
    for m in registry["models"]:
        if m["id"] == model_id:
            return m
    raise KeyError(model_id)
