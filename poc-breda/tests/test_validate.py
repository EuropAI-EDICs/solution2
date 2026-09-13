"""Offline tests: V0-schema + V1-sanitychecks van de scan."""

from __future__ import annotations

import copy
import unittest

from breda import validate  # noqa: E402
from tests import fixtures, util  # noqa: E402  — util zet ook sys.path goed


class TestValidateScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = util.full_scan(fixtures.layers_dict())

    def _validate(self, scan, degradations=None, **kw):
        return validate.validate_scan(
            scan, degradations or [], min_buurten=kw.pop("min_buurten", 40)
        )

    def test_fixture_scan_is_valide(self):
        result = self._validate(self.base)
        self.assertEqual(result["verdict"], "pass", msg=str(result["errors"]))
        self.assertEqual(result["errors"], [])

    def test_score_buiten_bereik_faalt(self):
        broken = copy.deepcopy(self.base)
        broken["buurten"][0]["scores"]["democratic"]["score"] = 140.0
        result = self._validate(broken)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any(c["id"] == "V1-scorebereik" for c in result["errors"]))

    def test_stille_missing_faalt(self):
        broken = copy.deepcopy(self.base)
        for b in broken["buurten"]:
            if b["scores"]["social"]["score"] is None:
                b["missing"]["social"] = []
                break
        result = self._validate(broken)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any(c["id"] == "V1-missing-gedocumenteerd" for c in result["errors"]))

    def test_volumecheck(self):
        result = self._validate(self.base, min_buurten=10_000)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any(c["id"] == "V1-buurtvolume" for c in result["errors"]))

    def test_degradaties_worden_geregistreerd(self):
        result = self._validate(
            self.base,
            degradations=[{"sourceId": "breda-bomen", "error": "test"}],
            min_buurten=10,
        )
        self.assertEqual(result["degradations"][0]["sourceId"], "breda-bomen")
        check = next(c for c in result["checks"] if c["id"] == "V1-degradaties-geregistreerd")
        self.assertIn("breda-bomen", check["detail"])


if __name__ == "__main__":
    unittest.main()
