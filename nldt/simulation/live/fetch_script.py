"""Stappenlijst fetch-keten v1 — data, geen vertakking.

Spec: docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md.
Elke stap is precies één MCP-toolcall; samenvattingen zijn pure functies van
het ruwe tool-resultaat (JSON-string).
"""

from __future__ import annotations

import json
from typing import Any


def _count_top_level(raw: str) -> str:
    data = json.loads(raw)
    if isinstance(data, list):
        return f"{len(data)} items"
    if isinstance(data, dict):
        return f"{len(data)} sleutels"
    return "ok"


def _sum_poc_tool(raw: str) -> str:
    payload = json.loads(raw)  # poc-server-patroon {tool, processId, status, outputs}
    s = (payload.get("outputs") or {}).get("summary") or {}
    return f"{s.get('featureCount')} features · {s.get('title')}"


def _sum_entities(raw: str) -> str:
    ents = json.loads(raw)
    mock = any(isinstance(e, dict) and e.get("mock") for e in ents)
    return f"{len(ents)} entities{' (mock)' if mock else ''}"


def _sum_fc(raw: str) -> str:
    fc = json.loads(raw)
    return f"{len(fc.get('features') or [])} features"


STAPPEN: list[dict[str, Any]] = [
    {
        "label": "Wat is beschikbaar?",
        "server": "catalog",
        "tool": "list_poc_capabilities",
        "args": {},
        "samenvatting": _count_top_level,
    },
    {
        "label": "Regels-instrumenten in het gebied",
        "server": "dso",
        "tool": "dso_kb_overview",
        "args": {},
        "samenvatting": _count_top_level,
    },
    {
        "label": "Inclusion-zone wind (agrest)",
        "server": "poc",
        "tool": "fetch_geo_layer",
        "args": {"source_id": "agrest-ov-gebied-windenergie"},
        "laag": {"source_id": "agrest-ov-gebied-windenergie", "laagtype": "zone"},
        "samenvatting": _sum_poc_tool,
    },
    {
        "label": "Kaartlaag wind (ArcGIS Online)",
        "server": "poc",
        "tool": "fetch_geo_layer",
        "args": {"source_id": "arcgis-et-wind-gebieden"},
        "laag": {"source_id": "arcgis-et-wind-gebieden", "laagtype": "zone"},
        "samenvatting": _sum_poc_tool,
    },
    {
        "label": "NGSI-LD entities (lucht)",
        "server": "data",
        "tool": "list_entities",
        "args": {"entity_type": "AirQualityObserved"},
        "samenvatting": _sum_entities,
    },
    {
        "label": "NGSI-LD → GeoJSON",
        "server": "data",
        "tool": "entities_to_geojson",
        "args": {"entity_type": "AirQualityObserved"},
        "laag": {"source_id": "ngsi-ld-dpl-airquality", "laagtype": "punten", "inline": True},
        "samenvatting": _sum_fc,
    },
]
