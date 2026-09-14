from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

NLDT = Path(__file__).resolve().parents[1]
WORKSPACE = NLDT.parent
PEILEN = WORKSPACE / "poc-rijnland" / "data" / "peilen" / "peilen.json"


def _load_script(name: str):
    path = NLDT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path / "lake"))
    monkeypatch.delenv("NLDT_STREAM_ALLOW_RESTRICTED", raising=False)
    if str(NLDT) not in sys.path:
        sys.path.insert(0, str(NLDT))
    yield


def test_fixture_capture_and_apply(tmp_path, monkeypatch):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")

    capture = _load_script("cdc_capture_peilen")
    apply = _load_script("cdc_apply_peilen")
    from services.cdc import bronze_cdc_dir, silver_peilen_path

    data = json.loads(PEILEN.read_text(encoding="utf-8"))
    stations = dict(list((data.get("stations") or {}).items())[:5])
    tiny = tmp_path / "tiny-peilen.json"
    tiny.write_text(json.dumps({"stations": stations}), encoding="utf-8")

    out = capture.capture_fixture(tiny)
    assert out
    assert out[0]["op"] == "I"
    dest = capture._write_batch(out, bronze_cdc_dir("rijnland"))
    assert dest.is_file()

    result = apply.apply_batches([dest], silver_peilen_path("rijnland"))
    assert result["applied"] == 1
    assert result["rows"] == len(out)
    assert Path(result["silver"]).is_file()
    assert Path(result["mirror"]).is_file()


def test_stream_adapter_restricted_gate(tmp_path, monkeypatch):
    from services.adapters import stream as stream_adapter
    from services.cdc import silver_peilen_path
    import duckdb

    silver = silver_peilen_path("rijnland")
    silver.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE t AS SELECT
          's1' AS peilgebied_id, -5.0::DOUBLE AS waterstand_m,
          now() AS measured_at, 'test' AS source, 1::BIGINT AS cdc_lsn, now() AS applied_at
        """
    )
    con.execute(f"COPY t TO '{silver.as_posix()}' (FORMAT PARQUET)")

    tables = stream_adapter.list_stream_tables(include_restricted=False)
    assert all(t.get("accessClass") != "restricted" for t in tables)

    with pytest.raises(PermissionError):
        stream_adapter.query_stream_table("rijnland_peilen", include_restricted=False)

    got = stream_adapter.query_stream_table("rijnland_peilen", include_restricted=True)
    assert got["rowCount"] >= 1

    stream_adapter.ALLOW_RESTRICTED = True
    fresh = stream_adapter.get_freshness("rijnland_peilen")
    assert fresh.get("exists") is True


def test_cdc_recipe_schema():
    from services.common.schema import load_recipe, validate_instance

    recipe = load_recipe("rijnland-peil-conflict-live")
    validate_instance(recipe, "recipe.schema.json")
    assert "cdc" in recipe["tags"]


def test_data_plane_cdc_hybrid():
    from agents.orchestrator.data_plane import infer_data_plane

    assert infer_data_plane("live peil cdc", "rijnland-peil-conflict-live") == "hybrid"


def test_poc_tools_include_live():
    from services.mcp_servers.poc_tools import POC_TOOLS

    assert "run_peil_conflict_live" in POC_TOOLS
