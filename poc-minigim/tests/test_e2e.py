"""E2E-test: volledige run.py offline (stub-fetch) — exit 0 only bij verdict pass."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run as runmod  # noqa: E402
from minigim import checklist as clmod  # noqa: E402

from tests import fixtures  # noqa: E402


class TestE2EOffline(unittest.TestCase):
    def test_full_run(self):
        fake = fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            aoi = tmp / "plangrens.geojson"
            aoi.write_text(json.dumps(fixtures.AOI_FC), encoding="utf-8")
            runs_dir = tmp / "runs"
            with mock.patch.object(clmod, "fetch_layer", fake):
                rc = runmod.main(["--aoi", str(aoi), "--label", "offline-test",
                                  "--runs-dir", str(runs_dir)])
            self.assertEqual(rc, 0)
            run_dirs = list(runs_dir.iterdir())
            self.assertEqual(len(run_dirs), 1)
            out = run_dirs[0]
            for name in ("report.html", "omgevingsanalyse.json", "ils-draft.json",
                         "ils-draft.features.28992.geojson", "validation.json",
                         "prov.json", "run_summary.json"):
                self.assertTrue((out / name).exists(), name)

            validation = json.loads((out / "validation.json").read_text())
            self.assertEqual(validation["verdict"], "pass")

            doc = json.loads((out / "omgevingsanalyse.json").read_text())
            self.assertEqual(doc["summary"]["itemCount"], 74)
            self.assertEqual(doc["summary"]["deliveredStatus"]["delivered"], 29)
            self.assertEqual(doc["summary"]["deliveredStatus"]["manual-action"], 45)

            # prov bevat manifests maar nooit volledige feature-collecties
            prov = json.loads((out / "prov.json").read_text())
            self.assertIn("layers", prov)
            for v in prov["layers"].values():
                self.assertNotIn("fc", v)
                self.assertNotIn("features", v)

            # rapport bevat de kaartdata compact
            report = (out / "report.html").read_text(encoding="utf-8")
            self.assertIn("MiniGIM gebiedscheck", report)
            self.assertIn("ILS draft", report)

            # run_summary
            rs = json.loads((out / "run_summary.json").read_text())
            self.assertEqual(rs["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
