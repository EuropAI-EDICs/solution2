# nldt/tests/test_poc_veenendaal_werkgrens.py
"""Tests voor de polygon-werkgrens in poc-veenendaal/run.py — de gecorrigeerde
zandloper-grens uit het Toekomstbeeld (Grift/spoor/Rondwegen + Franse Gat Noord).

Offline en deterministisch: alleen data/gebied.json (commit) en synthetische
geometrieën; geen netwerk, geen PDOK-cache.
"""
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "poc_veenendaal_run", ROOT / "poc-veenendaal" / "run.py")
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

GEBIED = json.loads((ROOT / "poc-veenendaal" / "data" / "gebied.json").read_text())


class TestEarcut(unittest.TestCase):
    def test_vierkant(self):
        vierkant = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        tris = run.earcut(vierkant)
        som = sum(0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                  for a, b, c in tris)
        self.assertAlmostEqual(som, 100.0, places=6)

    def test_concaaf_l_vorm(self):
        l = [[0, 0], [20, 0], [20, 10], [10, 10], [10, 20], [0, 20], [0, 0]]
        tris = run.earcut(l)
        som = sum(0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                  for a, b, c in tris)
        self.assertAlmostEqual(som, abs(run.ring_area(l)), places=6)
        self.assertEqual(len(tris), 4)

    def test_collineaire_punten_blokkeren_niet(self):
        # drie exact collineaire punten op één as — klassieke earcut-deadlock
        ring = [[0, 0], [5, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        tris = run.earcut(ring)
        som = sum(0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
                  for a, b, c in tris)
        self.assertAlmostEqual(som, 100.0, places=6)

    def test_werkgrens_ring_trianguleert_volledig(self):
        grens = run.laad_werkgrens(GEBIED["werkgrens"])
        self.assertAlmostEqual(grens["area_m2"] / 10_000, GEBIED["werkgrens"]["opp_ha"],
                               delta=0.2)  # afronding gebied.json is 0,1 ha


class TestRingCentroid(unittest.TestCase):
    def test_vierkant_centroid(self):
        vierkant = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        self.assertEqual(run.ring_centroid(vierkant), (5.0, 5.0))

    def test_rechthoek_centroid_gesloten_en_open(self):
        gesloten = [[0, 0], [20, 0], [20, 10], [0, 10], [0, 0]]
        open_ = gesloten[:-1]
        self.assertEqual(run.ring_centroid(gesloten), run.ring_centroid(open_))


class TestWerkgrensPolygon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grens = run.laad_werkgrens(GEBIED["werkgrens"])

    def test_modus(self):
        self.assertEqual(self.grens["mode"], "polygon")
        self.assertEqual(self.grens["bbox"], (165340, 447490, 167820, 448950))

    def test_ankerliggingen(self):
        # in: 't Goeie Spoor POI (tussen Grift en spoor), Franse Gat-straat,
        #     Engelenburg (De Tinneweide)
        for x, y in ((165889, 448344), (165356, 448144), (167090, 448062)):
            self.assertTrue(run.grens_bevat_zwaartepunt(
                {"type": "Point", "coordinates": [x, y]}, self.grens), (x, y))
        # buiten: centrum (Markt), het oude bbox-overschot ten oosten van
        # Rondweg-Oost, en Franse Gat-zuid onder de zuidrand van FG Noord
        for x, y in ((166475, 448620), (167950, 447850), (165795, 447474)):
            self.assertFalse(run.grens_bevat_zwaartepunt(
                {"type": "Point", "coordinates": [x, y]}, self.grens), (x, y))

    def test_vlakclip_volledig_binnen(self):
        vol = {"type": "Polygon", "coordinates": [
            [[166100, 448200], [166200, 448200], [166200, 448300],
             [166100, 448300], [166100, 448200]]]}
        self.assertAlmostEqual(run.grens_area_in(vol, self.grens), 10_000.0, delta=5)

    def test_vlakclip_half_erover(self):
        # 200 m breed vak dat de oostgrens (Rondweg-Oost ~x=167.780) kruist:
        # verwacht slechts het westelijke deel binnen de polygon
        vak = {"type": "Polygon", "coordinates": [
            [[167700, 447650], [167900, 447650], [167900, 447750],
             [167700, 447750], [167700, 447650]]]}
        opp = run.grens_area_in(vak, self.grens)
        self.assertGreater(opp, 0)
        self.assertLess(opp, 10_000)
        self.assertLessEqual(opp, self.grens["area_m2"])

    def test_lijnclip(self):
        # west-oost lijn door de knijp: volledig binnen bij het station,
        # nul ver buiten de zone
        lijn = {"type": "LineString", "coordinates": [[166100, 448200], [166300, 448200]]}
        self.assertGreater(run.grens_lijn_km(lijn, self.grens), 0.1)
        buiten = {"type": "LineString", "coordinates": [[168000, 448200], [168200, 448200]]}
        self.assertEqual(run.grens_lijn_km(buiten, self.grens), 0.0)


class TestDeelgebiedZones(unittest.TestCase):
    def test_zones_tegelen_werkgrens(self):
        grens = run.laad_werkgrens(GEBIED["werkgrens"])
        som = 0.0
        for z in GEBIED["deelgebied_zones"]["zones"]:
            self.assertIn("polygon", z, f"zone {z['naam']} moet een polygon hebben")
            zg = run.laad_werkgrens({"geojson_rd": z["polygon"]})
            som += zg["area_m2"]
            self.assertAlmostEqual(zg["area_m2"] / 10_000, z["opp_ha"], delta=0.2)
        self.assertAlmostEqual(som, grens["area_m2"], delta=0.01 * grens["area_m2"])

    def test_zone_indeling_volgens_toekomstbeeld(self):
        # 't Franse Gat Noord ligt als enige ten zuiden van het spoor:
        # station (op het spoor) mag in geen enkele zone-zwaartepunt-test
        # ten noorden van het spoor vallen onder FG Noord
        fg = run.laad_werkgrens(
            {"geojson_rd": next(z["polygon"] for z in GEBIED["deelgebied_zones"]["zones"]
                                if z["naam"] == "'t Franse Gat Noord")})
        self.assertTrue(run.point_in_ring(165356, 448144, fg["buitenringen"][0]))   # Westersingel
        self.assertFalse(run.point_in_ring(165889, 448344, fg["buitenringen"][0]))  # 't Goeie Spoor
        # 't Goeie Spoor-zone bevat het gelijknamige POI
        gs = run.laad_werkgrens(
            {"geojson_rd": next(z["polygon"] for z in GEBIED["deelgebied_zones"]["zones"]
                                if z["naam"] == "'t Goeie Spoor")})
        self.assertTrue(run.point_in_ring(165889, 448344, gs["buitenringen"][0]))


class TestBboxCompat(unittest.TestCase):
    def test_bbox_modus_blijft_werken(self):
        grens = run.laad_werkgrens({"bbox_rd": [0, 0, 100, 100]})
        self.assertEqual(grens["mode"], "bbox")
        self.assertEqual(grens["area_m2"], 10_000)
        vak = {"type": "Polygon", "coordinates": [
            [[50, 50], [150, 50], [150, 150], [50, 150], [50, 50]]]}
        self.assertAlmostEqual(run.grens_area_in(vak, grens), 2_500.0, places=6)
        lijn = {"type": "LineString", "coordinates": [[-50, 50], [150, 50]]}
        self.assertAlmostEqual(run.grens_lijn_km(lijn, grens), 0.1, places=6)
        self.assertTrue(run.grens_bevat_zwaartepunt(
            {"type": "Point", "coordinates": [10, 10]}, grens))


if __name__ == "__main__":
    unittest.main()
