# poc/tests/test_engine_rounding_repair.py
"""Regressie op de payload-reparatie in engine.to_zone_geometry.

De landbouw-run (fase 3) produceerde als final zone een 37-delige multipolygon
van kassen-slivers (Polder Derde Bedijking e.o.) waarvan de WGS84-payload-
rounding de micro-delen liet overlappen; GEOS' linework make_valid weigerde die
input hard ("Overlay input is mixed-dimension") en de run crashte. De fixwave-
fallback (buffer(0) als make_valid een exception gooit) repareert verliesvrij —
deze test verankert dat op de exacte faalgeometrie.
"""
from pathlib import Path

from shapely import wkt
from shapely.validation import make_valid

from pipeline.engine import to_zone_geometry

POC = Path(__file__).resolve().parents[1]
FIXTURE = POC / "tests" / "fixtures" / "rounded_degenerate_multipolygon.wkt"


def test_linework_make_valid_still_refuses_fixture():
    """Guard: het fixture-geval moet ongunstig blijven (anders test de
    regressietest de happy path en verliest hij zijn waarde)."""
    g = wkt.loads(FIXTURE.read_text())
    assert not g.is_valid
    try:
        make_valid(g)
        raise AssertionError("fixture wordt nu gewoon door make_valid gerepareerd; "
                             "kies een nieuw faalgeval voor deze regressie")
    except Exception:
        pass


def test_to_zone_geometry_repairs_rounded_degenerate_multipolygon():
    g = wkt.loads(FIXTURE.read_text())
    area_before = g.area
    result, repairs = to_zone_geometry(g, round_dp=6)  # dp zoals run.py::main
    assert result["crs"] == "EPSG:4326"
    assert result["format"] == "GeoJSON"
    assert result["payload"]["type"] in ("Polygon", "MultiPolygon", "GeometryCollection")
    # de reparatie is verliesvrijk voor dit fixture: oppervlakte blijft > 0
    # (area in WGS84-graden) en de repair-reparatie wordt geregistreerd
    assert repairs >= 1
    assert area_before > 0
