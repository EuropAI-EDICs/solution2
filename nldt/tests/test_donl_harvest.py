"""DONL harvest — CKAN mapping, lake ingest, publish, source monitor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

NLDT = Path(__file__).resolve().parents[1]
FIXTURE_PKG = NLDT / "data" / "donl-harvest" / "fixtures" / "sample-package.json"


@pytest.fixture
def sample_package() -> dict:
    return json.loads(FIXTURE_PKG.read_text(encoding="utf-8"))


@pytest.fixture
def lake_env(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("NLDT_DATASPACE_CONNECTOR", "edc-manifest")
    monkeypatch.setenv("NLDT_EDC_MANIFEST_DIR", str(tmp_path / "edc"))
    return tmp_path


def test_classify_resources(sample_package):
    from services.donl_harvest.distributions import classify_resources

    split = classify_resources(sample_package["resources"])
    assert len(split["download"]) == 1
    assert len(split["service"]) == 1
    assert split["download"][0]["format"] == "CSV"
    assert split["service"][0]["format"] == "WFS"


def test_map_package_to_dcat(sample_package):
    from services.donl_harvest.dcat_map import map_package_to_dcat

    dcat = map_package_to_dcat(sample_package, lake_uri="lake://nldt-poc-lake/catalog/dcat/x.json")
    assert dcat["dcterms:identifier"] == "demo-donl-dataset"
    assert dcat["nldt:poc"] == "donl"
    assert dcat["nldt:accessClass"] == "open"
    assert dcat["nldt:distributionSummary"]["download"] == 1
    assert dcat["nldt:distributionSummary"]["dataService"] == 1
    assert len(dcat["dcat:distribution"]) == 2


def test_harvest_package_metadata_only(lake_env, sample_package):
    from services.donl_harvest.harvest import harvest_package
    from services.lake import get_lake_client

    result = harvest_package(sample_package, download_files=False)
    client = get_lake_client()
    assert result["datasetId"] == "demo-donl-dataset"
    assert client.exists(result["dcatLakeKey"])
    assert client.exists(result["rawLakeKey"])
    assert result["serviceManifestUri"] is not None
    dcat = json.loads(client.get_bytes(result["dcatLakeKey"]))
    assert dcat["dcterms:identifier"] == "demo-donl-dataset"


def test_harvest_package_with_download(lake_env, sample_package):
    from services.donl_harvest.harvest import harvest_package

    csv_bytes = b"col1,col2\n1,2\n"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(csv_bytes))}
    mock_resp.iter_bytes = lambda chunk_size=65536: iter([csv_bytes])
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = lambda *a: None

    with patch("services.donl_harvest.distributions.httpx.stream", return_value=mock_resp):
        result = harvest_package(sample_package, download_files=True)

    assert any(d.get("status") == "ok" for d in result["downloads"])
    assert result["downloads"][0].get("lakeKey")


def test_harvest_datasets_integration(lake_env, sample_package):
    from services.donl_harvest.harvest import harvest_datasets
    from services.lake.publish import publish_dataset

    with patch("services.donl_harvest.harvest.CkanClient") as mock_cls:
        client = MagicMock()
        client.package_show.return_value = sample_package
        mock_cls.return_value = client
        summary = harvest_datasets(["demo-donl-dataset"], ckan_client=client, download_files=False)
    assert summary["count"] == 1
    assert summary["datasets"][0]["dcatLakeUri"].startswith("lake://")
    pub = publish_dataset(
        lake_uri=summary["datasets"][0]["dcatLakeUri"],
        dataset_id="demo-donl-dataset",
        access_class="open",
    )
    assert pub["status"] == "ok"
    assert pub["connector"]["backend"] == "edc-manifest"


def test_donl_source_monitor_replay():
    from services.source_monitor.run import run_monitor

    summary = run_monitor(mode="replay")
    assert summary["status"] == "ok"
    assert summary["worstSeverity"] in ("ok", "warn", "critical")


def test_donl_diff_metadata_change():
    from services.source_monitor.donl_probe import diff_donl_probe

    probe = {
        "probedAt": "2026-09-15T12:00:00Z",
        "mode": "replay",
        "registryPath": "fixture",
        "registrySnapshot": {
            "demo-donl-dataset": {
                "metadataModified": "2025-01-01T00:00:00Z",
                "resourceCount": 2,
            }
        },
        "results": [
            {
                "sourceId": "demo-donl-dataset",
                "probeStatus": "ok",
                "metadataModified": "2025-06-01T12:00:00Z",
                "resourceCount": 2,
            }
        ],
    }
    diff = diff_donl_probe(probe)
    assert diff["warnCount"] >= 1
    assert diff["findings"][0]["changes"][0]["field"] == "metadataModified"


def test_recipe_donl_harvest_publish_loads():
    from services.common.schema import load_recipe

    recipe = load_recipe("donl-harvest-publish")
    assert recipe["id"] == "donl-harvest-publish"
    assert "donl-harvest-run" in recipe["requiredProcesses"]
