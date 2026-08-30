"""Offline tests for the un-parser stages: critic (V0-V4 gates), explainer
(omzettabel.md + PROV), report (single-file HTML) and a full end-to-end run
against the archived Eindhoven corpus (no network — corpus-first)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

POC = Path(__file__).resolve().parent.parent
if str(POC) not in sys.path:
    sys.path.insert(0, str(POC))

from pipeline import contracts, critic, explainer, knowledgebank, report  # noqa: E402

T = "2026-08-30T00:00:00Z"
D = "2026-08-30"

# --------------------------------------------------------------------------- #
# minimal contract-valid fixtures shared by the critic/explainer/report tests
# --------------------------------------------------------------------------- #


def bron(i, tekst, artikel="22.1", status="geldend", thema="gebruik:wonen", doc="B01"):
    return {"id": f"BR-{i:03d}", "docId": doc, "instrument": "Testbestemmingsplan",
            "locator": {"hoofdstuk": "Hoofdstuk 22", "artikel": artikel,
                        "label": f"artikel {artikel} Woonactiviteit"},
            "tekst": tekst, "tekstLanguage": "nl", "url": "https://example.org/bron",
            "statusInBron": status, "thema": thema, "stackingRef": None,
            "extractedBy": "test#1.0", "extractedAt": D}


def doel(i, tekst, artikel="3.1", titel="Wonen"):
    return {"id": f"DR-{i:03d}", "cvdr": "CVDR000001/1",
            "locator": {"hoofdstukNr": 3, "hoofdstukTitel": "GEBRUIK", "afdeling": None,
                        "paragraaf": None, "artikel": artikel, "titel": titel,
                        "pad": "Hoofdstuk 3 GEBRUIK"},
            "tekst": tekst, "tekstLanguage": "nl",
            "url": "https://lokaleregelgeving.overheid.nl/CVDR000001", "lidaantal": 1,
            "gebruiksdoel": None, "extractedBy": "test#1.0", "extractedAt": D}


def kb(i, bron_label, doel_locator, doel_id, quote, relatie="vervangt", origin="officiele_publicatie"):
    return {"id": f"KB-{i:03d}", "bronLabel": bron_label, "doelLocator": doel_locator,
            "doelRegelId": doel_id, "relatie": relatie, "quote": quote, "bronDocId": "B02",
            "url": "https://example.org/besluit", "origin": origin,
            "methodTrace": ["MC-5"], "extractedBy": "test#1.0", "extractedAt": D}


def ot(i, bron_id, suggesties, status="voorgesteld", reden=None):
    return {"id": f"OT-{i:03d}", "bronRegelId": bron_id, "suggesties": suggesties,
            "status": status, "needsHumanReden": reden, "toelichting": "",
            "reviewTrail": [{"ts": T, "actor": "pipeline", "actie": "rij gegenereerd"}],
            "werkingsgebiedRef": None, "methodTrace": ["MC-3", "MC-5", "MC-6"]}


def sugg(doel_id, score, band, kb_id=None):
    return {"doelRegelId": doel_id, "score": score, "band": band,
            "kennisbankHitId": kb_id, "scoreDetail": "tfidf-cosinus fixture"}


def request():
    return {
        "id": "CR-test", "municipality": {"naam": "Testgemeente", "code": "gm0000", "deadline": "2032-01-01"},
        "beleid": "neutraal",
        "doelregeling": {"naam": "Testomgevingsplan", "cvdrId": "CVDR000001", "versie": 1,
                         "geldendVan": D, "url": "https://lokaleregelgeving.overheid.nl/CVDR000001",
                         "file": "corpus/test.html"},
        "bronset": [{"docId": "B01", "naam": "Testbestemmingsplan", "type": "bestemmingsplan",
                     "url": "https://example.org/bron", "file": "corpus/bron.html"},
                    {"docId": "B02", "naam": "Testwijzigingsbesluit", "type": "wijzigingsbesluit",
                     "url": "https://example.org/besluit", "file": "corpus/besluit.html"}],
        "kennisbankSeeds": ["B02"],
        "pilotCriteria": {"laagdynamisch": True, "geenOpenBeleidswijziging": True,
                          "vergelijkbareGebieden": True, "deelgebiedToegestaan": True},
        "methodCardsRef": "corpus/METHOD-CARDS.md",
    }


def coverage(bron_regels, omzettabel):
    from pipeline import analyser
    cov = analyser.coverage(bron_regels, omzettabel, {"B01": "Testbestemmingsplan"}, D)
    cov["portfolio"] = {"bronhouder": "Testgemeente", "laatstGeverifieerd": D,
                        "bron": "https://example.org", "plannenTotaal": 1, "vastgesteld": 1,
                        "tamOmgevingsplannen": 0}
    return cov


class CriticFixtureMixin:
    """A tiny grounded world: one bron regel, one doel regel, one kennisbank pair,
    one omzettabel row — all texts verbatim present in the fixture source files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        add = Path(self.tmp.name)
        self.bron_tekst = "Binnen het woongebied is het gebruik van gronden en bouwwerken voor wonen toegestaan."
        self.doel_tekst = "Het gebruik van gronden en bouwwerken voor wonen is toegestaan binnen het woongebied."
        self.kb_quote = "Artikel 3.1 komt in de plaats van artikel 22.1 van het bestemmingsplan."
        (add / "cvdr.html").write_text(
            f"<html><body><p>{self.doel_tekst}</p><p>Hoofdstuk 22 {self.bron_tekst}</p></body></html>",
            encoding="utf-8")
        (add / "besluit.html").write_text(f"<html><body><p>{self.kb_quote}</p></body></html>", encoding="utf-8")
        self.bron_regels = [bron(1, self.bron_tekst)]
        self.doel_regels = [doel(1, self.doel_tekst)]
        self.kb_pairs = [kb(1, "artikel 22.1 van het bestemmingsplan", "artikel 3.1", "DR-001", self.kb_quote)]
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-001", 0.95, "sterk", "KB-001")])]
        self.sources = {"doelregeling": add / "cvdr.html", "B01": add / "cvdr.html",
                        "B02": add / "besluit.html"}

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, **overrides):
        args = dict(request=self.request or request(), bron_regels=self.bron_regels,
                    doel_regels=self.doel_regels, kennisbank_pairs=self.kb_pairs,
                    omzettabel=self.omzettabel, coverage_report=self.coverage,
                    sources=self.sources, generated_at=T)
        args.update(overrides)
        return critic.validate_pipeline(**args)


class TestCriticHappyPath(CriticFixtureMixin, unittest.TestCase):
    request = None

    @classmethod
    def setUpClass(cls):
        cls.request = None  # placeholder; real request built per-test

    def setUp(self):
        super().setUp()
        self.coverage = coverage(self.bron_regels, self.omzettabel)
        self.request = request()

    def test_happy_path_pass(self):
        rep, detail = self.validate()
        contracts.validate("validation-report", rep)
        self.assertEqual(rep["verdict"], "pass")
        self.assertEqual(rep["levels"]["V4_human"], "pending")  # MC-6: altijd pending
        self.assertTrue(all(c["passed"] for c in rep["checks"]))
        self.assertIn("v3Agreement", detail)

    def test_v4_always_pending(self):
        rep, _ = self.validate()
        self.assertEqual(rep["levels"]["V4_human"], "pending")
        v4 = [c for c in rep["checks"] if c["level"] == "V4"]
        self.assertTrue(v4 and v4[0]["passed"])  # pending != failed


class TestCriticV1(CriticFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.request = request()
        self.coverage = coverage(self.bron_regels, self.omzettabel)

    def test_missende_rij(self):
        self.omzettabel = []  # bron regel BR-001 has no row
        self.coverage = coverage(self.bron_regels, self.omzettabel)
        rep, _ = self.validate()
        self.assertEqual(rep["levels"]["V1_completeness"], "fail")
        self.assertEqual(rep["verdict"], "fail")

    def test_dubbele_rij(self):
        self.omzettabel = self.omzettabel + [ot(2, "BR-001", [])]
        self.coverage = coverage(self.bron_regels, self.omzettabel)
        rep, _ = self.validate()
        self.assertEqual(rep["levels"]["V1_completeness"], "fail")

    def test_spookreferentie(self):
        self.omzettabel = [ot(1, "BR-999", [])]  # row pointing at a non-existing bron regel
        self.coverage = coverage(self.bron_regels, self.omzettabel)
        rep, _ = self.validate()
        self.assertEqual(rep["levels"]["V1_completeness"], "fail")

    def test_onoplosbare_doelreferentie(self):
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-999", 0.9, "sterk")])]
        self.coverage = coverage(self.bron_regels, self.omzettabel)
        rep, _ = self.validate()
        self.assertEqual(rep["levels"]["V1_completeness"], "fail")

    def test_kennisbank_naar_onbekende_doelregel(self):
        self.kb_pairs = [kb(1, "artikel 22.1", "artikel 3.1", "DR-999", self.kb_quote)]
        rep, _ = self.validate()
        self.assertEqual(rep["levels"]["V1_completeness"], "fail")


class TestCriticV2(CriticFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.request = request()
        self.coverage = coverage(self.bron_regels, self.omzettabel)

    def test_brontekst_niet_verbatim(self):
        self.bron_regels = [bron(1, "Deze tekst staat nergens in de bronpublicatie opgenomen.")]
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-001", 0.9, "sterk")])]
        rep, _ = self.validate(bron_regels=self.bron_regels, omzettabel=self.omzettabel)
        self.assertEqual(rep["levels"]["V2_grounding"], "fail")
        chk = [c for c in rep["checks"] if c["id"] == "chk-v2-bronteksten-verbatim"]
        self.assertIn("BR-001", chk[0]["evidence"])

    def test_doeltekst_niet_verbatim(self):
        self.doel_regels = [doel(1, "Deze doeltekst staat niet in de CVDR-consolidatie.")]
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-001", 0.9, "sterk")])]
        rep, _ = self.validate(doel_regels=self.doel_regels, omzettabel=self.omzettabel)
        self.assertEqual(rep["levels"]["V2_grounding"], "fail")

    def test_kennisbank_citaat_niet_in_besluit(self):
        self.kb_pairs = [kb(1, "artikel 22.1", "artikel 3.1", "DR-001",
                            "Dit citaat komt nergens in het wijzigingsbesluit voor.")]
        rep, _ = self.validate(kennisbank_pairs=self.kb_pairs)
        self.assertEqual(rep["levels"]["V2_grounding"], "fail")

    def test_verkeerde_permalink(self):
        self.doel_regels = [dict(self.doel_regels[0], url="https://example.org/verkeerd")]
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-001", 0.9, "sterk")])]
        rep, _ = self.validate(doel_regels=self.doel_regels, omzettabel=self.omzettabel)
        self.assertEqual(rep["levels"]["V2_grounding"], "fail")


class TestCriticV3(CriticFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.request = request()

    def test_kennisbank_gedreven_rij_buiten_vergelijking(self):
        # top-1 driven by a published kennisbank relation: V3 must not penalize it
        self.coverage = coverage(self.bron_regels, self.omzettabel)
        rep, detail = self.validate()
        self.assertEqual(rep["levels"]["V3_semantic"], "pass")
        self.assertEqual(detail["v3Compared"], 0)

    def test_tekstgedreven_overeenkomst_gemeten(self):
        # no kennisbank hit: top-1 comes from TF-IDF; Jaccard re-scores independently
        self.kb_pairs = []
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-001", 0.95, "sterk")])]
        self.coverage = coverage(self.bron_regels, self.omzettabel)
        rep, detail = self.validate(kennisbank_pairs=self.kb_pairs)
        self.assertEqual(rep["levels"]["V3_semantic"], "pass")
        self.assertEqual(detail["v3Compared"], 1)
        self.assertEqual(detail["v3Agreement"], 1.0)  # both matchers agree on DR-001


class TestCriticV0(CriticFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.request = request()
        self.coverage = coverage(self.bron_regels, self.omzettabel)

    def test_schema_overtreding(self):
        row = self.omzettabel[0]
        row["status"] = "gekoppeld_door_ai"  # MC-6: bestaat niet
        rep, _ = self.validate(omzettabel=[row])
        self.assertEqual(rep["levels"]["V0_syntactic"], "fail")
        self.assertEqual(rep["verdict"], "fail")


# --------------------------------------------------------------------------- #
# explainer + report
# --------------------------------------------------------------------------- #

class TestExplainer(unittest.TestCase):
    def setUp(self):
        self.bron_regels = [bron(1, "Wonen is toegestaan binnen het woongebied.")]
        self.doel_regels = [doel(1, "Gebruik voor wonen is toegestaan in het woongebied.")]
        self.kb_pairs = [kb(1, "artikel 22.1", "artikel 3.1", "DR-001",
                            "Artikel 3.1 komt in de plaats van artikel 22.1 van het plan.")]
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-001", 0.93, "sterk", "KB-001")])]

    def test_omzettabel_md_inhoud(self):
        md = explainer.omzettabel_md(self.omzettabel, self.bron_regels, self.doel_regels)
        for needle in ["OT-001", "artikel 22.1 Woonactiviteit", "Wonen is toegestaan",
                       "score 0.93", "[sterk]", "kennisbank KB-001",
                       "**status**: voorgesteld", "doelregel"]:
            self.assertIn(needle, md)

    def test_write_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            out = explainer.write_outputs(Path(td), self.omzettabel, self.bron_regels,
                                          self.doel_regels, self.kb_pairs)
            self.assertEqual(set(out), {"omzettabel", "bronregels", "doelregels", "kennisbank"})
            for name in ["omzettabel.json", "bronregels.json", "doelregels.json",
                         "kennisbank.json", "omzettabel.md"]:
                self.assertTrue((Path(td) / name).exists(), name)
            contracts.validate_many("omzettabel-row",
                                    json.loads((Path(td) / "omzettabel.json").read_text(encoding="utf-8")))

    def test_prov_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json"
            p.write_text("{}", encoding="utf-8")
            prov = explainer.prov_bundle(
                [{"id": "orchestrator", "name": "test"}], {"x": p},
                [{"naam": "matchen", "agent": "matcher", "methodTrace": ["MC-5"], "ts": T}],
                [{"generated": "omzettabel.json", "derivedFrom": ["bronregels.json"]}],
                ["MC-1", "MC-6", "MC-12"])
            self.assertEqual(prov["entities"]["x"]["sha256"], explainer.sha256_file(p))
            titels = [c["titel"] for c in prov["methodTrace"]["cards"]]
            self.assertIn("Transitiestrategie met doelregeling", titels)
            self.assertEqual(len(prov["methodTrace"]["cards"]), 3)


class TestReport(unittest.TestCase):
    def setUp(self):
        self.bron_regels = [bron(1, "Wonen is toegestaan binnen het woongebied."),
                            bron(2, "Detailhandel is uitsluitend toegestaan in het centrumgebied.",
                                 artikel="22.2", thema="gebruik:detailhandel")]
        self.doel_regels = [doel(1, "Gebruik voor wonen is toegestaan in het woongebied.")]
        self.kb_pairs = [kb(1, "artikel 22.1", "artikel 3.1", "DR-001",
                            "Artikel 3.1 komt in de plaats van artikel 22.1 van het plan.")]
        self.omzettabel = [ot(1, "BR-001", [sugg("DR-001", 0.93, "sterk", "KB-001")]),
                           ot(2, "BR-002", [], status="needs_human",
                              reden="Alleen zwakke overeenkomsten: geen koppeling zonder jurist.")]
        self.validation = {"artifact": "pipeline-run", "generatedAt": T,
                           "levels": {"V0_syntactic": "pass", "V1_completeness": "pass",
                                      "V2_grounding": "pass", "V3_semantic": "pass",
                                      "V4_human": "pending"},
                           "checks": [{"id": "chk-v4-jurist-checkpoint", "level": "V4",
                                       "passed": True, "evidence": "1 rij aangewezen"}],
                           "verdict": "pass"}

    def test_render_los_uit_bestand(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.html"
            report.render(out, title="bp2op test", subtitle="test ondertitel", generated=T,
                          run_id="testrun", verdict="pass",
                          headline_cards=[{"label": "bronregels", "value": "1", "note": "n=1"}],
                          coverage_rows=[{"docId": "B01", "naam": "Testbestemmingsplan", "nRegels": 2,
                                          "sterk": 1, "mogelijk": 0, "zwak": 0, "geenMatch": 1,
                                          "matchRatio": 0.5, "gereedheid": "deels_gereed"}],
                          needs_new=[{"thema": "gebruik:overig", "nRegels": 1,
                                      "voorbeeldBronRegelIds": ["BR-002"]}],
                          portfolio={"bronhouder": "Test", "plannenTotaal": 1, "vastgesteld": 1,
                                     "tamOmgevingsplannen": 0, "laatstGeverifieerd": D},
                          kb_pairs=self.kb_pairs, omzettabel=self.omzettabel,
                          bron_regels=self.bron_regels, doel_regels=self.doel_regels,
                          validation=self.validation, footer="test footer")
            html = out.read_text(encoding="utf-8")
        # method traceability table: all twelve cards
        for mc in ["MC-1", "MC-2", "MC-3", "MC-4", "MC-5", "MC-6", "MC-7", "MC-8",
                   "MC-9", "MC-10", "MC-11", "MC-12"]:
            self.assertIn(mc, html)
        # both sides visible (MC-7): bron label + doel artikel + needs_human reden
        self.assertIn("artikel 22.1 Woonactiviteit", html)
        self.assertIn("3.1 Wonen", html)  # doel artikel + titel
        self.assertIn("geen koppeling zonder jurist", html)
        self.assertIn("sterk", html)
        self.assertIn("needs_human", html)
        # single-file: geen externe script/style imports (file:// werkt)
        self.assertNotIn("<script src=", html)
        self.assertNotIn('<link rel="stylesheet"', html)


# --------------------------------------------------------------------------- #
# end-to-end over het gearchiveerde Eindhoven-corpus (offline, corpus-first)
# --------------------------------------------------------------------------- #

class TestEndToEndEindhoven(unittest.TestCase):
    """run.py draait volledig offline op de gearchiveerde corpusbestanden; het resultaat
    moet slagen (verdict pass, V4 pending) en aan zijn eigen contracten voldoen."""

    @classmethod
    def setUpClass(cls):
        import run as run_mod
        cls.run_mod = run_mod
        cls.tmp = tempfile.TemporaryDirectory()
        rc = run_mod.run("eindhoven", Path(cls.tmp.name))
        cls.rc = rc
        run_dirs = sorted(Path(cls.tmp.name).glob("*-eindhoven"))
        cls.run_dir = run_dirs[-1]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exit_code_en_artifacts(self):
        self.assertEqual(self.rc, 0)
        expected = {"request.json", "bronregels.json", "doelregels.json", "kennisbank.json",
                    "omzettabel.json", "omzettabel.md", "plan-inventory.json", "coverage.json",
                    "validation.json", "prov.json", "report.html", "run_summary.json"}
        self.assertEqual({p.name for p in self.run_dir.iterdir()}, expected)

    def test_summary_getallen(self):
        s = json.loads((self.run_dir / "run_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(s["verdict"], "pass")
        c = s["counts"]
        self.assertGreater(c["bronRegels"], 250)          # hoofdstuk 22/23 populatie
        self.assertGreater(c["doelRegels"], 500)          # hoofdstuk 1-21 index
        self.assertGreaterEqual(c["kennisbank"], 270)     # 275 renvooi-relaties + taxonomie
        self.assertEqual(c["omzettabelRijen"], c["bronRegels"])
        self.assertEqual(c["voorgesteld"] + c["nieuweRegel"] + c["needsHuman"], c["omzettabelRijen"])
        self.assertGreater(c["needsHuman"], 0)            # MC-6: er is altijd werk voor de jurist
        self.assertGreater(s["portfolio"]["plannenTotaal"], 300)  # Planviewer-inventaris

    def test_artifacts_contract_en_invarianten(self):
        bron = json.loads((self.run_dir / "bronregels.json").read_text(encoding="utf-8"))
        doel = json.loads((self.run_dir / "doelregels.json").read_text(encoding="utf-8"))
        rijen = json.loads((self.run_dir / "omzettabel.json").read_text(encoding="utf-8"))
        kbp = json.loads((self.run_dir / "kennisbank.json").read_text(encoding="utf-8"))
        cov = json.loads((self.run_dir / "coverage.json").read_text(encoding="utf-8"))
        val = json.loads((self.run_dir / "validation.json").read_text(encoding="utf-8"))
        contracts.validate_many("bron-regel", bron)
        contracts.validate_many("doel-regel", doel)
        contracts.validate_many("omzettabel-row", rijen)
        contracts.validate_many("kennisbank-pair", kbp)
        contracts.validate("coverage-report", cov)
        contracts.validate("validation-report", val)
        # V1 invarianten onafhankelijk hercontroleerd
        bron_ids = [b["id"] for b in bron]
        self.assertEqual(sorted(r["bronRegelId"] for r in rijen), sorted(bron_ids))
        doel_ids = {d["id"] for d in doel}
        for r in rijen:
            for s in r["suggesties"]:
                self.assertIn(s["doelRegelId"], doel_ids)
            self.assertIn(r["status"], {"voorgesteld", "nieuwe_regel_voorgesteld", "needs_human"})
        # MC-6: nooit automatisch gekoppeld
        self.assertFalse([r for r in rijen if "gekoppeld" in r["status"]])
        # MC-5: kennisbank uitsluitend officiele herkomst of taxonomie
        self.assertTrue(all(p["origin"] in {"officiele_publicatie", "doelregeling_taxonomie"} for p in kbp))

    def test_rapport_zichtbaar_beide_kanten(self):
        html = (self.run_dir / "report.html").read_text(encoding="utf-8")
        self.assertIn("Omgevingsplan gemeente Eindhoven", html)
        self.assertIn("CVDR696400", html)
        for mc in ["MC-1", "MC-6", "MC-8", "MC-10"]:
            self.assertIn(mc, html)


if __name__ == "__main__":
    unittest.main()
