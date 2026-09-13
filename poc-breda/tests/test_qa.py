"""Offline tests: Q&A-naad — parser, runner, grounding-gate, LLM-mocks, e2e."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from breda import qa  # noqa: E402  — tests/util zet sys.path
from tests import fixtures, util  # noqa: E402


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = util.full_scan(fixtures.layers_dict())

    def test_buurtvraag_met_waarde(self):
        q = qa.parse_question("waarom scoort Cel 3-2 laag op ruimtelijke waarde?", self.scan)
        self.assertIsNotNone(q)
        self.assertEqual(q["buurtNaam"], "Cel 3-2")
        self.assertEqual(q["waarde"], "spatial")
        self.assertEqual(q["focus"], "spatial")
        self.assertIsNone(q["ranking"])

    def test_rankingvraag(self):
        q = qa.parse_question("welke buurten scoren het hoogst op democratische waarde?",
                              self.scan)
        self.assertIsNone(q["buurtNaam"])
        self.assertEqual(q["waarde"], "democratic")
        self.assertEqual(q["ranking"], "hoogste")

    def test_laagste_en_top_n(self):
        q = qa.parse_question("top 3 buurten onbenut dakpotentieel", self.scan)
        self.assertEqual(q["ranking"], "hoogste")
        self.assertEqual(q["waarde"], "economic")
        self.assertEqual(q["limit"], 3)

    def test_hitte_synoniem(self):
        q = qa.parse_question("welke buurten hebben de meeste hitte-aandacht?", self.scan)
        self.assertEqual(q["waarde"], "social")

    def test_onthoudt_bij_niets_herkenbaars(self):
        self.assertIsNone(
            qa.parse_question("wat is de hoofdstad van Frankrijk?", self.scan)
        )
        self.assertIsNone(qa.parse_question("hoe laat is het?", self.scan))

    def test_onthoudt_bij_ambigue_buurt(self):
        # twee verschillende buurten genoemd -> geen unieke match -> onthouden
        self.assertIsNone(qa.parse_question("hoe scoort Cel 3-2 vergeleken met Cel 5-5?",
                                            self.scan))

    def test_diacritiek_en_case_ongevoelig(self):
        q = qa.parse_question("HOE SCOORT CEL 0-0 OP ALLE WAARDEN", self.scan)
        self.assertEqual(q["buurtNaam"], "Cel 0-0")

    def test_vraag_woordenschat_kleur(self):
        q = qa.parse_question("vertel meer over Cel 5-5", self.scan)
        self.assertEqual(q["buurtNaam"], "Cel 5-5")


class TestRunnerEnAntwoord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = util.full_scan(fixtures.layers_dict())

    def test_detail_antwoord(self):
        q = qa.parse_question("waarom scoort Cel 3-2 laag op ruimtelijke waarde?", self.scan)
        result = qa.execute_query(q, self.scan)
        self.assertEqual(result["mode"], "detail")
        self.assertEqual(len(result["rows"]), 1)
        tekst = qa.deterministic_answer(result, self.scan)
        self.assertIn("Cel 3-2", tekst)
        self.assertIn("ruimtelijke waarde", tekst)
        # elk cijfer in het antwoord groundt (deterministische narrator moet altijd door de gate)
        self.assertEqual(qa.check_answer_grounding(tekst, result, self.scan), [])

    def test_ranking_antwoord_volgorde(self):
        q = qa.parse_question("top 5 op sociale waarde", self.scan)
        result = qa.execute_query(q, self.scan)
        scores = [b["scores"]["social"]["score"] for b in result["rows"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        tekst = qa.deterministic_answer(result, self.scan)
        self.assertEqual(qa.check_answer_grounding(tekst, result, self.scan), [])

    def test_laagste_ranking(self):
        q = qa.parse_question("welke buurten scoren het laagst op economische waarde?",
                              self.scan)
        result = qa.execute_query(q, self.scan)
        scores = [b["scores"]["economic"]["score"] for b in result["rows"]]
        self.assertEqual(scores, sorted(scores))


class TestGroundingGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = util.full_scan(fixtures.layers_dict())
        q = qa.parse_question("top 5 op sociale waarde", cls.scan)
        cls.result = qa.execute_query(q, cls.scan)

    def test_gefabriceerd_cijfer_afgekeurd(self):
        schendingen = qa.check_answer_grounding(
            "De score is 99.9 en dat is hoog.", self.result, self.scan
        )
        self.assertTrue(any("99.9" in s for s in schendingen))

    def test_gegrond_cijfer_geaccepteerd(self):
        score = self.result["rows"][0]["scores"]["social"]["score"]
        schendingen = qa.check_answer_grounding(
            f"De hoogste score is {score}.", self.result, self.scan
        )
        self.assertEqual(schendingen, [])

    def test_tekengevouwen_magnitude(self):
        # PoC-1-les: "afname van 64.6" moet resolven tegen -64.6
        known = set()
        qa._collect_numbers({"delta": -64.6}, known)
        self.assertIn("64.6", {n.lstrip("-") for n in known})

    def test_volle_float_precisie_grondt(self):
        # gate-bug uit de live-run: :g-verkorting brak verbatim gekopieerde
        # floats — collectie moet de volle repr bevatten
        known = set()
        qa._collect_numbers({"share": 0.05724552641614901}, known)
        self.assertIn("0.05724552641614901", known)

    def test_dict_keys_gronden_hun_cijfers(self):
        known = set()
        qa._collect_numbers({"bomen_per_100_inw": 3.2}, known)
        self.assertIn("100", known)

    def test_nederlands_duizendtal_grondt(self):
        # "4.245 inwoners" is gegronde formulering van 4245 (PoC-1-les 5)
        self.result["rows"][0]["aantalInwoners"] = 4245
        schendingen = qa.check_answer_grounding(
            "De buurt telt 4.245 inwoners.", self.result, self.scan
        )
        self.assertEqual(
            [s for s in schendingen if "4.245" in s], [],
            "duizendtal-vorm moet resolven",
        )
        # maar een duizendtal dat nergens vandaan komt blijft afgekeurd
        overtreding = qa.check_answer_grounding(
            "De buurt telt 9.999 inwoners.", self.result, self.scan
        )
        self.assertTrue(any("9.999" in s for s in overtreding))

    def test_nieuwe_buurt_afgekeurd(self):
        # een buurt die WEL in de scan staat maar NIET in de resultaatrijen
        vraag = "top 5 op sociale waarde"
        q = qa.parse_question(vraag, self.scan)
        result = qa.execute_query(q, self.scan)
        erin = {b["buurtnaam"] for b in result["rows"]}
        erbuiten = next(
            b["buurtnaam"] for b in self.scan["buurten"]
            if b["water"] == "NEE" and b["buurtnaam"] not in erin and " " in b["buurtnaam"]
        )
        schendingen = qa.check_answer_grounding(
            f"Ook {erbuiten} valt op.", result, self.scan
        )
        self.assertTrue(any(erbuiten in s for s in schendingen))


class TestLLMSeam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = util.full_scan(fixtures.layers_dict())

    @staticmethod
    def _asker(scan, reply):
        def llm_call(endpoint, model, system, user, timeout):
            return reply

        return qa.LLMAsker(scan, llm_call=llm_call, endpoint="http://test", model="test-model")

    def test_geldige_proposal(self):
        asker = self._asker(
            self.scan,
            json.dumps({"question": "q", "buurtNaam": "Cel 3-2", "waarde": "spatial",
                        "ranking": None, "limit": 5, "focus": None}),
        )
        query, afwijzing = asker.propose("hoe scoort Cel 3-2 op groen?")
        self.assertIsNone(afwijzing)
        self.assertEqual(query["buurtNaam"], "Cel 3-2")
        # identiteitsstempel door de seam, niet het model
        self.assertEqual(query["proposedBy"], "llm-proposal#test-model")

    def test_gehallucineerde_buurt_naar_ledger(self):
        asker = self._asker(
            self.scan,
            json.dumps({"buurtNaam": "Zuidas", "waarde": "spatial"}),
        )
        query, afwijzing = asker.propose("hoe scoort de Zuidas?")
        self.assertIsNone(query)
        self.assertIn("komt niet in de scan voor", afwijzing["reason"])

    def test_onthouding_wordt_gerespecteerd(self):
        asker = self._asker(
            self.scan,
            json.dumps({"abstain": True, "reason": "vraag past niet op contract"}),
        )
        query, afwijzing = asker.propose("wat is de zin van het leven?")
        self.assertIsNone(query)
        self.assertIn("onthield", afwijzing["reason"])

    def test_kapotte_json_naar_ledger(self):
        asker = self._asker(self.scan, "geen json maar proza")
        query, afwijzing = asker.propose("willekeurige vraag over Cel 1-1")
        self.assertIsNone(query)
        self.assertIn("onparseerbaar", afwijzing["reason"])

    def test_think_blok_wordt_gestript(self):
        asker = self._asker(
            self.scan,
            "<think>gemijmer</think>" + json.dumps({"buurtNaam": "Cel 3-2"}),
        )
        query, _ = asker.propose("Cel 3-2")
        self.assertEqual(query["buurtNaam"], "Cel 3-2")

    def test_endpoint_vereist(self):
        asker = qa.LLMAsker(self.scan, endpoint="")
        with self.assertRaises(qa.QAError):
            asker.propose("vraag")

    def test_vormdrift_wordt_genormaliseerd(self):
        # PoC-1-les §5.2: modellen vullen bijv. een buurtnaam in 'focus' —
        # de seam herleidt dat deterministisch, de schema-gate blijft erachter
        asker = self._asker(
            self.scan,
            json.dumps({"buurtNaam": "Cel 3-2", "waarde": "spatial",
                        "focus": "Cel 3-2", "limit": 99, "extra": "ruis"}),
        )
        query, afwijzing = asker.propose("hoe scoort Cel 3-2 op groen?")
        self.assertIsNone(afwijzing)
        self.assertEqual(query["focus"], "spatial")  # afgeleid: buurt + waarde
        self.assertIsNone(query["limit"])  # 99 buiten bereik -> None
        self.assertNotIn("extra", query)

    def test_narrator_gate_integratie(self):
        q = qa.parse_question("top 5 op sociale waarde", self.scan)
        result = qa.execute_query(q, self.scan)

        def llm_goed(endpoint, model, system, user, timeout):
            score = result["rows"][0]["scores"]["social"]["score"]
            naam = result["rows"][0]["buurtnaam"]
            return f"{naam} voert met een score van {score}."

        narrator = qa.LLMNarrator(llm_call=llm_goed, endpoint="http://test")
        tekst = narrator.narrate(result, "fallback")
        self.assertEqual(qa.check_answer_grounding(tekst, result, self.scan), [])

        def llm_fabriceert(endpoint, model, system, user, timeout):
            # 999.5 kan geen percentiel (0-100) én geen input zijn
            return "De beste buurt heeft score 999.5."

        narrator_fout = qa.LLMNarrator(llm_call=llm_fabriceert, endpoint="http://test")
        tekst_fout = narrator_fout.narrate(result, "fallback")
        self.assertTrue(qa.check_answer_grounding(tekst_fout, result, self.scan))


class TestCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = util.full_scan(fixtures.layers_dict())
        cls.tmp = tempfile.TemporaryDirectory()
        cls.run_dir = Path(cls.tmp.name) / "run"
        cls.run_dir.mkdir()
        (cls.run_dir / "value-scan.json").write_text(
            json.dumps(cls.scan, ensure_ascii=False), encoding="utf-8"
        )
        spec = importlib.util.spec_from_file_location("poc_breda_qa_run",
                                                      Path(util.ROOT) / "qa_run.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["poc_breda_qa_run"] = mod
        spec.loader.exec_module(mod)
        cls.mod = mod

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_deterministische_vraag(self):
        code = self.mod.main([
            "--run", str(self.run_dir),
            "--question", "waarom scoort Cel 3-2 laag op ruimtelijke waarde?",
        ])
        self.assertEqual(code, 0)
        payload = json.loads(
            ((self.run_dir / "qa" / "answer.json")).read_text(encoding="utf-8")
        )
        self.assertEqual(payload["mode"], "detail")
        self.assertEqual(payload["asker"], "auto")

    def test_onmogelijke_vraag_onthoudt(self):
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = self.mod.main([
                "--run", str(self.run_dir),
                "--question", "wat is de hoofdstad van Peru?",
                "--out", str(self.run_dir / "qa2"),
            ])
        self.assertEqual(code, 1)
        self.assertIn("onthouden", buf.getvalue())
        self.assertTrue((self.run_dir / "qa2" / "query-rejected.json").exists())

    def test_demo_golden_set(self):
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = self.mod.main(["--run", str(self.run_dir), "--demo"])
        self.assertEqual(code, 0)
        self.assertIn("beantwoord", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
