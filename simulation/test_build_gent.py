"""Unit tests voor de Gent-embed (tab 5) in build_simulation.py."""
from __future__ import annotations

import json
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

    def test_elf_personas_met_verwachte_statussen(self):
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
                "ilse": "blokkade",
                "hanne": "geweigerd",
            },
        )

    def test_iam_auth_methode_en_loa_doorgegeven(self):
        auth = {p["id"]: p["auth"] for p in self.gent["personas"]}
        self.assertEqual(auth["sanne"]["methode"], "eudi-wallet")
        self.assertEqual(auth["sanne"]["loa"], "substantial")
        self.assertEqual(auth["wim"]["loa"], "low")
        self.assertEqual(auth["nadia"]["methode"], "acm-idm")
        self.assertNotIn("loa", auth["nadia"])

    def test_embed_maskeert_mandaatdetails(self):
        tekst = json.dumps(self.gent["personas"], ensure_ascii=False)
        self.assertNotIn("bewindvoering", tekst)
        self.assertNotIn("moeder", tekst)
        for p in self.gent["personas"]:
            self.assertNotIn("mandaten", p["auth"])
            self.assertIn("mandaatAantal", p["auth"])

    def test_events_ketting_geverifieerd_voor_alle_personas(self):
        for p in self.gent["personas"]:
            self.assertTrue(p["chainOk"], msg=f"ketting faalt voor {p['id']}")
            self.assertTrue(p["events"], msg=f"geen events voor {p['id']}")

    def test_events_bevatten_alleen_soort_en_volgnummer(self):
        for p in self.gent["personas"]:
            for e in p["events"]:
                self.assertEqual(set(e), {"seq", "kind"})

    def test_ontvangstbewijzen_sanne_en_hanne(self):
        """Fase-3: ontvangstbewijs (FR-16) en niet-ingediend in de embed."""
        sanne = next(p for p in self.gent["personas"] if p["id"] == "sanne")
        ontvangsten = sanne["submission"]["ontvangst"]["transacties"]
        self.assertEqual(len(ontvangsten), 2)
        for tr in ontvangsten:
            self.assertEqual(tr["status"], "geaccepteerd")
            self.assertTrue(tr["referentie"].startswith("GENT-"), msg=tr["referentie"])
        self.assertTrue(sanne["submission"]["vervolgsamenvatting"]["gereed"])

        hanne = next(p for p in self.gent["personas"] if p["id"] == "hanne")
        for tr in hanne["submission"]["ontvangst"]["transacties"]:
            self.assertEqual(tr["status"], "niet-ingediend")
            self.assertIsNone(tr["referentie"])
        self.assertEqual(hanne["submission"]["vervolgsamenvatting"]["gereed"], [])
        self.assertTrue(hanne["submission"]["vervolgsamenvatting"]["open"])

    def test_events_bevatten_geen_adresstring(self):
        """De masking-claim van de embed (SEC-05) blijft geldig na fase-3:
        events dragen alléén soort+volgnummer, dus geen adres of schets-woord."""
        adressen = ("Korenmarkt 1, Gent", "Korenmarkt", "Sint-Pietersplein",
                    "Koningin Maria Hendrikaplein")
        for p in self.gent["personas"]:
            tekst = json.dumps(p["events"], ensure_ascii=False)
            for adres in adressen:
                self.assertNotIn(adres, tekst, msg=f"{p['id']}: {adres} in events")
            self.assertNotIn("loodgieter", tekst)  # woord uit sanne's schets

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

    def test_kaart_blok_voor_alle_kenteken_personas(self):
        zonder = [p["id"] for p in self.gent["personas"] if not p.get("kaart")]
        self.assertEqual(zonder, ["maria"])
        for p in self.gent["personas"]:
            kaart = p.get("kaart")
            if not kaart:
                continue
            self.assertIn(kaart["gewenst"], ("primaire", "alternatief"))
            self.assertTrue(kaart["start"]["label"] and kaart["doel"])
            self.assertTrue(kaart["svg"]["routes"]["primaire"].startswith("M"))
            self.assertTrue(kaart["svg"]["grens"].startswith("M"))
            self.assertTrue(kaart["svg"]["zones"]["gent-lez"].startswith("M"))
            self.assertTrue(kaart["zones"]["gent-lez"], "doel in de LEZ → route kruist de LEZ")
            for coord in [kaart["svg"]["start"], kaart["svg"]["doel"], *kaart["svg"]["innames"]]:
                self.assertTrue(0 <= coord[0] <= 720 and 0 <= coord[1] <= 520, coord)
            labels = {r["label"] for r in kaart["routes"]}
            self.assertIn("primaire", labels)

    def test_routekeuze_en_afstand_tot_route(self):
        from build_simulation import _afstand_tot_route, kies_gewenste_route

        route = {"punten": [[3.72, 51.05], [3.73, 51.05]]}
        self.assertAlmostEqual(_afstand_tot_route([3.725, 51.05], route["punten"]), 0.0, delta=5)
        self.assertAlmostEqual(_afstand_tot_route([3.725, 51.06], route["punten"]), 1105.4, delta=10)  # 0,01° breedte ≈ 1,1 km

        inname = {"id": "GP-1", "straat": "Teststraat", "type": "grondwerk",
                  "van": "2026-11-02", "tot": "2026-11-06", "coord": [3.725, 51.05]}
        routes = {"primaire": route,
                  "alternatief": {"punten": [[3.72, 51.06], [3.73, 51.06]]}}
        gewenst, tellingen = kies_gewenste_route(routes, [inname])
        self.assertEqual(gewenst, "alternatief")
        self.assertEqual(len(tellingen["primaire"]), 1)
        self.assertEqual(tellingen["alternatief"], [])
        gewenst_schoon, _ = kies_gewenste_route(routes, [])
        self.assertEqual(gewenst_schoon, "primaire")  # gelijkspel → snelste route

    def test_bronversies_en_serviceTitels_aanwezig(self):
        self.assertIn("gent-lez", self.gent["bronversies"])
        self.assertIn("ontheffing-lez", self.gent["serviceTitels"])
        self.assertEqual(self.gent["lifeEventCode"], "GT-MOB-01")


if __name__ == '__main__':
    unittest.main()
