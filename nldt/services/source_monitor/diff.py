"""Machine diff: registry snapshot vs live/replay probe."""

from __future__ import annotations

from typing import Any


def _severity_for_count(
    registered: int | None,
    live: int | None,
    max_record: int | None,
) -> str:
    if registered is None or live is None:
        return "warn"
    if registered <= 0:
        return "ok" if live == registered else "warn"
    drop_ratio = (registered - live) / registered
    # Page-cap collapse: live equals maxRecordCount while registry is much larger
    if max_record and live == max_record and registered > max_record * 2:
        return "critical"
    if drop_ratio >= 0.5:
        return "critical"
    if drop_ratio >= 0.1 or live > registered * 1.1:
        return "warn"
    return "ok"


def diff_probe(probe_bundle: dict[str, Any]) -> dict[str, Any]:
    """Compare probe results to registrySnapshot embedded in the probe bundle."""
    snapshot = probe_bundle.get("registrySnapshot") or {}
    findings: list[dict[str, Any]] = []
    worst = "ok"

    for row in probe_bundle.get("results") or []:
        sid = row.get("sourceId")
        reg = snapshot.get(sid) or {}
        finding: dict[str, Any] = {
            "sourceId": sid,
            "probeStatus": row.get("probeStatus"),
            "registeredFeatureCount": reg.get("featureCount"),
            "liveFeatureCount": row.get("featureCount"),
            "registeredMaxRecordCount": reg.get("maxRecordCount"),
            "liveMaxRecordCount": row.get("maxRecordCount"),
            "changes": [],
        }

        if row.get("probeStatus") == "error":
            finding["severity"] = "critical"
            finding["changes"].append(
                {"field": "probe", "detail": row.get("error") or "probe error"}
            )
        else:
            sev = _severity_for_count(
                reg.get("featureCount"),
                row.get("featureCount"),
                row.get("maxRecordCount") or reg.get("maxRecordCount"),
            )
            if reg.get("featureCount") != row.get("featureCount"):
                finding["changes"].append(
                    {
                        "field": "featureCount",
                        "from": reg.get("featureCount"),
                        "to": row.get("featureCount"),
                    }
                )
            if reg.get("maxRecordCount") != row.get("maxRecordCount") and row.get(
                "maxRecordCount"
            ) is not None:
                finding["changes"].append(
                    {
                        "field": "maxRecordCount",
                        "from": reg.get("maxRecordCount"),
                        "to": row.get("maxRecordCount"),
                    }
                )
            reg_fields = set(reg.get("fieldNames") or [])
            live_fields = set(row.get("fieldNames") or [])
            if live_fields and reg_fields and reg_fields != live_fields:
                finding["changes"].append(
                    {
                        "field": "fields",
                        "added": sorted(live_fields - reg_fields),
                        "removed": sorted(reg_fields - live_fields),
                    }
                )
                if sev == "ok":
                    sev = "warn"
            if not finding["changes"] and row.get("probeStatus") == "ok":
                sev = "ok"
            finding["severity"] = sev

        findings.append(finding)
        order = {"ok": 0, "warn": 1, "critical": 2}
        if order.get(finding["severity"], 0) > order.get(worst, 0):
            worst = finding["severity"]

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
