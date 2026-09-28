"""Tests for the cross-twin timeseries silver layer (fase 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.lake import FilesystemLakeClient
from services.timeseries import (
    normalize_rijnland_peilen,
    normalize_rijnland_wkp,
    observations_to_series_meta,
    write_series_bundle,
)
from services.timeseries.validate import validate_observation

WORKSPACE = Path(__file__).resolve().parents[2]  # repo root (ldttoolbox)
PEILEN = WORKSPACE / "poc-rijnland" / "data" / "peilen" / "peilen.json"
WKP = WORKSPACE / "poc-rijnland" / "data" / "wkp" / "waterkwaliteit-monthly-2020-2026.json"


def test_normalize_peilen_all_stations_by_default():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    peilen = json.loads(PEILEN.read_text(encoding="utf-8"))
    n_stations = len(peilen.get("stations") or {})
    assert n_stations > 5
    capped = normalize_rijnland_peilen(peilen, max_stations=2)
    all_rows = normalize_rijnland_peilen(peilen, max_stations=None)
    series_capped = {r["seriesId"] for r in capped}
    series_all = {r["seriesId"] for r in all_rows}
    assert len(series_capped) == 2
    assert len(series_all) == n_stations
    assert series_capped < series_all


def test_normalize_peilen_schema(tmp_path, monkeypatch):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    peilen = json.loads(PEILEN.read_text(encoding="utf-8"))
    rows = normalize_rijnland_peilen(peilen, max_stations=2)
    assert rows
    for r in rows[:5]:
        validate_observation(r)
        assert r["accessClass"] == "restricted"
        assert r["variable"] == "waterstand"
    lake = FilesystemLakeClient(tmp_path)
    # write one series only
    sid = rows[0]["seriesId"]
    series_rows = [r for r in rows if r["seriesId"] == sid]
    meta = observations_to_series_meta(series_rows, title="test peil")
    result = write_series_bundle(series_rows, meta, lake=lake)
    assert result["observationCount"] == len(series_rows)
    assert lake.exists(result["seriesLakeKey"])


def test_max_peil_stations_helper():
    from services.process_adapter.handlers import _max_peil_stations

    assert _max_peil_stations(None) is None
    assert _max_peil_stations("") is None
    assert _max_peil_stations(0) is None
    assert _max_peil_stations(-1) is None
    assert _max_peil_stations(5) == 5
    assert _max_peil_stations("12") == 12


def test_normalize_wkp_open():
    if not WKP.is_file():
        pytest.skip("wkp monthly json missing")
    wkp = json.loads(WKP.read_text(encoding="utf-8"))
    rows = normalize_rijnland_wkp(wkp)
    assert len(rows) > 10
    validate_observation(rows[0])
    assert rows[0]["accessClass"] == "open"
    assert rows[0]["poc"] == "rijnland"


def test_ingest_knmi_cbs_wave(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path))
    from services.timeseries.ingest import ingest_open_wave

    summary = ingest_open_wave(
        include_peilen=False,
        include_wkp=False,
        include_knmi=True,
        include_cbs=True,
    )
    assert summary["sourceCount"] == 2
    assert summary["seriesCount"] >= 2
    assert summary["observationCount"] >= 10


def test_normalize_knmi_gilze_rijen_tx_breda():
    from services.timeseries.normalize import normalize_knmi_daily

    rows = [
        {"YYYYMMDD": "20240715", "TX": "312", "RH": "0"},
        {"YYYYMMDD": "20240716", "TX": "298", "RH": "45"},
    ]
    obs = normalize_knmi_daily(
        rows,
        station_id="350",
        station_name="Gilze-Rijen",
        variable="tmax",
        unit="degC",
        value_field="TX",
        poc="breda",
    )
    assert len(obs) == 2
    validate_observation(obs[0])
    assert obs[0]["poc"] == "breda"
    assert obs[0]["seriesId"] == "knmi-daily-tmax-350"
    assert obs[0]["spatialRef"]["id"] == "350"
    assert obs[0]["value"] == pytest.approx(31.2)
    assert obs[0]["unit"] == "degC"


def test_normalize_cbs_kwb_breda_multi_buurt():
    from services.timeseries.normalize import normalize_cbs_kwb_rows

    rows = [
        {
            "Perioden": "2021JJ00",
            "WijkenEnBuurten": "BU07580101",
            "buurtnaam": "Belcrum",
            "Measure": "aantalInwoners",
            "value": 4100,
            "unit": "1",
        },
        {
            "Perioden": "2022JJ00",
            "WijkenEnBuurten": "BU07580101",
            "buurtnaam": "Belcrum",
            "Measure": "aantalInwoners",
            "value": 4150,
            "unit": "1",
        },
        {
            "Perioden": "2022JJ00",
            "WijkenEnBuurten": "BU07580101",
            "buurtnaam": "Belcrum",
            "Measure": "percentagePersonen65JaarEnOuder",
            "value": 18.5,
            "unit": "%",
        },
        {
            "Perioden": "2022JJ00",
            "WijkenEnBuurten": "BU07580202",
            "buurtnaam": "Heusdenhout",
            "Measure": "percentageWoningenMetZonnestroom",
            "value": 22.0,
            "unit": "%",
        },
    ]
    obs = normalize_cbs_kwb_rows(rows)
    assert len(obs) == 4
    for o in obs:
        validate_observation(o)
        assert o["poc"] == "breda"
        assert o["sourceId"] == "cbs-kwb-breda"
        assert o["spatialRef"]["type"] == "buurt"
    series_ids = {o["seriesId"] for o in obs}
    assert "cbs-kwb-aantalinwoners-bu07580101" in series_ids
    assert "cbs-kwb-percentagepersonen65jaarenouder-bu07580101" in series_ids
    assert "cbs-kwb-percentagewoningenmetzonnestroom-bu07580202" in series_ids


def test_ingest_breda_knmi_cbs_wave(tmp_path, monkeypatch):
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    monkeypatch.setenv("NLDT_LAKE_FS_ROOT", str(tmp_path))
    from services.timeseries.ingest import ingest_open_wave

    summary = ingest_open_wave(
        include_peilen=False,
        include_wkp=False,
        include_knmi=True,
        include_cbs=True,
    )
    source_ids = {s["sourceId"] for s in summary["sources"]}
    assert "knmi-gilze-rijen-350" in source_ids
    assert "cbs-kwb-breda" in source_ids
    assert summary["seriesCount"] >= 4
    knmi = next(s for s in summary["sources"] if s["sourceId"] == "knmi-gilze-rijen-350")
    assert any("tmax" in (ser.get("seriesId") or "") for ser in knmi["series"])
