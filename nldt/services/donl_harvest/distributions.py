"""Classify and fetch DONL distributions (download vs DataService)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx

from services.donl_harvest.dcat_map import _is_service_resource, safe_filename

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MiB per file in PoC harvest


def classify_resources(resources: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    downloads: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    for resource in resources:
        if _is_service_resource(resource):
            services.append(resource)
        else:
            downloads.append(resource)
    return {"download": downloads, "service": services}


def fetch_download(
    resource: dict[str, Any],
    *,
    dest: Path,
    timeout: float = 120.0,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> dict[str, Any]:
    url = resource.get("url") or ""
    result: dict[str, Any] = {
        "resourceId": resource.get("id"),
        "url": url,
        "status": "skipped",
    }
    if not url:
        result["error"] = "missing url"
        return result

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
            if resp.status_code >= 400:
                result["status"] = "error"
                result["httpStatus"] = resp.status_code
                result["error"] = f"HTTP {resp.status_code}"
                return result
            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > max_bytes:
                result["status"] = "skipped"
                result["error"] = f"content-length {content_length} exceeds max {max_bytes}"
                return result
            hasher = hashlib.sha256()
            total = 0
            with dest.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=1 << 16):
                    total += len(chunk)
                    if total > max_bytes:
                        fh.close()
                        dest.unlink(missing_ok=True)
                        result["status"] = "skipped"
                        result["error"] = f"download exceeded max {max_bytes} bytes"
                        return result
                    hasher.update(chunk)
                    fh.write(chunk)
        result["status"] = "ok"
        result["bytes"] = total
        result["sha256"] = hasher.hexdigest()
        result["localPath"] = str(dest)
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"
        result["error"] = str(exc)
    return result


def build_service_manifest(
    package: dict[str, Any],
    services: list[dict[str, Any]],
) -> dict[str, Any]:
    dataset_id = package.get("name") or package.get("id")
    return {
        "datasetId": dataset_id,
        "title": package.get("title"),
        "metadataModified": package.get("metadata_modified"),
        "accessClass": "open",
        "hadPrimarySource": "data.overheid.nl",
        "services": [
            {
                "resourceId": r.get("id"),
                "name": r.get("name"),
                "url": r.get("url"),
                "format": r.get("format"),
                "distributionType": "DataService",
            }
            for r in services
        ],
    }


def download_resources(
    package: dict[str, Any],
    downloads: list[dict[str, Any]],
    *,
    files_dir: Path,
    timeout: float = 120.0,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for resource in downloads:
        rid = str(resource.get("id") or "unknown")
        fname = safe_filename(resource.get("name") or resource.get("url") or rid, fallback=rid)
        dest = files_dir / rid / fname
        results.append(
            fetch_download(resource, dest=dest, timeout=timeout, max_bytes=max_bytes)
        )
    return results
