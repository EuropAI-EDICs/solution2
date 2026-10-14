"""Integriteits-suite voor de vendored DigitalPlanning_Indicators-datasect.

Draait onder unittest én pytest, puur stdlib, offline:

    python3 -m unittest planning_indicators.tests.test_dataset

Verwachtingen (release v1.2, upstream-commit b81ebfa) zijn de bij vendoring
gemeten rij-aantallen; een upgrade van de dataset maakt een gerichte
bijwerking van EXPECTED_ROWS nodig — bewust, zodat versiesprongen niet
onopgemerkt doorglippen.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from planning_indicators import (  # noqa: E402
    AUTHORS,
    CITATION,
    DOI,
    FOREIGN_KEYS,
    LICENSE,
    SECTORS,
    SOURCE_URL,
    TABLES,
    UPSTREAM_COMMIT,
    VERSION,
    indicator_papers,
    indicators,
    load_all,
    load_table,
    papers_for_indicator,
    search,
    strip_html,
    validate,
)

# Bij vendoring gemeten rij-aantallen (release v1.2).
EXPECTED_ROWS = {
    "indicators": 280,
    "main_table": 1608,
    "paper": 560,
    "objective": 17,
    "topic": 7,
    "planning_sector": 3,
    "system_parts": 19,
    "countries": 222,
    "region": 9,
    "income_type": 5,
}


class ProvenanceTest(unittest.TestCase):
    def test_provenance_constanten_compleet(self):
        self.assertEqual(VERSION, "1.2")
        self.assertEqual(DOI, "10.5281/zenodo.17464468")
        self.assertEqual(UPSTREAM_COMMIT, "b81ebfad3c3a3fa6f90ec44cfb95455cc90ba5fa")
        self.assertEqual(LICENSE, "CC-BY-NC-SA-4.0")
        self.assertTrue(SOURCE_URL.startswith("https://github.com/"))
        self.assertEqual(len(AUTHORS), 4)

    def test_citation_noemt_authors_doi_en_licentie(self):
        for fragment in ("Cardenas-Leon", DOI, LICENSE):
            self.assertIn(fragment, CITATION)


class DatasetIntegriteitTest(unittest.TestCase):
    def setUp(self):
        self.tables = load_all()

    def test_alle_tien_tabellen_aanwezig(self):
        self.assertEqual(set(self.tables), set(TABLES))

    def test_rij_aantallen_bij_vendoring(self):
        for name, expected in EXPECTED_ROWS.items():
            self.assertEqual(
                len(self.tables[name]),
                expected,
                f"tabel {name}: rij-aantal wijkt af van v1.2 — dataset geüpdatet?",
            )

    def test_pk_uniek_en_gevuld(self):
        for name, rows in self.tables.items():
            ids = [row["ID"] for row in rows]
            self.assertTrue(all(i not in (None, "") for i in ids), f"{name}: lege ID")
            self.assertEqual(len(ids), len(set(ids)), f"{name}: dubbele ID's")

    def test_fk_integriteit_via_validate(self):
        self.assertEqual(validate(), [])

    def test_kolom_set_per_tabel_stabiel(self):
        verwacht = {
            "indicators": {"Indicator", "Definition", "System Part", "Units", "Calculation", "ID", "Objective", "Comment"},
            "main_table": {"ID", "IndicatorName", "Lookup Paper", "Comment"},
            "paper": {"ID", "ZoteroID", "Title", "Year", "Country"},
            "objective": {"Objective", "ID", "Topic"},
            "topic": {"IndicatorTopic", "ID", "Sector"},
            "planning_sector": {"ID", "Sector"},
            "system_parts": {"ID", "System Part"},
            "countries": {"ID", "Country", "Code", "Region_ID", "IncomeType_ID"},
            "region": {"Region", "ID"},
            "income_type": {"Income group", "ID"},
        }
        for name, columns in verwacht.items():
            self.assertEqual(set(self.tables[name][0].keys()), columns)


class JoinsTest(unittest.TestCase):
    def test_iedere_indicator_heeft_sector(self):
        joined = indicators()
        self.assertEqual(len(joined), EXPECTED_ROWS["indicators"])
        zonder = [ind for ind in joined if ind["sector_id"] is None]
        self.assertEqual(zonder, [])

    def test_sectoren_zijn_de_drie_upstream_sectoren(self):
        sectoren = {ind["sector"] for ind in indicators()}
        self.assertEqual(sectoren, {"Water Supply", "Urban Heat Stress", "Housing Provision"})
        self.assertEqual(SECTORS, {"water": 1, "heat": 2, "housing": 3})

    def test_papers_for_indicator_resolver(self):
        refs = papers_for_indicator(75)  # "Reused water"
        self.assertTrue(refs)
        for ref in refs:
            self.assertIn("id", ref)
            self.assertIn("year", ref)
            self.assertNotIn("<", ref["title"], "HTML niet gestript")

    def test_indicator_papers_dekt_main_table(self):
        links = indicator_papers()
        self.assertEqual(len(links), EXPECTED_ROWS["main_table"])

    def test_search_met_en_zonder_sectorfilter(self):
        hits = search("heat", sector="heat")
        self.assertTrue(hits)
        self.assertTrue(all(ind["sector_id"] == 2 for ind in hits))
        alles = search("water")
        self.assertTrue(alles)

    def test_onbekende_tabel_geeft_keyerror(self):
        with self.assertRaises(KeyError):
            load_table("bestaat_niet")


class QuirksTest(unittest.TestCase):
    def test_strip_html(self):
        self.assertEqual(strip_html("<div>Hello world</div>"), "Hello world")
        self.assertEqual(strip_html("A &amp; B"), "A & B")
        self.assertIsNone(strip_html(None))
        self.assertEqual(strip_html(""), "")

    def test_spookkolom_is_verworpen(self):
        row = load_table("indicators")[0]
        self.assertNotIn(None, row)

    def test_fk_kolommen_float_geformatteerd(self):
        # upstream slaat FK's op als "12.0"; joins moeten dat aan kunnen
        raw = load_table("indicators")[0]
        self.assertEqual(raw["System Part"], "12.0")


if __name__ == "__main__":
    unittest.main()
