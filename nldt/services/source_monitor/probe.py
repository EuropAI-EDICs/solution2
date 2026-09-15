"""Probe ArcGIS REST layer metadata + feature counts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from services.common.prov import utc_now


def _layer_meta_url(service_url: str, layer_id: int | str) -> str:
    base = service_url.rstrip("/") + "/"
    return urljoin(base, f"{layer_id}?f=json")


def _count_url(service_url: str, layer_id: int | str) -> str:
    base = service_url.rstrip("/") + "/"
    return urljoin(base, f"{layer_id}/query?where=1%3D1&returnCountOnly=true&f=json")


def probe_source_live(source: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    """Live HTTP probe of one registry source entry."""
    sid = source.get("id") or "unknown"
    service_url = source.get("serviceUrl") or ""
    layer_id = source.get("layerId", 0)
    checked = utc_now()
    result: dict[str, Any] = {
        "sourceId": sid,
        "serviceUrl": service_url,
        "layerId": layer_id,
        "probedAt": checked,
        "probeStatus": "ok",
        "mode": "live",
    }
    if not service_url:
        result["probeStatus"] = "error"
        result["error"] = "missing serviceUrl"
        return result

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            meta_resp = client.get(_layer_meta_url(service_url, layer_id))
            if meta_resp.status_code >= 400:
                result["probeStatus"] = "error"
                result["error"] = f"metadata HTTP {meta_resp.status_code}"
                result["httpStatus"] = meta_resp.status_code
                return result
            meta = meta_resp.json()
            if isinstance(meta, dict) and meta.get("error"):
                result["probeStatus"] = "error"
                result["error"] = str(meta["error"])
                return result

            fields = meta.get("fields") or []
            result["maxRecordCount"] = meta.get("maxRecordCount")
            result["geometryType"] = meta.get("geometryType")
            result["fieldNames"] = [
                f.get("name") for f in fields if isinstance(f, dict) and f.get("name")
            ]

            count_resp = client.get(_count_url(service_url, layer_id))
            if count_resp.status_code >= 400:
                result["probeStatus"] = "error"
                result["error"] = f"count HTTP {count_resp.status_code}"
                result["httpStatus"] = count_resp.status_code
                return result
            count_body = count_resp.json()
            if isinstance(count_body, dict) and "count" in count_body:
                result["featureCount"] = count_body["count"]
            elif isinstance(count_body, dict) and count_body.get("error"):
                result["probeStatus"] = "warn"
                result["error"] = f"count unsupported: {count_body['error']}"
            else:
                result["probeStatus"] = "warn"
                result["error"] = "count response missing count"
    except Exception as exc:  # noqa: BLE001 — probe must not crash the run
        result["probeStatus"] = "error"
        result["error"] = str(exc)
    return result


def probe_source_replay(source: dict[str, Any], fixture_dir: Path) -> dict[str, Any]:
    """Load probe result from fixtures/{sourceId}.json."""
    sid = source.get("id") or "unknown"
    path = fixture_dir / f"{sid}.json"
    checked = utc_now()
    if not path.is_file():
        return {
            "sourceId": sid,
            "probedAt": checked,
            "probeStatus": "error",
            "mode": "replay",
            "error": f"fixture missing: {path.name}",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("sourceId", sid)
    data.setdefault("probedAt", checked)
    data.setdefault("mode", "replay")
    data.setdefault("probeStatus", "ok")
    return data


def load_registry(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_sources(
    registry: dict[str, Any],
    *,
    allowlist: list[str] | None = None,
) -> list[dict[str, Any]]:
    sources = list(registry.get("sources") or [])
    if allowlist:
        allowed = set(allowlist)
        sources = [s for s in sources if s.get("id") in allowed]
    return sources


def _registry_snapshot(sources: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for s in sources:
        sid = s.get("id")
        if s.get("type") == "donl":
            snapshot[sid] = {
                "metadataModified": s.get("metadataModified"),
                "resourceCount": s.get("resourceCount"),
                "resourceUrls": s.get("resourceUrls"),
                "lastChecked": s.get("lastChecked"),
            }
        else:
            snapshot[sid] = {
                "featureCount": s.get("featureCount"),
                "maxRecordCount": s.get("maxRecordCount"),
                "serviceUrl": s.get("serviceUrl"),
                "layerId": s.get("layerId"),
                "fieldNames": [
                    f.get("name") for f in (s.get("fields") or []) if isinstance(f, dict)
                ],
                "lastChecked": s.get("lastChecked"),
            }
    return snapshot


def probe_registry(
    registry_path: Path,
    *,
    mode: str = "replay",
    fixture_dir: Path | None = None,
    allowlist: list[str] | None = None,
    timeout: float = 30.0,
    registry_type: str | None = None,
) -> dict[str, Any]:
    from services.source_monitor.donl_probe import (
        probe_donl_source_live,
        probe_donl_source_replay,
    )

    registry = load_registry(registry_path)
    sources = select_sources(registry, allowlist=allowlist)
    results: list[dict[str, Any]] = []
    for src in sources:
        is_donl = registry_type == "donl" or src.get("type") == "donl"
        if is_donl:
            if mode == "live":
                results.append(probe_donl_source_live(src, timeout=timeout))
            else:
                if fixture_dir is None:
                    raise ValueError("fixture_dir required for replay mode")
                results.append(probe_donl_source_replay(src, fixture_dir))
            continue
        if mode == "live":
            results.append(probe_source_live(src, timeout=timeout))
        else:
            if fixture_dir is None:
                raise ValueError("fixture_dir required for replay mode")
            results.append(probe_source_replay(src, fixture_dir))
    return {
        "registryPath": str(registry_path),
        "registryType": registry_type or ("donl" if any(s.get("type") == "donl" for s in sources) else "arcgis"),
        "mode": mode,
        "probedAt": utc_now(),
        "sourceCount": len(results),
        "results": results,
        "registrySnapshot": _registry_snapshot(sources),
    }
