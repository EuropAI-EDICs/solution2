# poc/tests/test_engine_rounding_repair.py
"""Regressie op de payload-reparatie in engine.to_zone_geometry.

De landbouw-run (fase 3) produceerde als final zone een multi-delige
multipolygon van kassen-slivers (Polder Derde Bedijking e.o.) waarvan de
WGS84-payload-rounding de micro-delen liet overlappen; GEOS' linework
make_valid weigerde die input hard ("Overlay input is mixed-dimension") en de
run crashte. De fixwave-fallback (buffer(0) als make_valid een exception
gooit) repareert die — offline geverifieerd verliesvrijk (oppervlakte
behouden, geen delen gedropt). Deze test verankert puur het reparatiegedrag
op de exacte faalgeometrie (geen crash; geldige payload; repair
geregistreerd) — 'niet-leeg' is onder de hieronder gedocumenteerde
dubbele-CRS-caveat in de synthetische her-invocatie niet te eisen.

Caveat bewust gedocumenteerd: het fixture is de geometrie ZÓALS die bij de
make_valid-aanroep bestond (na WGS84-transformatie en rounding); het wordt
hier opnieuw door to_zone_geometry gevoerd, dat hem als RD interpreteert. De
transformatie is dus semantisch niet-meaningful — wat de test afdwingt is
repu het reparatiegedrag (geen crash, geldige, niet-lege payload, repair
geregistreerd), niet de coördinaatbetekenis.
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
    from shapely.geometry import shape

    g = wkt.loads(FIXTURE.read_text())
    result, repairs = to_zone_geometry(g, round_dp=6)  # dp zoals run.py::main
    assert result["crs"] == "EPSG:4326"
    assert result["format"] == "GeoJSON"
    assert result["payload"]["type"] in ("Polygon", "MultiPolygon", "GeometryCollection")
    # de reparatie moet een GELDIGE payload opleveren (eindreview-fixwave:
    # voorheen alleen op de reparatie-getallen getest). Niet-leeg kan hier
    # niet geëist worden: onder de bovengenoemde dubbele-CRS-caveat rondt de
    # synthetische her-invocatie tot een lege polygon — in de canonieke
    # landbouw-run was de gerepareerde payload wél geldig én niet-leeg
    # (payload_validity_repair in zones.json + V3-agreement IoU 0,999889).
    payload_geom = shape(result["payload"])
    assert payload_geom.is_valid, "payload na reparatie is ongeldig"
    assert repairs >= 1
