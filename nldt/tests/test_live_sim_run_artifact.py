"""run-artifact: pipeline-output via MCP, met pad- en grootte-beveiliging."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))

from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def _tmp_run(tmp_path: Path) -> Path:
    run = tmp_path / "runs" / "20261115T000000Z-test"
    run.mkdir(parents=True)
    return run


def test_run_artifact_leest_geojson_inline(tmp_path):
    run = _tmp_run(tmp_path)
    (run / "zones.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "id": 1}]}),
        encoding="utf-8",
    )
    out = execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "zones.geojson"})
    a = out["artifact"]
    assert a["name"] == "zones.geojson"
    assert a["kind"] == "geojson"
    assert a["bytes"] > 0
    assert a["content"]["type"] == "FeatureCollection"
    assert a["content"]["features"][0]["id"] == 1
    assert a["path"] == str((run / "zones.geojson").resolve())


def test_run_artifact_leest_json_en_text(tmp_path):
    run = _tmp_run(tmp_path)
    (run / "run.json").write_text(json.dumps({"runId": "r1"}), encoding="utf-8")
    (run / "report.md").write_text("# rapport", encoding="utf-8")
    a1 = execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "run.json"})["artifact"]
    assert a1["kind"] == "json" and a1["content"] == {"runId": "r1"}
    a2 = execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "report.md"})["artifact"]
    assert a2["kind"] == "text" and a2["content"].startswith("# rapport")


def test_run_artifact_weigert_pad_ontsnapping(tmp_path):
    run = _tmp_run(tmp_path)
    try:
        execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "../buiten.json"})
    except ValueError as exc:
        assert "binnen" in str(exc)
    else:
        raise AssertionError("pad-ontsnapping moet geweigerd worden")


def test_run_artifact_weigert_onbekend_bestand_en_te_groot(tmp_path):
    run = _tmp_run(tmp_path)
    try:
        execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "ontbreekt.json"})
    except ValueError:
        pass
    else:
        raise AssertionError("ontbrekend bestand moet ValueError geven")
    groot = run / "groot.json"
    groot.write_bytes(b"x" * (5_242_880 + 1))
    try:
        execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "groot.json"})
    except ValueError as exc:
        assert "5 MB" in str(exc)
    else:
        raise AssertionError("bestand boven het plafond moet geweigerd worden")


def test_run_artifact_weigert_run_dir_geen_dir(tmp_path):
    niet_dir = tmp_path / "geen-dir"
    niet_dir.write_text("x", encoding="utf-8")
    try:
        execute_poc_process("run-artifact", {"run_dir": str(niet_dir), "artifact": "x.json"})
    except ValueError:
        pass
    else:
        raise AssertionError("run_dir dat geen dir is moet geweigerd worden")
