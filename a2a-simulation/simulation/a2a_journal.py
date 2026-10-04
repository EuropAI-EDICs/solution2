"""Journal helpers for A2A message/send results."""

from __future__ import annotations

import json
import re
from typing import Any

import journal


def metrics_from_response(result: dict[str, Any]) -> dict[str, Any]:
    text = result.get("responseText") or ""
    out: dict[str, Any] = {"agentId": result.get("agentId"), "eventCount": result.get("eventCount")}
    for blob in (text, json.dumps(result.get("events") or [])[:4000]):
        try:
            data = json.loads(text) if blob == text and text.strip().startswith("{") else None
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            _walk_metrics(data, out)
        for key in (
            "conflictCells",
            "aoiKm2",
            "finalOpportunityKm2",
            "rulesExecuted",
            "status",
            "mode",
        ):
            m = re.search(rf'"{key}"\s*:\s*("([^"]+)"|([\d.]+))', blob)
            if m and key not in out:
                out[key] = m.group(2) or m.group(3)
    if "mode" not in out and "nldt" in text.lower():
        out["mode"] = "nldt"
    if len(text) > 400:
        out["responsePreview"] = text[:400] + "…"
    else:
        out["responsePreview"] = text
    return out


def _walk_metrics(obj: Any, out: dict[str, Any], depth: int = 0) -> None:
    if depth > 6 or not isinstance(obj, dict):
        return
    for k, v in obj.items():
        if k in ("conflictCells", "aoiKm2", "finalOpportunityKm2", "rulesExecuted", "status", "mode"):
            if k not in out:
                out[k] = v
        if isinstance(v, dict):
            _walk_metrics(v, out, depth + 1)


def log_send(poc_id: str, message: str, port: int | None = None) -> None:
    journal.append(
        "a2a_send",
        "orchestrator",
        f"A2A message/send → {poc_id}",
        poc_id=poc_id,
        port=port,
        messagePreview=message[:240],
    )


def log_result(poc_id: str, result: dict[str, Any]) -> None:
    metrics = metrics_from_response(result)
    journal.append(
        "a2a_result",
        poc_id,
        f"A2A artifact van {poc_id}",
        poc_id=poc_id,
        metrics=metrics,
        url=result.get("url"),
    )
