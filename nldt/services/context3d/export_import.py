from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.common.prov import utc_now


def _bbox_from_geojson(fc: dict[str, Any]) -> list[float]:
    coords: list[tuple[float, float]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, list):
            if obj and isinstance(obj[0], (int, float)):
                if len(obj) >= 2:
                    coords.append((float(obj[0]), float(obj[1])))
            else:
                for item in obj:
                    walk(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)

    walk(fc.get("features", []))
    if not coords:
        return [0.0, 0.0, 1.0, 1.0]
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def _default_viewpoint(bbox: list[float], projection: str = "EPSG:28992") -> dict[str, Any]:
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    span = max(bbox[2] - bbox[0], bbox[3] - bbox[1], 1.0)
    altitude = span * 2.5
    return {
        "camera": {
            "position": [cx, cy, altitude],
            "direction": [0, 0, -1],
            "up": [0, 1, 0],
        },
        "projection": projection,
    }


def export_from_execution(
    execution: dict[str, Any],
    *,
    run_id: str | None = None,
    title: str | None = None,
    layer_href_base: str | None = None,
) -> dict[str, Any]:
    """Build Web3DContext from recipe execution outputs."""
    recipe_id = execution.get("recipeId", "unknown")
    outputs = execution.get("outputs", {})
    intersection = outputs.get("intersection")
    if not intersection:
        raise ValueError("execution outputs must include intersection GeoJSON")

    bbox = _bbox_from_geojson(intersection)
    layer_id = "overlay-result"
    href = layer_href_base or f"urn:nldt:geojson:{recipe_id}:{run_id or uuid4()}"

    prov_activities = [
        s.get("prov", {}).get("activity", "")
        for s in execution.get("steps", [])
        if s.get("prov")
    ]

    return {
        "type": "Web3DContext",
        "version": "1.0.0",
        "id": f"context-{run_id or uuid4()}",
        "title": title or f"3D context for {recipe_id}",
        "description": f"Exported from nLDT recipe execution {recipe_id}",
        "viewpoint": _default_viewpoint(bbox),
        "bbox": bbox,
        "time": None,
        "services": [
            {
                "id": "nldt-process-adapter",
                "type": "process",
                "href": "http://localhost:8082",
                "title": "nLDT Process Adapter",
            }
        ],
        "layers": [
            {
                "id": layer_id,
                "type": "geojson",
                "href": href,
                "title": execution.get("recipeId", "result"),
                "visible": True,
                "opacity": 0.85,
            }
        ],
        "provenance": {
            "recipeId": recipe_id,
            "runId": run_id,
            "generatedAt": utc_now(),
            "provActivities": prov_activities,
        },
        "metadata": {
            "statistics": outputs.get("statistics"),
            "inlineGeoJson": intersection,
        },
    }


def import_context(document: dict[str, Any]) -> dict[str, Any]:
    """Parse imported Web3DContext; return normalized layer list and viewpoint."""
    if document.get("type") != "Web3DContext":
        raise ValueError("not a Web3DContext document")
    layers = document.get("layers", [])
    return {
        "id": document.get("id"),
        "title": document.get("title"),
        "viewpoint": document.get("viewpoint"),
        "bbox": document.get("bbox"),
        "layers": [
            {"id": l["id"], "type": l["type"], "href": l["href"], "title": l.get("title")}
            for l in layers
        ],
        "provenance": document.get("provenance"),
        "inlineGeoJson": document.get("metadata", {}).get("inlineGeoJson"),
    }


def save_context(document: dict[str, Any], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{document['id']}.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def load_context(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)
