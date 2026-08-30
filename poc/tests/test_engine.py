#!/usr/bin/env python3
"""Track-B unit tests: deterministic zone engine, geo connector (pure parts),
and cartographer serialization. Synthetic fixture polygons ONLY — no network.

Run from the workspace root:

    python3 -m unittest discover -s poc/tests

Fixture frame: EPSG:28992 (RD New, metric), origin around (140000, 455000)
(well inside the province Utrecht domain so pyproj reprojection is exercised
on realistic coordinates).
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPE_DIR = ROOT / "poc" / "pipeline"
if str(PIPE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPE_DIR))

import engine  # noqa: E402
import geodata  # noqa: E402
import cartographer  # noqa: E402

from shapely.geometry import Polygon, box, mapping, shape  # noqa: E402

X0, Y0 = 140000.0, 455000.0
REL_TOL = 1e-6

# --------------------------------------------------------------------------- #
# fixture helpers
# ---------------------------------------------------------------------------


def square(x0, y0, w, h):
    return box(x0, y0, x0 + w, y0 + h)


def feature_collection(*geoms, source_id="fixture", last_checked="2026-08-30T00:00:00Z"):
    feats = [
        {
            "type": "Feature",
            "id": i,
            "properties": {"fid": i},
            "geometry": mapping(g),
        }
        for i, g in enumerate(geoms)
    ]
    return {
        "type": "FeatureCollection",
        "name": source_id,
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": feats,
        "properties": {
            "sourceId": source_id,
            "serviceUrl": "https://example.test/FeatureServer",
            "layerId": 0,
            "lastChecked": last_checked,
        },
    }


def rule_incl(rid, layer, **kw):
    r = {"id": rid, "zoneSemantics": "inclusion", "sourceLayerId": layer}
    r.update(kw)
    return r


def rule_excl(rid, layer, value=None, unit="m", **kw):
    r = {"id": rid, "zoneSemantics": "exclusion", "sourceLayerId": layer}
    if value is not None:
        r["value"] = value
        r["unit"] = unit
    r.update(kw)
    return r


def assert_close(test, actual, expected, rel=REL_TOL, msg=""):
    test.assertTrue(
        math.isclose(actual, expected, rel_tol=rel, abs_tol=1e-9),
        f"{msg} actual={actual!r} expected={expected!r}",
    )


# --------------------------------------------------------------------------- #
# engine tests
# --------------------------------------------------------------------------- #

class TestEngineInclusion(unittest.TestCase):
    def test_inclusion_union_and_aoi_clip(self):
        # two overlapping 100x100 squares (overlap 50x50): union = 17500 m2
        a = square(X0, Y0, 100, 100)
        b = square(X0 + 50, Y0 + 50, 100, 100)
        aoi = square(X0, Y0, 200, 200)  # 40000 m2, contains the union
        layers = {"incl": feature_collection(a, b, source_id="incl")}
        rules = [rule_incl("R-INCL", "incl")]
        zones = engine.execute_rules(rules, layers, aoi=mapping(aoi))
        final = zones[-1]
        self.assertEqual(final["operation"], "final")
        assert_close(self, final["areaM2"], 17500.0, msg="inclusion union area")
        assert_close(self, final["areaKm2"], 0.0175, msg="inclusion union area km2")
        # ZoneResult geometry payload must be WGS84 GeoJSON
        geom = final["geometry"]
        self.assertEqual(geom["format"], "GeoJSON")
        self.assertEqual(geom["crs"], "EPSG:4326")
        shp = shape(geom["payload"])
        self.assertFalse(shp.is_empty)
        lon, lat = shp.representative_point().x, shp.representative_point().y
        self.assertTrue(4.0 < lon < 7.0 and 51.0 < lat < 53.5, f"not NL lon/lat: {lon},{lat}")

    def test_inclusion_clipped_by_aoi(self):
        # AOI cuts the inclusion square in half
        a = square(X0, Y0, 100, 100)
        aoi = square(X0, Y0, 50, 100)
        layers = {"incl": feature_collection(a)}
        zones = engine.execute_rules([rule_incl("R-INCL", "incl")], layers, aoi=mapping(aoi))
        assert_close(self, zones[-1]["areaM2"], 5000.0, msg="clipped inclusion area")

    def test_no_inclusion_no_aoi_is_error(self):
        with self.assertRaises(engine.RuleError):
            engine.execute_rules([], {})

    def test_aoi_seed_when_only_exclusions(self):
        aoi = square(X0, Y0, 100, 100)
        excl = square(X0 + 80, Y0 + 80, 40, 40)  # overlap with AOI = 20x20
        layers = {"excl": feature_collection(excl)}
        rules = [rule_excl("R-EXCL", "excl", value=0)]  # no buffer
        zones = engine.execute_rules(rules, layers, aoi=mapping(aoi))
        assert_close(self, zones[-1]["areaM2"], 9600.0, msg="AOI-seeded difference")


class TestEngineExclusion(unittest.TestCase):
    def setUp(self):
        # inclusion square 100x100 = 10000 m2
        self.layers = {
            "incl": feature_collection(square(X0, Y0, 100, 100), source_id="incl"),
            # exclusion square sharing the y-range, 150 m to the east
            "excl": feature_collection(
                square(X0 + 150, Y0, 100, 100), source_id="excl"
            ),
        }
        self.rules = [
            rule_incl("R-INCL", "incl"),
            rule_excl("R-EXCL", "excl", value=60, unit="m"),
        ]

    def test_buffer_and_difference_exact_area(self):
        # buffered exclusion's straight left edge sits at X0+150-60 = X0+90,
        # covering the inclusion square's full y-range -> bite = 10 x 100 m
        zones = engine.execute_rules(self.rules, self.layers)
        final = zones[-1]
        assert_close(self, final["areaM2"], 9000.0, msg="buffer+difference area")
        diff_zones = [z for z in zones if z["operation"] == "difference"]
        self.assertEqual(len(diff_zones), 1)
        self.assertEqual(diff_zones[0]["ruleIds"], ["R-EXCL"])

    def test_distance_unit_km_and_alternate_keys(self):
        # 0.06 km == 60 m; alternate key spellings (layer/distance)
        rules = [
            {"id": "R-INCL", "zoneSemantics": "inclusion", "layer": "incl"},
            {
                "id": "R-EXCL",
                "zoneSemantics": "exclusion",
                "layer": "excl",
                "distance": 0.06,
                "distanceUnit": "km",
            },
        ]
        zones = engine.execute_rules(rules, self.layers)
        assert_close(self, zones[-1]["areaM2"], 9000.0, msg="km-unit buffer")

    def test_unknown_layer_raises_clear_error(self):
        rules = [rule_incl("R-INCL", "not-fetched")]
        with self.assertRaises(engine.RuleError) as cm:
            engine.execute_rules(rules, self.layers)
        self.assertIn("not-fetched", str(cm.exception))

    def test_missing_semantics_refuses_to_guess(self):
        rules = [{"id": "R-X", "sourceLayerId": "maybe"}]
        with self.assertRaises(engine.RuleError):
            engine.execute_rules(rules, {"maybe": feature_collection(square(X0, Y0, 10, 10))})

    def test_attention_semantics_is_marker_not_exclusion(self):
        # track-A Formalizer emits non-core semantics such as 'attention'
        layers = {
            "incl": feature_collection(square(X0, Y0, 100, 100)),
            "stilte": feature_collection(square(X0 + 300, Y0 + 300, 50, 50)),
        }
        rules = [
            rule_incl("R-INCL", "incl"),
            {
                "id": "R-ATT",
                "normCardId": "nc-1",
                "zoneSemantics": "attention",
                "zoneSelector": {
                    "zoneIds": [],
                    "geometrySource": "stilte",
                    "bufferDistanceM": 1500,
                },
                "executableRef": "engine.zone.buffer@poc-v1",
            },
        ]
        zones = engine.execute_rules(rules, layers)
        marks = [z for z in zones if z["operation"] == "attention_mark"]
        self.assertEqual(len(marks), 1)
        # 50x50 square + 1500 m buffer: bounded by the inscribed square
        # (3100^2 = 9.61e6, corners rounded off) and well above the raw square
        self.assertGreater(marks[0]["areaM2"], 7.0e6)
        self.assertLess(marks[0]["areaM2"], 9.61e6)
        # the opportunity zone itself is untouched by the attention marker
        assert_close(self, zones[-1]["areaM2"], 10000.0, msg="attention neutrality")

    def test_track_a_formal_rule_shape(self):
        # zoneSelector.geometrySource + bufferDistanceM + conditions fallback
        layers = {
            "incl": feature_collection(square(X0, Y0, 100, 100)),
            "excl": feature_collection(square(X0 + 150, Y0, 100, 100)),
        }
        rules = [
            {
                "id": "R-1", "normCardId": "nc-1", "status": "active",
                "ruleType": "prohibition", "zoneSemantics": "inclusion",
                "zoneSelector": {"zoneIds": ["incl"], "geometrySource": "incl",
                                 "selection": "within"},
                "executableRef": "engine.zone.union@poc-v1",
            },
            {
                "id": "R-2", "normCardId": "nc-2", "status": "active",
                "ruleType": "prohibition", "zoneSemantics": "exclusion",
                "zoneSelector": {"zoneIds": ["excl"], "geometrySource": "excl",
                                 "bufferDistanceM": 60},
                "conditions": [{"parameter": "distance", "operator": ">=",
                                "value": 60, "unit": "m"}],
                "executableRef": "engine.zone.buffer@poc-v1",
            },
        ]
        zones = engine.execute_rules(rules, layers)
        assert_close(self, zones[-1]["areaM2"], 9000.0, msg="zoneSelector shape")
        geom_b = engine.reexecute_independent(rules, layers)
        rel = abs(zones[-1]["areaM2"] - geom_b.area) / zones[-1]["areaM2"]
        self.assertLessEqual(rel, 1e-6)
        # track-A ZoneResult contract keys present on every zone
        for z in zones:
            for key in ("id", "ruleIds", "operation", "geometry", "geometryValid",
                        "provenance", "computedBy", "computedAt", "areaKm2"):
                self.assertIn(key, z)
            self.assertEqual(z["geometry"]["format"], "GeoJSON")

    def test_compensation_marks_without_subtracting(self):
        rules = self.rules + [
            {"id": "R-COMP", "zoneSemantics": "compensation", "sourceLayerId": "excl",
             "value": 10}
        ]
        zones = engine.execute_rules(rules, self.layers)
        comp = [z for z in zones if z["operation"] == "compensation_mark"]
        self.assertEqual(len(comp), 1)
        # zone untouched by the compensation rule
        assert_close(self, zones[-1]["areaM2"], 9000.0, msg="compensation neutrality")


class TestEngineValidation(unittest.TestCase):
    def test_invalid_input_geometry_repaired_and_flagged(self):
        # bowtie: make_valid -> two triangles of 10000 m2 each = 20000 m2
        bowtie = Polygon(
            [
                (X0, Y0),
                (X0 + 200, Y0 + 200),
                (X0 + 200, Y0),
                (X0, Y0 + 200),
            ]
        )
        self.assertFalse(bowtie.is_valid)
        layers = {"incl": feature_collection(bowtie, source_id="incl")}
        zones = engine.execute_rules([rule_incl("R-INCL", "incl")], layers)
        final = zones[-1]
        assert_close(self, final["areaM2"], 20000.0, msg="make_valid area")
        all_steps = [s for z in zones for s in z.get("provSteps", [])]
        self.assertTrue(
            any("make_valid_repairs=1" in s for s in all_steps),
            f"repair not flagged in provenance: {all_steps}",
        )

    def test_zone_geometry_validity(self):
        layers = {
            "incl": feature_collection(square(X0, Y0, 100, 100)),
            "excl": feature_collection(square(X0 + 150, Y0, 100, 100)),
        }
        rules = [
            rule_incl("R-INCL", "incl"),
            rule_excl("R-EXCL", "excl", value=60),
        ]
        for z in engine.execute_rules(rules, layers):
            shp = shape(z["geometry"]["payload"])
            self.assertTrue(shp.is_valid, f"zone {z['id']} invalid in WGS84")

    def test_provenance_records_rule_layer_lastchecked_and_ops(self):
        layers = {
            "incl": feature_collection(square(X0, Y0, 100, 100), source_id="incl",
                                       last_checked="2026-08-30T07:45:26Z"),
            "excl": feature_collection(square(X0 + 150, Y0, 100, 100), source_id="excl",
                                       last_checked="2026-08-30T07:42:33Z"),
        }
        rules = [
            rule_incl("R-INCL", "incl"),
            rule_excl("R-EXCL", "excl", value=300),
        ]
        zones = engine.execute_rules(
            rules, layers,
            sources={
                "incl": {"serviceUrl": "https://agrest.test/OV/FeatureServer",
                         "layerId": 0, "lastChecked": "2026-08-30T07:45:26Z"},
                "excl": {"serviceUrl": "https://services.arcgis.com/x/FeatureServer",
                         "layerId": 13, "lastChecked": "2026-08-30T07:42:33Z"},
            },
        )
        prov = " | ".join(zones[-1]["provSteps"])
        for needle in (
            "op=inclusion_union",
            "op=union; layer=incl(https://agrest.test/OV/FeatureServer/0; lastChecked=2026-08-30T07:45:26Z)",
            "op=buffer; rule=R-EXCL",
            "layer=excl(https://services.arcgis.com/x/FeatureServer/13; lastChecked=2026-08-30T07:42:33Z)",
            "op=difference; rule=R-EXCL",
            "distance_m=300.0",
        ):
            self.assertIn(needle, prov, f"missing provenance: {needle!r}")
        # each emitted ZoneResult carries its own prov steps (per-op provenance)
        for z in zones:
            if z["operation"] != "final":
                self.assertTrue(z["provSteps"], f"zone {z['id']} lacks per-op provenance")

    def test_determinism_same_output_across_runs(self):
        layers = {
            "incl": feature_collection(square(X0, Y0, 100, 100)),
            "excl": feature_collection(square(X0 + 150, Y0, 100, 100)),
        }
        rules = [
            rule_incl("R-INCL", "incl"),
            rule_excl("R-EXCL", "excl", value=60),
        ]
        run1 = engine.execute_rules(rules, layers)
        run2 = engine.execute_rules(rules, layers)
        self.assertEqual(json.dumps(run1, sort_keys=True), json.dumps(run2, sort_keys=True))


class TestIndependentReexecution(unittest.TestCase):
    def test_reexecute_agrees_within_tolerance(self):
        layers = {
            "incl": feature_collection(
                square(X0, Y0, 100, 100), square(X0 + 250, Y0 + 250, 80, 80)
            ),
            "excl": feature_collection(square(X0 + 150, Y0, 100, 100)),
            "excl2": feature_collection(square(X0 + 40, Y0 + 40, 20, 20)),
        }
        rules = [
            rule_incl("R-INCL", "incl"),
            rule_excl("R-EXCL1", "excl", value=60),
            rule_excl("R-EXCL2", "excl2", value=0.05, unit="km"),
        ]
        aoi = square(X0, Y0, 500, 500)
        zones = engine.execute_rules(rules, layers, aoi=mapping(aoi))
        final_area = zones[-1]["areaM2"]
        geom_b = engine.reexecute_independent(rules, layers, aoi=mapping(aoi))
        area_b = geom_b.area
        rel = abs(final_area - area_b) / max(final_area, area_b, 1e-12)
        self.assertLessEqual(
            rel, 1e-6,
            f"V3 disagreement: engine={final_area} independent={area_b}",
        )
        # IoU cross-check: compare both sides in the SAME single-reprojection
        # space (RD -> WGS84), since the ZoneResult payload is stored in 4326.
        geom_a_wgs = shape(zones[-1]["geometry"]["payload"])
        geom_b_wgs = engine.to_wgs84(geom_b)
        self.assertGreaterEqual(engine.iou(geom_a_wgs, geom_b_wgs), 0.999999)

    def test_reexecute_agrees_on_invalid_input_too(self):
        bowtie = Polygon(
            [(X0, Y0), (X0 + 200, Y0 + 200), (X0 + 200, Y0), (X0, Y0 + 200)]
        )
        layers = {"incl": feature_collection(bowtie)}
        rules = [rule_incl("R-INCL", "incl")]
        zones = engine.execute_rules(rules, layers)
        geom_b = engine.reexecute_independent(rules, layers)
        rel = abs(zones[-1]["areaM2"] - geom_b.area) / max(zones[-1]["areaM2"], 1e-12)
        self.assertLessEqual(rel, 1e-6)


# --------------------------------------------------------------------------- #
# geodata pure-function tests (no network)
# --------------------------------------------------------------------------- #

class TestGeoDataRegistry(unittest.TestCase):
    def test_load_real_registry(self):
        sources = geodata.load_sources()
        self.assertGreaterEqual(len(sources), 60)
        ids = set(sources)
        self.assertEqual(len(ids), len(sources), "duplicate ids")
        # the two known-broken entries are present but flagged by absence of layerId
        self.assertIn("arcgis-natura2000-buffers", sources)
        self.assertIn("pdok-natura2000-wfs", sources)

    def test_missing_registry_raises_clear_error(self):
        with self.assertRaises(geodata.GeoDataError):
            geodata.load_sources(path="/nonexistent/sources.json")


class TestGeoDataQueryParams(unittest.TestCase):
    def setUp(self):
        self.sources = geodata.load_sources()

    def test_hosted_geojson_dialect(self):
        src = self.sources["arcgis-et-wind-gebieden"]
        params, use_geojson = geodata.build_query_params(src, offset=2000)
        self.assertTrue(use_geojson)
        self.assertEqual(params["f"], "geojson")
        self.assertEqual(params["outSR"], "28992")
        self.assertEqual(params["resultRecordCount"], 2000)
        self.assertEqual(params["resultOffset"], 2000)
        self.assertEqual(params["orderByFields"], "objectid")
        self.assertEqual(params["where"], "1=1")

    def test_agrest_json_dialect(self):
        src = self.sources["agrest-ov-gebied-windenergie"]
        params, use_geojson = geodata.build_query_params(src, offset=1000)
        self.assertFalse(use_geojson)
        self.assertEqual(params["f"], "json")
        self.assertEqual(params["returnGeometry"], "true")
        self.assertEqual(params["resultRecordCount"], 1000)
        self.assertEqual(params["where"], "NAAM='Gebied windenergie'")
        self.assertNotIn("orderByFields", params)

    def test_bbox_envelope_params(self):
        src = self.sources["arcgis-natura2000"]
        params, _ = geodata.build_query_params(
            src, offset=0, bbox=(140000, 455000, 150000, 465000)
        )
        self.assertEqual(params["geometryType"], "esriGeometryEnvelope")
        self.assertEqual(params["inSR"], "28992")
        self.assertEqual([float(v) for v in params["geometry"].split(",")],
                         [140000, 455000, 150000, 465000])

    def test_simplify_param(self):
        src = self.sources["arcgis-natura2000"]
        params, _ = geodata.build_query_params(src, offset=0, simplify_m=25)
        self.assertEqual(float(params["maxAllowableOffset"]), 25.0)

    def test_broken_source_raises_clear_error(self):
        src = self.sources["arcgis-natura2000-buffers"]
        with self.assertRaises(geodata.GeoDataError) as cm:
            geodata.build_query_params(src, offset=0)
        self.assertIn("layerId", str(cm.exception))

    def test_bad_bbox_rejected(self):
        src = self.sources["arcgis-natura2000"]
        for bad in [(1, 2, 3), (10, 10, 0, 50), "1,2,3"]:
            with self.assertRaises(geodata.GeoDataError):
                geodata.build_query_params(src, offset=0, bbox=bad)


class TestEsriRingsConversion(unittest.TestCase):
    def test_donut_ccw_outer_cw_hole(self):
        rings = [
            [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],          # CCW shell
            [(25, 25), (25, 75), (75, 75), (75, 25), (25, 25)],         # CW hole
        ]
        g = geodata.esri_rings_to_geometry(rings)
        self.assertEqual(g.geom_type, "Polygon")
        self.assertEqual(len(g.interiors), 1)
        self.assertTrue(g.is_valid)
        assert_close(self, g.area, 7500.0, msg="donut area")

    def test_donut_reversed_orientations(self):
        # orientation-adaptive: same donut, windings flipped
        rings = [
            [(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)],          # CW shell
            [(25, 25), (75, 25), (75, 75), (25, 75), (25, 25)],         # CCW hole
        ]
        g = geodata.esri_rings_to_geometry(rings)
        self.assertEqual(g.geom_type, "Polygon")
        self.assertEqual(len(g.interiors), 1)
        assert_close(self, g.area, 7500.0, msg="flipped donut area")

    def test_two_shells_become_multipolygon(self):
        rings = [
            [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
            [(20, 0), (30, 0), (30, 10), (20, 10), (20, 0)],
        ]
        g = geodata.esri_rings_to_geometry(rings)
        self.assertEqual(g.geom_type, "MultiPolygon")
        assert_close(self, g.area, 200.0, msg="two shells area")

    def test_island_inside_donut(self):
        rings = [
            [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
            [(20, 20), (80, 20), (80, 80), (20, 80), (20, 20)],
            [(40, 40), (60, 40), (60, 60), (40, 60), (40, 40)],
        ]
        g = geodata.esri_rings_to_geometry(rings)
        # shell with hole + inner island shell: 10000 - 3600 + 400 = 6800
        assert_close(self, g.area, 6800.0, msg="island-in-donut area")

    def test_degenerate_rings_return_none(self):
        self.assertIsNone(geodata.esri_rings_to_geometry([]))
        self.assertIsNone(geodata.esri_rings_to_geometry([[(0, 0), (1, 1)]]))

    def test_esri_feature_conversion(self):
        feat = {
            "attributes": {"OBJECTID": 7, "NAAM": "Gebied windenergie"},
            "geometry": {"rings": [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]]},
        }
        gf = geodata.esri_feature_to_geojson(feat)
        self.assertEqual(gf["type"], "Feature")
        self.assertEqual(gf["id"], 7)
        self.assertEqual(gf["properties"]["NAAM"], "Gebied windenergie")
        assert_close(self, shape(gf["geometry"]).area, 100.0)
        self.assertIsNone(geodata.esri_feature_to_geojson({"attributes": {}, "geometry": None}))

    def test_wgs84_twin_reprojection(self):
        fc = feature_collection(square(X0, Y0, 100, 100), source_id="s")
        fc["properties"]["crs"] = "OGC:CRS84/WGS84 (RFC 7946 default, no crs member)"
        out = geodata.feature_collection_to_wgs84(fc)
        g = shape(out["features"][0]["geometry"])
        self.assertTrue(4.0 < g.bounds[0] < 7.0, f"lon out of NL range: {g.bounds}")
        self.assertTrue(51.0 < g.bounds[1] < 53.5, f"lat out of NL range: {g.bounds}")


class TestGeoDataCacheLogic(unittest.TestCase):
    def test_fetch_layer_uses_cache_and_writes_wgs84_twin(self):
        # offline: pre-seed the cache, then confirm fetch_layer returns it
        # without any network (a missing-layer error would raise otherwise).
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            fc = feature_collection(square(X0, Y0, 100, 100), source_id="cache-test")
            fc["properties"]["queryFingerprint"] = geodata._fingerprint(None, None)
            (td / "cache-test.28992.geojson").write_text(json.dumps(fc))
            got = geodata.fetch_layer("cache-test", cache_dir=td)
            self.assertEqual(len(got["features"]), 1)
            self.assertTrue((td / "cache-test.4326.geojson").exists())

    def test_fingerprint_changes_on_bbox(self):
        fp_plain = geodata._fingerprint(None, None)
        fp_box = geodata._fingerprint((1, 2, 3, 4), None)
        self.assertNotEqual(fp_plain, fp_box)


# --------------------------------------------------------------------------- #
# cartographer tests
# --------------------------------------------------------------------------- #

def _demo_zones():
    layers = {
        "incl": feature_collection(square(X0, Y0, 100, 100), source_id="incl"),
        "excl": feature_collection(square(X0 + 150, Y0, 100, 100), source_id="excl"),
    }
    rules = [
        rule_incl("R-INCL", "incl"),
        rule_excl("R-EXCL", "excl", value=60),
    ]
    return engine.execute_rules(rules, layers)


class TestCartographer(unittest.TestCase):
    def test_write_geojson(self):
        zones = _demo_zones()
        with tempfile.TemporaryDirectory() as td:
            p = cartographer.write_geojson(zones, Path(td) / "zones.geojson")
            doc = json.loads(p.read_text())
            self.assertEqual(doc["type"], "FeatureCollection")
            self.assertEqual(len(doc["features"]), len(zones))
            self.assertIn("CRS84", json.dumps(doc["crs"]))
            for f, z in zip(doc["features"], zones):
                self.assertEqual(f["properties"]["operation"], z["operation"])
                self.assertEqual(f["properties"]["areaKm2"], z["areaKm2"])

    def test_report_input(self):
        zones = _demo_zones()
        report = cartographer.build_report_input(
            zones,
            sources={
                "incl": {"id": "incl", "title": "Gebied windenergie",
                         "serviceUrl": "https://agrest.test/OV/FeatureServer",
                         "layerId": 0, "role": "inclusion",
                         "lastChecked": "2026-08-30T07:45:26Z"},
            },
            outputs={"geojson": "poc/output/zones.geojson"},
        )
        self.assertEqual(report["stats"]["zoneCount"], len(zones))
        self.assertEqual(report["stats"]["finalAreaKm2"], zones[-1]["areaKm2"])
        ids = [l["id"] for l in report["layers"]]
        self.assertIn("incl", ids)
        self.assertIn("excl", ids)
        incl_meta = next(l for l in report["layers"] if l["id"] == "incl")
        self.assertEqual(incl_meta["lastChecked"], "2026-08-30T07:45:26Z")

    def test_gml_graceful_degradation_when_binary_missing(self):
        zones = _demo_zones()
        with tempfile.TemporaryDirectory() as td:
            gj = cartographer.write_geojson(zones, Path(td) / "zones.geojson")
            res = cartographer.write_gml(gj, ogr2ogr_path="/nonexistent/ogr2ogr")
            self.assertFalse(res["ok"])
            self.assertIn("error", res)
            # the GeoJSON remains authoritative and untouched
            self.assertTrue(gj.exists())

    def test_gml_real_conversion_when_ogr2ogr_present(self):
        ogr = cartographer._find_ogr2ogr()
        if ogr is None:
            self.skipTest("ogr2ogr not installed")
        zones = _demo_zones()
        with tempfile.TemporaryDirectory() as td:
            gj = cartographer.write_geojson(zones, Path(td) / "zones.geojson")
            res = cartographer.write_gml(gj, Path(td) / "zones.gml")
            self.assertTrue(res["ok"], f"ogr2ogr failed: {res['error']}")
            text = (Path(td) / "zones.gml").read_text()[:4000]
            self.assertIn("gml", text.lower())
            self.assertTrue((Path(td) / "zones.xsd").exists(), "GML schema file missing")


if __name__ == "__main__":
    unittest.main()
