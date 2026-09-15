"""Probe DONL CKAN registry entries for metadata/resource continuity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from services.common.prov import utc_now
from services.donl_harvest.ckan import CKAN_ACTION_BASE


def _head_ok(url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    if not url:
        return {"url": url, "reachable": False, "error": "missing url"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.head(url)
            if resp.status_code >= 400:
                resp = client.get(url, headers={"Range": "bytes=0-0"})
            return {
                "url": url,
                "reachable": resp.status_code < 400,
                "httpStatus": resp.status_code,
            }
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "reachable": False, "error": str(exc)}


def probe_donl_source_live(source: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    """Live probe: CKAN package_show + resource URL reachability."""
    sid = source.get("id") or source.get("ckanId") or "unknown"
    ckan_id = source.get("ckanId") or sid
    checked = utc_now()
    result: dict[str, Any] = {
        "sourceId": sid,
        "type": "donl",
        "ckanId": ckan_id,
        "probedAt": checked,
        "probeStatus": "ok",
        "mode": "live",
    }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(
                f"{CKAN_ACTION_BASE}/package_show",
                params={"id": ckan_id},
            )
            if resp.status_code >= 400:
                result["probeStatus"] = "error"
                result["error"] = f"CKAN HTTP {resp.status_code}"
                return result
            body = resp.json()
            if not body.get("success"):
                result["probeStatus"] = "error"
                result["error"] = str(body.get("error"))
                return result
            package = body["result"]
            resources = package.get("resources") or []
            result["metadataModified"] = package.get("metadata_modified")
            result["resourceCount"] = len(resources)
            result["resourceUrls"] = [r.get("url") for r in resources if r.get("url")]
            url_checks = [_head_ok(u, timeout=min(timeout, 15.0)) for u in result["resourceUrls"][:5]]
            result["resourceUrlChecks"] = url_checks
            unreachable = [c for c in url_checks if not c.get("reachable")]
            if unreachable:
                result["probeStatus"] = "warn"
                result["unreachableCount"] = len(unreachable)
    except Exception as exc:  # noqa: BLE001
        result["probeStatus"] = "error"
        result["error"] = str(exc)
    return result


def probe_donl_source_replay(source: dict[str, Any], fixture_dir: Path) -> dict[str, Any]:
    sid = source.get("id") or source.get("ckanId") or "unknown"
    path = fixture_dir / f"{sid}.json"
    checked = utc_now()
    if not path.is_file():
        return {
            "sourceId": sid,
            "type": "donl",
            "probedAt": checked,
            "probeStatus": "error",
            "mode": "replay",
            "error": f"fixture missing: {path.name}",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("sourceId", sid)
    data.setdefault("type", "donl")
    data.setdefault("probedAt", checked)
    data.setdefault("mode", "replay")
    data.setdefault("probeStatus", "ok")
    return data


def diff_donl_probe(probe_bundle: dict[str, Any]) -> dict[str, Any]:
    """Diff DONL probe results against registry snapshot."""
    snapshot = probe_bundle.get("registrySnapshot") or {}
    findings: list[dict[str, Any]] = []
    worst = "ok"
    order = {"ok": 0, "warn": 1, "critical": 2}

    for row in probe_bundle.get("results") or []:
        sid = row.get("sourceId")
        reg = snapshot.get(sid) or {}
        finding: dict[str, Any] = {
            "sourceId": sid,
            "type": "donl",
            "probeStatus": row.get("probeStatus"),
            "registeredMetadataModified": reg.get("metadataModified"),
            "liveMetadataModified": row.get("metadataModified"),
            "registeredResourceCount": reg.get("resourceCount"),
            "liveResourceCount": row.get("resourceCount"),
            "changes": [],
        }

        if row.get("probeStatus") == "error":
            finding["severity"] = "critical"
            finding["changes"].append({"field": "probe", "detail": row.get("error")})
        else:
            if reg.get("metadataModified") and row.get("metadataModified"):
                if reg["metadataModified"] != row["metadataModified"]:
                    finding["changes"].append(
                        {
                            "field": "metadataModified",
                            "from": reg["metadataModified"],
                            "to": row["metadataModified"],
                        }
                    )
            reg_count = reg.get("resourceCount")
            live_count = row.get("resourceCount")
            if reg_count is not None and live_count is not None and reg_count != live_count:
                finding["changes"].append(
                    {"field": "resourceCount", "from": reg_count, "to": live_count}
                )
            unreachable = int(row.get("unreachableCount") or 0)
            if unreachable:
                finding["changes"].append(
                    {"field": "resourceUrls", "detail": f"{unreachable} unreachable"}
                )

            if row.get("probeStatus") == "warn" or finding["changes"]:
                finding["severity"] = "warn"
            else:
                finding["severity"] = "ok"

        if order.get(finding.get("severity"), 0) > order.get(worst, 0):
            worst = finding["severity"]
        if finding["changes"] or finding.get("severity") != "ok":
            findings.append(finding)

    return {
        "worstSeverity": worst,
        "findingCount": len(findings),
        "criticalCount": sum(1 for f in findings if f.get("severity") == "critical"),
        "warnCount": sum(1 for f in findings if f.get("severity") == "warn"),
        "findings": findings,
        "probedAt": probe_bundle.get("probedAt"),
        "registryPath": probe_bundle.get("registryPath"),
        "mode": probe_bundle.get("mode"),
    }
