"""Registry patch proposals — never applied by the monitor."""

from __future__ import annotations

from typing import Any

from services.common.prov import utc_now


def build_patch_proposal(diff: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    """Suggested field updates for human merge into sources.json."""
    by_id = {r.get("sourceId"): r for r in (probe.get("results") or [])}
    ops: list[dict[str, Any]] = []
    for finding in diff.get("findings") or []:
        if finding.get("severity") == "ok" and not finding.get("changes"):
            continue
        sid = finding.get("sourceId")
        live = by_id.get(sid) or {}
        suggested: dict[str, Any] = {"lastChecked": live.get("probedAt") or utc_now()}
        if live.get("featureCount") is not None:
            suggested["featureCount"] = live["featureCount"]
        if live.get("maxRecordCount") is not None:
            suggested["maxRecordCount"] = live["maxRecordCount"]
        ops.append(
            {
                "op": "replace",
                "sourceId": sid,
                "severity": finding.get("severity"),
                "path": f"/sources/[id={sid}]",
                "suggestedFields": suggested,
                "rationale": finding.get("changes") or [],
                "autoApply": False,
            }
        )
    return {
        "type": "registry-patch-proposal",
        "createdAt": utc_now(),
        "registryPath": diff.get("registryPath"),
        "autoApply": False,
        "note": "Human must merge; monitor never writes sources.json",
        "operations": ops,
    }
