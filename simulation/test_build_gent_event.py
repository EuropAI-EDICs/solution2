"""Unit tests voor de event-embed (GT-EVT-01) in build_simulation.py."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
sys.path.insert(0, str(SIM))


class TestBuildGentEvent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from build_simulation import build_gent

        cls.evt = build_gent("gent-evenement-organisator")

    def test_zes_eventpersonas_met_verwachte_statussen(self):
        statussen = {p["id"]: p["status"] for p in self.evt["personas"]}
        self.assertEqual(statussen, {
            "fien": "gereed",
            "mo": "gereed-met-waarschuwing",
            "lorne": "blokkade",
            "nathalie": "gereed-met-waarschuwing",
            "gil": "gereed-met-waarschuwing",
            "jef": "geweigerd",
        })

    def test_pakketmeta_en_diensten(self):
        self.assertEqual(self.evt["lifeEventCode"], "GT-EVT-01")
        self.assertIn("evenement-aanvragen", self.evt["serviceTitels"])

    def test_kaart_is_eventmodus_met_lez(self):
        for p in self.evt["personas"]:
            kaart = p.get("kaart")
            self.assertIsNotNone(kaart, msg=p["id"])
            self.assertEqual(kaart["mode"], "event")
            self.assertTrue(kaart["svg"]["zones"]["gent-lez"].startswith("M"))
            self.assertIsNone(kaart["svg"]["routes"])

    def test_aanlooptijd_in_het_formulier_en_de_feiten(self):
        fien = next(p for p in self.evt["personas"] if p["id"] == "fien")
        velden = {v["veld"]: v for t in fien["prefill"]["transacties"] for v in t["velden"]}
        self.assertEqual(velden["aanlooptijd"]["waarde"], "ruim-op-tijd")
        self.assertTrue(velden["aanlooptijd"]["bron"].startswith("timing:aanlooptijd"))
        gil = next(p for p in self.evt["personas"] if p["id"] == "gil")
        gvelden = {v["veld"]: v for t in gil["prefill"]["transacties"] for v in t["velden"]}
        self.assertEqual(gvelden["feestenzone"]["waarde"], "in")

    def test_events_ketting_geverifieerd_en_gemaskeerd(self):
        for p in self.evt["personas"]:
            self.assertTrue(p["chainOk"], msg=f"ketting faalt voor {p['id']}")
            tekst = json.dumps(p["events"], ensure_ascii=False)
            self.assertNotIn("Veldstraat", tekst)
            self.assertNotIn("2026-12-20", tekst)  # datums blijven buiten de events (SEC-05)


if __name__ == '__main__':
    unittest.main()
