"""Elasticsearch mock index + search tests."""

from __future__ import annotations

from services.elasticsearch import reset_memory_store, search_lake
from services.elasticsearch.indexer import bulk_index, reindex
from services.timeseries.ingest import ingest_open_wave


def test_elasticsearch_mock_search_after_ingest(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path))
    monkeypatch.setenv("NLDT_ELASTICSEARCH_MOCK", "1")
    monkeypatch.delenv("NLDT_ELASTICSEARCH_URL", raising=False)
    reset_memory_store()

    summary = ingest_open_wave(
        include_peilen=False,
        include_wkp=False,
        include_knmi=True,
        include_cbs=True,
    )
    assert summary["seriesCount"] >= 2

    # Index from series.json under the temp lake root
    from services.elasticsearch import indexer

    docs = indexer.docs_from_series_json()
    assert docs
    bulk_index(docs)

    hits = search_lake("neerslag")
    assert hits
    assert any(h.get("variable") == "neerslag" for h in hits)

    peil_hits = search_lake("peil rijnland")
    # no peilen ingested in this test — may be empty
    assert isinstance(peil_hits, list)

    breda = search_lake("aantalInwoners", poc="breda")
    assert breda
    assert any(h.get("variable") == "aantalInwoners" for h in breda)