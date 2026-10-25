# nldt/tests/test_simulation_tpod.py
"""Tests voor de tpod-index over gecachte IMOW-annotaties (docs/POC_TPOD_IMOW_KANSEN.md).

Offline en deterministisch: synthetische Presenteren-payloads volgens de
vorm zoals geleverd door Presenteren v8 (PRE, oktober 2026); geen netwerk
en geen afhankelijkheid van de gitignored cache onder dso_overlap/out/.
"""
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGELRECHT_DIR = ROOT / "nldt" / "simulation" / "regelrecht"
sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator  # noqa: E402

from nldt.simulation.regelrecht.tpod import (  # noqa: E402
    CONTRACT,
    TOETS_CONTRACT,
    activiteit_structuur,
    build_index,
    build_toets,
    geo_feiten,
    match_gebiedsaanwijzing,
    parse_regels,
    parse_regelteksten,
    parse_wid,
    pons_annotaties,
)
from nldt.simulation.regelrecht.tpod.toets import resolve_input  # noqa: E402

_AMBTS = "nl.imow-gm0772.ambtsgebied.9999999999"
_G1 = "nl.imow-gm0772.gebiedengroep.g1"
_G2 = "nl.imow-gm0772.gebiedengroep.g2"
_TOPHAAK = "nl.imow-gm0772.activiteit.Tophaak"
_KIND = "nl.imow-gm0772.activiteit.Kind"
_EXTERN_KIND = "nl.imow-gm0772.activiteit.ExtKind"
_GA_GROEN = "nl.imow-gm0772.gebiedsaanwijzing.groen"


def _payload():
    """Mini-Presenteren-antwoord: 4 regelteksten, 3 regels, 3 activiteiten, 3 locaties."""
    return {
        "regelteksten": [
            {
                "identificatie": "nl.imow-gm0772.regeltekst.t1",
                "wId": "gm0772_h1__chp_10__subchp_10.2__art_10.2__para_1",
            },
            {
                "identificatie": "nl.imow-gm0772.regeltekst.t2",
                "wId": "gm0772_h1__chp_10__subchp_10.2__art_10.2__para_2",
            },
            {
                "identificatie": "nl.imow-gm0772.regeltekst.t3",
                "wId": "gm0772_h1__chp_22__subchp_22.1__art_22.1__para_1",
            },
            {
                "identificatie": "nl.imow-gm0772.regeltekst.t4",
                "wId": "gm0772_h1__chp_6__art_6.8",
            },
            {
                # tekst zonder artikel-segment (vrije-tekststructuur)
                "identificatie": "nl.imow-gm0772.regeltekst.t5",
                "wId": "gm0772_h1__chp_9",
            },
        ],
        "regelsVoorIedereen": [
            {
                "identificatie": "nl.imow-gm0772.juridischeregel.r1",
                "idealisatie": {"waarde": "exact"},
                "regeltekstRef": "nl.imow-gm0772.regeltekst.t1",
                "locatieRefs": [_AMBTS],
                "activiteitLocatieaanduidingen": [
                    {"identificatie": "…ala1", "activiteitRef": _KIND}
                ],
            },
            {
                "identificatie": "nl.imow-gm0772.juridischeregel.r2",
                "idealisatie": {"waarde": "idealiserend"},
                "regeltekstRef": "nl.imow-gm0772.regeltekst.t2",
                "locatieRefs": [_AMBTS, _G1],
                "gebiedsaanwijzingRefs": [_GA_GROEN],
                "activiteitLocatieaanduidingen": [],
            },
            {
                "identificatie": "nl.imow-gm0772.juridischeregel.r3",
                "idealisatie": {"waarde": "exact"},
                "regeltekstRef": "nl.imow-gm0772.regeltekst.ontbreekt",
                "locatieRefs": [_AMBTS],
            },
        ],
        "instructieregels": [
            {
                "identificatie": "nl.imow-gm0772.instructieregel.i1",
                "regeltekstRef": "nl.imow-gm0772.regeltekst.t3",
                "locatieRefs": [_AMBTS],
            }
        ],
        "activiteiten": [
            {
                "identificatie": _TOPHAAK,
                "naam": "Activiteit gereguleerd in het omgevingsplan gemeente X",
            },
            {
                "identificatie": _KIND,
                "naam": "Milieubelastende activiteit ter plaatse van …",
                "groep": {"waarde": "milieubelastende activiteit"},
                "bovenliggendeActiviteitRef": _TOPHAAK,
            },
            {
                "identificatie": _EXTERN_KIND,
                "naam": "Activiteit onder de rijkstophaak",
                "groep": {"waarde": "overig"},
                "bovenliggendeActiviteitRef": "nl.imow-mnre1034.activiteit.RijksTop",
            },
        ],
        "locaties": [
            {
                "identificatie": _AMBTS,
                "locatieType": "Ambtsgebied",
                "geometrieIdentificatie": None,
            },
            {
                "identificatie": _G1,
                "locatieType": "Gebiedengroep",
                "noemer": "risicobedrijf",
                "geometrieIdentificatie": "11111111-1111-1111-1111-111111111111",
            },
            {
                "identificatie": _G2,
                "locatieType": "Gebiedengroep",
                "noemer": "niet op het punt",
                "geometrieIdentificatie": "22222222-2222-2222-2222-222222222222",
            },
        ],
        "geselecteerdeLocatieRefs": [_AMBTS, _G1],
        "gebiedsaanwijzingen": [
            {
                "identificatie": _GA_GROEN,
                "naam": "groengebied",
                "groep": {"waarde": "groen"},
                "type": {"waarde": "functie"},
            }
        ],
    }


def _report():
    return {
        "articles": [
            {"number": "10.2", "status": "formalized"},
            {"number": "22.1", "status": "unmatched", "reason": "no_template"},
        ]
    }


def _artikelen():
    return {
        "articles": [
            {"number": "10.2", "text": "…"},
            {"number": "22.1", "text": "…"},
            {"number": "9.9", "text": "…"},
        ]
    }


def _index(gegenereerd_op="2026-10-20T00:00:00+00:00"):
    return build_index(
        instrument_id="eindhoven",
        instrument={
            "label": "Omgevingsplan gemeente Eindhoven",
            "akn_uri": "_akn_nl_act_gm0772_2020_omgevingsplan",
            "akn_path": "/akn/nl/act/gm0772/2020/omgevingsplan",
            "cvdr": "CVDR696400",
            "bevoegd_gezag": "gm0772",
        },
        locatie={"id": "eindhoven-woensel-proxy", "notes": "fixture"},
        annotaties_payload=_payload(),
        annotaties_sha256="ab" * 32,
        gegenereerd_op=gegenereerd_op,
        formalization_report=_report(),
        artikelen=_artikelen(),
    )


class TestParseWid(unittest.TestCase):
    def test_volledige_pad(self):
        p = parse_wid("gm0772_hash__chp_5__subchp_5.4__subsec_5.4.2__art_5.117__para_1")
        self.assertEqual(
            p,
            {
                "prefix": "gm0772_hash",
                "hoofdstuk": "5",
                "afdeling": "5.4",
                "paragraaf": "5.4.2",
                "artikel": "5.117",
                "lid": "1",
                "onbekend": [],
            },
        )

    def test_zonder_lid_en_afdeling(self):
        p = parse_wid("pv26_1053__chp_3__subchp_3.3__subsec_3.3.5__art_3.84")
        self.assertIsNone(p["lid"])
        self.assertEqual(p["artikel"], "3.84")
        self.assertEqual(p["paragraaf"], "3.3.5")

    def test_onbekende_segmenten_blijven_behouden(self):
        p = parse_wid("x__chp_1__div_9__art_1.1")
        self.assertEqual(p["onbekend"], ["div_9"])
        self.assertEqual(p["artikel"], "1.1")

    def test_leeg(self):
        self.assertIsNone(parse_wid("")["artikel"])


class TestAnnotaties(unittest.TestCase):
    def setUp(self):
        self.payload = _payload()

    def test_regelteksten(self):
        rts = parse_regelteksten(self.payload)
        self.assertEqual(len(rts), 5)
        self.assertEqual(rts[0]["artikel"], "10.2")
        self.assertEqual(rts[0]["lid"], "1")
        self.assertEqual(rts[2]["artikel"], "22.1")
        self.assertIsNone(rts[3]["lid"])
        self.assertIsNone(rts[4]["artikel"])

    def test_regels_gejoint_op_artikel_en_activiteit(self):
        regels = parse_regels(self.payload)
        self.assertEqual(len(regels), 4)  # 3 rvi + 1 instructieregel
        r1 = next(r for r in regels if r["identificatie"].endswith("r1"))
        self.assertEqual(r1["soort"], "regelVoorIedereen")
        self.assertEqual(r1["artikel"], "10.2")
        self.assertEqual(r1["activiteitRefs"], [_KIND])
        r3 = next(r for r in regels if r["identificatie"].endswith("r3"))
        self.assertFalse(r3["tekstInPayload"])
        self.assertIsNone(r3["artikel"])
        i1 = next(r for r in regels if r["soort"] == "instructieregel")
        self.assertEqual(i1["artikel"], "22.1")

    def test_activiteit_structuur(self):
        s = activiteit_structuur(self.payload)
        self.assertEqual(s["totaal"], 3)
        # enige root is de (synthetische) landelijke tophaak-vergelijkbare
        self.assertEqual([r["identificatie"] for r in s["roots"]], [_TOPHAAK])
        # 'gereguleerd' zit in de naam van de lokale top — onafhankelijk van ouder
        self.assertEqual([t["identificatie"] for t in s["tophaakKandidaten"]],
                         [_TOPHAAK])
        self.assertEqual(s["metExterneBovenliggende"], 1)
        self.assertEqual(s["maxDiepte"], 1)
        self.assertEqual(s["groepen"], {"milieubelastende activiteit": 1,
                                        "overig": 1})

    def test_geo_feiten(self):
        f = geo_feiten(self.payload)
        self.assertEqual(f["ambtsgebiedRef"], _AMBTS)
        geselecteerd = {l["identificatie"] for l in f["locaties"]
                        if l["geselecteerdOpPunt"]}
        self.assertEqual(geselecteerd, {_AMBTS, _G1})
        self.assertEqual(f["aantalLocatiesMetGeometrie"], 2)
        self.assertEqual(f["gebiedsaanwijzingen"][0]["naam"], "groengebied")

    def test_pons_afwezig_explicit(self):
        p = pons_annotaties(self.payload)
        self.assertFalse(p["beschikbaar"])
        self.assertEqual(p["aantal"], 0)
        with_pons = dict(self.payload, pons=[{"identificatie": "nl.imow-gm0772.pons.p1"}])
        p2 = pons_annotaties(with_pons)
        self.assertTrue(p2["beschikbaar"])
        self.assertEqual(p2["aantal"], 1)


class TestBuildIndex(unittest.TestCase):
    def setUp(self):
        self.index = _index()

    def test_contract_en_schema(self):
        self.assertEqual(self.index["contract"], CONTRACT)
        schema = json.loads(
            (REGELRECHT_DIR / "tpod" / "tpod-index.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(self.index)

    def test_wid_anchoring_per_artikel(self):
        profielen = {p["artikel"]: p for p in self.index["artikelProfielen"]}
        # '10.2' vóór '22.1' in numerieke volgorde, ook al is het tekstueel later
        volgorde = [p["artikel"] for p in self.index["artikelProfielen"]]
        self.assertEqual(volgorde, sorted(volgorde, key=lambda n: tuple(map(int, n.split(".")))))
        self.assertEqual(profielen["10.2"]["leden"], ["1", "2"])
        self.assertEqual(profielen["10.2"]["aantalRegels"], 2)
        self.assertEqual(profielen["10.2"]["activiteitGroepen"],
                         ["milieubelastende activiteit"])
        # ambtsgebied (= heel de gemeente) is gefilterd; G1 blijft over (r2, lid 2)
        self.assertEqual(profielen["10.2"]["locatieRefs"], [_G1])
        self.assertEqual(profielen["10.2"]["gebiedsaanwijzingen"], ["groengebied"])
        # 22.1 krijgt alleen de instructieregel; die wijkt naar het ambtsgebied
        self.assertEqual(profielen["22.1"]["aantalRegels"], 1)
        self.assertEqual(profielen["22.1"]["locatieRefs"], [])
        self.assertEqual(profielen["22.1"]["hoofdstuk"], "22")
        # 6.8 heeft een regeltekst maar geen regel -> geen profiel
        self.assertNotIn("6.8", profielen)

    def test_formaliseringsstatus_gejoined(self):
        profielen = {p["artikel"]: p for p in self.index["artikelProfielen"]}
        self.assertTrue(profielen["10.2"]["formalized"])
        self.assertEqual(profielen["22.1"]["rrStatus"], "unmatched")

    def test_hit_coverage_tegen_poc_populatie(self):
        hc = self.index["hitCoverage"]
        self.assertEqual(hc["pocArtikelen"], 3)
        self.assertEqual(hc["pocArtikelenInHit"], 2)  # 10.2 + 22.1, 9.9 niet in hit
        self.assertEqual(hc["formalizedInHit"], 1)

    def test_regels_zonder_tekst_geteld(self):
        self.assertEqual(self.index["regels"]["zonderTekstInPayload"], 1)
        self.assertEqual(self.index["regelteksten"]["zonderArtikel"], 1)

    def test_geen_woordelijke_regeltekst_in_index(self):
        # de index bevat alleen identificaties/locators/aggregaten — geen
        # veld met regeltekst-inhoud (die zit sowieso niet in de payload)
        dump = json.dumps(self.index)
        self.assertNotIn('"tekst"', dump)
        self.assertNotIn('"inhoud"', dump)

    def test_deterministisch(self):
        self.assertEqual(_index(), _index())


class TestMatchEnResolve(unittest.TestCase):
    _GA = [
        {"naam": "Stedelijk gebied noord"},
        {"naam": "Stedelijk gebied zuid"},
        {"naam": "tijdelijke regels tijdelijk deel nog in werking"},
    ]

    def test_unieke_match(self):
        self.assertEqual(
            match_gebiedsaanwijzing("in_stedelijk_gebied_noord", self._GA),
            "Stedelijk gebied noord",
        )

    def test_ambigu_nooit_gokken(self):
        self.assertEqual(
            match_gebiedsaanwijzing("in_stedelijk_gebied", self._GA), "AMBIGU"
        )

    def test_geen_match(self):
        self.assertIsNone(
            match_gebiedsaanwijzing("in_bosgroeiplaatsen", self._GA)
        )

    def test_resolve_input_bronnen(self):
        ga = [{"naam": "Stedelijk gebied"}]
        self.assertEqual(
            resolve_input("in_werkingsgebied", gebiedsaanwijzingen=ga),
            {"bron": "presenteren-hit", "waarde": True},
        )
        self.assertEqual(
            resolve_input("strijd_met_tijdelijk_deel", gebiedsaanwijzingen=ga),
            {"bron": "scenario", "waarde": None},
        )
        self.assertEqual(
            resolve_input("activiteit_valt_onder_verbod", gebiedsaanwijzingen=ga),
            {"bron": "scenario", "waarde": None},
        )
        self.assertEqual(
            resolve_input("bouwhoogte_m", gebiedsaanwijzingen=ga),
            {"bron": "onbekend", "waarde": None, "reden": "geen_zoneveld"},
        )
        self.assertEqual(
            resolve_input("in_stedelijk_gebied", gebiedsaanwijzingen=ga),
            {"bron": "gebiedsaanwijzing", "waarde": True,
             "match": "Stedelijk gebied"},
        )
        self.assertEqual(
            resolve_input("in_landelijk_gebied", gebiedsaanwijzingen=ga),
            {"bron": "afwezig_in_hit", "waarde": False},
        )
        self.assertEqual(
            resolve_input("in_stedelijk_gebied",
                          gebiedsaanwijzingen=self._GA),
            {"bron": "onbekend", "waarde": None,
             "reden": "ambigu_gebiedsaanwijzing"},
        )


def _mini_index():
    """Minimale tpod-index voor de toets (vorm zoals build_index die levert)."""
    return {
        "artikelProfielen": [
            {"artikel": "6.8", "formalized": True, "locatieRefs": [_G1]},
            {"artikel": "5.8", "formalized": True, "locatieRefs": []},
            {"artikel": "9.9", "formalized": True, "locatieRefs": []},
            {"artikel": "10.2", "formalized": True, "locatieRefs": []},
            {"artikel": "7.1", "formalized": True, "locatieRefs": []},
            {"artikel": "8.1", "formalized": True, "locatieRefs": []},
        ],
        "geoFeiten": {
            "gebiedsaanwijzingen": [
                {"naam": "Stedelijk gebied noord"},
                {"naam": "Stedelijk gebied zuid"},
                {"naam": "tijdelijke regels tijdelijk deel nog in werking"},
            ],
            "locaties": [
                {"identificatie": _G1, "noemer": "risicobedrijf"}
            ],
        },
    }


def _mini_yaml():
    return {
        "articles": [
            {
                "number": "6.8",
                "machine_readable": {
                    "execution": {
                        "input": [{"name": "in_werkingsgebied"}],
                        "output": [{"name": "toegestaan_6_8"}],
                        "actions": [
                            {
                                "output": "toegestaan_6_8",
                                "value": {
                                    "operation": "EQUALS",
                                    "subject": "$in_werkingsgebied",
                                    "value": True,
                                },
                            }
                        ],
                    }
                },
            },
            {
                "number": "5.8",
                "machine_readable": {
                    "execution": {
                        "input": [
                            {"name": "activiteit_valt_onder_verbod"},
                            {"name": "in_werkingsgebied"},
                        ],
                        "output": [{"name": "toegestaan_5_8"}],
                        "actions": [
                            {
                                "output": "toegestaan_5_8",
                                "value": {
                                    "operation": "AND",
                                    "conditions": [
                                        {
                                            "operation": "EQUALS",
                                            "subject":
                                                "$activiteit_valt_onder_verbod",
                                            "value": False,
                                        },
                                        {
                                            "operation": "EQUALS",
                                            "subject": "$in_werkingsgebied",
                                            "value": True,
                                        },
                                    ],
                                },
                            }
                        ],
                    }
                },
            },
            {
                "number": "9.9",
                "machine_readable": {
                    "execution": {
                        "input": [{"name": "in_werkingsgebied"}],
                        "output": [{"name": "kapot_9_9"}],
                        "actions": [
                            {
                                "output": "kapot_9_9",
                                "value": {
                                    "operation": "EQUALS",
                                    "subject": "$niet_bestaand",
                                    "value": True,
                                },
                            }
                        ],
                    }
                },
            },
            {
                "number": "10.2",
                "machine_readable": {
                    "execution": {
                        "input": [{"name": "strijd_met_tijdelijk_deel"}],
                        "output": [{"name": "equivalentie_houdt_10_2"}],
                        "actions": [
                            {
                                "output": "equivalentie_houdt_10_2",
                                "value": {
                                    "operation": "IF",
                                    "cases": [
                                        {
                                            "when": {
                                                "operation": "EQUALS",
                                                "subject":
                                                    "$strijd_met_tijdelijk_deel",
                                                "value": True,
                                            },
                                            "then": False,
                                        }
                                    ],
                                    "default": True,
                                },
                            }
                        ],
                    }
                },
            },
            {
                "number": "7.1",
                "machine_readable": {
                    "execution": {
                        "input": [{"name": "in_stedelijk_gebied"}],
                        "output": [{"name": "result_7_1"}],
                        "actions": [
                            {
                                "output": "result_7_1",
                                "value": {
                                    "operation": "EQUALS",
                                    "subject": "$in_stedelijk_gebied",
                                    "value": True,
                                },
                            }
                        ],
                    }
                },
            },
            # 8.1: formalized volgens de index, maar zonder machine_readable
            {"number": "8.1"},
        ]
    }


def _toets(gegenereerd_op="2026-10-20T00:00:00+00:00"):
    return build_toets(
        instrument_id="eindhoven",
        instrument={
            "label": "Omgevingsplan gemeente Eindhoven",
            "cvdr": "CVDR696400",
        },
        locatie={"id": "eindhoven-woensel-proxy"},
        tpod_index=_mini_index(),
        yaml_doc=_mini_yaml(),
        gegenereerd_op=gegenereerd_op,
    )


class TestToets(unittest.TestCase):
    def setUp(self):
        self.toets = _toets()
        self.by_num = {a["artikel"]: a for a in self.toets["artikelen"]}

    def test_contract_en_schema(self):
        self.assertEqual(self.toets["contract"], TOETS_CONTRACT)
        schema = json.loads(
            (REGELRECHT_DIR / "tpod" / "punt-toets.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(self.toets)

    def test_getoetst_met_feit_en_trace(self):
        a = self.by_num["6.8"]
        self.assertEqual(a["status"], "getoetst")
        self.assertEqual(a["inputsWaarden"], {"in_werkingsgebied": True})
        self.assertEqual(a["outputs"], {"toegestaan_6_8": True})
        self.assertTrue(a["trace"])
        self.assertEqual(a["zones"], [{"ref": _G1, "noemer": "risicobedrijf"}])

    def test_scenario_twee_polariteiten_met_context(self):
        a = self.by_num["10.2"]
        self.assertEqual(a["status"], "scenario")
        runs = {r["scenario"]: r["outputs"] for r in a["runs"]}
        self.assertEqual(runs["strijd_met_tijdelijk_deel=false"],
                         {"equivalentie_houdt_10_2": True})
        self.assertEqual(runs["strijd_met_tijdelijk_deel=true"],
                         {"equivalentie_houdt_10_2": False})
        self.assertTrue(a["scenarioContext"]["tijdelijkDeelGeldtOpPunt"])

    def test_scenario_feit_plus_verstelveld(self):
        a = self.by_num["5.8"]
        self.assertEqual(a["status"], "scenario")
        self.assertEqual(a["scenarioVelden"], ["activiteit_valt_onder_verbod"])
        runs = {r["scenario"]: r["outputs"] for r in a["runs"]}
        # in_werkingsgebied=true is feit (hit); alleen het verbodsveld varieert
        self.assertEqual(
            runs["activiteit_valt_onder_verbod=false"],
            {"toegestaan_5_8": True},
        )
        self.assertEqual(
            runs["activiteit_valt_onder_verbod=true"],
            {"toegestaan_5_8": False},
        )

    def test_ambigu_leidt_tot_onthouding(self):
        a = self.by_num["7.1"]
        self.assertEqual(a["status"], "onthouding")
        self.assertEqual(a["reden"], "input_onbekend:in_stedelijk_gebied")

    def test_zonder_machine_readable_blijft_onthouding(self):
        a = self.by_num["8.1"]
        self.assertEqual(a["status"], "onthouding")
        self.assertEqual(a["reden"], "geen_machine_readable_in_export")

    def test_engine_fout_wordt_gerapporteerd_niet_gefixt(self):
        a = self.by_num["9.9"]
        self.assertEqual(a["status"], "engineFout")
        self.assertIn("niet_bestaand", a["reden"])

    def test_tellingen_sluiten(self):
        t = self.toets["tellingen"]
        self.assertEqual(t, {
            "getoetst": 1, "scenario": 2, "onthouding": 2, "engineFout": 1,
            "formalizedInHit": 6, "artikelen": 6,
        })

    def test_scenario_loopt_nooit_onder_feitenlabel(self):
        # scenario-uitkomsten staan alleen onder 'runs', nooit bij status getoetst
        for a in self.toets["artikelen"]:
            if a["status"] == "scenario":
                self.assertNotIn("outputs", a)

    def test_deterministisch(self):
        self.assertEqual(_toets(), _toets())


class TestDocumentstructuurEnPakket(unittest.TestCase):
    def test_parse_documentstructuur(self):
        payload = {
            "_embedded": {
                "documentComponenten": [
                    {
                        "type": "LICHAAM",
                        "_embedded": {
                            "documentComponenten": [
                                {
                                    "type": "HOOFDSTUK",
                                    "_embedded": {
                                        "documentComponenten": [
                                            {
                                                "type": "ARTIKEL",
                                                "_embedded": {
                                                    "documentComponenten": [
                                                        {"type": "LID"},
                                                        {"type": "LID"},
                                                    ]
                                                },
                                            }
                                        ]
                                    },
                                }
                            ]
                        },
                    }
                ]
            }
        }
        from nldt.simulation.regelrecht.tpod.annotaties import (
            parse_documentstructuur,
        )

        d = parse_documentstructuur(payload)
        self.assertEqual(d["artikelen"], 1)
        self.assertEqual(d["leden"], 2)
        self.assertEqual(d["hoofdstukken"], 1)
        self.assertEqual(d["maxDiepte"], 3)
        self.assertEqual(d["componenten"], {
            "LICHAAM": 1, "HOOFDSTUK": 1, "ARTIKEL": 1, "LID": 2,
        })

    def test_pakket_extract_pons_en_gio(self):
        import io
        import zipfile

        from nldt.simulation.regelrecht.tpod import pakket

        ns_p = "https://standaarden.omgevingswet.overheid.nl/pons"
        ns_l = "https://standaarden.omgevingswet.overheid.nl/locatie"
        ow_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ow-dc:owObjecten xmlns:ow-dc="https://standaarden.omgevingswet.overheid.nl/ow-dc"
                  xmlns:pons="{ns_p}" xmlns:l="{ns_l}"
                  xmlns:xlink="http://www.w3.org/1999/xlink">
  <ow-dc:owObject>
    <pons:Pons>
      <pons:identificatie>nl.imow-gm0772.pons.p1</pons:identificatie>
      <pons:naam>bouwvlak Akkerslootweg</pons:naam>
      <pons:locatieaanduiding>
        <l:LocatieRef xlink:href="nl.imow-gm0772.gebied.g1"/>
      </pons:locatieaanduiding>
    </pons:Pons>
  </ow-dc:owObject>
  <ow-dc:owObject>
    <l:Gebied>
      <l:identificatie>nl.imow-gm0772.gebied.g1</l:identificatie>
    </l:Gebied>
  </ow-dc:owObject>
</ow-dc:owObjecten>"""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("OW-bestanden/pons.xml", ow_xml)
            z.writestr(
                "IO-11111111/nl.imow-gm0772.gebied.g1.gml", "<gml/>"
            )
            z.writestr("Regeling/Tekst.xml", "<tekst/>")
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="pakket-"))
        try:
            zip_path = tmp / "pakket.zip"
            zip_path.write_bytes(buf.getvalue())
            index = pakket.extract_pakket(zip_path)
            self.assertTrue(index["pons"]["beschikbaar"])
            self.assertEqual(index["pons"]["aantal"], 1)
            obj = index["pons"]["objecten"][0]
            self.assertEqual(obj["identificatie"], "nl.imow-gm0772.pons.p1")
            self.assertEqual(obj["locatieRefs"], ["nl.imow-gm0772.gebied.g1"])
            self.assertEqual(index["gio"], [{
                "bestand": "IO-11111111/nl.imow-gm0772.gebied.g1.gml",
                "locatieIdentificatie": "nl.imow-gm0772.gebied.g1",
            }])
            self.assertEqual(index["bestanden"], {"xml": 2, "gml": 1})
            schema = json.loads(
                (REGELRECHT_DIR / "tpod" / "punt-toets.schema.json").read_text()
            )  # schema-gelding van de index zelf:
            idx_schema = json.loads(
                (REGELRECHT_DIR / "tpod" / "tpod-index.schema.json").read_text()
            )
            # pons-sectie uit het pakket past in de tpod-index
            mini = _index()
            mini["pons"] = index["pons"]
            Draft202012Validator(idx_schema).validate(mini)
            self.assertTrue(schema)  # rookcheck: schema is geldige json
        finally:
            shutil.rmtree(tmp)

    def test_pakket_zonder_pons_geeft_opmerking(self):
        import io
        import zipfile

        from nldt.simulation.regelrecht.tpod import pakket

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(
                "OW-bestanden/activiteiten.xml",
                "<ow-dc:owObjecten xmlns:ow-dc='x'/>",
            )
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="pakket-leeg-"))
        try:
            zip_path = tmp / "pakket.zip"
            zip_path.write_bytes(buf.getvalue())
            index = pakket.extract_pakket(zip_path)
            self.assertFalse(index["pons"]["beschikbaar"])
            self.assertEqual(index["pons"]["aantal"], 0)
            self.assertIn("geen Pons", index["pons"]["opmerking"])
        finally:
            shutil.rmtree(tmp)


class TestGeo(unittest.TestCase):
    """Punt-in-polygoon tegen synthetische GIO-GML's (kans 1, eindstap)."""

    @staticmethod
    def _synthetische_gml(polygonen):
        delen = []
        for buiten, gaten in polygonen:
            ring = " ".join(f"{x} {y}" for x, y in buiten)
            holes = "".join(
                "<gml:interior><gml:LinearRing><gml:posList srsDimension=\"2\">"
                + " ".join(f"{x} {y}" for x, y in gat)
                + "</gml:posList></gml:LinearRing></gml:interior>"
                for gat in gaten
            )
            delen.append(
                "<gml:Polygon srsName=\"urn:ogc:def:crs:EPSG::28992\">"
                f"<gml:exterior><gml:LinearRing><gml:posList srsDimension=\"2\">"
                f"{ring}</gml:posList></gml:LinearRing></gml:exterior>"
                f"{holes}</gml:Polygon>"
            )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<geo:GeoInformatieObjectVaststelling '
            'xmlns:geo="https://standaarden.overheid.nl/stop/imop/geo/" '
            'xmlns:basisgeo="http://www.geostandaarden.nl/basisgeometrie/1.0" '
            'xmlns:gml="http://www.opengis.net/gml/3.2">'
            "<geo:vastgesteldeVersie><geo:locaties>"
            f"<geo:Locatie><geo:geometrie>{''.join(delen)}</geo:geometrie></geo:Locatie>"
            "</geo:locaties></geo:vastgesteldeVersie>"
            "</geo:GeoInformatieObjectVaststelling>"
        )

    def test_punt_in_polygoon_en_conflict(self):
        import io
        import zipfile as zipmod

        from nldt.simulation.regelrecht.tpod import geo

        vierkant = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        met_gat = (
            [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0), (0.0, 0.0)],
            [[(5.0, 5.0), (15.0, 5.0), (15.0, 15.0), (5.0, 15.0), (5.0, 5.0)]],
        )
        buf = io.BytesIO()
        with zipmod.ZipFile(buf, "w") as z:
            z.writestr(
                "IO-x/nl.imow-gm0772.gebied.vierkant.gml",
                self._synthetische_gml([(vierkant, [])]),
            )
            z.writestr(
                "IO-y/nl.imow-gm0772.gebiedengroep.gat.gml",
                self._synthetische_gml([met_gat]),
            )
            z.writestr(
                "IO-z/locaties_vrijenaam-v1.gml",
                self._synthetische_gml([(vierkant, [])]),
            )
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="geo-test-"))
        try:
            zip_path = tmp / "pakket.zip"
            zip_path.write_bytes(buf.getvalue())
            index = geo.geo_index_uit_pakket(zip_path)
            # vrijenaam telt als overgeslagen (geen IMOW-conventie)
            self.assertEqual(len(index["locaties"]), 2)
            self.assertEqual(index["overgeslagen"], 1)
            vierkant_shape = index["locaties"][
                "nl.imow-gm0772.gebied.vierkant"
            ]
            self.assertEqual(vierkant_shape["crs"],
                             "urn:ogc:def:crs:EPSG::28992")
            self.assertTrue(geo.bevat_punt(vierkant_shape["vorm"], (5.0, 5.0)))
            self.assertFalse(geo.bevat_punt(vierkant_shape["vorm"], (50.0, 50.0)))
            # gat: punt in het gat is níét covered
            gat_shape = index["locaties"]["nl.imow-gm0772.gebiedengroep.gat"]
            self.assertFalse(geo.bevat_punt(gat_shape["vorm"], (10.0, 10.0)))
            self.assertTrue(geo.bevat_punt(gat_shape["vorm"], (2.0, 2.0)))

            validatie = geo.valideer_punt(
                index,
                punt=(10.0, 10.0),  # binnen het gat van de tweede locatie
                geselecteerde_refs=["nl.imow-gm0772.gebied.vierkant"],
                hit_locaties=[
                    {
                        "identificatie": "nl.imow-gm0772.gebied.vierkant",
                        "noemer": None,
                        "geselecteerdOpPunt": True,
                    },
                    {
                        "identificatie": "nl.imow-gm0772.gebiedengroep.gat",
                        "noemer": "gatgebied",
                        "geselecteerdOpPunt": True,
                    },
                ],
            )
            self.assertEqual(validatie["validatie"]["getoetst"], 2)
            self.assertEqual(validatie["validatie"]["overeenstemming"], 1)
            self.assertEqual(len(validatie["validatie"]["conflicten"]), 1)
            self.assertEqual(
                validatie["validatie"]["conflicten"][0]["identificatie"],
                "nl.imow-gm0772.gebiedengroep.gat",
            )
        finally:
            shutil.rmtree(tmp)


    def test_naam_afstemming_utrecht_patroon(self):
        from nldt.simulation.regelrecht.tpod import geo

        af = geo.naam_afstemming(
            [{"naam": "Klein open bodemenergiesysteem"},
             {"naam": "Stedelijk gebied"}],
            [
                {"locatieIdentificatie":
                    "locaties_Kleinopenbodemenergiesysteem-v1"},
                {"locatieIdentificatie": "locaties_Stedelijkgebied-v1"},
                {"locatieIdentificatie": "locaties_Anderezone-v1"},
            ],
        )
        self.assertEqual(af["naamOvereenkomend"], 2)
        self.assertEqual(af["gebiedsaanwijzingenInHit"], 2)
        self.assertEqual(af["sweepGmls"], 3)

    def test_voorstel_makt_numeriek_en_scenario_getoetst(self):
        from nldt.simulation.regelrecht.tpod.toets import resolve_input

        ga = [{"naam": "Stedelijk gebied"}]
        params = {"bouwhoogte_m": 12, "strijd_met_tijdelijk_deel": False}
        res = resolve_input("bouwhoogte_m", gebiedsaanwijzingen=ga,
                            voorstel_params=params)
        self.assertEqual(res, {"bron": "voorstel", "waarde": 12})
        res = resolve_input("strijd_met_tijdelijk_deel", gebiedsaanwijzingen=ga,
                            voorstel_params=params)
        self.assertEqual(res, {"bron": "voorstel", "waarde": False})
        # zonder voorstelwaarde blijft de numerieke input onbekend
        res = resolve_input("bouwhoogte_m", gebiedsaanwijzingen=ga)
        self.assertEqual(res["bron"], "onbekend")

    def test_build_toets_met_voorstel_geeft_scorecard(self):
        toets = build_toets(
            instrument_id="eindhoven",
            instrument={"label": "Omgevingsplan gemeente Eindhoven",
                        "cvdr": "CVDR696400"},
            locatie={"id": "eindhoven-woensel-proxy"},
            tpod_index=_mini_index(),
            yaml_doc=_mini_yaml(),
            gegenereerd_op="2026-10-21T00:00:00+00:00",
            voorstel={
                "label": "demo",
                "parameters": {
                    "strijd_met_tijdelijk_deel": False,
                    "voorschriften_verbonden_voor_iwt": False,
                },
            },
        )
        # 10.2 (strijd + iwt) en 5.8 (verbod) worden nu allebei getoetst;
        # 5.8's verbodsveld zit niet in het voorstel -> blijft scenario
        self.assertEqual(toets["artikelen"][0]["status"], "getoetst") \
            if toets["artikelen"][0]["artikel"] == "6.8" else None
        statussen = {a["artikel"]: a["status"] for a in toets["artikelen"]}
        self.assertEqual(statussen["10.2"], "getoetst")
        self.assertEqual(statussen["5.8"], "scenario")
        self.assertIn("voorstel", toets)
        self.assertIn("scorecard", toets["voorstel"])


    def test_sweep_vindt_kantelpunten(self):
        from nldt.simulation.regelrecht.tpod.toets import bouw_sweep

        sweep = bouw_sweep(
            instrument_id="eindhoven",
            instrument={"label": "Omgevingsplan gemeente Eindhoven",
                        "cvdr": "CVDR696400"},
            locatie={"id": "eindhoven-woensel-proxy"},
            tpod_index=_mini_index(),
            yaml_doc=_mini_yaml(),
            gegenereerd_op="2026-10-21T00:00:00+00:00",
            voorstel={
                "label": "sweep-demo",
                "parameters": {
                    "strijd_met_tijdelijk_deel": False,
                    "voorschriften_verbonden_voor_iwt": False,
                    "activiteit_valt_onder_verbod": False,
                },
                "variaties": [
                    {"strijd_met_tijdelijk_deel": False},
                    {"strijd_met_tijdelijk_deel": True},
                ],
            },
        )
        self.assertEqual(sweep["aantalVarianten"], 2)
        # 10.2 (equivalentie-orakel) kantelt met strijd; 6.8 en 5.8 niet
        kantel = {k["artikel"] for k in sweep["kantelArtikelen"]}
        self.assertIn("10.2", kantel)
        self.assertNotIn("6.8", kantel)
        varianten = sweep["varianten"]
        self.assertEqual(varianten[0]["afgewezenArtikelen"], [])
        self.assertEqual(varianten[1]["afgewezenArtikelen"], ["10.2"])
        # 10.2 is in variant 1 waar (equivalentie houdt) en variant 2 onwaar
        self.assertEqual(varianten[0]["uitkomsten"]["onwaar"], 0)
        self.assertEqual(varianten[1]["uitkomsten"]["onwaar"], 1)


class TestCli(unittest.TestCase):
    """Rooktest: main() op een tmp-cache met synthetische annotaties.

    De joins (formalization-report, artikelen-export) komen uit de
    git-tracked full_export/out — deterministische committted data.
    """

    def test_bouwt_index_en_valideert(self):
        from nldt.simulation.regelrecht.tpod.__main__ import main

        tmp = pathlib.Path(tempfile.mkdtemp(prefix="tpod-test-"))
        try:
            stem = "eindhoven__eindhoven-woensel-proxy"
            (tmp / f"{stem}.annotaties.json").write_text(
                json.dumps(_payload()), encoding="utf-8"
            )
            (tmp / f"{stem}.annotaties.meta.json").write_text(
                json.dumps({"sha256": "cd" * 32, "fetchedAt": "2026-10-19T16:12:44Z"}),
                encoding="utf-8",
            )
            rc = main([
                "--instruments", "eindhoven",
                "--cache-dir", str(tmp),
                "--out-dir", str(tmp),
            ])
            self.assertEqual(rc, 0)
            out = tmp / f"{stem}.tpod-index.json"
            self.assertTrue(out.is_file())
            index = json.loads(out.read_text(encoding="utf-8"))
            schema = json.loads(
                (REGELRECHT_DIR / "tpod" / "tpod-index.schema.json").read_text()
            )
            Draft202012Validator(schema).validate(index)
            self.assertFalse(index["pons"]["beschikbaar"])
            # joins op de echte exports: 10.2 zit in payload én in report
            profielen = {p["artikel"]: p for p in index["artikelProfielen"]}
            self.assertTrue(profielen["10.2"]["formalized"])
            self.assertEqual(index["hitCoverage"]["pocArtikelenInHit"], 2)
        finally:
            shutil.rmtree(tmp)

    def test_mist_cache_is_duidelijke_fout(self):
        from nldt.simulation.regelrecht.tpod.__main__ import main

        tmp = pathlib.Path(tempfile.mkdtemp(prefix="tpod-leeg-"))
        try:
            with self.assertRaises(SystemExit) as ctx:
                main([
                    "--instruments", "eindhoven",
                    "--cache-dir", str(tmp),
                    "--out-dir", str(tmp),
                ])
            self.assertIn("cache mist", str(ctx.exception))
        finally:
            shutil.rmtree(tmp)

    def test_toets_rooktest_op_echte_exporten(self):
        from nldt.simulation.regelrecht.tpod.__main__ import main

        tmp = pathlib.Path(tempfile.mkdtemp(prefix="tpod-toets-"))
        try:
            stem = "eindhoven__eindhoven-woensel-proxy"
            (tmp / f"{stem}.annotaties.json").write_text(
                json.dumps(_payload()), encoding="utf-8"
            )
            (tmp / f"{stem}.annotaties.meta.json").write_text(
                json.dumps({"sha256": "cd" * 32, "fetchedAt": "2026-10-19T16:12:44Z"}),
                encoding="utf-8",
            )
            rc = main([
                "--instruments", "eindhoven",
                "--cache-dir", str(tmp),
                "--out-dir", str(tmp),
                "--toets",
            ])
            self.assertEqual(rc, 0)
            toets = json.loads(
                (
                    tmp / "eindhoven__eindhoven-woensel-proxy.toets.json"
                ).read_text(encoding="utf-8")
            )
            schema = json.loads(
                (REGELRECHT_DIR / "tpod" / "punt-toets.schema.json").read_text()
            )
            Draft202012Validator(schema).validate(toets)
            t = toets["tellingen"]
            # op de synthetische cache: alleen 10.2 en 22.1 in de hit; beide
            # formalized met uitsluitend scenariovelden (strijd / strijd+iwt)
            self.assertEqual(t["formalizedInHit"], 2)
            self.assertEqual(t["getoetst"], 0)
            self.assertEqual(t["scenario"], 2)
            self.assertEqual(t["onthouding"], 0)
            self.assertEqual(t["engineFout"], 0)
            # 10.2 heeft twee scenariovelden -> 4 combinaties
            art102 = next(
                a for a in toets["artikelen"] if a["artikel"] == "10.2"
            )
            self.assertEqual(len(art102["runs"]), 4)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
