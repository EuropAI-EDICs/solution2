from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from services.common.schema import validate_instance

COOKBOOK_BASE = os.environ.get("NLDT_COOKBOOK_URL", "http://localhost:8081")
CATALOG_BASE = os.environ.get("NLDT_CATALOG_URL", "http://localhost:8083")

# Catalogued applications (App Store records, type "application"). Every
# entry's descriptor is validated against application.schema.json at seed
# time — an invalid app fails loudly, it is never served unvalidated.
APPLICATIONS: list[tuple[str, str, dict[str, Any], list[str]]] = [
    (
        "beleidskompas",
        "Beleidskompas (GovChat-NL)",
        {
            "appId": "beleidskompas",
            "launchUrl": "https://www.govchat-nl.nl",
            "publisher": "GovChat-NL / Provincie Limburg",
            "trustLevel": "experimental",
            "docsUrl": "https://github.com/jeannotdamoiseaux/GovChat-NL/blob/main/docs/app-launcher/beleidskompas/beleidskompas.md",
            "requiredCapabilities": ["mcp", "ogc-processes"],
            "consumesRecipes": ["beleidskompas-omgevingsanalyse", "breda-scan-qa"],
        },
        ["beleidskompas", "govchat-nl", "policy", "app-launcher"],
    ),
]


def seed_records() -> list[dict[str, Any]]:
    processes = [
        ("fetch-features", "Fetch GeoJSON features from URI"),
        ("spatial-intersection", "Intersect two feature collections"),
        ("compute-area-statistics", "Compute area statistics"),
        ("h3-polygon-to-cells", "H3 hex coverage of a polygon layer"),
        ("h3-cells-to-geojson", "H3 cell boundaries as GeoJSON"),
        ("h3-spatial-join-points", "Join points to H3 cells (counts per cell)"),
        ("h3-knn", "K nearest points by H3 grid distance"),
        ("h3-morans-i", "Global Moran's I over H3 cell values"),
        ("h3-grid-disk", "H3 grid_disk neighbours per cell"),
        ("breda-scan-query", "Breda five-value scan Q&A (S4)"),
        ("scenario-author-propose", "Scenario author proposals (S7)"),
        ("scenario-sweep", "Utrecht scenario sweep (Plane B)"),
        ("opportunity-map-run", "Utrecht opportunity-map (Plane A)"),
        ("crosstrack-overlay", "Crosstrack overlay (Plane C)"),
        ("breda-scan-run", "Breda five-value scan run"),
        ("rijnland-peil-conflict", "Rijnland peil conflict (H3)"),
        ("rijnland-peil-whatif", "Rijnland peilen what-if (CDC)"),
        ("bp2op-transform", "Eindhoven bp2op transform"),
        ("lake-publish-dataset", "Publish lake dataset to Data Space (ODRL stub)"),
        ("validate-artifact", "Validate artifact against nLDT/PoC JSON Schema"),
    ]
    records: list[dict[str, Any]] = []
    for pid, title in processes:
        records.append(
            {
                "id": f"process-{pid}",
                "type": "process",
                "title": title,
                "properties": {
                    "processId": pid,
                    "tags": (
                        ["poc", "poc-eindhoven"]
                        if pid == "bp2op-transform"
                        else (
                            ["poc"]
                            if pid.startswith(("breda-", "scenario-", "opportunity-", "crosstrack-", "rijnland-"))
                            or "scan" in pid
                            else (
                                ["validation", "trust", "phase-5"]
                                if pid == "validate-artifact"
                                else (["lake", "dataspace"] if pid.startswith("lake-") else [])
                            )
                        )
                    ),
                },
                "links": [
                    {"rel": "self", "href": f"{CATALOG_BASE}/records/process-{pid}"},
                    {
                        "rel": "process-description",
                        "href": f"http://localhost:8082/processes/{pid}",
                        "type": "application/json",
                    },
                ],
            }
        )

    recipes = [
        (
            "spatial-overlay-analysis",
            "Spatial Overlay Analysis",
            ["spatial", "overlay", "analysis", "generic"],
        ),
        (
            "hex-overlay-analysis",
            "Hex Overlay Analysis",
            ["spatial", "h3", "overlay"],
        ),
        (
            "breda-scan-qa",
            "Breda five-value scan Q&A",
            ["poc-breda", "qa", "s4", "scan", "legal", "beleidskompas", "policy-step:substantiation"],
        ),
        (
            "utrecht-scenario-sweep",
            "Utrecht scenario sweep",
            ["poc-utrecht", "scenario", "s7", "plane-b"],
        ),
        (
            "utrecht-opportunity-map",
            "Utrecht opportunity-map",
            ["poc-utrecht", "opportunity-map", "plane-a"],
        ),
        (
            "utrecht-scenario-author",
            "Utrecht scenario author (S7)",
            ["poc-utrecht", "scenario", "s7", "proposals"],
        ),
        (
            "rijnland-peil-conflict",
            "Rijnland peil conflict",
            ["poc-rijnland", "peil", "h3", "conflict"],
        ),
        (
            "rijnland-peil-conflict-live",
            "Rijnland peil conflict (CDC lake)",
            ["poc-rijnland", "peil", "cdc", "live", "hybrid"],
        ),
        (
            "rijnland-peil-whatif",
            "Rijnland peilen what-if (CDC)",
            ["poc-rijnland", "peil", "whatif", "cdc", "scenario", "simulation"],
        ),
        (
            "breda-five-value-scan",
            "Breda five-value scan run",
            ["poc-breda", "scan", "plane-a"],
        ),
        (
            "multi-track-crosstrack",
            "Utrecht multi-track crosstrack",
            ["poc-utrecht", "crosstrack", "plane-c"],
        ),
        (
            "eindhoven-bp2op",
            "Eindhoven bp2op transform",
            ["poc-eindhoven", "bp2op", "legal"],
        ),
        (
            "beleidskompas-omgevingsanalyse",
            "Beleidskompas omgevingsanalyse (overlay)",
            ["beleidskompas", "policy-step:omgevingsanalyse", "spatial", "overlay"],
        ),
        (
            "lake-publish-offer",
            "Publish lake dataset as Data Space offer",
            ["lake", "dataspace", "publish", "odrl", "phase-6"],
        ),
    ]
    for rid, title, tags in recipes:
        records.append(
            {
                "id": f"recipe-{rid}",
                "type": "recipe",
                "title": title,
                "properties": {"recipeId": rid, "tags": tags},
                "links": [
                    {"rel": "self", "href": f"{CATALOG_BASE}/records/recipe-{rid}"},
                    {
                        "rel": "recipe",
                        "href": f"{COOKBOOK_BASE}/recipes/{rid}",
                        "type": "application/json",
                    },
                ],
            }
        )

    for aid, title, descriptor, tags in APPLICATIONS:
        if aid != descriptor["appId"]:
            raise ValueError(f"application id mismatch: {aid} != {descriptor['appId']}")
        validate_instance({**descriptor, "tags": tags}, "application.schema.json")
        links = [
            {"rel": "self", "href": f"{CATALOG_BASE}/records/application-{aid}"},
            {"rel": "launch", "href": descriptor["launchUrl"], "type": "text/html"},
        ]
        if "docsUrl" in descriptor:
            links.append(
                {"rel": "docs", "href": descriptor["docsUrl"], "type": "text/html"}
            )
        records.append(
            {
                "id": f"application-{aid}",
                "type": "application",
                "title": title,
                "properties": {**descriptor, "tags": tags},
                "links": links,
            }
        )

    # Lake datasets from inventory (DCAT-ish Records)
    inv = Path(__file__).resolve().parents[2] / "data" / "lake-inventory.json"
    if inv.is_file():
        import json

        for ds in json.loads(inv.read_text(encoding="utf-8")).get("datasets") or []:
            if not ds.get("exists"):
                continue
            did = ds.get("id") or ds.get("lakeKey", "").replace("/", "-")
            records.append(
                {
                    "id": f"dataset-{did}",
                    "type": "dataset",
                    "title": f"{ds.get('poc')} {ds.get('zone')} {ds.get('kind')}",
                    "properties": {
                        "poc": ds.get("poc"),
                        "zone": ds.get("zone"),
                        "accessClass": ds.get("accessClass"),
                        "license": ds.get("license"),
                        "crs": ds.get("crs"),
                        "sha256": ds.get("sha256"),
                        "lakeUri": ds.get("lakeUri"),
                        "hadPrimarySource": ds.get("sourceId"),
                        "tags": ["lake", ds.get("zone"), ds.get("poc")],
                    },
                    "links": [
                        {"rel": "self", "href": f"{CATALOG_BASE}/records/dataset-{did}"},
                        {
                            "rel": "enclosure",
                            "href": ds.get("lakeUri"),
                            "type": "application/octet-stream",
                        },
                    ],
                }
            )
    return records


def find_records(
    *,
    q: str | None = None,
    record_type: str | None = None,
) -> list[dict[str, Any]]:
    records = seed_records()
    if record_type:
        records = [r for r in records if r.get("type") == record_type]
    if q:
        q_lower = q.lower()
        records = [
            r
            for r in records
            if q_lower in r.get("title", "").lower()
            or q_lower in str(r.get("properties", {})).lower()
        ]
    return records


def find_lake_datasets(
    *,
    poc: str | None = None,
    zone: str | None = None,
    access_class: str | None = None,
    q: str | None = None,
    include_restricted: bool = False,
) -> list[dict[str, Any]]:
    from services.mcp_servers.lake_governance import (
        dataset_to_catalog_record,
        filter_lake_datasets,
        load_inventory_datasets,
    )

    datasets = filter_lake_datasets(
        load_inventory_datasets(), include_restricted=include_restricted
    )
    if poc:
        datasets = [d for d in datasets if d.get("poc") == poc]
    if zone:
        datasets = [d for d in datasets if d.get("zone") == zone]
    if access_class:
        datasets = [d for d in datasets if d.get("accessClass") == access_class]
    if q:
        q_lower = q.lower()
        datasets = [
            d
            for d in datasets
            if q_lower in json.dumps(d, default=str).lower()
        ]
    return [dataset_to_catalog_record(d) for d in datasets]


def get_lake_manifest(
    *,
    record_id: str | None = None,
    lake_uri: str | None = None,
    include_restricted: bool = False,
) -> dict[str, Any] | None:
    from services.mcp_servers.lake_governance import (
        filter_lake_datasets,
        is_restricted_dataset,
        load_inventory_datasets,
    )

    datasets = load_inventory_datasets()
    for ds in datasets:
        did = ds.get("id") or (ds.get("lakeKey") or "").replace("/", "-")
        if record_id and record_id.replace("dataset-", "") == did:
            if not include_restricted and is_restricted_dataset(ds):
                return None
            return ds
        if lake_uri and ds.get("lakeUri") == lake_uri:
            if not include_restricted and is_restricted_dataset(ds):
                return None
            return ds
    return None


def find_poc_capabilities() -> list[dict[str, Any]]:
    """Processes and recipes tagged poc-* (governed agent layer §5.3)."""
    records = seed_records()
    return [
        r
        for r in records
        if r.get("type") in ("process", "recipe")
        and any(
            str(t).startswith("poc-") or t == "poc"
            for t in (r.get("properties") or {}).get("tags") or []
        )
    ]
