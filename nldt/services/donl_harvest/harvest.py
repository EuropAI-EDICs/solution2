"""Orchestrate DONL CKAN harvest into the nLDT medallion lake."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.donl_harvest.ckan import CkanClient
from services.donl_harvest.dcat_map import map_package_to_dcat, package_registry_entry
from services.donl_harvest.distributions import (
    build_service_manifest,
    classify_resources,
    download_resources,
)
from services.lake import DEFAULT_BUCKET, NLDT_ROOT, get_lake_client

DEFAULT_WATCHLIST = NLDT_ROOT / "data" / "donl-watchlist.json"
DEFAULT_REGISTRY = NLDT_ROOT / "data" / "donl-harvest-registry.json"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_watchlist(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_package_ids(watchlist: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for entry in watchlist.get("datasets") or []:
        pid = entry.get("ckanId") or entry.get("id") or entry.get("name")
        if pid:
            ids.append(str(pid))
    return ids


def _should_skip_download(entry: dict[str, Any] | None) -> bool:
    if not entry:
        return False
    return bool(entry.get("metadataOnly"))


def _entry_for_id(watchlist: dict[str, Any], package_id: str) -> dict[str, Any] | None:
    for entry in watchlist.get("datasets") or []:
        if str(entry.get("ckanId") or entry.get("id") or entry.get("name")) == package_id:
            return entry
    return None


def harvest_package(
    package: dict[str, Any],
    *,
    client: Any | None = None,
    retrieved_at: str | None = None,
    download_files: bool = True,
    max_download_bytes: int | None = None,
) -> dict[str, Any]:
    """Harvest one CKAN package to bronze + catalog/dcat (+ silver services manifest)."""
    lake = get_lake_client()
    retrieved = retrieved_at or _utc_stamp()
    dataset_id = package.get("name") or package.get("id") or "unknown"
    bronze_prefix = f"bronze/donl/ckan/{dataset_id}/{retrieved}"

    # Raw CKAN snapshot
    raw_key = f"{bronze_prefix}/package.json"
    raw_bytes = json.dumps(package, indent=2, ensure_ascii=False).encode("utf-8")
    raw_uri = lake.put_bytes(raw_key, raw_bytes, content_type="application/json")

    classified = classify_resources(package.get("resources") or [])
    download_results: list[dict[str, Any]] = []
    service_manifest: dict[str, Any] | None = None
    silver_service_uri: str | None = None

    if classified["service"]:
        service_manifest = build_service_manifest(package, classified["service"])
        svc_key = f"silver/donl/services/{dataset_id}/manifest.json"
        silver_service_uri = lake.put_bytes(
            svc_key,
            json.dumps(service_manifest, indent=2, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
        )

    if download_files and classified["download"]:
        from services.lake import fs_root

        local_files = fs_root() / DEFAULT_BUCKET / "bronze" / "donl" / dataset_id / "files"
        local_files.mkdir(parents=True, exist_ok=True)
        kwargs: dict[str, Any] = {}
        if max_download_bytes is not None:
            kwargs["max_bytes"] = max_download_bytes
        download_results = download_resources(
            package,
            classified["download"],
            files_dir=local_files,
            **kwargs,
        )
        lake_root = fs_root() / DEFAULT_BUCKET
        for item in download_results:
            if item.get("status") != "ok":
                continue
            local = Path(item["localPath"]).resolve()
            rel = local.relative_to(lake_root.resolve()).as_posix()
            item["lakeUri"] = lake.uri_for(rel)
            item["lakeKey"] = rel
            meta_path = local.with_suffix(local.suffix + ".meta.json")
            if not meta_path.is_file():
                meta_path.write_text(
                    json.dumps(
                        {"poc": "donl", "accessClass": "open", "source": "data.overheid.nl"},
                        indent=2,
                    ),
                    encoding="utf-8",
                )

    dcat = map_package_to_dcat(package, lake_uri=raw_uri, retrieved_at=retrieved)
    if silver_service_uri:
        dcat["nldt:serviceManifestUri"] = silver_service_uri
    cat_key = f"catalog/dcat/{dataset_id}.json"
    cat_uri = lake.put_bytes(
        cat_key,
        json.dumps(dcat, indent=2, ensure_ascii=False).encode("utf-8"),
        content_type="application/json",
    )

    return {
        "datasetId": dataset_id,
        "title": package.get("title"),
        "metadataModified": package.get("metadata_modified"),
        "retrievedAt": retrieved,
        "rawLakeUri": raw_uri,
        "rawLakeKey": raw_key,
        "dcatLakeUri": cat_uri,
        "dcatLakeKey": cat_key,
        "serviceManifestUri": silver_service_uri,
        "distributionSummary": dcat.get("nldt:distributionSummary"),
        "downloads": download_results,
        "registryEntry": package_registry_entry(package),
    }


def harvest_datasets(
    package_ids: list[str],
    *,
    ckan_client: CkanClient | None = None,
    download_files: bool = True,
    max_download_bytes: int | None = None,
) -> dict[str, Any]:
    """Harvest explicit CKAN package ids."""
    owns_client = ckan_client is None
    client = ckan_client or CkanClient()
    harvested: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    try:
        for pid in package_ids:
            try:
                package = client.package_show(pid)
                item = harvest_package(
                    package,
                    download_files=download_files,
                    max_download_bytes=max_download_bytes,
                )
                harvested.append(item)
            except Exception as exc:  # noqa: BLE001
                errors.append({"packageId": pid, "error": str(exc)})
    finally:
        if owns_client:
            client.close()

    summary = {
        "status": "ok" if harvested else ("partial" if errors else "empty"),
        "harvestedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(harvested),
        "errorCount": len(errors),
        "datasets": harvested,
        "errors": errors,
    }
    return summary


def harvest_watchlist(
    watchlist_path: Path | None = None,
    *,
    download_files: bool = True,
    max_download_bytes: int | None = None,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    """Harvest datasets listed in donl-watchlist.json and refresh registry."""
    watchlist_path = watchlist_path or DEFAULT_WATCHLIST
    watchlist = _load_watchlist(watchlist_path)
    package_ids = _resolve_package_ids(watchlist)

    with CkanClient() as client:
        harvested: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for pid in package_ids:
            entry = _entry_for_id(watchlist, pid)
            try:
                package = client.package_show(pid)
                item = harvest_package(
                    package,
                    download_files=download_files and not _should_skip_download(entry),
                    max_download_bytes=max_download_bytes,
                )
                harvested.append(item)
            except Exception as exc:  # noqa: BLE001
                errors.append({"packageId": pid, "error": str(exc)})

    registry_path = registry_path or DEFAULT_REGISTRY
    registry = {
        "version": "1.0",
        "description": "DONL harvest registry for source monitor continuity checks",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "watchlistPath": str(watchlist_path),
        "sources": [h["registryEntry"] for h in harvested],
    }
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Also sync registry to lake silver
    lake = get_lake_client()
    reg_key = "silver/donl/meta/harvest-registry.json"
    reg_uri = lake.put_bytes(
        reg_key,
        json.dumps(registry, indent=2, ensure_ascii=False).encode("utf-8"),
        content_type="application/json",
    )

    return {
        "status": "ok" if harvested else ("partial" if errors else "empty"),
        "harvestedAt": datetime.now(timezone.utc).isoformat(),
        "watchlistPath": str(watchlist_path),
        "registryPath": str(registry_path),
        "registryLakeUri": reg_uri,
        "count": len(harvested),
        "errorCount": len(errors),
        "datasets": harvested,
        "errors": errors,
    }
