"""Build Elasticsearch documents from lake inventory, TS series, and gold scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.lake import NLDT_ROOT, fs_root, DEFAULT_BUCKET
from services.elasticsearch import bulk_index, ensure_index, reset_memory_store, use_mock
from services.mcp_servers.lake_governance import load_inventory_datasets

WORKSPACE = NLDT_ROOT.parent


def _text_blob(*parts: Any) -> str:
    return " ".join(str(p) for p in parts if p)


def docs_from_inventory(datasets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    datasets = datasets if datasets is not None else load_inventory_datasets()
    docs: list[dict[str, Any]] = []
    for d in datasets:
        kind = str(d.get("kind") or "dataset")
        doc_kind = "timeseries_series" if kind in ("timeseries", "timeseries-observations") else "dataset"
        if kind == "timeseries-observations":
            continue  # series.json is enough for discovery
        doc_id = f"inv-{d.get('id') or d.get('lakeKey')}"
        docs.append(
            {
                "_id": doc_id,
                "id": doc_id,
                "kind": doc_kind if kind == "timeseries" else "dataset",
                "poc": d.get("poc"),
                "variable": d.get("variable"),
                "accessClass": d.get("accessClass"),
                "title": d.get("seriesId") or d.get("lakeKey") or d.get("id"),
                "description": _text_blob(d.get("kind"), d.get("sourceId"), d.get("license")),
                "seriesId": d.get("seriesId"),
                "lakeUri": d.get("lakeUri"),
                "lakeKey": d.get("lakeKey"),
                "timeRange": d.get("timeRange"),
                "text": _text_blob(
                    d.get("poc"),
                    d.get("zone"),
                    d.get("kind"),
                    d.get("seriesId"),
                    d.get("variable"),
                    d.get("lakeKey"),
                    d.get("sourceId"),
                ),
            }
        )
    return docs


def docs_from_series_json() -> list[dict[str, Any]]:
    root = fs_root() / DEFAULT_BUCKET / "silver" / "timeseries"
    docs: list[dict[str, Any]] = []
    if not root.is_dir():
        return docs
    for path in sorted(root.glob("*/series.json")):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        sid = str(meta.get("seriesId") or path.parent.name)
        doc_id = f"ts-{sid}"
        docs.append(
            {
                "_id": doc_id,
                "id": doc_id,
                "kind": "timeseries_series",
                "poc": meta.get("poc"),
                "variable": meta.get("variable"),
                "unit": meta.get("unit"),
                "accessClass": meta.get("accessClass"),
                "title": meta.get("title") or sid,
                "description": meta.get("description") or "",
                "seriesId": sid,
                "lakeUri": meta.get("lakeUri"),
                "lakeKey": meta.get("lakeKey"),
                "timeRange": meta.get("timeRange"),
                "observationCount": meta.get("observationCount"),
                "text": _text_blob(
                    meta.get("title"),
                    meta.get("description"),
                    meta.get("variable"),
                    meta.get("unit"),
                    meta.get("poc"),
                    sid,
                    "timeseries",
                    "neerslag" if meta.get("variable") == "neerslag" else "",
                    "peil" if "peil" in sid else "",
                ),
            }
        )
    return docs


def docs_from_scenario_gold(limit_per_poc: int = 30) -> list[dict[str, Any]]:
    """Index lightweight gold scenario run summaries for AI discovery."""
    roots = [
        ("utrecht", WORKSPACE / "poc" / "scenario-runs"),
        ("breda", WORKSPACE / "poc-breda" / "runs"),
        ("rijnland", WORKSPACE / "poc-rijnland" / "runs"),
    ]
    docs: list[dict[str, Any]] = []
    for poc, root in roots:
        if not root.is_dir():
            continue
        dirs = sorted([p for p in root.iterdir() if p.is_dir()], reverse=True)[:limit_per_poc]
        for d in dirs:
            summary_path = d / "run_summary.json"
            report_path = d / "scenario-report.json"
            headline = ""
            if summary_path.is_file():
                try:
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    headline = str(
                        summary.get("headline")
                        or summary.get("verdict")
                        or summary.get("title")
                        or ""
                    )
                except json.JSONDecodeError:
                    headline = ""
            elif report_path.is_file():
                try:
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    headline = str(report.get("verdict") or report.get("id") or "")
                except json.JSONDecodeError:
                    headline = ""
            doc_id = f"gold-{poc}-{d.name}"
            docs.append(
                {
                    "_id": doc_id,
                    "id": doc_id,
                    "kind": "scenario_gold",
                    "poc": poc,
                    "title": d.name,
                    "description": headline,
                    "lakeUri": f"lake://nldt-poc-lake/gold/{poc}/scenario/{d.name}/",
                    "text": _text_blob(poc, d.name, headline, "scenario", "gold"),
                }
            )
    return docs


def build_all_docs() -> list[dict[str, Any]]:
    # Prefer live series.json; merge with inventory (dedupe by seriesId)
    series_docs = docs_from_series_json()
    inv_docs = docs_from_inventory()
    seen_series = {d.get("seriesId") for d in series_docs if d.get("seriesId")}
    merged = list(series_docs)
    for d in inv_docs:
        if d.get("kind") == "timeseries_series" and d.get("seriesId") in seen_series:
            continue
        merged.append(d)
    merged.extend(docs_from_scenario_gold())
    return merged


def reindex(*, clear_mock: bool = True) -> dict[str, Any]:
    if use_mock() and clear_mock:
        reset_memory_store()
    ensure_index()
    docs = build_all_docs()
    result = bulk_index(docs)
    result["docCount"] = len(docs)
    result["byKind"] = {}
    for d in docs:
        k = str(d.get("kind") or "?")
        result["byKind"][k] = result["byKind"].get(k, 0) + 1
    return result
