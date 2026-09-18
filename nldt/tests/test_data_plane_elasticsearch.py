"""data_plane Elasticsearch enrichment + S7 digest hints."""

from __future__ import annotations

from agents.orchestrator.data_plane import enrich_catalog_hits
from services.elasticsearch import bulk_index, reset_memory_store


def test_data_plane_prefers_elasticsearch_for_ts_query(monkeypatch):
    monkeypatch.setenv("NLDT_ELASTICSEARCH_MOCK", "1")
    monkeypatch.delenv("NLDT_ELASTICSEARCH_URL", raising=False)
    reset_memory_store()
    bulk_index(
        [
            {
                "_id": "ts-knmi",
                "kind": "timeseries_series",
                "poc": "cross",
                "variable": "neerslag",
                "seriesId": "knmi-daily-neerslag-260",
                "title": "KNMI neerslag De Bilt",
                "text": "neerslag knmi timeseries",
                "lakeUri": "lake://nldt-poc-lake/silver/timeseries/knmi/series.json",
            }
        ]
    )
    out = enrich_catalog_hits([], request="neerslag scenario Breda")
    assert out["search_backend"].startswith("elasticsearch")
    assert out["lakeSeriesHints"]
    assert out["lakeSeriesHints"][0]["seriesId"] == "knmi-daily-neerslag-260"


def test_build_llm_digest_includes_hints():
    import sys
    from pathlib import Path

    poc = Path(__file__).resolve().parents[2] / "poc"
    if str(poc) not in sys.path:
        sys.path.insert(0, str(poc))
    from pipeline import scenario_author

    baseline = {
        "request": {"objectType": "wind_turbine"},
        "formalrules": [],
        "normcards": [],
        "lakeSeriesHints": [
            {"seriesId": "knmi-daily-neerslag-260", "variable": "neerslag"}
        ],
    }
    digest = scenario_author.build_llm_digest(baseline, 3)
    assert digest["lakeSeriesHints"][0]["seriesId"] == "knmi-daily-neerslag-260"
