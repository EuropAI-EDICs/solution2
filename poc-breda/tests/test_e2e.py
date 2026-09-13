"""Offline e2e: volledige run.py-pipeline op fixtures (netwerk weggemockt)."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from tests import fixtures, util  # noqa: E402  — util zet ook sys.path goed


def _fake_fetch_all(**kwargs):
    include_bomen = kwargs.get("include_bomen", True)
    return {
        "layers": fixtures.layers_dict(include_bomen=include_bomen),
        "degradations": [],
        "bbox": "115000,400000,127000,410000",
    }


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run_mod = util.run_module()
        import tempfile
        from pathlib import Path

        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "run"
        with mock.patch.object(run_mod.fetch, "fetch_all", side_effect=_fake_fetch_all):
            cls.exit = run_mod.run(["--out", str(cls.out)])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exit_code(self):
        self.assertEqual(self.exit, 0)

    def test_artefacten(self):
        for name in ("value-scan.json", "validation.json", "layers.json",
                     "prov.json", "run_summary.json", "report.html", "report.md",
                     "geo-buurten.wgs84.geojson", "overlays.wgs84.geojson"):
            self.assertTrue((self.out / name).exists(), name)

    def test_scan_is_schema_valide_en_valideert_pass(self):
        scan = json.loads((self.out / "value-scan.json").read_text(encoding="utf-8"))
        validation = json.loads((self.out / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(scan["scan"]["gemeenteCode"], "GM0758")
        self.assertEqual(len(scan["buurten"]), fixtures.COLS * fixtures.ROWS)
        self.assertEqual(validation["verdict"], "pass")

    def test_run_summary(self):
        summary = json.loads((self.out / "run_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["verdict"], "pass")
        self.assertEqual(summary["nBuurten"], fixtures.COLS * fixtures.ROWS)
        self.assertGreater(summary["scoresComputed"]["democratic"], 0)
        for name, meta in summary["artifacts"].items():
            self.assertRegex(meta["sha256"], r"^[0-9a-f]{64}$")

    def test_souvereiniteitsmanifest_compleet(self):
        scan = json.loads((self.out / "value-scan.json").read_text(encoding="utf-8"))
        manifest = scan["values"]["autonomous"]["manifest"]
        self.assertGreaterEqual(len(manifest), 7)
        self.assertTrue(all(m["met"] for m in manifest))
        self.assertTrue(all(m["evidence"] for m in manifest))

    def test_programma_koppeling_aanwezig(self):
        scan = json.loads((self.out / "value-scan.json").read_text(encoding="utf-8"))
        for value, spec in scan["values"].items():
            self.assertTrue(spec["programmeItems"], f"{value} zonder programma-items")


if __name__ == "__main__":
    unittest.main()
