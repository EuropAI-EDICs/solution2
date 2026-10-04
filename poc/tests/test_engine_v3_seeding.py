#!/usr/bin/env python3
"""V3-seeding regression tests: ``reexecute_independent`` must seed the zone
from the AOI *before* the exclusion loop, mirroring ``execute_rules``
(``test_aoi_seed_when_only_exclusions``). Before the fix, a ruleset with only
exclusion rules (no inclusion) left ``zone is None`` during the whole
exclusion loop — every exclusion was silently skipped and the AOI was returned
verbatim (the water track's IoU 0.996697 instead of ~1.0). Synthetic fixture
polygons ONLY — no network, mirroring test_engine.py's construction.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPE_DIR = ROOT / "poc" / "pipeline"
if str(PIPE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPE_DIR))

import engine  # noqa: E402

from shapely.geometry import box, mapping  # noqa: E402

X0, Y0 = 140000.0, 455000.0
REL_TOL = 1e-6


def square(x0, y0, w, h):
    return box(x0, y0, x0 + w, y0 + h)


def feature_collection(*geoms, source_id="fixture", last_checked="2026-10-04T00:00:00Z"):
    feats = [
        {"type": "Feature", "id": i, "properties": {"fid": i}, "geometry": mapping(g)}
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


def rule_excl(rid, layer, **kw):
    r = {"id": rid, "zoneSemantics": "exclusion", "sourceLayerId": layer}
    r.update(kw)
    return r


def assert_close(testcase, actual, expected, msg, rel=REL_TOL):
    testcase.assertLessEqual(
        abs(actual - expected) / (abs(expected) if expected else 1.0), rel,
        msg=f"{msg}: expected ~{expected}, got {actual}",
    )


class TestV3AoiSeedingBeforeExclusions(unittest.TestCase):
    def test_only_exclusion_rules_seed_from_aoi(self):
        """The bug: exclusion-only ruleset + AOI. Pre-fix the independent
        result was the bare AOI (10000 m2, exclusion skipped); post-fix it is
        AOI minus the exclusion overlap (20x20 m bite = 9600 m2)."""
        aoi = square(X0, Y0, 100, 100)
        excl = square(X0 + 80, Y0 + 80, 40, 40)  # overlap with AOI = 20x20
        layers = {"excl": feature_collection(excl)}
        rules = [rule_excl("R-EXCL", "excl", value=0)]

        zone = engine.reexecute_independent(rules, layers, aoi=mapping(aoi))
        assert_close(self, zone.area, 9600.0, msg="AOI-seeded V3 difference")

    def test_only_exclusions_agrees_with_primary_path(self):
        """Primary (shapely) and independent (geopandas) paths must agree on
        the AOI-seeded exclusion semantics — IoU ~ 1.0, mirroring the V3
        critic check that the water run exposed at province scale."""
        aoi = square(X0, Y0, 100, 100)
        excl = square(X0 + 80, Y0 + 80, 40, 40)
        layers = {"excl": feature_collection(excl)}
        rules = [rule_excl("R-EXCL", "excl", value=0)]

        primary = engine.execute_rules(rules, layers, aoi=mapping(aoi))[-1]
        independent = engine.reexecute_independent(rules, layers, aoi=mapping(aoi))
        assert_close(self, independent.area, primary["areaM2"],
                     msg="V3 vs primary final area (AOI-seeded exclusion)")

    def test_only_exclusions_no_aoi_still_refused(self):
        """No inclusion rules and no AOI remains a cite-or-abstain error in
        the independent path too (pre- and post-fix behaviour)."""
        layers = {"excl": feature_collection(square(X0, Y0, 10, 10))}
        rules = [rule_excl("R-EXCL", "excl", value=0)]
        with self.assertRaises(engine.RuleError):
            engine.reexecute_independent(rules, layers)

    def test_inclusion_path_unchanged_by_seeding_fix(self):
        """Guard: an inclusion+exclusion ruleset (wind/zon/bos shape) keeps
        its exact V3 result — the seeding only adds a branch for tracks
        without inclusion rules."""
        aoi = square(X0, Y0, 100, 100)
        layers = {
            "incl": feature_collection(square(X0, Y0, 100, 100)),
            "excl": feature_collection(square(X0 + 80, Y0 + 80, 40, 40)),
        }
        rules = [
            {"id": "R-INCL", "zoneSemantics": "inclusion", "sourceLayerId": "incl"},
            rule_excl("R-EXCL", "excl", value=0),
        ]
        zone = engine.reexecute_independent(rules, layers, aoi=mapping(aoi))
        assert_close(self, zone.area, 9600.0,
                     msg="inclusion-path V3 area unchanged")


if __name__ == "__main__":
    unittest.main()
