from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from services.common import h3kit
from services.common.geo import (
    area_statistics,
    intersect_feature_collections,
    parse_geojson_input,
)


def _load_source(source: str, aoi: Any = None) -> dict[str, Any]:
    if source.startswith("ngsi-ld://"):
        from services.hybrid_bridge import fetch_ngsi_as_features

        entity_type = source.replace("ngsi-ld://", "").split("?")[0]
        return fetch_ngsi_as_features(entity_type)
    if source.startswith("file://"):
        path = Path(urlparse(source).path)
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    if source.startswith("{") or source.startswith("["):
        return json.loads(source)
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(source)
        resp.raise_for_status()
        return resp.json()


PROCESS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "fetch-features": {
        "id": "fetch-features",
        "title": "Fetch features",
        "description": "Load GeoJSON from URI or inline and optionally clip to AOI",
        "version": "1.0.0",
        "inputs": {
            "source": {"title": "Source URI or GeoJSON", "schema": {"type": "string"}},
            "aoi": {"title": "Area of interest", "schema": {"type": "object"}},
        },
        "outputs": {
            "features": {"title": "FeatureCollection", "schema": {"type": "object"}},
        },
    },
    "spatial-intersection": {
        "id": "spatial-intersection",
        "title": "Spatial intersection",
        "description": "Intersect two GeoJSON FeatureCollections",
        "version": "1.0.0",
        "inputs": {
            "layerA": {"title": "Layer A", "schema": {"type": "object"}},
            "layerB": {"title": "Layer B", "schema": {"type": "object"}},
        },
        "outputs": {
            "result": {"title": "Intersection", "schema": {"type": "object"}},
        },
    },
    "compute-area-statistics": {
        "id": "compute-area-statistics",
        "title": "Compute area statistics",
        "description": "Compute planar area statistics for features",
        "version": "1.0.0",
        "inputs": {
            "features": {"title": "FeatureCollection", "schema": {"type": "object"}},
        },
        "outputs": {
            "statistics": {"title": "Statistics JSON", "schema": {"type": "object"}},
        },
    },
    "h3-polygon-to-cells": {
        "id": "h3-polygon-to-cells",
        "title": "H3 polygon to cells",
        "description": "Discretise a GeoJSON polygon layer into H3 cells with planar EPSG:28992 coverage fractions; optional restrictCells / compact",
        "version": "1.0.0",
        "inputs": {
            "polygon": {"title": "Polygon (GeoJSON or file:// URI)",
                        "schema": {"type": ["object", "string"]}},
            "resolution": {"title": "H3 resolution (default 8)",
                           "schema": {"type": "integer"}},
            "restrictCells": {"title": "Compute coverage for exactly these cells",
                              "schema": {"type": "array",
                                         "items": {"type": "string"}}},
            "compact": {"title": "Also emit a compacted cell set",
                        "schema": {"type": "boolean"}},
        },
        "outputs": {
            "coverage": {"title": "H3Coverage", "schema": {"type": "object"}},
        },
    },
    "h3-cells-to-geojson": {
        "id": "h3-cells-to-geojson",
        "title": "H3 cells to GeoJSON",
        "description": "Cell boundaries as a GeoJSON FeatureCollection",
        "version": "1.0.0",
        "inputs": {
            "cells": {"title": "H3 cell indexes",
                      "schema": {"type": "array", "items": {"type": "string"}}},
        },
        "outputs": {
            "features": {"title": "FeatureCollection", "schema": {"type": "object"}},
        },
    },
    "h3-spatial-join-points": {
        "id": "h3-spatial-join-points",
        "title": "H3 spatial join (points)",
        "description": "Index points (or footprint centroids) into cells; counts per cell",
        "version": "1.0.0",
        "inputs": {
            "points": {"title": "Points (GeoJSON or file:// URI)",
                       "schema": {"type": ["object", "string"]}},
            "cells": {"title": "Cell set (else polygon+resolution)",
                      "schema": {"type": "array", "items": {"type": "string"}}},
            "polygon": {"title": "Polygon to derive cells from",
                        "schema": {"type": ["object", "string"]}},
            "resolution": {"title": "H3 resolution (default 8)",
                           "schema": {"type": "integer"}},
        },
        "outputs": {
            "join": {"title": "Join result", "schema": {"type": "object"}},
        },
    },
    "h3-knn": {
        "id": "h3-knn",
        "title": "H3 K nearest neighbours",
        "description": "Nearest candidates by H3 grid distance with haversine tie-break",
        "version": "1.0.0",
        "inputs": {
            "point": {"title": "Origin {lat, lng}", "schema": {"type": "object"}},
            "candidates": {"title": "Candidate points",
                           "schema": {"type": "array"}},
            "k": {"title": "K (default 1)", "schema": {"type": "integer"}},
            "resolution": {"title": "H3 resolution (default 8)",
                           "schema": {"type": "integer"}},
        },
        "outputs": {
            "neighbors": {"title": "Ranked neighbours", "schema": {"type": "object"}},
        },
    },
    "h3-morans-i": {
        "id": "h3-morans-i",
        "title": "Global Moran's I (H3)",
        "description": "Spatial autocorrelation over grid_disk neighbourhoods; seeded permutation p-value",
        "version": "1.0.0",
        "inputs": {
            "values": {"title": "Cell values (map, rows, or join perCell)",
                       "schema": {"type": ["object", "array"]}},
            "permutations": {"title": "Permutations (default 199)",
                             "schema": {"type": "integer"}},
        },
        "outputs": {
            "statistics": {"title": "Moran's I statistics", "schema": {"type": "object"}},
        },
    },
}


def list_processes() -> list[dict[str, Any]]:
    return list(PROCESS_DEFINITIONS.values())


def describe_process(process_id: str) -> dict[str, Any]:
    if process_id not in PROCESS_DEFINITIONS:
        raise KeyError(process_id)
    return PROCESS_DEFINITIONS[process_id]


def execute_local(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if process_id == "fetch-features":
        fc = _load_source(str(inputs["source"]), inputs.get("aoi"))
        return {"features": fc}
    if process_id == "spatial-intersection":
        a = parse_geojson_input(inputs["layerA"])
        b = parse_geojson_input(inputs["layerB"])
        return {"result": intersect_feature_collections(a, b)}
    if process_id == "compute-area-statistics":
        fc = parse_geojson_input(inputs["features"])
        return {"statistics": area_statistics(fc)}
    if process_id == "h3-polygon-to-cells":
        return {"coverage": h3kit.polygon_to_cells(
            inputs["polygon"], inputs.get("resolution", 8),
            restrict_cells=inputs.get("restrictCells"),
            compact=inputs.get("compact", False))}
    if process_id == "h3-cells-to-geojson":
        return {"features": h3kit.cells_to_geojson(list(inputs["cells"]))}
    if process_id == "h3-spatial-join-points":
        return {"join": h3kit.join_points_to_cells(
            inputs["points"], inputs.get("cells"),
            polygon=inputs.get("polygon"),
            resolution=inputs.get("resolution", 8))}
    if process_id == "h3-knn":
        return {"neighbors": h3kit.knn(
            inputs["point"], inputs["candidates"],
            inputs.get("k", 1), inputs.get("resolution", 8))}
    if process_id == "h3-morans-i":
        return {"statistics": h3kit.morans_i(
            inputs["values"], inputs.get("permutations", 199))}
    raise KeyError(f"Unknown process: {process_id}")
