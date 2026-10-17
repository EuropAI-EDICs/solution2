"""Puntlagen als gebufferde operand (PDOK-catalogus 2026-10-16).

Vóór deze fix verwijderde ``polygonal()`` punt-/lijnfeatures nog vóór de
buffer, zodat bijv. restwarmtebronnen (51 punten) als 1 km-inclusie een lege
zone gaven. Beide engine-paden (shapely ``execute_rules`` en de V3-
tegenimplementatie ``reexecute_independent``) moeten de puntlaag nu tot
schijven bufferen; zonder buffer blijft een puntlaag — terecht — leeg.
"""
import math
import sys
from pathlib import Path

from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import engine  # noqa: E402

AOI = box(0.0, 400000.0, 20000.0, 420000.0)  # 20×20 km


def _punten(n: int = 3) -> dict:
    return {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
            "features": [{"type": "Feature", "properties": {"fid": i},
                          "geometry": {"type": "Point", "coordinates": [5000.0 + i * 6000.0, 410000.0]}}
                         for i in range(n)]}


def _regel(sem: str, buffer_m) -> dict:
    zs = {"zoneIds": ["punten"], "selection": "within", "geometrySource": "national_source"}
    if buffer_m is not None:
        zs["bufferDistanceM"] = buffer_m
    return {"id": f"R-{sem}", "status": "formalized", "zoneSemantics": sem,
            "zoneSelector": zs, "conditions": []}


def test_puntlaag_met_buffer_wordt_schijven_in_beide_paden():
    lagen = {"punten": _punten()}
    rich = engine.execute_rules([_regel("inclusion", 1000.0)], lagen, aoi=AOI, sources={})
    final = next(z for z in rich if z["operation"] == "final")
    verwacht = 3 * math.pi * 1.0  # drie disjuncte schijven van r = 1 km
    assert abs(final["areaKm2"] - verwacht) / verwacht < 0.01, final["areaKm2"]
    # V3-tegenimplementatie (geopandas) rekent hetzelfde uit
    onafh = engine.reexecute_independent([_regel("inclusion", 1000.0)], lagen, aoi=AOI)
    onafh_km2 = (onafh.area / 1e6) if hasattr(onafh, "area") else float(onafh["areaKm2"])
    assert abs(onafh_km2 - final["areaKm2"]) / final["areaKm2"] < 0.01


def test_puntlaag_zonder_buffer_blijft_leeg_en_exclusie_buffert_ook():
    lagen = {"punten": _punten(), "aoi": {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": shape(AOI).__geo_interface__}]}}
    rich = engine.execute_rules([_regel("inclusion", None)], lagen, aoi=AOI, sources={})
    final = next(z for z in rich if z["operation"] == "final")
    assert final["areaKm2"] == 0.0, "een punt is zonder buffer nooit een zone"
    aoi_regel = {"id": "R-AOI", "status": "formalized", "zoneSemantics": "inclusion",
                 "zoneSelector": {"zoneIds": ["aoi"], "selection": "within",
                                  "geometrySource": "national_source"}, "conditions": []}
    rich = engine.execute_rules([aoi_regel, _regel("exclusion", 500.0)], lagen, aoi=AOI, sources={})
    final = next(z for z in rich if z["operation"] == "final")
    verwacht = 400.0 - 3 * math.pi * 0.25
    assert abs(final["areaKm2"] - verwacht) / verwacht < 0.005, final["areaKm2"]
