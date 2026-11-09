# nldt/tests/test_simulation_corpus_export.py
"""Tests voor de corpus-staging (MAPPING_DSO_NAAR_REGELRECHT.md, fase 1).

Offline en deterministisch: levert op de gecommitte full-export onder
nldt/simulation/regelrecht/full_export/out/. Padconventie conform het
HHNK-precedent in NederlandseDigitaleDienst/regelrecht-corpus
(regulation/nl/<laag>/<slug>/<valid_from>.yaml + status.yaml).
"""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

from nldt.simulation.regelrecht import corpus_export  # noqa: E402
from nldt.simulation.regelrecht.dso_overlap.instruments import INSTRUMENTS  # noqa: E402

# (relatief pad, totaal artikelen, formalized) — zelfde totalen als
# POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md en de full-export-tests.
_VERWACHT = {
    "eindhoven": (
        "regulation/nl/gemeentelijke_verordening/"
        "omgevingsplan_gemeente_eindhoven/2026-06-29.yaml",
        1074,
        567,
    ),
    "utrecht": (
        "regulation/nl/provinciale_verordening/"
        "omgevingsverordening_provincie_utrecht/2025-10-13.yaml",
        427,
        60,
    ),
}


class CorpusExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = pathlib.Path(cls.tmp.name)
        cls.validator = Draft202012Validator(
            json.loads(corpus_export.SCHEMA_PATH.read_text(encoding="utf-8"))
        )
        cls.regs = {
            iid: corpus_export._stage_instrument(
                iid,
                out_dir=cls.out,
                validator=cls.validator,
                stamp="2026-11-08T00:00:00+00:00",
            )
            for iid in _VERWACHT  # alléén de PoC's met volle export (geen RTR-only)
        }

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_padconventie_en_aantallen(self):
        for iid, (rel, artikelen, formalized) in _VERWACHT.items():
            rec = self.regs[iid]
            self.assertEqual(rec["pad"], rel)
            self.assertEqual(rec["artikelen"], artikelen)
            self.assertEqual(rec["formalized"], formalized)
            self.assertTrue((self.out / rel).is_file())

    def test_staging_is_byteidentiek_en_schema_valide(self):
        for iid, (rel, _, _) in _VERWACHT.items():
            bron = INSTRUMENTS[iid]["instrument_yaml"]
            self.assertEqual(
                (self.out / rel).read_bytes(), bron.read_bytes(), iid
            )
            doc = yaml.safe_load((self.out / rel).read_text(encoding="utf-8"))
            self.assertEqual(
                list(self.validator.iter_errors(doc)), [], f"{iid} schema-ongeldig"
            )

    def test_status_yaml_is_poc_export_met_provenance(self):
        for iid, (rel, _, _) in _VERWACHT.items():
            status = yaml.safe_load(
                (self.out / rel).parent.joinpath("status.yaml").read_text("utf-8")
            )
            self.assertEqual(status["status"], "poc_export")
            self.assertIn("CVDR", status["law_id"])
            self.assertEqual(len(status["slug"]), len(status["slug"].strip()))
            self.assertTrue(status["bron_sha256"])
            self.assertGreater(status["article_count"], 0)


if __name__ == "__main__":
    unittest.main()
