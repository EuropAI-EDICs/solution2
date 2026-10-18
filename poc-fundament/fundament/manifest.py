"""Laadt en valideert een fase-manifest (de agent–fase–tool matrix)."""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "fase-manifest.schema.json"


class ManifestError(RuntimeError):
    """Manifest ongeldig tegen fase-manifest.schema.json."""


def load_manifest(path: Path) -> dict:
    """Leest het manifest en valideert tegen het schema; luide faal."""
    import jsonschema

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(p) for p in exc.absolute_path) or "<top>"
        raise ManifestError(f"{Path(path).name}: {where}: {exc.message[:300]}") from exc
    return doc
