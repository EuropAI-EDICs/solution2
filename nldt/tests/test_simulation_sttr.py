# nldt/tests/test_simulation_sttr.py
"""Tests voor de STTR/DMN-import (docs/POC_STTR_IMTR_KANSEN.md, kans 2 en 3).

Offline en deterministisch: synthetische DMN naar de vorm van de echte
aanleveringen (DMN 1.1/v1.0 en DMN 1.2/v2.0), het officiële IPLO-voorbeeld
`ConclusieBouwenDakkapel.dmn` en de gecommitte Eindhoven-corpus onder
docs/research/sttr-imtr/. Geen netwerk, geen afhankelijkheid van de
gitignored cache onder dso_overlap/out/.
"""
import itertools
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator  # noqa: E402

from nldt.simulation.regelrecht import reference_engine  # noqa: E402
from nldt.simulation.regelrecht.sttr import (  # noqa: E402
    CONTRACT,
    ExportFout,
    export_document,
    parse_sttr,
    projecteer_decision,
    roundtrip_verschil,
    scenario_run,
    valideer_tegen_xsd,
)
from nldt.simulation.regelrecht.sttr import dmn as sttr_dmn  # noqa: E402
from nldt.simulation.regelrecht.sttr import __main__ as sttr_cli  # noqa: E402

RESEARCH = ROOT / "docs" / "research" / "sttr-imtr"
DAKKAPEL = RESEARCH / "dmn-voorbeelden-sttr-3.0.0" / "Voorbeeldbestanden STTR 3.0.0" / "ConclusieBouwenDakkapel.dmn"
EINDHOVEN_DIR = RESEARCH / "rtr-pre-eindhoven"

# Minimale DMN 1.1 / STTR v1.0 naar de vorm van de echte Tilburgse en
# Eindhovense aanleveringen (Geodan/RuleArts): één boolean-vraag, FIRST-hit
# met een no-hit vangnet — het "Bouwwerk slopen"-patroon.
_DMN11 = """<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="http://www.omg.org/spec/DMN/20151101/dmn.xsd"
                 xmlns:inter="http://toepasbare-regels.omgevingswet.overheid.nl/v1.0/Interactieregel"
                 xmlns:bedr="http://toepasbare-regels.omgevingswet.overheid.nl/v1.0/Bedrijfsregel"
                 xmlns:uitv="http://toepasbare-regels.omgevingswet.overheid.nl/v1.0/Uitvoeringsregel"
                 xmlns="http://toepasbare-regels.omgevingswet.overheid.nl/00000001001902763000"
                 namespace="http://toepasbare-regels.omgevingswet.overheid.nl/00000001001902763000"
                 name="Test activiteit" exporter="Test Builder">
  <dmn:extensionElements>
    <inter:regelgroepen>
      <inter:regelgroep id="groep1"><inter:naam>Algemene vragen</inter:naam><inter:prioriteit>1</inter:prioriteit></inter:regelgroep>
    </inter:regelgroepen>
    <uitv:uitvoeringsregels>
      <uitv:uitvoeringsregel id="uitv_1">
        <uitv:regelgroepRef href="#groep1"/>
        <uitv:vraag><uitv:gegevensType>boolean</uitv:gegevensType>
          <uitv:vraagTekst>Is het een monument?</uitv:vraagTekst></uitv:vraag>
      </uitv:uitvoeringsregel>
    </uitv:uitvoeringsregels>
  </dmn:extensionElements>
  <dmn:inputData id="input_1" name="invoer_monument">
    <dmn:extensionElements><uitv:uitvoeringsregelRef href="#uitv_1"/></dmn:extensionElements>
    <dmn:variable id="var_1" name="invoer_monument" typeRef="feel:boolean"/>
  </dmn:inputData>
  <dmn:decision id="dec_1" name="Vergunningplicht">
    <dmn:extensionElements>
      <bedr:functioneleStructuurRef href="http://toepasbare-regels.omgevingswet.overheid.nl/00000001001902763000/id/concept/Conclusienl.imow-gm0772.activiteit.TestActiviteit"/>
    </dmn:extensionElements>
    <dmn:variable id="dvar_1" name="Vergunningplicht" typeRef="feel:string"/>
    <dmn:informationRequirement><dmn:requiredInput href="#input_1"/></dmn:informationRequirement>
    <dmn:decisionTable hitPolicy="FIRST" id="tbl_1" outputLabel="Vergunningplicht">
      <dmn:input id="in_1" label="Is het een monument?">
        <dmn:inputExpression typeRef="feel:boolean"><dmn:text>invoer_monument</dmn:text></dmn:inputExpression>
      </dmn:input>
      <dmn:output id="out_1" label="Vergunningplicht"/>
      <dmn:rule id="r1">
        <dmn:inputEntry id="c1"><dmn:text><![CDATA[true]]></dmn:text></dmn:inputEntry>
        <dmn:outputEntry id="o1"><dmn:text><![CDATA["Vergunningplicht"]]></dmn:text></dmn:outputEntry>
        <dmn:annotationEntry><dmn:text>CVDR696400/4 art. 1.1</dmn:text></dmn:annotationEntry>
      </dmn:rule>
      <dmn:rule id="r2">
        <dmn:inputEntry id="c2"><dmn:text><![CDATA[false]]></dmn:text></dmn:inputEntry>
        <dmn:outputEntry id="o2"><dmn:text><![CDATA["no hit"]]></dmn:text></dmn:outputEntry>
      </dmn:rule>
    </dmn:decisionTable>
  </dmn:decision>
  <dmn:knowledgeSource id="ks_1" name="/akn/nl/act/gm0772/2020/omgevingsplan_v1_chp_1_art001">
    <dmn:authorityRequirement><dmn:requiredDecision href="#dec_1"/></dmn:authorityRequirement>
  </dmn:knowledgeSource>
</dmn:definitions>
"""


def _decision_vorm(hit="ANY", cel="<= 175", cel_type="number"):
    return {
        "naam": "Fysiek toegestaan",
        "tabel": {
            "hitPolicy": hit,
            "outputLabel": "Fysiek toegestaan",
            "type": "boolean",
            "invoer": [{"label": "Hoogte dakkapel", "naam": "hoogte", "type": cel_type}],
            "uitgangen": [{"label": "Fysiek toegestaan", "outputValues": "true,false"}],
            "rijen": [
                {"id": "r1", "cellen": [cel], "uitgangen": ["false"], "annotatie": ""},
                {"id": "r2", "cellen": ["-"], "uitgangen": ["true"], "annotatie": ""},
            ],
        },
    }


class TestParser(unittest.TestCase):
    def test_dmn11_v1(self):
        parsed = parse_sttr(_DMN11)
        self.assertEqual(parsed["dmnVersie"], "1.1")
        self.assertEqual(parsed["sttrNamespace"], "v1.0")
        self.assertEqual(parsed["oin"], "00000001001902763000")
        self.assertEqual(parsed["exporter"], "Test Builder")
        self.assertEqual(len(parsed["regelgroepen"]), 1)
        self.assertEqual(parsed["uitvoeringsregels"][0]["vraag"]["vraagTekst"], "Is het een monument?")
        self.assertEqual(len(parsed["decisions"]), 1)
        tabel = parsed["decisions"][0]["tabel"]
        self.assertEqual(tabel["hitPolicy"], "FIRST")
        self.assertEqual(tabel["rijen"][0]["cellen"], ["true"])
        self.assertEqual(tabel["rijen"][0]["uitgangen"], ['"Vergunningplicht"'])
        self.assertEqual(tabel["rijen"][0]["annotatie"], "CVDR696400/4 art. 1.1")
        self.assertEqual(parsed["kennisbronnen"], ["/akn/nl/act/gm0772/2020/omgevingsplan_v1_chp_1_art001"])

    def test_officieel_voorbeeld_dakkapel(self):
        parsed = parse_sttr(DAKKAPEL.read_text(encoding="utf-8"))
        self.assertEqual(parsed["dmnVersie"], "1.2")
        self.assertEqual(parsed["sttrNamespace"], "v2.0")
        self.assertGreaterEqual(len(parsed["kennisbronnen"]), 3)
        geo = [u for u in parsed["uitvoeringsregels"] if "geoVerwijzing" in u]
        self.assertEqual(len(geo), 1)
        self.assertEqual(geo[0]["geoVerwijzing"]["locatieIdentificatie"], "nl.imow-gm0345.gebied.gemeentegrens")
        namen = [d["naam"] for d in parsed["decisions"]]
        self.assertIn("Conclusie Dakkapel", namen)
        conclusie = next(d for d in parsed["decisions"] if d["naam"] == "Conclusie Dakkapel")
        self.assertEqual(conclusie["tabel"]["hitPolicy"], "COLLECT")
        self.assertIn('"Vergunningplicht"', conclusie["tabel"]["uitgangen"][0]["outputValues"])

    def test_onbekende_namespace_is_expliciete_fout(self):
        with self.assertRaises(sttr_dmn.SttrParseFout):
            parse_sttr('<dmn:definitions xmlns:dmn="http://example.com/onsbekend"/>')


class TestProjectie(unittest.TestCase):
    def test_rijen_naar_if_met_defaultrij(self):
        projectie = projecteer_decision(_decision_vorm())
        self.assertTrue(projectie["projecteerbaar"])
        self.assertTrue(projectie["defaultRij"])
        execution = projectie["execution"]
        self.assertEqual(execution["input"][0]["name"], "Hoogte dakkapel")
        actie = execution["actions"][0]["value"]
        self.assertEqual(actie["operation"], "IF")
        self.assertEqual(actie["cases"][0]["when"]["operation"], "LESS_THAN_OR_EQUAL")
        self.assertEqual(actie["cases"][0]["when"]["subject"], "$Hoogte dakkapel")
        self.assertIs(actie["cases"][0]["then"], False)
        self.assertIs(actie["default"], True)

    def test_engine_voert_projectie_uit(self):
        # rij 1: hoogte <= 175 → false; vangnetrij → true
        projectie = projecteer_decision(_decision_vorm())
        resultaat = reference_engine.evaluate(projectie["execution"], {"Hoogte dakkapel": 200.0})
        self.assertTrue(resultaat["outputs"]["Fysiek toegestaan"])
        resultaat = reference_engine.evaluate(projectie["execution"], {"Hoogte dakkapel": 100.0})
        self.assertFalse(resultaat["outputs"]["Fysiek toegestaan"])

    def test_scenario_run_boolean_polariteiten(self):
        decision = {
            "naam": "Toegestaan",
            "tabel": {
                "hitPolicy": "ANY",
                "outputLabel": "Toegestaan",
                "type": "boolean",
                "invoer": [{"label": "Monument", "naam": "monument", "type": "boolean"}],
                "uitgangen": [{"label": "Toegestaan"}],
                "rijen": [
                    {"id": "r1", "cellen": ["true"], "uitgangen": ["false"], "annotatie": ""},
                    {"id": "r2", "cellen": ["-"], "uitgangen": ["true"], "annotatie": ""},
                ],
            },
        }
        projectie = projecteer_decision(decision)
        scenario = scenario_run(projectie)
        self.assertEqual(scenario["status"], "uitgevoerd")
        self.assertEqual(scenario["combinaties"], 2)
        self.assertEqual(scenario["uitkomsten"], {"False": 1, "True": 1})

    def test_multihit_en_meeruitgangen_zijn_eerlijk_onmogelijk(self):
        self.assertFalse(projecteer_decision(_decision_vorm(hit="COLLECT"))["projecteerbaar"])
        twee_uitgangen = _decision_vorm()
        twee_uitgangen["tabel"]["uitgangen"].append({"label": "extra"})
        projectie = projecteer_decision(twee_uitgangen)
        self.assertFalse(projectie["projecteerbaar"])
        self.assertIn("uitgangskolommen", projectie["reden"])

    def test_cel_buiten_engine_subset_is_expliciete_reden(self):
        for cel in ("> 175", "not(null)", "(50..100)"):
            projectie = projecteer_decision(_decision_vorm(cel=cel))
            self.assertFalse(projectie["projecteerbaar"], cel)
            self.assertIn("engine-subset", projectie["reden"])


class TestEindhovenCorpus(unittest.TestCase):
    """De 162 gecommitte PRE-bestanden (docs/POC_STTR_IMTR_KANSEN.md, kans 3)."""

    @classmethod
    def setUpClass(cls):
        cls.paden = sorted(EINDHOVEN_DIR.glob("*.dmn"))
        cls.parsed = [parse_sttr(p.read_text(encoding="utf-8", errors="replace")) for p in cls.paden]

    def test_corpus_volledig_en_herkend(self):
        self.assertGreaterEqual(len(self.paden), 160)
        for parsed in self.parsed:
            self.assertEqual(parsed["oin"], "00000001001902763000")
            self.assertIn(parsed["dmnVersie"], ("1.1", "1.2"))

    def test_projectie_over_het_hele_corpus(self):
        projecteerbaar = 0
        for parsed in self.parsed:
            for decision in parsed["decisions"]:
                if projecteer_decision(decision)["projecteerbaar"]:
                    projecteerbaar += 1
        self.assertGreaterEqual(projecteerbaar, 2000)


class TestRtrClient(unittest.TestCase):
    def test_base_override(self):
        from nldt.simulation.regelrecht.dso_overlap import rtr
        with mock.patch.dict(os.environ, {"RTR_API_BASE": "https://voorbeeld/api/v9/"}):
            self.assertEqual(rtr.rtr_base(), "https://voorbeeld/api/v9")

    def test_refresh_schrijft_cache_en_herbruikt(self):
        from nldt.simulation.regelrecht.dso_overlap import rtr

        xml = _DMN11.encode("utf-8")
        entries = [
            {"identifier": 42, "oin": "00000001001902763000",
             "functioneleStructuurRef": "…nl.imow-gm0772.activiteit.Test", "begindatum": "01-01-2026"},
            {"identifier": 43, "oin": "00000001001902763000",
             "functioneleStructuurRef": "…", "begindatum": "01-01-2026", "einddatum": "01-02-2026"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"DSO_API_KEY": "test-key"}):
                with mock.patch.object(rtr, "fetch_toepasbare_regels", return_value=entries), \
                     mock.patch.object(rtr, "fetch_sttr_bestand", return_value=(xml, "abc")) as fetch_bestand:
                    uit = rtr.refresh_instrument(
                        "eindhoven", out_dir=pathlib.Path(tmp), met_bestanden=True
                    )
                    self.assertEqual(uit["counts"]["geldig"], 1)
                    self.assertEqual(fetch_bestand.call_count, 1)  # alleen de geldige
                    self.assertTrue((pathlib.Path(tmp) / "eindhoven.rtr.42.dmn").is_file())
                    # tweede run: cache-hit, geen nieuwe download
                    uit2 = rtr.refresh_instrument(
                        "eindhoven", out_dir=pathlib.Path(tmp), met_bestanden=True
                    )
                    self.assertEqual(fetch_bestand.call_count, 1)
                    self.assertEqual(uit2["bestanden"]["42"]["cache"], "bestaand")


class TestDsoKbSttr(unittest.TestCase):
    def _tmp_cache(self):
        tmp = tempfile.TemporaryDirectory()
        out = pathlib.Path(tmp.name)
        rtr = {
            "contract": "rtr/v1", "instrument": "eindhoven", "label": "x",
            "oin": "00000001001902763000", "base": "b", "gegenereerdOp": "nu",
            "counts": {"entries": 1, "geldig": 1, "metEinddatum": 0, "bestanden": 1},
            "entries": [
                {"identifier": 7, "oin": "00000001001902763000",
                 "functioneleStructuurRef": "…nl.imow-gm0772.activiteit.BouwwerkSlopen",
                 "begindatum": "01-01-2026"},
            ],
            "bestanden": {},
        }
        (out / "eindhoven.rtr.json").write_text(json.dumps(rtr), encoding="utf-8")
        (out / "eindhoven.rtr.7.dmn").write_bytes(b"<dmn/>")
        sttr = {
            "contract": CONTRACT, "instrument": "eindhoven", "oin": "00000001001902763000",
            "gegenereerdOp": "nu", "bronnen": {},
            "totals": {"bestanden": 1, "decisions": 2, "projecteerbaar": 1,
                        "nietProjecteerbaar": 1, "dmnVersies": {"1.1": 1}, "exporters": {},
                        "redenen": {}, "geoVerwijzingen": 0, "kennisbronnen": 0,
                        "scenarioUitgevoerd": 1},
            "bestanden": [
                {"identifier": 7, "naam": "Bouwwerk slopen", "dmnVersie": "1.1",
                 "exporter": None, "decisions": []}
            ],
        }
        (out / "eindhoven.sttr.json").write_text(json.dumps(sttr), encoding="utf-8")
        return tmp, out

    def test_lijst_en_lees(self):
        from nldt.services import dso_kb

        tmp, out = self._tmp_cache()
        with tmp:
            lijst = dso_kb.lijst_toepasbare_regels("eindhoven", out_dir=out)
            self.assertEqual(lijst["oin"], "00000001001902763000")
            self.assertEqual(lijst["toepasbareRegels"][0]["activiteit"], "BouwwerkSlopen")
            self.assertTrue(lijst["toepasbareRegels"][0]["bestandGecacht"])
            gelezen = dso_kb.lees_sttr("eindhoven", 7, out_dir=out)
            self.assertEqual(gelezen["bestanden"][0]["naam"], "Bouwwerk slopen")

    def test_fouten_noemen_herstelpad(self):
        from nldt.services import dso_kb

        tmp, out = self._tmp_cache()
        with tmp:
            with self.assertRaises(dso_kb.DsoKbFout) as ctx:
                dso_kb.lijst_toepasbare_regels("bestaatniet", out_dir=out)
            self.assertIn("onbekend instrument", str(ctx.exception))
            # instrument zónder OIN (injecteerbaar — utrecht zelf is inmiddels gekoppeld)
            instrument_zonder_oin = {"geenoin": {"label": "Zonder OIN", "default_location_id": "l"}}
            locatie_l = {"l": {"id": "l", "label": "Locatie", "instrument": "geenoin"}}
            with self.assertRaises(dso_kb.DsoKbFout) as ctx:
                dso_kb.lijst_toepasbare_regels(
                    "geenoin", out_dir=out,
                    instrumenten=instrument_zonder_oin, locaties=locatie_l)
            self.assertIn("geen OIN", str(ctx.exception))
            with self.assertRaises(dso_kb.DsoKbFout) as ctx:
                dso_kb.lees_sttr(
                    "geenoin", out_dir=out,
                    instrumenten=instrument_zonder_oin, locaties=locatie_l)
            self.assertIn("geen OIN", str(ctx.exception))
            with self.assertRaises(dso_kb.DsoKbFout) as ctx:
                dso_kb.lees_sttr("eindhoven", 999, out_dir=out)
            self.assertIn("onbekende toepasbare-regel", str(ctx.exception))
        with tempfile.TemporaryDirectory() as leeg:
            with self.assertRaises(dso_kb.DsoKbFout) as ctx:
                dso_kb.lees_sttr("eindhoven", out_dir=pathlib.Path(leeg))
            self.assertIn("regelrecht.sttr", str(ctx.exception))


class TestVoorbeeldenIndex(unittest.TestCase):
    def test_bouw_uit_voorbeelden_schema_geldig(self):
        index = sttr_cli.bouw_uit_voorbeelden()
        self.assertEqual(index["totals"]["bestanden"], 6)
        schema = json.loads(
            (ROOT / "nldt/simulation/regelrecht/sttr/sttr-index.schema.json").read_text("utf-8")
        )
        fouten = list(Draft202012Validator(schema).iter_errors(index))
        self.assertEqual(fouten, [])


class TestExport(unittest.TestCase):
    """RegelRecht → STTR (kans 2, autorauteitsroute): XSD + roundtrip-eigenschap."""

    OIN = "00000001001902763000"

    @staticmethod
    def _exec_limiet():
        # exact de vorm van art. 1.8 in de volle Eindhoven-export (template maximaal 1.0 m)
        return {
            "produces": {"legal_character": "TOETS"},
            "parameters": [],
            "input": [
                {"name": "limiet_m", "type": "number",
                 "description": "Gemeten limiet_m van het voorstel t.o.v. limiet 1.0.",
                 "source": {"description": "voorstelfeit"}},
                {"name": "in_werkingsgebied", "type": "boolean",
                 "description": "Geo-feit: locatie binnen werkingsgebied van de regel.",
                 "source": {"description": "werkingsgebiedRef / zone-engine (MC-11)"}},
            ],
            "output": [{"name": "toegestaan_art_1_8", "type": "boolean",
                        "description": "Of artikel 1.8 de activiteit toelaat."}],
            "actions": [{"output": "toegestaan_art_1_8",
                         "value": {"operation": "AND", "conditions": [
                             {"operation": "LESS_THAN_OR_EQUAL", "subject": "$limiet_m", "value": 1.0},
                             {"operation": "EQUALS", "subject": "$in_werkingsgebied", "value": True}]}}],
        }

    @staticmethod
    def _exec_102():
        # het gecommitte voorbeeld (docs/examples/regelrecht/…10.2.yaml): IF met twee cases
        pad = (ROOT / "docs" / "examples" / "regelrecht"
               / "omgevingsplan-eindhoven-art22.1-en-10.2.yaml")
        art = next(a for a in yaml.safe_load(pad.read_text("utf-8"))["articles"]
                   if a["number"] == "10.2")
        return art["machine_readable"]["execution"]

    @staticmethod
    def _exec_verbod():
        return {
            "produces": {"legal_character": "TOETS"},
            "parameters": [],
            "input": [
                {"name": "activiteit_valt_onder_verbod", "type": "boolean",
                 "description": "Of de voorgenomen activiteit onder het verbod valt.",
                 "source": {"description": "voorstelfeit"}},
                {"name": "in_werkingsgebied", "type": "boolean",
                 "description": "Geo-feit: locatie binnen werkingsgebied.",
                 "source": {"description": "MC-11"}},
            ],
            "output": [{"name": "toegestaan_art_5_21", "type": "boolean",
                        "description": ""}],
            "actions": [{"output": "toegestaan_art_5_21",
                         "value": {"operation": "AND", "conditions": [
                             {"operation": "EQUALS", "subject": "$activiteit_valt_onder_verbod", "value": False},
                             {"operation": "EQUALS", "subject": "$in_werkingsgebied", "value": True}]}}],
        }

    def _document(self, *executies_ankers):
        artikelen = [{"naam": naam, "anker": anker, "execution": ex}
                     for ex, naam, anker in executies_ankers]
        return export_document(artikelen, oin=self.OIN,
                               naam="RegelRecht naar STTR — test")

    def test_xsd_geldig_officieel_en_eigen_export(self):
        # de vastgepinde DMN_v12.xsd keurt het officiële IPLO-voorbeeld…
        self.assertEqual(
            valideer_tegen_xsd(DAKKAPEL.read_text(encoding="utf-8")), []
        )
        # …én onze eigen export (limiet + IF + verbod in één document)
        xml = self._document(
            (self._exec_limiet(), "art. 1.8", "CVDR696400/4 art. 1.8"),
            (self._exec_102(), "art. 10.2", "CVDR696400/4 art. 10.2"),
            (self._exec_verbod(), "art. 5.21", "CVDR696400/4 art. 5.21"),
        )
        self.assertEqual(valideer_tegen_xsd(xml), [])

    def test_exportvorm_is_sttr_30_dmn_12(self):
        xml = self._document((self._exec_limiet(), "art. 1.8", "CVDR696400/4 art. 1.8"))
        parsed = parse_sttr(xml)
        self.assertEqual(parsed["dmnVersie"], "1.2")
        self.assertEqual(parsed["sttrNamespace"], "v2.0")
        self.assertEqual(parsed["sttrVersie"], "3")
        self.assertEqual(parsed["oin"], self.OIN)
        self.assertEqual(parsed["kennisbronnen"], ["CVDR696400/4 art. 1.8"])
        vragen = [u for u in parsed["uitvoeringsregels"] if "vraag" in u]
        self.assertEqual(len(vragen), 2)
        self.assertIn("werkingsgebied", vragen[1]["vraag"]["vraagTekst"])

    def test_roundtrip_limiet_verbod_en_if(self):
        xml = self._document(
            (self._exec_limiet(), "art. 1.8", "CVDR696400/4 art. 1.8"),
            (self._exec_102(), "art. 10.2", "CVDR696400/4 art. 10.2"),
            (self._exec_verbod(), "art. 5.21", "CVDR696400/4 art. 5.21"),
        )
        combi_limiet = [{"limiet_m": m, "in_werkingsgebied": w}
                        for m in (0.5, 1.0, 1.5) for w in (True, False)]
        combi_10_2 = [
            dict(zip(["strijd_met_tijdelijk_deel", "voorschriften_verbonden_voor_iwt"], c))
            for c in itertools.product((True, False), repeat=2)
        ]
        combi_verbod = [{"activiteit_valt_onder_verbod": a, "in_werkingsgebied": w}
                        for a in (True, False) for w in (True, False)]
        self.assertEqual(roundtrip_verschil(self._exec_limiet(), xml, combi_limiet), [])
        self.assertEqual(roundtrip_verschil(self._exec_102(), xml, combi_10_2), [])
        self.assertEqual(roundtrip_verschil(self._exec_verbod(), xml, combi_verbod), [])

    def test_niet_exporteerbaar_is_expliciete_fout(self):
        or_exec = {"input": [{"name": "x", "type": "boolean", "description": "", "source": {}}],
                   "output": [{"name": "y", "type": "boolean", "description": ""}],
                   "actions": [{"output": "y", "value": {"operation": "OR", "conditions": []}}]}
        with self.assertRaises(ExportFout):
            self._document((or_exec, "or", None))
        spook_exec = {"input": [{"name": "x", "type": "boolean", "description": "", "source": {}}],
                      "output": [{"name": "y", "type": "boolean", "description": ""}],
                      "actions": [{"output": "y", "value": {
                          "operation": "EQUALS", "subject": "$bestaatniet", "value": True}}]}
        with self.assertRaises(ExportFout):
            self._document((spook_exec, "spook", None))
        with self.assertRaises(ExportFout):
            export_document([{"naam": "x", "anker": None, "execution": self._exec_limiet()}],
                            oin="geen-oin", naam="fout")


class TestRtrOnlyInstrument(unittest.TestCase):
    """Veenendaal: RTR-only koppeling (gm0345) — de Presenteren-CLIs wijzen door."""

    def test_registry_veenendaal(self):
        from nldt.simulation.regelrecht.dso_overlap.instruments import INSTRUMENTS

        v = INSTRUMENTS["veenendaal"]
        self.assertEqual(v["oin"], "00000001001104470000")
        self.assertEqual(v["bevoegd_gezag"], "gm0345")
        self.assertFalse(v.get("akn_uri"))  # geen Presenteren-koppeling

    def test_compare_en_tpod_wijzen_naar_rtr_route(self):
        from nldt.simulation.regelrecht.dso_overlap import compare
        from nldt.simulation.regelrecht.tpod import __main__ as tpod_main

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                compare.compare_instrument(
                    "veenendaal", location_id=None,
                    out_dir=pathlib.Path(tmp), offline=True, skip_rp=True,
                )
            self.assertIn("RTR-only", str(ctx.exception))
            with self.assertRaises(SystemExit) as ctx:
                tpod_main.build_for_instrument(
                    "veenendaal",
                    cache_dir=pathlib.Path(tmp), out_dir=pathlib.Path(tmp),
                )
            self.assertIn("RTR-only", str(ctx.exception))

    def test_dso_kb_annotaties_wijzen_naar_rtr_route(self):
        from nldt.services import dso_kb

        with self.assertRaises(dso_kb.DsoKbFout) as ctx:
            dso_kb.lees_annotaties("veenendaal")
        self.assertIn("RTR-only", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
