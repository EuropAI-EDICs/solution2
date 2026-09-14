"""Lake dataset governance for MCP catalog tools (accessClass + deny-list)."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any

NLDT_ROOT = Path(__file__).resolve().parents[2]
DENY_PATH = NLDT_ROOT / "data" / "lake-deny.json"
INVENTORY_PATH = NLDT_ROOT / "data" / "lake-inventory.json"


def load_deny_config() -> dict[str, Any]:
    if DENY_PATH.is_file():
        return json.loads(DENY_PATH.read_text(encoding="utf-8"))
    return {}


def load_inventory_datasets() -> list[dict[str, Any]]:
    if not INVENTORY_PATH.is_file():
        return []
    data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return [ds for ds in (data.get("datasets") or []) if ds.get("exists")]


def _matches_deny_glob(lake_key: str, local_path: str, globs: list[str]) -> bool:
    for pattern in globs:
        if fnmatch.fnmatch(lake_key, pattern.replace("poc-rijnland/data/", "bronze/rijnland/")):
            return True
        if fnmatch.fnmatch(local_path, pattern):
            return True
        if fnmatch.fnmatch(lake_key, pattern):
            return True
    return False


def is_restricted_dataset(dataset: dict[str, Any], deny: dict[str, Any] | None = None) -> bool:
    """True when dataset must not be exposed to agents without explicit scope."""
    deny = deny if deny is not None else load_deny_config()
    access = (dataset.get("accessClass") or "internal").lower()
    if access == "restricted":
        return True
    lake_key = dataset.get("lakeKey") or ""
    local_path = dataset.get("localPath") or ""
    globs = deny.get("denyPublishGlobs") or []
    if _matches_deny_glob(lake_key, local_path, globs):
        return True
    for override in deny.get("pathOverrides") or []:
        glob = override.get("glob", "")
        if override.get("accessClass") == "restricted" and _matches_deny_glob(
            lake_key, local_path, [glob]
        ):
            return True
    return False


def filter_lake_datasets(
    datasets: list[dict[str, Any]],
    *,
    include_restricted: bool = False,
) -> list[dict[str, Any]]:
    deny = load_deny_config()
    if include_restricted:
        return list(datasets)
    return [ds for ds in datasets if not is_restricted_dataset(ds, deny)]


def dataset_to_catalog_record(dataset: dict[str, Any]) -> dict[str, Any]:
    did = dataset.get("id") or (dataset.get("lakeKey") or "").replace("/", "-")
    catalog_base = "http://localhost:8083"
    return {
        "id": f"dataset-{did}",
        "type": "dataset",
        "title": f"{dataset.get('poc')} {dataset.get('zone')} {dataset.get('kind')}",
        "properties": {
            "poc": dataset.get("poc"),
            "zone": dataset.get("zone"),
            "kind": dataset.get("kind"),
            "accessClass": dataset.get("accessClass"),
            "license": dataset.get("license"),
            "crs": dataset.get("crs"),
            "sha256": dataset.get("sha256"),
            "lakeUri": dataset.get("lakeUri"),
            "lakeKey": dataset.get("lakeKey"),
            "hadPrimarySource": dataset.get("sourceId"),
            "tags": ["lake", dataset.get("zone"), dataset.get("poc")],
        },
        "links": [
            {"rel": "self", "href": f"{catalog_base}/records/dataset-{did}"},
            {
                "rel": "enclosure",
                "href": dataset.get("lakeUri"),
                "type": "application/octet-stream",
            },
        ],
    }
