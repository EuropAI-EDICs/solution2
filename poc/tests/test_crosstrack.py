"""Offline tests for the cross-track conflict overlay (phase C base).

Run from the workspace root:

    python3 -m unittest poc.tests.test_crosstrack

Synthetic fixtures use two square 100 km2 tracks overlapping on 25 km2 plus a
shared instrument zone; the real-cache test replays the canonical zon/bos runs
from poc/data/cache (~10 s, no network).
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts, crosstrack, scenarios  # noqa: E402
from shapely.geometry import box, mapping  # noqa: E402


def _fc(box, name):
    x0, y0, x1, y1 = box
    return {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": [{
            "type": "Feature", "id": 1, "properties": {},
            "geometry": {"type": "Polygon",
                         "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]},
        }],
        "properties": {"sourceId": name},
    }


AOI_A = (150000, 455000, 160000, 465000)
AOI_B = (155000, 455000, 165000, 465000)   # overlaps A on 5 x 10 km = 50 km2
SHARED = (157000, 457000, 162000, 459000)  # 5 x 2 km = 10 km2; A claims 6, B claims 10

LAYERS_A = {"a_incl": _fc(AOI_A, "a_incl"), "cont": _fc(SHARED, "cont")}
LAYERS_B = {"b_incl": _fc(AOI_B, "b_incl"), "cont": _fc(SHARED, "cont")}


def _rule(rid, zone_id, nc):
    return {
        "id": rid, "normCardId": nc, "status": "formalized",
        "ruleType": "designation_rule", "zoneSemantics": "inclusion",
        "appliesTo": {"objectType": "solar_field"},
        "executableRef": "engine.zone.inclusion@poc-v1",
        "formalizedBy": "test", "formalizedAt": "2026-08-31",
        "zoneSelector": {"zoneIds": [zone_id], "geometrySource": "province_source"},
    }


def _baseline(use_case, rid, zone_id, final_km2, aoi_box):
    request = {
        "id": f"0d9f61aa-4b8e-4f2f-9f6a-6f21cb53d0{'0a' if use_case == 'zon' else '0b'}",
        "objectType": "solar_field",
        "areaOfInterest": {"geometry": _fc(aoi_box, "aoi")["features"][0]["geometry"],
                           "crs": "EPSG:28992"},
        "policyStage": "programming",
        "effortBudget": {"maxSubagents": 1},
        "requestedAt": "2026-08-31T00:00:00Z",
    }
    contracts.validate(request, "opportunity-map-request")
    return {
        "runDir": Path("/tmp/unused"),
        "runId": f"20260831T000000Z-{use_case}",
        "request": request,
        "formalrules": [_rule(rid, zone_id, f"NC-{rid[-2:]}")],
        "normcards": [{"id": f"NC-{rid[-2:]}"}],
        "runSummary": {"runId": f"20260831T000000Z-{use_case}",
                       "useCase": use_case,
                       "headline": {"finalOpportunityKm2": final_km2}},
        "manifest": {},
        "inputSimplifyM": 0.0,
    }


class CrosstrackSchemaTests(unittest.TestCase):

    def test_schema_meta_validates(self):
        schema = contracts.load_schema("crosstrack-report")
        self.assertEqual(schema["$schema"],
                         "https://json-schema.org/draft/2020-12/schema")


class CrosstrackOverlayTests(unittest.TestCase):

    def _run(self):
        return crosstrack.run_crosstrack(
            track_baselines=[
                ("zon", _baseline("zon", "FR-Z-01", "a_incl", 100.0, AOI_A), LAYERS_A),
                ("bos", _baseline("bos", "FR-B-01", "b_incl", 100.0, AOI_B), LAYERS_B),
            ],
            shared_zones=[("cont", "synthetic shared instrument zone")],
            report_id="XR-test-0001")

    def test_conflict_area_and_shares(self):
        report = self._run()
        report.pop("_validation")
        report.pop("_tracks")
        self.assertEqual(len(report["tracks"]), 2)
        self.assertEqual(len(report["conflicts"]), 1)
        c = report["conflicts"][0]
        self.assertEqual(sorted(c["pair"]), ["bos", "zon"])
        self.assertAlmostEqual(c["areaKm2"], 50.0, delta=0.01)
        self.assertAlmostEqual(c["shareOfTrackFinal"]["zon"], 50.0, delta=0.05)
        self.assertAlmostEqual(c["shareOfTrackFinal"]["bos"], 50.0, delta=0.05)

    def test_shared_zone_claims(self):
        report = self._run()
        z = report["sharedZones"][0]
        self.assertAlmostEqual(z["areaKm2"], 10.0, delta=0.01)
        by_uc = {p["useCase"]: p for p in z["perTrack"]}
        self.assertAlmostEqual(by_uc["zon"]["overlapKm2"], 6.0, delta=0.01)
        self.assertAlmostEqual(by_uc["zon"]["shareOfZone"], 60.0, delta=0.05)
        self.assertAlmostEqual(by_uc["bos"]["overlapKm2"], 10.0, delta=0.01)
        self.assertAlmostEqual(by_uc["bos"]["shareOfZone"], 100.0, delta=0.05)

    def test_report_and_validation_schema_valid_and_pass(self):
        report = self._run()
        validation = report.pop("_validation")
        report.pop("_tracks")
        self.assertEqual(report["verdict"], "pass")
        contracts.validate(report, "crosstrack-report")
        contracts.validate(validation, "validation-report")
        self.assertEqual(validation["levels"]["V2"]["status"], "not_applicable")
        self.assertEqual(validation["levels"]["V3"]["status"], "pass")

    def test_control_reproduction_gate_fails_on_mismatch(self):
        lying = _baseline("bos", "FR-B-01", "b_incl", 55.0, AOI_B)  # not 100
        report = crosstrack.run_crosstrack(
            track_baselines=[
                ("zon", _baseline("zon", "FR-Z-01", "a_incl", 100.0, AOI_A), LAYERS_A),
                ("bos", lying, LAYERS_B),
            ],
            shared_zones=[],
            report_id="XR-test-0002")
        validation = report.pop("_validation")
        report.pop("_tracks")
        self.assertEqual(report["verdict"], "fail")
        self.assertEqual(validation["levels"]["V3"]["status"], "fail")

    def test_single_track_refused(self):
        with self.assertRaises(crosstrack.CrossTrackError):
            crosstrack.run_crosstrack(
                track_baselines=[("zon", _baseline(
                    "zon", "FR-Z-01", "a_incl", 100.0, AOI_A), LAYERS_A)],
                shared_zones=[], report_id="XR-test-0003")

    def test_markdown_renders_conflicts_and_shared_zones(self):
        report = self._run()
        report.pop("_validation")
        report.pop("_tracks")
        md = crosstrack.conflict_markdown(report)
        self.assertIn("zon × bos", md)
        self.assertIn("cont", md)
        self.assertIn("60.00%", md)   # zon claim on the shared zone
        self.assertIn("100.00%", md)  # bos claim on the shared zone


class RealCacheCrosstrackTests(unittest.TestCase):
    """Replay the canonical zon/bos runs from the layer cache (~10 s)."""

    CANONICAL = {"zon": "20260830T142439Z-zon", "bos": "20260830T142446Z-bos"}

    def test_zon_bos_energy_vs_nature_conflict(self):
        track_baselines = []
        for uc, run_name in self.CANONICAL.items():
            run_dir = POC_ROOT / "runs" / run_name
            if not (run_dir / "run_summary.json").is_file():
                self.skipTest(f"canonical {uc} run not present")
            baseline = scenarios.load_baseline(run_dir)
            layers, degrades = scenarios.load_layers(
                baseline["manifest"], simplify_m=baseline["inputSimplifyM"])
            self.assertEqual(degrades, [])
            track_baselines.append((uc, baseline, layers))
        report = crosstrack.run_crosstrack(
            track_baselines=track_baselines,
            shared_zones=[("groene_contour", "energy-vs-nature conflict zone")],
            report_id="XR-test-real")
        validation = report.pop("_validation")
        report.pop("_tracks")
        self.assertEqual(report["verdict"], "pass")
        by_pair = {tuple(sorted(c["pair"])): c for c in report["conflicts"]}
        c = by_pair[("bos", "zon")]
        # matches the canonical SC-Z-GROENE-CONTOUR-HARD scenario (22.665 km2):
        # the bos final zone IS the contour, so the conflict equals the zon
        # claim on it
        self.assertAlmostEqual(c["areaKm2"], 22.665, delta=0.05)
        self.assertAlmostEqual(c["shareOfTrackFinal"]["bos"], 94.74, delta=0.1)
        z = report["sharedZones"][0]
        by_uc = {p["useCase"]: p for p in z["perTrack"]}
        self.assertAlmostEqual(by_uc["zon"]["shareOfZone"], 94.7, delta=0.1)
        self.assertAlmostEqual(by_uc["bos"]["shareOfZone"], 100.0, delta=0.05)
        contracts.validate(report, "crosstrack-report")


class TestH3Overlay(unittest.TestCase):

    def _report(self):
        # minimal schema-valid crosstrack report (generatedBy needs a '#',
        # tracks needs minItems 2 — see crosstrack-report.schema.json)
        return {
            "id": "XR-T", "generatedAt": "2026-01-01T00:00:00Z",
            "generatedBy": "t#t",
            "tracks": [
                {"useCase": "zon", "baselineRunId": "run-zon",
                 "requestId": "req-zon", "finalAreaKm2": 1.0,
                 "baselineFinalAreaKm2": 1.0, "reproductionRelDelta": 0.0,
                 "reproductionWithinTolerance": True},
                {"useCase": "bos", "baselineRunId": "run-bos",
                 "requestId": "req-bos", "finalAreaKm2": 1.0,
                 "baselineFinalAreaKm2": 1.0, "reproductionRelDelta": 0.0,
                 "reproductionWithinTolerance": True},
            ],
            "conflicts": [],
            "sharedZones": [], "verdict": "pass",
            "validationReportFile": "validation.json",
            "degradations": [], "notes": [],
        }

    def _fake_call(self):
        calls = {"n": 0}

        def call(process_id, inputs):
            assert process_id == "h3-polygon-to-cells"
            calls["n"] += 1
            if inputs.get("restrictCells") is not None:
                return {"coverage": {
                    "resolution": inputs["resolution"],
                    "cellCount": len(inputs["restrictCells"]),
                    "cells": [{"cell": c, "coverageFraction": 0.5,
                               "cellAreaM2": 740000.0}
                              for c in inputs["restrictCells"]],
                    "crs": "cells-EPSG:4326-areas-EPSG:28992",
                    "h3Version": "test"}}
            return {"coverage": {
                "resolution": inputs["resolution"], "cellCount": 2,
                "cells": [{"cell": "c1", "coverageFraction": 0.8,
                           "cellAreaM2": 740000.0},
                          {"cell": "c2", "coverageFraction": 0.8,
                           "cellAreaM2": 740000.0}],
                "crs": "cells-EPSG:4326-areas-EPSG:28992",
                "h3Version": "test"}}

        return call, calls

    def test_attach_h3_overlay_weights_and_revalidates(self):
        layers = {"groene_contour": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": mapping(box(155000, 456000, 165000, 464000))}]}}
        tracks = [{"useCase": "zon", "geometry": box(156000, 457000, 164000, 463000)}]
        call, calls = self._fake_call()
        report = self._report()
        artifact = crosstrack.attach_h3_overlay(
            report, tracks, zone_id="groene_contour", layers=layers, call=call)
        self.assertEqual(calls["n"], 2)  # contour cells + restricted zon coverage
        self.assertEqual(report["h3Overlay"]["cells"], 2)
        self.assertEqual(report["h3Overlay"]["conflictCells"], 2)
        self.assertEqual(report["h3Overlay"]["weightedConflictSharePct"], 50.0)
        self.assertEqual(artifact["cells"][0]["conflictFraction"], 0.5)
        contracts.validate(report, "crosstrack-report")  # attach already did

    def test_attach_h3_overlay_degrades_without_client(self):
        report = self._report()
        self.assertIsNone(
            crosstrack.attach_h3_overlay(report, [], zone_id="z", layers={}))
        self.assertNotIn("h3Overlay", report)
        self.assertEqual(report["degradations"][0]["kind"], "h3-unavailable")
        contracts.validate(report, "crosstrack-report")

    def test_markdown_renders_h3_section(self):
        report = self._report()
        report["h3Overlay"] = {
            "zoneId": "groene_contour", "resolution": 8, "cells": 10,
            "conflictCells": 7, "weightedConflictSharePct": 94.7,
            "artifactFile": "h3-crosstrack.json"}
        md = crosstrack.conflict_markdown(report)
        self.assertIn("H3 overlay", md)
        self.assertIn("7 of 10 cells", md)

    def test_attach_buildings_join_counts_per_track(self):
        def call(process_id, inputs):
            assert process_id == "h3-spatial-join-points"
            return {"join": {"pointCount": 3, "cellCount": 2, "resolution": 8,
                             "perPoint": [], "perCell": [
                                 {"cell": "c1", "count": 2},
                                 {"cell": "c2", "count": 1}],
                             "h3Version": "test"}}

        tracks = [{"useCase": "zon", "geometry": box(156000, 457000, 164000, 463000)},
                  {"useCase": "bos", "geometry": box(150000, 450000, 160000, 460000)}]
        points = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": {"type": "Point", "coordinates": [5.11, 52.09]}}]}
        art = crosstrack.attach_buildings_join(tracks, points, call=call)
        self.assertEqual([t["buildingsInZoneCells"] for t in art["tracks"]],
                         [3, 3])
        self.assertEqual(art["resolution"], 8)

    def test_attach_buildings_join_without_client_returns_none(self):
        self.assertIsNone(crosstrack.attach_buildings_join([], {}))


class TestHexMapReport(unittest.TestCase):

    def test_render_hex_map_html(self):
        from pipeline import h3report

        fc = {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {"cell": "deadbeefdeadbee", "resolution": 8,
                           "conflictFraction": 0.83},
            "geometry": {"type": "Polygon", "coordinates": [
                [[5.10, 52.08], [5.11, 52.08], [5.11, 52.09],
                 [5.10, 52.09], [5.10, 52.08]]]}}]}
        html = h3report.render_hex_map(fc, title="XR-T hex overlay")
        self.assertIn("leaflet@1.9.4", html)
        self.assertIn("L.map('map'", html)
        self.assertIn("XR-T hex overlay", html)
        self.assertIn("deadbeefdeadbee", html)
        self.assertIn("conflictFraction", html)
        self.assertIn("weight: 0", html)  # contiguous heatmap (no borders)
        # domain copy never leaks without an explicit preset (generic % stops)
        self.assertNotIn("Groene contour", html)
        self.assertIn("75%", html)
        import json as _json
        import re as _re
        meta = _json.loads(
            _re.search(r'id="map-meta">(\{.*?\})</script>', html, _re.S).group(1))
        self.assertEqual(meta["zoneLabel"], "in zone")  # generic default

    def test_render_hex_map_preset_supplies_domain_copy(self):
        from pipeline import h3report

        fc = {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {"cell": "deadbeefdeadbee", "resolution": 8,
                           "conflictFraction": 0.83, "inZoneFraction": 0.6},
            "geometry": None}]}
        html = h3report.render_hex_map(fc, title="t", preset="groene-contour")
        self.assertIn("Volledig conflict", html)  # preset stops
        self.assertIn("Aandeel in Groene contour", html)  # preset zone label
        # explicit zone_label wins over the preset
        html2 = h3report.render_hex_map(fc, title="t", preset="groene-contour",
                                        zone_label="Aandeel in peilgebied")
        self.assertIn("Aandeel in peilgebied", html2)
        self.assertNotIn("Aandeel in Groene contour", html2)

        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "h3.html"
            h3report.render_hex_map(fc, title="t", out_path=out)
            self.assertTrue(out.exists())

    def test_stitch_for_heatmap_fills_neighbours_via_bridge(self):
        from pipeline import h3report

        ring = [[[0, 0], [1, 0], [1, 1], [0, 0]]]
        fc = {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {"cell": "m1", "resolution": 8,
                           "conflictFraction": 0.9, "inZoneFraction": 0.5},
            "geometry": {"type": "Polygon", "coordinates": ring}}]}

        def call(process_id, inputs):
            if process_id == "h3-grid-disk":
                return {"disk": {"ring": 1,
                                 "disks": {"m1": ["m1", "n1", "n2"]}}}
            assert process_id == "h3-cells-to-geojson", process_id
            assert inputs["cells"] == ["n1", "n2"]
            return {"features": {"type": "FeatureCollection", "features": [
                {"type": "Feature",
                 "properties": {"cell": "n1", "resolution": 8},
                 "geometry": {"type": "Polygon", "coordinates": ring}},
                {"type": "Feature",
                 "properties": {"cell": "n2", "resolution": 8},
                 "geometry": {"type": "Polygon", "coordinates": ring}}]}}

        stitched = h3report.stitch_for_heatmap(fc, call=call)
        by = {f["properties"]["cell"]: f["properties"]
              for f in stitched["features"]}
        self.assertEqual(set(by), {"m1", "n1", "n2"})
        self.assertFalse(by["m1"]["interpolated"])
        self.assertEqual(by["m1"]["conflictFraction"], 0.9)
        for nbr in ("n1", "n2"):
            self.assertTrue(by[nbr]["interpolated"])  # display-only fill
            self.assertEqual(by[nbr]["conflictFraction"], 0.9)  # inherited
            # inherited too, but the popup gates on !interpolated
            self.assertEqual(by[nbr]["inZoneFraction"], 0.5)
        # measured geometry is reused, not refetched
        m1 = [f for f in stitched["features"]
              if f["properties"]["cell"] == "m1"][0]
        self.assertEqual(m1["geometry"]["coordinates"], ring)
        # without a bridge (offline): input returned unchanged
        self.assertEqual(h3report.stitch_for_heatmap(fc), fc)


if __name__ == "__main__":
    unittest.main()
