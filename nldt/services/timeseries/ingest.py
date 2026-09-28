"""Open-data and PoC time-series ingest into lake silver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.lake import NLDT_ROOT, get_lake_client
from services.timeseries.normalize import (
    group_by_series,
    normalize_cbs_kwb_rows,
    normalize_cbs_statline_rows,
    normalize_knmi_daily,
    normalize_rijnland_peilen,
    normalize_rijnland_wkp,
    observations_to_series_meta,
)
from services.timeseries.write_silver import write_series_bundle

WORKSPACE = NLDT_ROOT.parent
FIXTURES = NLDT_ROOT / "tests" / "fixtures" / "timeseries"
DEFAULT_PEILEN = WORKSPACE / "poc-rijnland" / "data" / "peilen" / "peilen.json"
DEFAULT_WKP = WORKSPACE / "poc-rijnland" / "data" / "wkp" / "waterkwaliteit-monthly-2020-2026.json"
KNMI_GILZE_FIXTURE = FIXTURES / "knmi_daily_gilze_rijen.json"
CBS_KWB_BREDA_FIXTURE = FIXTURES / "cbs_kwb_breda_sample.json"

# KNMI Gilze-Rijen (350) — Breda AOI climate / hitte context
KNMI_GILZE = {
    "station_id": "350",
    "station_name": "Gilze-Rijen",
    "source_id": "knmi-gilze-rijen-350",
    "poc": "breda",
    "series": (
        {"variable": "tmax", "unit": "degC", "value_field": "TX"},
        {"variable": "tmean", "unit": "degC", "value_field": "TG"},
        {"variable": "neerslag", "unit": "mm", "value_field": "RH"},
    ),
}


def _write_bronze(source_id: str, name: str, data: bytes) -> str:
    lake = get_lake_client()
    key = f"bronze/timeseries/{source_id}/{name}"
    return lake.put_bytes(key, data, content_type="application/octet-stream")


def _commit_observations(observations: list[dict[str, Any]], *, title_prefix: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for series_id, rows in group_by_series(observations).items():
        meta = observations_to_series_meta(
            rows,
            title=f"{title_prefix}: {series_id}",
            description=f"Ingested series {series_id}",
        )
        results.append(write_series_bundle(rows, meta))
    return results


def ingest_rijnland_peilen(
    path: Path | None = None,
    *,
    max_stations: int | None = None,
) -> dict[str, Any]:
    """Ingest peilen archive; ``max_stations=None`` keeps every station."""
    src = path or DEFAULT_PEILEN
    raw = src.read_bytes()
    bronze_uri = _write_bronze("rijnland-peilen", "peilen.json", raw)
    peilen = json.loads(raw.decode("utf-8"))
    rows = normalize_rijnland_peilen(peilen, max_stations=max_stations)
    written = _commit_observations(rows, title_prefix="Rijnland peil")
    return {
        "sourceId": "rijnland-peilen",
        "bronzeUri": bronze_uri,
        "series": written,
        "observationCount": len(rows),
        "stationCap": max_stations,
    }


def ingest_rijnland_wkp(path: Path | None = None) -> dict[str, Any]:
    src = path or DEFAULT_WKP
    raw = src.read_bytes()
    bronze_uri = _write_bronze("rijnland-wkp", "wkp-monthly.json", raw)
    wkp = json.loads(raw.decode("utf-8"))
    rows = normalize_rijnland_wkp(wkp)
    written = _commit_observations(rows, title_prefix="Rijnland WKP")
    return {
        "sourceId": "rijnland-wkp",
        "bronzeUri": bronze_uri,
        "series": written,
        "observationCount": len(rows),
    }


def load_knmi_rows(fixture_path: Path | None = None) -> list[dict[str, Any]]:
    path = fixture_path or (FIXTURES / "knmi_daily_de_bilt.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return list(data.get("rows") or data.get("data") or [])


def ingest_knmi_daily(fixture_path: Path | None = None) -> dict[str, Any]:
    """Legacy De Bilt fixture ingest (cross twin). Prefer ingest_knmi_gilze_rijen for Breda."""
    rows_raw = load_knmi_rows(fixture_path)
    bronze_uri = _write_bronze(
        "knmi-daggegevens",
        "knmi_daily.json",
        json.dumps(rows_raw, indent=2).encode("utf-8"),
    )
    rows = normalize_knmi_daily(rows_raw)
    written = _commit_observations(rows, title_prefix="KNMI daily")
    return {
        "sourceId": "knmi-daggegevens",
        "bronzeUri": bronze_uri,
        "series": written,
        "observationCount": len(rows),
    }


def ingest_knmi_gilze_rijen(fixture_path: Path | None = None) -> dict[str, Any]:
    """KNMI station 350 (Gilze-Rijen): tmax / tmean / neerslag for Breda PoC."""
    path = fixture_path or KNMI_GILZE_FIXTURE
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    rows_raw = list(data.get("rows") or []) if isinstance(data, dict) else list(data)
    bronze_uri = _write_bronze("knmi-gilze-rijen-350", "knmi_daily_gilze_rijen.json", raw)

    cfg = KNMI_GILZE
    all_obs: list[dict[str, Any]] = []
    for spec in cfg["series"]:
        all_obs.extend(
            normalize_knmi_daily(
                rows_raw,
                station_id=str(cfg["station_id"]),
                station_name=str(cfg["station_name"]),
                variable=str(spec["variable"]),
                unit=str(spec["unit"]),
                value_field=str(spec["value_field"]),
                poc=str(cfg["poc"]),
                source_id=str(cfg["source_id"]),
            )
        )
    written = _commit_observations(all_obs, title_prefix="KNMI Gilze-Rijen")
    return {
        "sourceId": "knmi-gilze-rijen-350",
        "bronzeUri": bronze_uri,
        "series": written,
        "observationCount": len(all_obs),
    }


def load_cbs_rows(fixture_path: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = fixture_path or (FIXTURES / "cbs_statline_sample.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = {
        "seriesId": data.get("seriesId") or "cbs-breda-population",
        "poc": data.get("poc") or "breda",
        "variable": data.get("variable") or "bevolking",
        "unit": data.get("unit") or "1",
        "sourceId": data.get("sourceId") or "cbs-statline",
    }
    return list(data.get("rows") or []), meta


def ingest_cbs_statline(fixture_path: Path | None = None) -> dict[str, Any]:
    """Legacy single-series StatLine sample. Prefer ingest_cbs_kwb_breda for Breda."""
    rows_raw, meta = load_cbs_rows(fixture_path)
    bronze_uri = _write_bronze(
        "cbs-statline",
        "statline_sample.json",
        json.dumps({"meta": meta, "rows": rows_raw}, indent=2).encode("utf-8"),
    )
    rows = normalize_cbs_statline_rows(
        rows_raw,
        series_id=str(meta["seriesId"]),
        poc=str(meta["poc"]),
        variable=str(meta["variable"]),
        unit=str(meta["unit"]),
        source_id=str(meta["sourceId"]),
    )
    written = _commit_observations(rows, title_prefix="CBS StatLine")
    return {
        "sourceId": "cbs-statline",
        "bronzeUri": bronze_uri,
        "series": written,
        "observationCount": len(rows),
    }


def ingest_cbs_kwb_breda(fixture_path: Path | None = None) -> dict[str, Any]:
    """CBS Kerncijfers wijken/buurten — Breda buurten, PoC-aligned measures."""
    path = fixture_path or CBS_KWB_BREDA_FIXTURE
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    rows_raw = list(data.get("rows") or [])
    bronze_uri = _write_bronze("cbs-kwb-breda", "cbs_kwb_breda.json", raw)
    rows = normalize_cbs_kwb_rows(
        rows_raw,
        poc=str(data.get("poc") or "breda"),
        source_id=str(data.get("sourceId") or "cbs-kwb-breda"),
    )
    written = _commit_observations(rows, title_prefix="CBS KWB Breda")
    return {
        "sourceId": "cbs-kwb-breda",
        "bronzeUri": bronze_uri,
        "series": written,
        "observationCount": len(rows),
    }


def ingest_open_wave(
    *,
    include_peilen: bool = True,
    include_wkp: bool = True,
    include_knmi: bool = True,
    include_cbs: bool = True,
    max_peil_stations: int | None = None,
) -> dict[str, Any]:
    """Curated ingest: Rijnland + KNMI Gilze-Rijen (Breda) + CBS KWB Breda.

    ``max_peil_stations=None`` (default) ingests every station in peilen.json.
    """
    parts: list[dict[str, Any]] = []
    if include_peilen and DEFAULT_PEILEN.is_file():
        parts.append(ingest_rijnland_peilen(max_stations=max_peil_stations))
    if include_wkp and DEFAULT_WKP.is_file():
        parts.append(ingest_rijnland_wkp())
    if include_knmi:
        parts.append(ingest_knmi_gilze_rijen())
    if include_cbs:
        parts.append(ingest_cbs_kwb_breda())
    series_count = sum(len(p.get("series") or []) for p in parts)
    obs_count = sum(int(p.get("observationCount") or 0) for p in parts)
    return {
        "sources": parts,
        "sourceCount": len(parts),
        "seriesCount": series_count,
        "observationCount": obs_count,
    }
