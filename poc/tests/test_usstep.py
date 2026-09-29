"""Offline tests for pipeline.usstep (Urban Strategy bridge)."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

POC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POC_ROOT))

from pipeline import usstep  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "us_fixtures"
SCHEMA = POC_ROOT / "schemas" / "us-stiltegebied-eval.schema.json"


class UsStepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["POC_US_OFFLINE"] = "1"
        if not (FIXDIR / "fetch-input.json").exists():
            raise unittest.SkipTest(
                "us fixtures missing — run: "
                "POC_US_OFFLINE= ../nldt/.venv/bin/python tests/make_us_fixtures.py"
            )

    def test_fingerprint_stable(self):
        a = usstep.fingerprint("p", {"x": 1, "y": [1, 2]})
        b = usstep.fingerprint("p", {"y": [1, 2], "x": 1})
        self.assertEqual(a, b)

    def test_fetch_from_cache_offline(self):
        inputs = json.loads((FIXDIR / "fetch-input.json").read_text(encoding="utf-8"))
        with mock.patch.object(usstep.subprocess, "run",
                               side_effect=AssertionError("must not spawn")):
            out = usstep.call("us-fetch-noise-receptors", inputs)
        self.assertEqual(len(out["receptors"]["features"]), 5)
        # second call still cache-only
        self.assertEqual(out, usstep.call("us-fetch-noise-receptors", inputs))

    def test_eval_from_cache_offline(self):
        inputs = json.loads((FIXDIR / "eval-input.json").read_text(encoding="utf-8"))
        with mock.patch.object(usstep.subprocess, "run",
                               side_effect=AssertionError("must not spawn")):
            out = usstep.call("us-stiltegebied-noise-eval", inputs)
        evaluation = out["evaluation"]
        self.assertEqual(evaluation["counts"]["exceedancesTotal"], 2)
        self.assertEqual(evaluation["normCardId"], "NC-W-11")
        # optional schema check when jsonschema available
        try:
            import jsonschema
            schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema).validate(evaluation)
        except ImportError:
            pass

    def test_offline_miss_raises(self):
        with self.assertRaises(usstep.UsUnavailableError):
            usstep.call("us-fetch-noise-receptors",
                        {"source": "fixture://does-not-exist-xyz.geojson"})


if __name__ == "__main__":
    unittest.main()
