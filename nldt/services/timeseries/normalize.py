"""Normalize PoC and open-data payloads into TimeseriesObservation rows."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

PEILEN_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
WKP_LICENSE = "https://creativecommons.org/publicdomain/zero/1.0/"
KNMI_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
CBS_LICENSE = "https://creativecommons.org/licenses/by/4.0/"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "x"


def observations_to_series_meta(
    observations: list[dict[str, Any]],
    *,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    if not observations:
        raise ValueError("empty observations")
    first = observations[0]
    times = [o["observedAt"] for o in observations]
    spatial = first.get("spatialRef") or {}
    return {
        "seriesId": first["seriesId"],
        "poc": first["poc"],
        "variable": first["variable"],
        "unit": first["unit"],
        "title": title or f"{first['variable']} ({first['seriesId']})",
        "description": description or "",
        "sourceId": first["sourceId"],
        "license": first["license"],
        "accessClass": first["accessClass"],
        "spatialCoverage": spatial,
        "timeRange": {"start": min(times), "end": max(times)},
        "observationCount": len(observations),
    }


def normalize_rijnland_peilen(
    peilen: dict[str, Any],
    *,
    max_stations: int | None = None,
) -> list[dict[str, Any]]:
    """Map poc-rijnland peilen.json day medians → observations (restricted)."""
    stations = peilen.get("stations") or {}
    out: list[dict[str, Any]] = []
    for i, (sid, st) in enumerate(stations.items()):
        if max_stations is not None and i >= max_stations:
            break
        series_id = f"rijnland-peil-{_slug(str(sid))}"
        unit = str(st.get("unit") or "mNAP")
        spatial = {
            "type": "station",
            "id": str(sid),
            "name": st.get("name"),
            "x": st.get("x"),
            "y": st.get("y"),
            "crs": "EPSG:4326",
        }
        for day, stats in (st.get("days") or {}).items():
            if not isinstance(stats, dict):
                continue
            value = stats.get("median")
            if value is None:
                continue
            out.append(
                {
                    "seriesId": series_id,
                    "poc": "rijnland",
                    "variable": "waterstand",
                    "unit": unit,
                    "observedAt": f"{day}T12:00:00Z",
                    "value": float(value),
                    "spatialRef": spatial,
                    "sourceId": "rijnland-peilen",
                    "license": PEILEN_LICENSE,
                    "accessClass": "restricted",
                    "quality": {
                        k: stats[k] for k in ("n", "min", "max", "median") if k in stats
                    },
                }
            )
    return out


def normalize_rijnland_wkp(wkp: dict[str, Any]) -> list[dict[str, Any]]:
    """Map WKP monthly series medians → open observations (poc=rijnland)."""
    out: list[dict[str, Any]] = []
    for key, points in (wkp.get("series") or {}).items():
        parts = str(key).split("|")
        variable = parts[1] if len(parts) >= 2 else str(key)
        unit = parts[2] if len(parts) >= 3 else "1"
        if not str(variable).strip():
            variable = parts[0] if parts and parts[0] else str(key) or "unknown"
        if not str(unit).strip():
            unit = "1"
        series_id = f"rijnland-wkp-{_slug(str(key))}"
        if not isinstance(points, list):
            continue
        for pt in points:
            if not isinstance(pt, dict):
                continue
            ym = pt.get("ym")
            if not ym:
                continue
            value = pt.get("median")
            out.append(
                {
                    "seriesId": series_id,
                    "poc": "rijnland",
                    "variable": str(variable),
                    "unit": str(unit),
                    "observedAt": f"{ym}-01T00:00:00Z",
                    "value": None if value is None else float(value),
                    "spatialRef": {
                        "type": "aoi",
                        "id": "rijnland",
                        "name": wkp.get("areaName") or "Hoogheemraadschap van Rijnland",
                    },
                    "sourceId": "rijnland-wkp",
                    "license": WKP_LICENSE,
                    "accessClass": "open",
                    "quality": {
                        k: pt[k] for k in ("n", "nLocations", "p25", "p75", "median") if k in pt
                    },
                }
            )
    return out


# KNMI fields stored in 0.1 units (RH=0.1 mm, TX/TG/TN=0.1 °C)
_KNMI_TENTHS_FIELDS = frozenset({"RH", "TX", "TG", "TN", "T10N"})


def normalize_knmi_daily(
    rows: list[dict[str, Any]],
    *,
    station_id: str = "260",
    station_name: str = "De Bilt",
    variable: str = "neerslag",
    unit: str = "mm",
    value_field: str = "RH",
    poc: str = "cross",
    source_id: str = "knmi-daggegevens",
) -> list[dict[str, Any]]:
    """Normalize KNMI daily rows (YYYYMMDD + field) to observations."""
    series_id = f"knmi-daily-{variable}-{_slug(station_id)}"
    field = value_field.upper()
    out: list[dict[str, Any]] = []
    for row in rows:
        ymd = str(row.get("YYYYMMDD") or row.get("date") or "")
        if len(ymd) != 8 or not ymd.isdigit():
            continue
        raw = row.get(value_field)
        if raw is None:
            raw = row.get(field)
        if raw is None or raw == "" or str(raw).strip() in ("", "-1", "     "):
            continue
        try:
            num = float(str(raw).strip())
        except ValueError:
            continue
        # KNMI tenths: RH 0.1 mm, TX/TG/TN 0.1 °C when integer-like
        if field in _KNMI_TENTHS_FIELDS and abs(num) >= 1 and num == int(num):
            num = num / 10.0
        iso = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}T12:00:00Z"
        out.append(
            {
                "seriesId": series_id,
                "poc": poc,
                "variable": variable,
                "unit": unit,
                "observedAt": iso,
                "value": num,
                "spatialRef": {
                    "type": "station",
                    "id": station_id,
                    "name": station_name,
                    "crs": "EPSG:4326",
                },
                "sourceId": source_id,
                "license": KNMI_LICENSE,
                "accessClass": "open",
            }
        )
    return out


def normalize_cbs_statline_rows(
    rows: list[dict[str, Any]],
    *,
    series_id: str,
    poc: str = "breda",
    variable: str,
    unit: str,
    source_id: str = "cbs-statline",
    time_field: str = "Perioden",
    value_field: str = "value",
    spatial_id: str | None = None,
) -> list[dict[str, Any]]:
    """Normalize flat StatLine-like rows (Perioden + value) to observations."""
    out: list[dict[str, Any]] = []
    for row in rows:
        period = str(row.get(time_field) or "")
        raw = row.get(value_field)
        if raw is None or period == "":
            continue
        try:
            num = float(raw)
        except (TypeError, ValueError):
            continue
        # Perioden like "2020JJ00" or "2020"
        year = period[:4]
        if not year.isdigit():
            continue
        observed = f"{year}-01-01T00:00:00Z"
        spatial: dict[str, Any] = {"type": "buurt", "id": spatial_id or poc}
        if row.get("RegioS"):
            spatial["id"] = str(row["RegioS"])
        out.append(
            {
                "seriesId": series_id,
                "poc": poc,
                "variable": variable,
                "unit": unit,
                "observedAt": observed,
                "value": num,
                "spatialRef": spatial,
                "sourceId": source_id,
                "license": CBS_LICENSE,
                "accessClass": "open",
            }
        )
    return out


def normalize_cbs_kwb_rows(
    rows: list[dict[str, Any]],
    *,
    poc: str = "breda",
    source_id: str = "cbs-kwb-breda",
) -> list[dict[str, Any]]:
    """Normalize CBS Kerncijfers wijken/buurten rows → one series per (Measure, buurt).

    Expected row keys: Perioden, WijkenEnBuurten (or RegioS), Measure, value, optional
    unit / buurtnaam. Aligns with poc-breda indicator fields (aantalInwoners,
    percentagePersonen65JaarEnOuder, percentageWoningenMetZonnestroom, …).
    """
    out: list[dict[str, Any]] = []
    for row in rows:
        period = str(row.get("Perioden") or row.get("period") or "")
        measure = str(row.get("Measure") or row.get("variable") or "").strip()
        buurt = str(
            row.get("WijkenEnBuurten") or row.get("RegioS") or row.get("buurtcode") or ""
        ).strip()
        raw = row.get("value")
        if not period or not measure or not buurt or raw is None:
            continue
        try:
            num = float(raw)
        except (TypeError, ValueError):
            continue
        year = period[:4]
        if not year.isdigit():
            continue
        variable = measure
        unit = str(row.get("unit") or "1")
        series_id = f"cbs-kwb-{_slug(variable)}-{_slug(buurt)}"
        spatial: dict[str, Any] = {"type": "buurt", "id": buurt}
        if row.get("buurtnaam"):
            spatial["name"] = str(row["buurtnaam"])
        out.append(
            {
                "seriesId": series_id,
                "poc": poc,
                "variable": variable,
                "unit": unit,
                "observedAt": f"{year}-01-01T00:00:00Z",
                "value": num,
                "spatialRef": spatial,
                "sourceId": source_id,
                "license": CBS_LICENSE,
                "accessClass": "open",
            }
        )
    return out


def group_by_series(observations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for obs in observations:
        grouped[str(obs["seriesId"])].append(obs)
    return dict(grouped)
