"""veenendaal-gebiedscheck-run wrapper: replay op run-dir, execute met gestubde main."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(NLDT_ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from services.process_adapter import poc_handlers  # noqa: E402
from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def _fixture_run(root: Path, naam: str, indicators: int) -> Path:
    run = root / "runs" / naam
    run.mkdir(parents=True)
    (run / "indicators.json").write_text(
        json.dumps({"indicators": [{"id": f"i{k}"} for k in range(indicators)]}),
        encoding="utf-8",
    )
    (run / "manifest.json").write_text("{}", encoding="utf-8")
    return run


def test_veenendaal_replay_leest_nieuwste_run_dir(tmp_path, monkeypatch):
    oud = _fixture_run(tmp_path, "20261106T151732Z-gebiedscheck", 3)
    nieuw = _fixture_run(tmp_path, "20261112T194937Z-gebiedscheck", 74)
    monkeypatch.setattr(poc_handlers, "POC_VEENENDAAL", tmp_path)
    out = execute_poc_process("veenendaal-gebiedscheck-run", {"mode": "replay"})
    s = out["summary"]
    assert s["mode"] == "replay"
    assert s["runDir"] == str(nieuw)  # lexicaal nieuwste wint
    assert s["indicatorCount"] == 74


def test_veenendaal_execute_roept_main_en_resolvets_nieuwe_run(tmp_path, monkeypatch):
    monkeypatch.setattr(poc_handlers, "POC_VEENENDAAL", tmp_path)

    def fake_main(refresh: bool = False) -> int:
        _fixture_run(tmp_path, "20261201T000000Z-gebiedscheck", 74)
        return 0

    monkeypatch.setattr(poc_handlers, "_veenendaal_main", fake_main)
    out = execute_poc_process("veenendaal-gebiedscheck-run", {"mode": "execute"})
    s = out["summary"]
    assert s["mode"] == "execute"
    assert s["runDir"] == str(tmp_path / "runs" / "20261201T000000Z-gebiedscheck")
    assert s["indicatorCount"] == 74


def test_veenendaal_onbekende_mode_geweigerd():
    try:
        execute_poc_process("veenendaal-gebiedscheck-run", {"mode": "anders"})
    except ValueError:
        pass
    else:
        raise AssertionError("onbekende mode moet geweigerd worden")
