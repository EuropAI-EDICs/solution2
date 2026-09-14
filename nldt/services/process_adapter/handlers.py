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
from services.process_adapter.poc_handlers import (
    POC_PROCESS_DEFINITIONS,
    execute_poc_process,
)


def _load_source(source: str | dict[str, Any] | list[Any], aoi: Any = None) -> dict[str, Any] | list[Any]:
    if isinstance(source, (dict, list)):
        return source
    if source.startswith("ngsi-ld://"):
        from services.hybrid_bridge import fetch_ngsi_as_features

        entity_type = source.replace("ngsi-ld://", "").split("?")[0]
        return fetch_ngsi_as_features(entity_type)
    if source.startswith("file://"):
        path = Path(urlparse(source).path)
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    if source.startswith("lake://") or source.startswith("s3://"):
        from services.lake import resolve_uri_to_local

        path = resolve_uri_to_local(source)
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    if source.startswith("{") or source.startswith("["):
        return json.loads(source)
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(source)
        resp.raise_for_status()
        return resp.json()


PROCESS_DEFINITIONS_CORE: dict[str, dict[str, Any]] = {
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
            "polygon": {"title": "Polygon (GeoJSON or file:// URI, EPSG:4326/RFC 7946)",
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
            "points": {"title": "Points (GeoJSON or file:// URI, EPSG:4326/RFC 7946)",
                       "schema": {"type": ["object", "string"]}},
            "cells": {"title": "Cell set (else polygon+resolution)",
                      "schema": {"type": "array", "items": {"type": "string"}}},
            "polygon": {"title": "Polygon to derive cells from (EPSG:4326)",
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
    "h3-grid-disk": {
        "id": "h3-grid-disk",
        "title": "H3 grid_disk neighbours",
        "description": "Origin plus all cells within k steps, per input cell (display stitching, proximity rings)",
        "version": "1.0.0",
        "inputs": {
            "cells": {"title": "H3 cell indexes",
                      "schema": {"type": "array", "items": {"type": "string"}}},
            "ring": {"title": "Ring distance k (default 1)",
                     "schema": {"type": "integer"}},
        },
        "outputs": {
            "disk": {"title": "Per-cell disks", "schema": {"type": "object"}},
        },
    },
    "lake-publish-dataset": {
        "id": "lake-publish-dataset",
        "title": "Publish lake dataset to Data Space",
        "description": (
            "Create an ODRL-stub offer for a lake:// or s3:// dataset. "
            "Rejects accessClass=restricted unless forceHitlApproved=true."
        ),
        "version": "1.0.0",
        "inputs": {
            "lakeUri": {"title": "Lake URI", "schema": {"type": "string"}},
            "lakeKey": {"title": "Lake object key", "schema": {"type": "string"}},
            "datasetId": {"title": "Dataset id", "schema": {"type": "string"}},
            "accessClass": {
                "title": "open|internal|restricted",
                "schema": {"type": "string"},
            },
            "forceHitlApproved": {
                "title": "HITL override for restricted",
                "schema": {"type": "boolean", "default": False},
            },
            "license": {"title": "License string", "schema": {"type": "string"}},
        },
        "outputs": {
            "result": {"title": "Publish result", "schema": {"type": "object"}},
        },
    },
}


PROCESS_DEFINITIONS: dict[str, dict[str, Any]] = {
    **PROCESS_DEFINITIONS_CORE,
    **POC_PROCESS_DEFINITIONS,
}


def list_processes() -> list[dict[str, Any]]:
    return list(PROCESS_DEFINITIONS.values())


def describe_process(process_id: str) -> dict[str, Any]:
    if process_id not in PROCESS_DEFINITIONS:
        raise KeyError(process_id)
    return PROCESS_DEFINITIONS[process_id]


def execute_local(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if process_id in POC_PROCESS_DEFINITIONS:
        return execute_poc_process(process_id, inputs)
    if process_id == "fetch-features":
        fc = _load_source(inputs["source"], inputs.get("aoi"))
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
    if process_id == "h3-grid-disk":
        return {"disk": h3kit.grid_disk_cells(
            list(inputs["cells"]), inputs.get("ring", 1))}
    if process_id == "lake-publish-dataset":
        from services.lake.publish import publish_dataset

        return {
            "result": publish_dataset(
                lake_uri=inputs.get("lakeUri"),
                lake_key=inputs.get("lakeKey"),
                dataset_id=inputs.get("datasetId"),
                access_class=inputs.get("accessClass"),
                force_hitl_approved=bool(inputs.get("forceHitlApproved")),
                license_=inputs.get("license"),
            )
        }
    raise KeyError(f"Unknown process: {process_id}")
