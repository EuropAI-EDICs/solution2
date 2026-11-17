# nldt/tests/test_cim_vth_flo.py
"""Vastgepinde checks op het CIm VTH FLo 0.9.1-extract.

Bewaakt nldt/references/cim-vth-flo/0.9.1/ tegen onopgemerkte wijziging: de
objecttypen-lijst, kernsemantiek, generalisaties, referentielijsten en de
sha256 van bron-PDF en extract. Bij de 1.0-vaststelling van het model hoort
een nieuwe versiemap + verlengde versie van deze tests, geen aanpassing van
de 0.9.1-pins."""
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
REF = ROOT / "nldt" / "references" / "cim-vth-flo" / "0.9.1"
PDF = ROOT / "docs" / "EvT Conceptueel Informatiemodel Fysieke Leefomgeving VTH 0.9.1 07-2025 AVG.pdf"

OBJECTTYPEN = {
    "ACTIVITEIT", "ACTIVITEITINFORMATIE", "ACTIVITEITMELDING", "ACTIVITEITUITVOERING",
    "ADRESSEERBAAR OBJECT", "ALGEMEEN VERBINDEND VOORSCHRIFT", "ANDER GEO-OBJECT",
    "BETROKKENE", "BEVINDING", "CONTROLE", "GEO-OBJECT", "HANDHAVINGSMAATREGEL",
    "HANDHAVINGSVERZOEK", "INCIDENTMELDING", "INFORMATIEOBJECT",
    "KADASTRALE ONROERENDE ZAAK", "KLACHT", "NATUURLIJK PERSOON",
    "NIET-NATUURLIJK PERSOON", "OVERTREDING", "OVERWEGING", "PAND", "SIGNAAL",
    "SPECIFIEK VOORSCHRIFT", "TOESTEMMING", "TOESTEMMINGAANVRAAG",
    "TOPOGRAFISCH OBJECT", "VERZOEK", "VESTIGING", "VOORVAL", "VOORVALSIGNAAL",
    "VTH-OBJECT", "ZAAK",
}

GENERALISATIES = {
    ("ADRESSEERBAAR OBJECT", "GEO-OBJECT"),
    ("ANDER GEO-OBJECT", "GEO-OBJECT"),
    ("INCIDENTMELDING", "VOORVALSIGNAAL"),
    ("KADASTRALE ONROERENDE ZAAK", "GEO-OBJECT"),
    ("KLACHT", "VOORVALSIGNAAL"),
    ("NATUURLIJK PERSOON", "BETROKKENE"),
    ("PAND", "GEO-OBJECT"),
    ("SIGNAAL", "VOORVALSIGNAAL"),
    ("TOPOGRAFISCH OBJECT", "GEO-OBJECT"),
    ("VESTIGING", "BETROKKENE"),
}

VIEWS = {
    "Activiteit-view", "Betrokkene-view", "Locatie-view",
    "Toezicht- en handhaving-view", "Verzoek-view", "Zaak- en document-view",
}


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


class CimVthFloPin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((REF / "model.json").read_text("utf-8"))
        cls.pin = json.loads((REF / "pin.json").read_text("utf-8"))
        cls.by_naam = {o["naam"]: o for o in cls.model["objecttypen"]}

    def test_pin_meta_en_hashes(self):
        meta = self.model["model"]
        self.assertEqual(meta["versie"], "0.9.1")
        self.assertEqual(meta["status"], "concept")
        self.assertEqual(meta["bronhouder"], "Programma Digitaal VTH-stelsel Milieu")
        self.assertEqual(meta["metamodel"], "MIM (Metamodel Informatiemodellering)")
        self.assertIn("Eenheid van Taal", meta["project"])
        self.assertEqual(self.pin["bronSha256"], _sha256(PDF))
        self.assertEqual(self.pin["modelSha256"], _sha256(REF / "model.json"))
        self.assertEqual(meta["bronSha256"], self.pin["bronSha256"])

    def test_objecttypen_volledig(self):
        self.assertEqual(len(self.model["objecttypen"]), 33)
        self.assertEqual({o["naam"] for o in self.model["objecttypen"]}, OBJECTTYPEN)

    def test_objecttypen_hebben_definitie(self):
        for o in self.model["objecttypen"]:
            with self.subTest(objecttype=o["naam"]):
                self.assertTrue(o.get("definitie", "").strip())
                self.assertIsInstance(o.get("indicatieAbstractObject"), bool)

    def test_kernsemantiek(self):
        toestemming = self.by_naam["TOESTEMMING"]
        self.assertIn(
            "Toestemming van een bevoegd gezag",
            toestemming["definitie"],
        )
        rels = {(r["naam"], r["gerelateerdObjecttype"]): r for r in toestemming["relatiesoorten"]}
        self.assertIn(("legitimeert", "ACTIVITEITUITVOERING"), rels)
        self.assertEqual(rels[("legitimeert", "ACTIVITEITUITVOERING")]["kardinaliteit"], "1 .. *")
        self.assertIn(("heeft als onderdeel", "SPECIFIEK VOORSCHRIFT"), rels)

        sv = self.by_naam["SPECIFIEK VOORSCHRIFT"]
        self.assertTrue(sv["definitie"].startswith("Een dwingende eis"), sv["definitie"])
        avgs = self.by_naam["ALGEMEEN VERBINDEND VOORSCHRIFT"]
        self.assertIn("regelgevende bevoegdheid", avgs["definitie"])
        self.assertIn(
            "Het niet naleven van de geldende regels",
            self.by_naam["OVERTREDING"]["definitie"],
        )

    def test_controle_details(self):
        controle = self.by_naam["CONTROLE"]
        self.assertEqual(
            [a["naam"] for a in controle["attribuutsoorten"]],
            ["Controle-identificatie", "Controledatum", "Controletype", "Eindoordeel"],
        )
        controle_type = next(a for a in controle["attribuutsoorten"] if a["naam"] == "Controletype")
        self.assertEqual(controle_type["formaat"], "Controletype")  # referentielijst als formaat
        rels = {(r["naam"], r["gerelateerdObjecttype"]): r for r in controle["relatiesoorten"]}
        self.assertEqual(rels[("van", "ACTIVITEITUITVOERING")]["kardinaliteit"], "1 .. *")
        self.assertIn(("wordt uitgevoerd door", "BETROKKENE"), rels)

    def test_generalisaties(self):
        gevonden = {(g["objecttype"], g["generaliseert"]) for g in self.model["generalisaties"]}
        self.assertEqual(gevonden, GENERALISATIES)

    def test_zonder_h5_detail(self):
        zonder = sorted(o["naam"] for o in self.model["objecttypen"] if o["detailHoofdstuk"] is None)
        self.assertEqual(zonder, ["KLACHT", "SIGNAAL"])
        for naam in zonder:
            self.assertEqual(self.by_naam[naam]["attribuutsoorten"], [])
            self.assertEqual(self.by_naam[naam]["relatiesoorten"], [])

    def test_relatieklasse(self):
        rk = self.model["relatieklasse"]
        self.assertEqual(rk["naam"], "Mutatie specifiek voorschrift")
        soort_mutatie = rk["attribuutsoorten"][0]
        self.assertEqual(soort_mutatie["naam"], "Soort mutatie")
        self.assertIn("van kracht", soort_mutatie["patroon"])

    def test_gegevensgroeptype_adres(self):
        ggp = self.model["gegevensgroeptypen"][0]
        self.assertEqual(ggp["naam"], "Adres")
        self.assertEqual(ggp["bijObjecttype"], "BETROKKENE")
        self.assertEqual(
            [a["naam"] for a in ggp["attribuutsoorten"]],
            ["Adresregel 1", "Adresregel 2", "Adresregel 3", "Landnaam", "Adrestype",
             "BAG-nummeraanduiding-Id"],
        )

    def test_referentielijsten(self):
        lijsten = {rl["naam"]: rl for rl in self.model["referentielijsten"]}
        self.assertEqual(
            set(lijsten),
            {"Controletype", "Controle-onderwerp", "Handhavingsinstrument", "Type VTH-object"},
        )
        for naam, rl in lijsten.items():
            with self.subTest(referentielijst=naam):
                self.assertTrue(rl["definitie"])
                elementen = {e["naam"] for e in rl["elementen"]}
                self.assertIn("Begindatum geldigheid", elementen)
                if naam == "Type VTH-object":
                    # tweedelig type (hoofd-/subtype), ld. de toelichting
                    self.assertIn("Naam hoofdtype", elementen)
                    self.assertIn("Naam subtype", elementen)
                else:
                    self.assertIn("Naam", elementen)
                # waarden worden buiten het model beheerd (ld. de toelichting)
                self.assertIsNone(rl["waarden"])
        self.assertIn("Zwaarte", {e["naam"] for e in lijsten["Handhavingsinstrument"]["elementen"]})

    def test_views(self):
        self.assertEqual({v["naam"] for v in self.model["views"]}, VIEWS)
        for v in self.model["views"]:
            self.assertIsNone(v["kernObjecttypen"])  # alleen in figuren

    def test_attributen_en_relaties_totaal(self):
        n_attr = sum(len(o["attribuutsoorten"]) for o in self.model["objecttypen"])
        n_rel = sum(len(o["relatiesoorten"]) for o in self.model["objecttypen"])
        self.assertEqual(n_attr, 127)
        self.assertEqual(n_rel, 74)


if __name__ == "__main__":
    unittest.main()
