"""Actual water-quality measurements per peilgebied cell (PoC-3 fase 2b).

Builds on the WKP fixture (``data/wkp/waterkwaliteit-<jaar>.json``,
fetched by ``scripts/fetch_wkp.py`` from the Waterkwaliteitsportaal
download API): per-location annual medians for measured parameters. This
module joins the locations onto the peilgebied H3 grid (bridge:
``h3-spatial-join-points``), aggregates per cell, scales the parameter
against the observed P10–P90 range of location medians (no invented
legal norms — the scale is relative to what Rijnland itself measured)
and computes Moran's I over the per-cell values (``h3-morans-i``).
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Mapping, Optional

try:
    from pyproj import Transformer
except ImportError:  # pragma: no cover
    Transformer = None  # type: ignore

WQ_VERSION = "poc-rijnland-waterkwaliteit/0.1"

#: per parameter-key: display label and which direction is "worse"
NORMS: Dict[str, Dict[str, str]] = {
    "CONCTTE|chloride|mg/l": {"label": "Chloride (mg/l)", "worse": "high"},
    "CONCTTE|chlorofyl-a|ug/l": {"label": "Chlorofyl-a (µg/l)", "worse": "high"},
    "CONCTTE|ammonium|mg/l": {"label": "Ammonium (mg/l)", "worse": "high"},
    "CONCTTE|nitraat|mg/l": {"label": "Nitraat (mg/l)", "worse": "high"},
    "CONCTTE|nitriet|mg/l": {"label": "Nitriet (mg/l)", "worse": "high"},
    "CONCTTE|zuurstof|mg/l": {"label": "Zuurstof (mg/l)", "worse": "low"},
    "VERZDGGD|zuurstof|%": {"label": "Zuurstofverzadiging (%)", "worse": "low"},
    "GELDHD||uS/cm": {"label": "Elektrische geleidbaarheid (µS/cm)", "worse": "high"},
    "T||oC": {"label": "Temperatuur (°C)", "worse": "high"},
    "ZICHT||m": {"label": "Zichtdiepte (m)", "worse": "low"},
    "pH||DIMSLS": {"label": "Zuurgraad (pH)", "worse": "high"},
}

__all__ = ["WQ_VERSION", "NORMS", "attach_water_quality"]

_TO_WGS84 = None


def _transformer():
    global _TO_WGS84
    if _TO_WGS84 is None:
        if Transformer is None:
            raise RuntimeError("pyproj is required for water-quality CRS transform")
        _TO_WGS84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    return _TO_WGS84


def attach_water_quality(
    report: Dict[str, Any],
    *,
    fixture: Mapping[str, Any],
    parameter_key: str,
    peil_cells: List[Mapping[str, Any]],
    resolution: int = 8,
    call=None,
) -> Optional[Dict[str, Any]]:
    """Per-cell water quality for one measured parameter.

    Cell value = median over the annual location medians that fall in the
    cell (bridge join). ``value01`` scales against the P10–P90 range of
    all location medians, inverted when low values are the bad direction,
    so 0 = most favourable and 1 = least favourable *relative to the
    measured range* — not a legal norm.
    """
    if call is None:
        report.setdefault("degradations", []).append({
            "kind": "wq-unavailable",
            "error": "no H3 process client provided (offline run)",
        })
        return None
    norm = NORMS.get(parameter_key)
    if norm is None:
        raise ValueError(f"unknown parameter key: {parameter_key!r}")
    tr = _transformer()

    locs = [(code, loc, loc["params"][parameter_key])
            for code, loc in (fixture.get("locations") or {}).items()
            if parameter_key in (loc.get("params") or {})]
    if not locs:
        report.setdefault("degradations", []).append({
            "kind": "wq-no-data",
            "error": f"fixture has no locations for {parameter_key!r}",
        })
        return None

    feats = []
    for code, loc, _param in locs:
        lng, lat = tr.transform(float(loc["x"]), float(loc["y"]))
        feats.append({"type": "Feature",
                      "properties": {"code": code},
                      "geometry": {"type": "Point",
                                   "coordinates": [round(lng, 6),
                                                   round(lat, 6)]}})
    points = {"type": "FeatureCollection", "features": feats}
    cells = sorted(str(r["cell"]) for r in peil_cells)
    join = call("h3-spatial-join-points",
                {"points": points, "cells": cells,
                 "resolution": resolution})["join"]
    point_cell = {r["index"]: r["cell"] for r in join.get("perPoint", [])
                  if r.get("inCells")}

    per_cell: Dict[str, List[float]] = {}
    n_meas_per_cell: Dict[str, int] = {}
    for i, (_code, _loc, param) in enumerate(locs):
        cell = point_cell.get(i)
        if cell is None:
            continue
        per_cell.setdefault(cell, []).append(float(param["median"]))
        n_meas_per_cell[cell] = (n_meas_per_cell.get(cell, 0)
                                 + int(param["n"]))
    if not per_cell:
        report.setdefault("degradations", []).append({
            "kind": "wq-no-cells",
            "error": "no measurement locations fall inside the peilgebied cells",
        })
        return None

    all_medians = sorted(float(p["median"]) for _c, _l, p in locs)
    qs = statistics.quantiles(all_medians, n=10)
    p10, p90 = qs[0], qs[-1]
    span = (p90 - p10) or 1.0
    invert = norm["worse"] == "low"

    conflict = {str(r["cell"]): float(r.get("conflictFraction") or 0.0)
                for r in peil_cells}
    rows = []
    for cell in sorted(per_cell):
        value = statistics.median(per_cell[cell])
        v01 = max(0.0, min(1.0, (value - p10) / span))
        if invert:
            v01 = 1.0 - v01
        rows.append({
            "cell": cell,
            "value": round(value, 4),
            "value01": round(v01, 4),
            "nLocations": len(per_cell[cell]),
            "nMeasurements": n_meas_per_cell[cell],
            "conflictFraction": conflict.get(cell, 0.0),
        })

    stats = call("h3-morans-i",
                 {"values": {r["cell"]: r["value01"]
                             for r in rows}})["statistics"]
    report["waterkwaliteit"] = {
        "parameter": parameter_key,
        "label": norm["label"],
        "year": fixture.get("year"),
        "locationsWithParameter": len(locs),
        "locationsInCells": sum(len(v) for v in per_cell.values()),
        "cellsWithData": len(rows),
        "p10": round(p10, 4),
        "p90": round(p90, 4),
        "moransI": stats.get("moransI"),
        "pValue": stats.get("pValue"),
    }
    return {
        "parameter": parameter_key,
        "label": norm["label"],
        "resolution": resolution,
        "computedBy": WQ_VERSION,
        "rows": rows,
        "summary": dict(report["waterkwaliteit"]),
        "notes": [
            "value = mediaan over de jaarlijkse locatie-medianen per cel "
            f"({norm['label']}, {fixture.get('source')}, jaar {fixture.get('year')}). "
            "value01 schaalt tussen het P10–P90-bereik van alle gemeten "
            "locaties (0 = gunstigste, 1 = ongunstigste helft van het "
            "eigen waargenomen bereik) — geen wettelijke norm.",
        ],
    }
