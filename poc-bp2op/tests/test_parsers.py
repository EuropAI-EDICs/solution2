"""Offline tests: parsers (MC-4), matcher (MC-5), analyser (MC-8), critic gates (MC-6)."""

import sys
import unittest
from pathlib import Path

POC = Path(__file__).resolve().parent.parent
if str(POC) not in sys.path:
    sys.path.insert(0, str(POC))

from pipeline import analyser, contracts, knowledgebank, parsers  # noqa: E402

CVDR_FIXTURE = """
<html><body>
<div data-element="tekst:Hoofdstuk"><h2 class="docHoofdstuk"><a id="chp_1"></a><span>Hoofdstuk 1 ALGEMENE BEPALINGEN</span></h2>
 <div><h3 class="docArtikel"><a id="chp_1__art_1.1"></a><span>Artikel 1.1 Oogmerk</span></h3>
  <p><a id="chp_1__art_1.1__para_1"></a>Deze regels gelden voor het grondgebied van de gemeente.</p>
 </div>
 <div><h3 class="docArtikel"><a id="chp_1__art_1.2"></a><span>Artikel 1.2 Waar deze regels gelden</span></h3>
  <ul><li class="list-custom__item"><a id="chp_1__art_1.2__para_1"></a><span class="list-custom__itemtype">1.</span><p>De regels gelden in Eindhoven.</p></li>
      <li class="list-custom__item"><a id="chp_1__art_1.2__para_2"></a><span class="list-custom__itemtype">2.</span><p>Zij gelden ook voor het water.</p></li></ul>
 </div>
</div>
<div data-element="tekst:Hoofdstuk"><h2 class="docHoofdstuk"><a id="chp_22"></a><span>Hoofdstuk 22 ACTIVITEITEN (BRUIDSSCHAT VAN HET RIJK)</span></h2>
 <div data-element="tekst:Paragraaf"><h4 class="docParagraaf"><a id="chp_22__subchp_22.2__subsec_22.2.1"></a><span>Paragraaf 22.2.1 Algemene bepalingen</span></h4>
 <div><h5 class="docArtikel"><a id="chp_22__subchp_22.2__subsec_22.2.1__art_22.6"></a><span>Artikel 22.6 Bouwen [Vervallen]</span></h5>
  <p>Het is verboden zonder omgevingsvergunning te bouwen.</p></div>
 <div><h5 class="docArtikel"><a id="chp_22__subchp_22.2__subsec_22.2.1__art_22.29"></a><span>Artikel 22.29 Binnenplanse vergunningplicht</span></h5>
  <p>Het is verboden zonder omgevingsvergunning bouwwerken op te richten.</p></div>
 </div>
</div>
</body></html>
"""

BESLUIT_FIXTURE = """
<html><body><div>
<p>Artikel 1.2 komt in de plaats van artikel 22.46 van de Bruidsschat.</p>
<p>Artikel 3.7 is een voortzetting van artikel 1.2 van het voormalige Activiteitenbesluit milieubeheer.</p>
<p>Het begrip gebruiksdoel komt in de plaats van het begrip bestemming.</p>
</div></body></html>
"""


class TestParsers(unittest.TestCase):
    def setUp(self):
        self.index = parsers.parse_doelregeling(
            CVDR_FIXTURE, cvdr="test", cvdr_id="CVDR000001", versie=1,
            exclude_hoofdstukken=set(), today="2026-08-30")

    def test_artikelen_gevonden(self):
        arts = [d["locator"]["artikel"] for d in self.index]
        self.assertIn("1.1", arts)
        self.assertIn("22.29", arts)
        self.assertEqual(len(arts), 4)

    def test_lid_telling_en_pad(self):
        by = {d["locator"]["artikel"]: d for d in self.index}
        self.assertEqual(by["1.2"]["lidaantal"], 2)
        self.assertEqual(by["1.1"]["lidaantal"], 0)
        self.assertIn("Hoofdstuk 1", by["1.1"]["locator"]["pad"])
        self.assertIn("Paragraaf 22.2.1", by["22.6"]["locator"]["pad"])

    def test_filter_en_bronregels(self):
        doel = parsers.filter_doel_index(self.index, {1})
        bron = parsers.bronregels_uit_doelindex(
            self.index, {22}, "B01", "testinstrument", "https://example.org", "2026-08-30")
        self.assertEqual([d["id"] for d in doel], ["DR-001", "DR-002"])
        self.assertEqual(len(bron), 2)
        vervallen = [b for b in bron if b["statusInBron"] == "vervallen_in_bron"]
        self.assertEqual(len(vervallen), 1)
        self.assertIn("22.6", vervallen[0]["locator"]["label"])
        contracts.validate_many("bron-regel", bron)
        contracts.validate_many("doel-regel", doel)

    def test_kennisbank_pairs(self):
        doel = parsers.filter_doel_index(self.index, {1})
        pairs = parsers.parse_kennisbank_pairs(
            BESLUIT_FIXTURE, "B02", "https://example.org/b", "2026-08-30", doel)
        vervangt = [p for p in pairs if p["relatie"] == "vervangt"]
        voortzetting = [p for p in pairs if p["relatie"] == "voortzetting"]
        self.assertEqual(len(vervangt), 1)
        self.assertIn("22.46", vervangt[0]["bronLabel"])
        self.assertEqual(vervangt[0]["doelLocator"], "artikel 1.2")
        self.assertEqual(vervangt[0]["doelRegelId"], "DR-002")
        self.assertTrue(voortzetting)
        contracts.validate_many("kennisbank-pair", pairs)


class TestMatcher(unittest.TestCase):
    def setUp(self):
        self.doel = [
            {"id": "DR-001", "cvdr": "CVDR000001/1",
             "locator": {"hoofdstukNr": 3, "hoofdstukTitel": "GEBRUIK", "afdeling": None,
                         "paragraaf": None, "artikel": "3.1", "titel": "Wonen toegestaan",
                         "pad": "Hoofdstuk 3 GEBRUIK"},
             "tekst": "Het gebruik van gronden en bouwwerken voor wonen is toegestaan binnen het woongebied.",
             "url": "https://example.org#x", "lidaantal": 1, "gebruiksdoel": None,
             "extractedBy": "t#1", "extractedAt": "2026-08-30", "tekstLanguage": "nl"},
            {"id": "DR-002", "cvdr": "CVDR000001/1",
             "locator": {"hoofdstukNr": 3, "hoofdstukTitel": "GEBRUIK", "afdeling": None,
                         "paragraaf": None, "artikel": "3.2", "titel": "Bedrijf toegestaan",
                         "pad": "Hoofdstuk 3 GEBRUIK"},
             "tekst": "Het gebruik voor een bedrijf of bedrijfsactiviteit is onder voorwaarden toegestaan.",
             "url": "https://example.org#y", "lidaantal": 1, "gebruiksdoel": None,
             "extractedBy": "t#1", "extractedAt": "2026-08-30", "tekstLanguage": "nl"},
        ]
        self.index = knowledgebank.TfidfIndex(
            {d["id"]: f"artikel {d['locator']['artikel']} {d['locator']['titel']} {d['tekst']}" for d in self.doel})
        self.bron = {
            "id": "BR-001", "docId": "B01", "instrument": "test", "tekstLanguage": "nl",
            "locator": {"hoofdstuk": None, "artikel": "22.31", "label": "artikel 22.31 Woonactiviteit"},
            "tekst": "Binnen het woongebied is het gebruik van gronden en bouwwerken voor wonen in overeenstemming met de bestemming.",
            "url": "https://example.org", "statusInBron": "geldend", "thema": "gebruik:wonen",
            "stackingRef": None, "extractedBy": "t#1", "extractedAt": "2026-08-30",
        }

    def test_tekstgelijkenis_geeft_woonen_boven_bedrijf(self):
        sugg = knowledgebank.suggereer(self.bron, self.doel, self.index, knowledgebank.Kennisbank([]))
        self.assertTrue(sugg)
        self.assertEqual(sugg[0]["doelRegelId"], "DR-001")
        self.assertGreater(sugg[0]["score"], sugg[-1]["score"])

    def test_kennisbank_boost_domeert(self):
        pairs = [{"id": "KB-001", "bronLabel": "artikel 22.31 van de Bruidsschat",
                  "doelLocator": "artikel 3.2", "doelRegelId": "DR-002", "relatie": "vervangt",
                  "quote": "Artikel 3.2 komt in de plaats van artikel 22.31 van de Bruidsschat.",
                  "bronDocId": "B02", "url": "https://x", "origin": "officiele_publicatie",
                  "methodTrace": ["MC-5"], "extractedBy": "t#1", "extractedAt": "2026-08-30"}]
        sugg = knowledgebank.suggereer(self.bron, self.doel, self.index, knowledgebank.Kennisbank(pairs))
        self.assertEqual(sugg[0]["doelRegelId"], "DR-002")
        self.assertEqual(sugg[0]["kennisbankHitId"], "KB-001")
        self.assertGreaterEqual(sugg[0]["score"], knowledgebank.BAND_STERK)

    def test_normalize_negeert_stopwoorden(self):
        toks = knowledgebank.normalize("De regel geldt in het kader van de Omgevingswet")
        self.assertNotIn("het", toks)
        self.assertIn("omgevingswet", toks)

    def test_jaccard_onafhankelijk(self):
        j = knowledgebank.JaccardMatcher.score(
            "gebruik van gronden voor wonen", "wonen van gronden toegestaan gebruik")
        self.assertGreater(j, 0.3)


class TestAnalyser(unittest.TestCase):
    def test_coverage_bands(self):
        rows = [
            {"bronRegelId": "BR-001", "status": "voorgesteld",
             "suggesties": [{"doelRegelId": "DR-001", "score": 0.95, "band": "sterk",
                             "kennisbankHitId": None, "scoreDetail": "tfidf-cosinus=0.95"}]},
            {"bronRegelId": "BR-002", "status": "geen_match", "suggesties": []},
        ]
        bron = [
            {"id": "BR-001", "docId": "B01", "thema": "gebruik:wonen"},
            {"id": "BR-002", "docId": "B01", "thema": "milieu:geluid"},
        ]
        cov = analyser.coverage(bron, rows, {"B01": "Testdocument"}, "2026-08-30")
        cov["portfolio"] = {"bronhouder": "testgemeente", "plannenTotaal": 0, "vastgesteld": 0,
                            "tamOmgevingsplannen": 0, "laatstGeverifieerd": "2026-08-30",
                            "bron": "https://example.org"}
        contracts.validate("coverage-report", cov)
        d = cov["perBronDocument"][0]
        self.assertEqual(d["nRegels"], 2)
        self.assertEqual(d["sterk"], 1)
        self.assertEqual(d["geenMatch"], 1)
        self.assertEqual(d["matchRatio"], 0.5)
        self.assertEqual(d["gereedheid"], "deels_gereed")
        self.assertEqual(cov["needsNewRules"][0]["thema"], "milieu:geluid")


class TestOmzettabelContract(unittest.TestCase):
    def test_rij_contract_met_audit_trail(self):
        row = {"id": "OT-001", "bronRegelId": "BR-001", "status": "voorgesteld", "toelichting": "",
               "needsHumanReden": None,
               "suggesties": [{"doelRegelId": "DR-001", "score": 0.93, "band": "sterk",
                               "kennisbankHitId": "KB-001", "scoreDetail": "tfidf + kennisbank"}],
               "reviewTrail": [{"ts": "2026-08-30T00:00:00Z", "actor": "pipeline", "actie": "rij gegenereerd"}],
               "werkingsgebiedRef": None, "methodTrace": ["MC-3", "MC-5"]}
        contracts.validate("omzettabel-row", row)
        with self.assertRaises(contracts.ContractError):
            row["status"] = "gekoppeld_door_ai"  # MC-6: er bestaat geen autonome koppelstatus
            contracts.validate("omzettabel-row", row)


if __name__ == "__main__":
    unittest.main()
