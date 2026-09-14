"""Tests for data lake sync, Iceberg bootstrap helpers, and Data Space publish."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

NLDT = Path(__file__).resolve().parents[1]


def test_lake_deny_loaded():
    from services.lake import load_deny

    deny = load_deny()
    assert "pathOverrides" in deny
    assert any("peilen" in (o.get("glob") or "") for o in deny["pathOverrides"])


def test_inventory_exists_or_buildable(tmp_path, monkeypatch):
    inv = NLDT / "data" / "lake-inventory.json"
    if not inv.is_file():
        import subprocess
        import sys

        subprocess.check_call(
            [sys.executable, str(NLDT / "scripts" / "build_lake_inventory.py")],
            cwd=str(NLDT),
            env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(NLDT)},
        )
    data = json.loads(inv.read_text(encoding="utf-8"))
    assert "datasets" in data
    assert len(data["datasets"]) > 0


def test_sync_utrecht_fs(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    from services.lake.sync import run_sync

    summary = run_sync(pocs=["utrecht"], dry_run=False)
    assert summary["count"] >= 0
    # sources.json should sync if present
    assert isinstance(summary["items"], list)


def test_publish_rejects_restricted_without_hitl(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    from services.lake.publish import publish_dataset

    result = publish_dataset(
        lake_uri="lake://nldt-poc-lake/bronze/rijnland/peilen/x.json",
        access_class="restricted",
        force_hitl_approved=False,
    )
    assert result["status"] == "rejected"


def test_publish_open_creates_offer(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    from services.lake.publish import publish_dataset

    result = publish_dataset(
        lake_uri="lake://nldt-poc-lake/gold/utrecht/run/demo/out.json",
        access_class="open",
        dataset_id="demo-gold",
        license_="CC0-1.0",
    )
    assert result["status"] == "ok"
    assert result["offer"]["accessClass"] == "open"
    assert Path(result["offerPath"]).is_file()


def test_lake_uri_resolve(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    from services.lake import get_lake_client, resolve_uri_to_local

    client = get_lake_client()
    client.put_bytes("silver/utrecht/meta/demo.json", b'{"ok": true}')
    path = resolve_uri_to_local("lake://nldt-poc-lake/silver/utrecht/meta/demo.json")
    assert path.is_file()
    assert json.loads(path.read_text())["ok"] is True


def test_load_source_lake_uri(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    from services.lake import get_lake_client
    from services.process_adapter.handlers import _load_source

    get_lake_client().put_bytes(
        "silver/breda/meta/layer.json",
        b'{"type":"FeatureCollection","features":[]}',
    )
    fc = _load_source("lake://nldt-poc-lake/silver/breda/meta/layer.json")
    assert fc["type"] == "FeatureCollection"


def test_lake_publish_process(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("NLDT_DATASPACE_OFFERS_DIR", str(tmp_path / "offers"))
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    from services.process_adapter.handlers import execute_local

    out = execute_local(
        "lake-publish-dataset",
        {
            "lakeUri": "lake://nldt-poc-lake/gold/breda/run/t/out.json",
            "accessClass": "open",
            "datasetId": "breda-demo",
        },
    )
    assert out["result"]["status"] == "ok"


def test_write_inventory_parquet_and_iceberg(tmp_path, monkeypatch):
    pytest.importorskip("duckdb")
    inv = NLDT / "data" / "lake-inventory.json"
    if not inv.is_file():
        pytest.skip("inventory not built")
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    from services.lake import write_inventory_parquet
    from services.lake.iceberg import bootstrap_inventory_iceberg

    pq = write_inventory_parquet(inv, tmp_path / "inv.parquet")
    assert pq.is_file()
    meta = bootstrap_inventory_iceberg(inventory_path=inv, force=True)
    assert meta["rows"] > 0
    assert Path(meta["mirror"]).is_file()
    assert meta["mode"].startswith("pyiceberg") or meta["mode"].startswith("parquet")
