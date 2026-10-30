"""Unit tests voor de Gent-embed (tab 5) in build_simulation.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
sys.path.insert(0, str(SIM))


class TestBuildGent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from build_simulation import build_gent

        cls.gent = build_gent()

    def test_negen_personas_met_verwachte_statussen(self):
        statussen = {p["id"]: p["status"] for p in self.gent["personas"]}
        self.assertEqual(
            statussen,
            {
                "sanne": "gereed",
                "ahmed": "gereed-met-waarschuwing",
                "maria": "gereed",
                "fatima": "gereed-met-waarschuwing",
                "jeroen": "gereed",
                "ellen": "geweigerd",
                "dirk": "blokkade",
                "wim": "blokkade",
                "nadia": "gereed",
            },
        )

    def test_iam_auth_methode_en_loa_doorgegeven(self):
        auth = {p["id"]: p["auth"] for p in self.gent["personas"]}
        self.assertEqual(auth["sanne"]["methode"], "eudi-wallet")
        self.assertEqual(auth["sanne"]["loa"], "substantial")
        self.assertEqual(auth["wim"]["loa"], "low")
        self.assertEqual(auth["nadia"]["methode"], "acm-idm")
        self.assertNotIn("loa", auth["nadia"])

    def test_events_ketting_geverifieerd_voor_alle_personas(self):
        for p in self.gent["personas"]:
            self.assertTrue(p["chainOk"], msg=f"ketting faalt voor {p['id']}")
            self.assertTrue(p["events"], msg=f"geen events voor {p['id']}")

    def test_events_bevatten_alleen_soort_en_volgnummer(self):
        for p in self.gent["personas"]:
            for e in p["events"]:
                self.assertEqual(set(e), {"seq", "kind"})

    def test_weigering_stopt_zonder_prefill(self):
        ellen = next(p for p in self.gent["personas"] if p["id"] == "ellen")
        self.assertEqual(ellen["prefill"]["transacties"], [])
        self.assertEqual(ellen["auth"]["toestemming"], "geweigerd")
        self.assertEqual(ellen["h3"]["verdict"], "n.v.t.")

    def test_prefill_dracht_herkomstlabels(self):
        sanne = next(p for p in self.gent["personas"] if p["id"] == "sanne")
        velden = [v for t in sanne["prefill"]["transacties"] for v in t["velden"]]
        labels = {v["label"] for v in velden}
        self.assertIn("authentiek", labels)
        self.assertTrue(labels <= {"authentiek", "gebruiker", "correctie", "afgeleid"})
        kenteken = next(v for v in velden if v["veld"] == "kenteken")
        self.assertTrue(kenteken["bron"].startswith("magda:kenteken"))

    def test_bronversies_en_serviceTitels_aanwezig(self):
        self.assertIn("gent-lez", self.gent["bronversies"])
        self.assertIn("ontheffing-lez", self.gent["serviceTitels"])
        self.assertEqual(self.gent["lifeEventCode"], "GT-MOB-01")


if __name__ == "__main__":
    unittest.main()
