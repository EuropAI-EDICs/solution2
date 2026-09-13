"""Offline tests: rapportbouw, escaping (les uit PoC-1), markdown-tweeling."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from breda import report, validate  # noqa: E402
from tests import fixtures, util  # noqa: E402  — util zet ook sys.path goed


def _build(tmp: Path):
    scan = util.full_scan(fixtures.layers_dict())
    # gevaarlijk genaamde buurt: escaping moet echt werken (PoC-1-les);
    # score naar de top forceert de naam server-side in de rollup-kaart
    scan["buurten"][0]["buurtnaam"] = "<script>alert('x')</script> & co"
    scan["buurten"][0]["scores"]["democratic"]["score"] = 100.0
    scan["rollup"]["democratic"]["top"].insert(0, [
        scan["buurten"][0]["buurtnaam"], 100.0,
    ])
    validation = validate.validate_scan(scan, [], min_buurten=40)
    return scan, validation, report.build_reports(
        scan, fixtures.layers_dict(), validation, {}, tmp
    )


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.scan, cls.validation, cls.out = _build(cls.dir)
        cls.html = (cls.dir / "report.html").read_text(encoding="utf-8")
        cls.md = (cls.dir / "report.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_artefacten_bestaan(self):
        for name in ("report.html", "report.md", "geo-buurten.wgs84.geojson",
                     "overlays.wgs84.geojson"):
            self.assertTrue((self.dir / name).exists(), name)
        for name, sha in self.out["artifacts"].items():
            self.assertRegex(sha, r"^[0-9a-f]{64}$")

    def test_scripts_in_json_data_geescapet(self):
        # de ingebedde JSON-blokken mogen geen letterlijke </script> bevatten
        for marker in ("window.__SCAN_DATA__", "window.__GEO_DATA__", "window.__OVERLAYS__"):
            start = self.html.index(marker) + len(marker)
            end = self.html.index(";", start)
            blob = self.html[start:end]
            self.assertNotIn("</script>", blob)
            self.assertNotIn("<script>", blob)

    def test_gevaarlijke_buurtnaam_geescapet_in_html(self):
        # buiten de JSON-blokken: HTML-entiteiten, geen ruwe <script>-tag
        self.assertNotIn("<script>alert", self.html)
        self.assertIn("&lt;script&gt;", self.html)

    def test_json_data_is_geldig_json_na_unescape(self):
        start = self.html.index("window.__GEO_DATA__")
        eq = self.html.index("=", start) + 1
        end = self.html.index(";", eq)
        blob = self.html[eq:end].strip()
        self.assertTrue(blob.startswith("{"))
        parsed = json.loads(blob)  # \u003c is automatisch geldig
        self.assertGreater(len(parsed["features"]), 0)

    def test_geo_features_wgs84(self):
        fc = json.loads((self.dir / "geo-buurten.wgs84.geojson").read_text(encoding="utf-8"))
        for f in fc["features"]:
            ring = f["geometry"]["coordinates"][0]
            for x, y in ring:
                self.assertTrue(3.0 < x < 7.5, f"lon buiten NL: {x}")
                self.assertTrue(50.0 < y < 54.0, f"lat buiten NL: {y}")

    def test_markdown_bevat_waardesecties(self):
        for heading in ("## Democratische waarde", "## Ruimtelijke waarde",
                        "## Economische waarde", "## Sociale waarde",
                        "## Autonome waarde", "## Bronnen", "## Beperkingen"):
            self.assertIn(heading, self.md)

    def test_verdict_zichtbaar(self):
        self.assertIn("PASS", self.html)

    def test_programma_items_geciteerd(self):
        self.assertIn("Green Spaces and Water as the backbone of the city", self.html)
        self.assertIn("Residents in the driving seat", self.html)
        self.assertIn("destad.ai", self.html)


if __name__ == "__main__":
    unittest.main()
