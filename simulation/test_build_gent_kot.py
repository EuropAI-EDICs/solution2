"""Unit tests voor de kot-embed (GT-KOT-01) in build_simulation.py."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
sys.path.insert(0, str(SIM))


class TestBuildGentKot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from build_simulation import build_gent

        cls.kot = build_gent("gent-kot-verhuurder")

    def test_zes_kotpersonas_met_verwachte_statussen(self):
        statussen = {p["id"]: p["status"] for p in self.kot["personas"]}
        self.assertEqual(statussen, {
            "wouter": "gereed",
            "saartje": "gereed-met-waarschuwing",
            "gregory": "gereed-met-waarschuwing",
            "lea": "gereed-met-waarschuwing",
            "milan": "gereed",
            "karel": "geweigerd",
        })

    def test_pakketmeta_en_diensten(self):
        self.assertEqual(self.kot["lifeEventCode"], "GT-KOT-01")
        self.assertEqual(self.kot["packageId"], "gent-kot-verhuurder")
        self.assertIn("kot-melden", self.kot["serviceTitels"])
        self.assertIn("gent-kotzone", self.kot["bronversies"])

    def test_kaart_is_kotmodus_met_benoemde_kotzone(self):
        for p in self.kot["personas"]:
            kaart = p.get("kaart")
            self.assertIsNotNone(kaart, msg=p["id"])
            self.assertEqual(kaart["mode"], "kot")
            self.assertTrue(kaart["svg"]["zones"]["gent-kotzone"].startswith("M"))
            self.assertTrue(kaart["zoneNaam"])  # echte zone-naam uit het attribuut
            self.assertIsNone(kaart["svg"]["routes"])

    def test_kotzone_in_het_meldingsformulier(self):
        wouter = next(p for p in self.kot["personas"] if p["id"] == "wouter")
        velden = {v["veld"]: v for t in wouter["prefill"]["transacties"] for v in t["velden"]}
        self.assertIn("kotzone", velden)
        self.assertTrue(velden["kotzone"]["waarde"])  # bijv. "Sint-Pietersplein"
        self.assertTrue(velden["kotzone"]["bron"].startswith("gis:gent-kotzone"))

    def test_events_ketting_geverifieerd_en_gemaskeerd(self):
        for p in self.kot["personas"]:
            self.assertTrue(p["chainOk"], msg=f"ketting faalt voor {p['id']}")
            tekst = json.dumps(p["events"], ensure_ascii=False)
            self.assertNotIn("Overpoortstraat", tekst)

    def test_ontvangstbewijs_en_niet_ingediend(self):
        wouter = next(p for p in self.kot["personas"] if p["id"] == "wouter")
        ontvangst = wouter["submission"]["ontvangst"]["transacties"]
        self.assertEqual(len(ontvangst), 1)
        self.assertEqual(ontvangst[0]["status"], "geaccepteerd")
        karel = next(p for p in self.kot["personas"] if p["id"] == "karel")
        self.assertEqual(karel["submission"]["ontvangst"]["transacties"][0]["status"], "niet-ingediend")


if __name__ == '__main__':
    unittest.main()


class TestKotregisterEmbed(unittest.TestCase):
    """Het blok wordt door main() aan data["gentKot"] gehangen; verify_static
    toetst de kaart tegen het échte gebouwde bestand."""

    @classmethod
    def setUpClass(cls):
        from build_simulation import _kotregister_blok

        cls.register = _kotregister_blok(ROOT / "poc-gent")

    def test_kotregister_ingebed_in_het_kotpakket(self):
        reg = self.register
        self.assertIsNotNone(reg)
        self.assertGreaterEqual(reg["totaalInDatabase"], 5000)
        self.assertGreaterEqual(len(reg["koten"]), 90)
        for kot in reg["koten"]:
            self.assertTrue(kot["titel"] and kot["adres"] and kot["url"])
            self.assertIn(kot["type"], ("kamer", "studio", None))

    def test_beeldverwijzingen_wijzen_naar_de_broncache(self):
        bron = ROOT / "poc-gent" / "fixtures" / "source"
        met_beeld = [k for k in self.register["koten"] if k["beeld"]]
        self.assertGreaterEqual(len(met_beeld), 80)
        for kot in met_beeld:
            self.assertTrue((bron / kot["beeld"]).is_file(), kot["beeld"])
