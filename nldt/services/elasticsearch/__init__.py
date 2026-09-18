"""Elasticsearch client for nLDT lake discovery (with in-memory mock)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

INDEX_NAME = os.environ.get("NLDT_ELASTICSEARCH_INDEX", "nldt-lake-v1")


def elasticsearch_url() -> str:
    return (os.environ.get("NLDT_ELASTICSEARCH_URL") or "").rstrip("/")


def use_mock() -> bool:
    if os.environ.get("NLDT_ELASTICSEARCH_MOCK", "").lower() in ("1", "true", "yes"):
        return True
    return not elasticsearch_url()


class _MemoryStore:
    """Process-local document store used when Elasticsearch is unavailable."""

    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    def bulk_index(self, docs: list[dict[str, Any]]) -> int:
        for d in docs:
            doc_id = str(d.get("_id") or d.get("id") or "")
            if not doc_id:
                continue
            body = {k: v for k, v in d.items() if k != "_id"}
            self.docs[doc_id] = body
        return len(self.docs)

    def search(
        self,
        query: str,
        *,
        poc: str | None = None,
        kind: str | None = None,
        variable: str | None = None,
        size: int = 20,
    ) -> list[dict[str, Any]]:
        tokens = [t for t in (query or "").lower().split() if t]
        hits: list[dict[str, Any]] = []
        for doc_id, body in self.docs.items():
            if poc and body.get("poc") != poc:
                continue
            if kind and body.get("kind") != kind:
                continue
            if variable and str(body.get("variable") or "").lower() != variable.lower():
                continue
            blob = json.dumps(body, default=str).lower()
            if tokens and not any(t in blob for t in tokens):
                continue
            hits.append({"id": doc_id, "score": 1.0 if tokens else 0.5, **body})
            if len(hits) >= size:
                break
        return hits


_MEMORY = _MemoryStore()


def get_memory_store() -> _MemoryStore:
    return _MEMORY


def reset_memory_store() -> None:
    _MEMORY.docs.clear()


def _http_json(method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Elasticsearch HTTP {exc.code}: {detail[:500]}") from exc


def ensure_index(mapping: dict[str, Any] | None = None) -> None:
    if use_mock():
        return
    base = elasticsearch_url()
    url = f"{base}/{INDEX_NAME}"
    try:
        _http_json("GET", url)
        return
    except RuntimeError:
        pass
    body = mapping or {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "properties": {
                "kind": {"type": "keyword"},
                "poc": {"type": "keyword"},
                "variable": {"type": "keyword"},
                "accessClass": {"type": "keyword"},
                "title": {"type": "text"},
                "description": {"type": "text"},
                "seriesId": {"type": "keyword"},
                "lakeUri": {"type": "keyword"},
                "text": {"type": "text"},
            }
        },
    }
    _http_json("PUT", url, body)


def bulk_index(docs: list[dict[str, Any]]) -> dict[str, Any]:
    if use_mock():
        n = _MEMORY.bulk_index(docs)
        return {"mock": True, "indexed": n}
    ensure_index()
    lines: list[str] = []
    for d in docs:
        doc_id = str(d.get("_id") or d.get("id"))
        body = {k: v for k, v in d.items() if k != "_id"}
        lines.append(json.dumps({"index": {"_index": INDEX_NAME, "_id": doc_id}}))
        lines.append(json.dumps(body, default=str))
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    req = urllib.request.Request(
        f"{elasticsearch_url()}/_bulk",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-ndjson"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return {"mock": False, "errors": result.get("errors"), "items": len(result.get("items") or [])}


def search_lake(
    query: str,
    *,
    poc: str | None = None,
    kind: str | None = None,
    variable: str | None = None,
    size: int = 20,
) -> list[dict[str, Any]]:
    if use_mock():
        return _MEMORY.search(query, poc=poc, kind=kind, variable=variable, size=size)
    must: list[dict[str, Any]] = []
    if query:
        must.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "description", "text", "variable", "seriesId", "poc"],
                }
            }
        )
    filters: list[dict[str, Any]] = []
    if poc:
        filters.append({"term": {"poc": poc}})
    if kind:
        filters.append({"term": {"kind": kind}})
    if variable:
        filters.append({"term": {"variable": variable}})
    body: dict[str, Any] = {
        "size": size,
        "query": {
            "bool": {
                "must": must or [{"match_all": {}}],
                "filter": filters,
            }
        },
    }
    result = _http_json("POST", f"{elasticsearch_url()}/{INDEX_NAME}/_search", body)
    hits_out: list[dict[str, Any]] = []
    for h in (result.get("hits") or {}).get("hits") or []:
        src = h.get("_source") or {}
        hits_out.append({"id": h.get("_id"), "score": h.get("_score"), **src})
    return hits_out


def available() -> bool:
    """True when mock is active or live Elasticsearch responds."""
    if use_mock():
        return True
    try:
        _http_json("GET", f"{elasticsearch_url()}/")
        return True
    except Exception:
        return False
