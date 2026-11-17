# nldt/tests/test_poc_veenendaal_kennisgraaf.py
"""Tests voor poc-veenendaal/kennisgraaf.py — contract kennisgraaf/v1.

Offline en deterministisch: synthetische bron-dicts (zelfde vorm als gebied.json,
loketvragen.json, zones.json en de RTR-index); geen netwerk, geen run-artefacten.
"""
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "poc_veenendaal_kennisgraaf", ROOT / "poc-veenendaal" / "kennisgraaf.py")
kg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kg)

GEBIED = {
    "gebied": "Spoorzone Veenendaal",
    "werkgrens": {"opp_ha": 30.0, "geojson_rd": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}},
    "doelen_uit_toekomstbeeld": {"woningen_nieuw_feiten_tabel": 100, "groen_ha_minimum": 5},
    "deelgebied_zones": {"zones": [
        {"naam": "Zone West", "opp_ha": 18.0},
        {"naam": "Zone Oost", "opp_ha": 12.0},
    ]},
}
LOKET = {
    "runId": "t-loket",
    "regeling": {"identificatie": "/akn/nl/act/gm0345/2020/omgevingsplan",
                 "officieleTitel": "Omgevingsplan", "pakketSha256": "abc"},
    "oin": "00000001001104470000",
    "locatieGebonden": {
        "gios": [
            {"bestand": "gio_a.gml", "frbrWork": "/join/id/regdata/gm0345/2026/a",
             "snijdtWerkgrens": True, "overlapHa": 30.0, "aantalPolygonen": 1},
            {"bestand": "gio_b.gml", "frbrWork": None, "snijdtWerkgrens": False},
        ],
        "verwijzingen": [
            {"rtrId": 1, "locatieIdentificatie": "x", "status": "afwezig-in-pakket"},
            {"rtrId": 2, "locatieIdentificatie": "y", "status": "aanwezig-als-ow-object"},
        ],
    },
    "programmaGebonden": [
        {"activiteit": "BouwwerkVeranderen", "soort": "programma", "bewijs": "100 woningen"},
    ],
}
ZONES_RUN = {
    "runId": "t-zones",
    "zones": [
        {"naam": "Zone West", "opp_ha": 18.0,
         "gio_lagen": [{"gio": "gio_a", "frbrWork": "w", "overlapHa": 18.0,
                        "objecten": 1, "dekkingPct": 100.0}]},
        {"naam": "Zone Oost", "opp_ha": 12.0, "gio_lagen": []},
    ],
}
STTR = {
    "bestanden": [
        {"identifier": 1, "naam": "Regel A", "activiteit": "ActX", "begindatum": "01-01-2024",
         "einddatum": None, "dmnVersie": "1.2", "geoVerwijzingen": 0,
         "decisions": [{"projecteerbaar": True}, {"projecteerbaar": False}], "sha256": "aa"},
        {"identifier": 2, "naam": "Regel B", "activiteit": "ActY", "begindatum": "01-01-2023",
         "einddatum": None, "dmnVersie": "1.1", "geoVerwijzingen": 1,
         "decisions": [], "sha256": "bb"},
        {"identifier": 3, "naam": "Vervallen", "activiteit": "ActX", "begindatum": "01-01-2020",
         "einddatum": "01-01-2024", "dmnVersie": "1.1", "geoVerwijzingen": 0,
         "decisions": [], "sha256": "cc"},
    ]
}


class TestBouwGraaf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = kg.bouw_graaf(GEBIED, LOKET, ZONES_RUN, STTR)

    def test_knoop_en_edge_aantallen(self):
        per_type = {n["type"] for n in self.g["nodes"]}
        self.assertEqual(set, type(per_type))
        self.assertEqual(sum(1 for n in self.g["nodes"] if n["type"] == "zone"), 2)
        self.assertEqual(sum(1 for n in self.g["nodes"] if n["type"] == "gio"), 2)
        self.assertEqual(sum(1 for n in self.g["nodes"] if n["type"] == "rtr"), 2)  # vervallen weg
        self.assertEqual(len(self.g["koppelgaten"]), 1)

    def test_vervallen_rtr_niet_geprojecteerd(self):
        ids = {n["id"] for n in self.g["nodes"]}
        self.assertIn("rtr:1", ids)
        self.assertNotIn("rtr:3", ids)

    def test_edges_resolveerbaar_en_uniek_getypeerd(self):
        ids = {n["id"] for n in self.g["nodes"]}
        for e in self.g["edges"]:
            self.assertIn(e["van"], ids)
            self.assertIn(e["naar"], ids)

    def test_overlapt_edges_uit_zones_run(self):
        ov = [e for e in self.g["edges"] if e["type"] == "overlapt"]
        self.assertEqual(len(ov), 1)
        self.assertEqual(ov[0]["dekkingPct"], 100.0)
        self.assertEqual(ov[0]["bron"], "t-zones")

    def test_programma_edge_draagt_bewijs(self):
        nodes = {n["id"]: n for n in self.g["nodes"]}
        p = [n for n in self.g["nodes"] if n["type"] == "programma-feit"]
        self.assertEqual(len(p), 1)
        self.assertIn("100 woningen", p[0]["bewijs"])
        raakt = [e for e in self.g["edges"] if e["type"] == "raakt"]
        self.assertEqual(raakt[0]["naar"], "activiteit:bouwwerkveranderen")

    def test_koppelgat_eerlijkheid_geen_rtr_gio(self):
        # de synthetische verwijzingen zijn niet legbaar → geen rtr→gio-edges
        for e in self.g["edges"]:
            self.assertFalse(e["van"].startswith("rtr:") and e["naar"].startswith("gio:"))
        self.assertIn("geen rtr→gio-edges", self.g["koppelgaten"][0]["consequentie"])


class TestControleerGraaf(unittest.TestCase):
    def test_consistente_input_pass(self):
        g = kg.bouw_graaf(GEBIED, LOKET, ZONES_RUN, STTR)
        checks = kg.controleer_graaf(g, GEBIED, LOKET, ZONES_RUN, STTR)
        self.assertTrue(all(c["ok"] for c in checks), [c for c in checks if not c["ok"]])

    def test_tampering_valt_door_de_mand(self):
        g = kg.bouw_graaf(GEBIED, LOKET, ZONES_RUN, STTR)
        g["nodes"] = [n for n in g["nodes"] if n["id"] != "gio:gio_a"]  # knoop weggehaald
        checks = kg.controleer_graaf(g, GEBIED, LOKET, ZONES_RUN, STTR)
        namen = {c["check"] for c in checks if not c["ok"]}
        self.assertIn("edges resolveerbaar", namen)
        self.assertIn("gio-aantal ≡ pakket-sweep", namen)

    def test_zone_som_check(self):
        gebied = {**GEBIED, "werkgrens": {"opp_ha": 99.0}}
        g = kg.bouw_graaf(gebied, LOKET, ZONES_RUN, STTR)
        checks = kg.controleer_graaf(g, gebied, LOKET, ZONES_RUN, STTR)
        namen = {c["check"] for c in checks if not c["ok"]}
        self.assertIn("Σ zone-opp ≈ werkgrens", namen)


if __name__ == "__main__":
    unittest.main()
