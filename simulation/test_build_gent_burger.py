"""Unit tests voor de burger-embed (GT-VERH-01) in build_simulation.py."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
sys.path.insert(0, str(SIM))


class TestBuildGentBurger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from build_simulation import build_gent

        cls.burger = build_gent("gent-verhuizen-burger")

    def test_zeven_burgerpersonas_met_verwachte_statussen(self):
        statussen = {p["id"]: p["status"] for p in self.burger["personas"]}
        self.assertEqual(statussen, {
            "lisa": "gereed",
            "tomas": "gereed",
            "farah": "gereed-met-waarschuwing",
            "noor": "gereed-met-waarschuwing",
            "emma": "blokkade",
            "yana": "gereed",
            "robrecht": "geweigerd",
        })

    def test_pakketmeta_en_diensten(self):
        self.assertEqual(self.burger["lifeEventCode"], "GT-VERH-01")
        self.assertEqual(self.burger["packageId"], "gent-verhuizen-burger")
        self.assertIn("bewonerskaart", self.burger["serviceTitels"])
        self.assertIn("gent-bewonerszone", self.burger["bronversies"])

    def test_kaart_is_burgermodus_met_regelingzones(self):
        for p in self.burger["personas"]:
            kaart = p.get("kaart")
            self.assertIsNotNone(kaart, msg=p["id"])
            self.assertEqual(kaart["mode"], "burger")
            self.assertTrue(kaart["start"]["adres"])
            for laag in ("gent-bewonerszone", "gent-parkeertariefzone", "gent-lez"):
                self.assertTrue(kaart["svg"]["zones"][laag].startswith("M"), msg=f"{p['id']}: {laag}")
            self.assertIn(kaart["zones"]["gent-bewonerszone"], ("in", "niet-in"))
            self.assertIsNone(kaart["svg"]["routes"])

    def test_lisa_in_bewonerszone_tomas_buiten(self):
        zones = {p["id"]: p["kaart"]["zones"] for p in self.burger["personas"]}
        self.assertEqual(zones["lisa"]["gent-bewonerszone"], "in")
        self.assertEqual(zones["lisa"]["gent-lez"], "in")
        self.assertEqual(zones["tomas"]["gent-bewonerszone"], "niet-in")
        self.assertEqual(zones["tomas"]["gent-lez"], "niet-in")

    def test_events_ketting_geverifieerd_en_gemaskeerd(self):
        for p in self.burger["personas"]:
            self.assertTrue(p["chainOk"], msg=f"ketting faalt voor {p['id']}")
            for e in p["events"]:
                self.assertEqual(set(e), {"seq", "kind"})
            tekst = json.dumps(p["events"], ensure_ascii=False)
            self.assertNotIn("Veldstraat", tekst)
            self.assertNotIn("Ottergemsesteenweg", tekst)

    def test_data_lookup_stap_en_afvalsfeiten_aanwezig(self):
        lisa = next(p for p in self.burger["personas"] if p["id"] == "lisa")
        stap_ids = [s["stepId"] for s in lisa["steps"]]
        self.assertIn("data-lookup", stap_ids)
        afval_feiten = [r for r in lisa["context"]["regels"] if r["feit"].startswith("afval")]
        self.assertTrue(afval_feiten)
        self.assertTrue(all(r["bron"].startswith("dataset:ivago-ophaalkalender") for r in afval_feiten))

    def test_ontvangstbewijs_en_niet_ingediend(self):
        lisa = next(p for p in self.burger["personas"] if p["id"] == "lisa")
        ontvangst = lisa["submission"]["ontvangst"]["transacties"]
        self.assertEqual(len(ontvangst), 1)
        self.assertEqual(ontvangst[0]["status"], "geaccepteerd")
        self.assertTrue(ontvangst[0]["referentie"].startswith("GENT-"))

        robrecht = next(p for p in self.burger["personas"] if p["id"] == "robrecht")
        self.assertEqual(robrecht["submission"]["ontvangst"]["transacties"][0]["status"], "niet-ingediend")


if __name__ == '__main__':
    unittest.main()
