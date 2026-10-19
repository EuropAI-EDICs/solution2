# nldt/tests/test_simulation_regelrecht_full.py
"""Tests volle RegelRecht-instrument-export (spec 2026-10-14)."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FULL = ROOT / "nldt" / "simulation" / "regelrecht" / "full_export"
sys.path.insert(0, str(FULL))

from split_cvdr_html import split_instrument, write_articles_json  # noqa: E402
import paths  # noqa: E402


class TestArticleSplitter(unittest.TestCase):
    def test_utrecht_contains_art_5_3(self):
        arts = split_instrument("utrecht")
        by_num = {a["number"]: a for a in arts}
        self.assertIn("5.3", by_num)
        self.assertIn("kleine windturbine", by_num["5.3"]["text"].lower())
        self.assertGreater(len(arts), 100)

    def test_eindhoven_contains_art_10_2_and_22_1(self):
        arts = split_instrument("eindhoven")
        nums = {a["number"] for a in arts}
        self.assertIn("10.2", nums)
        self.assertIn("22.1", nums)
        self.assertGreater(len(arts), 500)

    def test_articles_json_roundtrip_sha(self):
        arts = split_instrument("utrecht")[:3]
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "u.json"
            write_articles_json("utrecht", arts, out)
            data = json.loads(out.read_text())
            self.assertEqual(data["poc"], "utrecht")
            self.assertEqual(
                data["sourceSha256"],
                hashlib.sha256(paths.HTML_UTRECHT.read_bytes()).hexdigest(),
            )
            self.assertEqual(len(data["articles"]), 3)


class TestEvidenceAligner(unittest.TestCase):
    def test_utrecht_5_3_links_nc_w_03_and_fr_w_03(self):
        from align_evidence import align

        arts = split_instrument("utrecht")
        by_num, orphans = align("utrecht", arts)
        a = by_num["5.3"]
        nc_ids = {c["id"] for c in a["normCards"]}
        fr_ids = {r["id"] for r in a["formalRules"]}
        self.assertIn("NC-W-03", nc_ids)
        self.assertIn("FR-W-03", fr_ids)

    def test_eindhoven_10_2_links_doelregel(self):
        from align_evidence import align

        arts = split_instrument("eindhoven")
        by_num, _ = align("eindhoven", arts)
        self.assertTrue(
            any(
                d.get("locator", {}).get("artikel") == "10.2"
                for d in by_num["10.2"]["doelRegels"]
            )
        )

    def test_normalize_article_ref(self):
        from align_evidence import normalize_article_ref

        self.assertEqual(normalize_article_ref("art. 5.3, eerste lid"), "5.3")
        self.assertEqual(normalize_article_ref("Artikel 22.1"), "22.1")
        self.assertIsNone(normalize_article_ref("par. Duurzame energie"))


class TestFormalizer(unittest.TestCase):
    def test_fr_w_03_produces_machine_readable(self):
        from align_evidence import align
        from formalize_to_rr import formalize

        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        by_num, report = formalize("utrecht", arts, al, orphans)
        self.assertEqual(by_num["5.3"]["status"], "formalized")
        self.assertIsNotNone(by_num["5.3"]["machineReadable"])
        self.assertIn(
            "toegestaan_kleine_windturbine",
            str(by_num["5.3"]["machineReadable"]),
        )

    def test_ambiguous_has_no_mr(self):
        from align_evidence import align
        from formalize_to_rr import formalize

        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        by_num, report = formalize("utrecht", arts, al, orphans)
        self.assertGreaterEqual(
            report["counts"]["ambiguous"] + report["counts"]["unmatched"], 1
        )
        for art in report["articles"]:
            if art["status"] in ("ambiguous", "rejected", "unmatched"):
                self.assertIsNone(by_num[art["number"]].get("machineReadable"))

    def test_report_counts_sum_to_articles(self):
        from align_evidence import align
        from formalize_to_rr import formalize

        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        _, report = formalize("utrecht", arts, al, orphans)
        c = report["counts"]
        self.assertEqual(
            sum(c[k] for k in ("formalized", "ambiguous", "rejected", "unmatched")),
            len(arts),
        )


class TestEindhovenTemplates(unittest.TestCase):
    def test_bouwhoogte_article_formalized(self):
        from align_evidence import align
        from formalize_to_rr import formalize

        arts = split_instrument("eindhoven")
        al, orphans = align("eindhoven", arts)
        by_num, _ = formalize("eindhoven", arts, al, orphans)
        self.assertEqual(by_num["6.19"]["status"], "formalized")
        mr = by_num["6.19"]["machineReadable"]
        self.assertIsNotNone(mr)
        self.assertIn("bouwhoogte_m", str(mr))
        self.assertEqual(by_num["6.19"]["source"], "eindhoven-doel-template")

    def test_verbod_article_formalized(self):
        from align_evidence import align
        from formalize_to_rr import formalize

        arts = split_instrument("eindhoven")
        al, orphans = align("eindhoven", arts)
        by_num, _ = formalize("eindhoven", arts, al, orphans)
        self.assertEqual(by_num["3.13"]["status"], "formalized")
        self.assertIn("activiteit_valt_onder_verbod", str(by_num["3.13"]["machineReadable"]))

    def test_sterk_omzet_gives_equivalentie(self):
        from align_evidence import align
        from formalize_to_rr import formalize

        arts = split_instrument("eindhoven")
        al, orphans = align("eindhoven", arts)
        by_num, _ = formalize("eindhoven", arts, al, orphans)
        # 22.1 is smoke-linked via OT-001; bron side should get template or smoke path.
        # Doel 1.5 is a classic kennisbank "komt in de plaats van" pair (KB).
        self.assertEqual(by_num["1.5"]["status"], "formalized")
        self.assertIn("equivalentie", by_num["1.5"]["source"])

    def test_conflicting_limits_ambiguous(self):
        from eindhoven_templates import _try_limit_or_verbod

        text = (
            "De maximum bouwhoogte bedraagt 5 m. "
            "In afwijking daarvan bedraagt de bouwhoogte maximaal 10 m."
        )
        hit = _try_limit_or_verbod(text, "9.99", source="test")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["status"], "ambiguous")
        self.assertIsNone(hit["machineReadable"])

    def test_eindhoven_formalized_coverage_at_least_50(self):
        from align_evidence import align
        from formalize_to_rr import formalize

        arts = split_instrument("eindhoven")
        al, orphans = align("eindhoven", arts)
        _, report = formalize("eindhoven", arts, al, orphans)
        self.assertGreaterEqual(report["counts"]["formalized"], 50)


class TestWriter(unittest.TestCase):
    def test_yaml_schema_valid_and_53_has_mr(self):
        import yaml
        from jsonschema import Draft202012Validator
        from align_evidence import align
        from formalize_to_rr import formalize
        from write_instrument_yaml import write_instrument_yaml

        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        form, report = formalize("utrecht", arts, al, orphans)
        path = write_instrument_yaml(
            "utrecht", arts, form, stamp="2026-10-14T00:00:00Z", report=report
        )
        doc = yaml.safe_load(path.read_text())
        schema = json.loads(
            (
                ROOT / "nldt/simulation/regelrecht/schema/regelrecht-v0.7.1.schema.json"
            ).read_text()
        )
        Draft202012Validator(schema).validate(doc)
        art53 = next(a for a in doc["articles"] if a["number"] == "5.3")
        self.assertIn("machine_readable", art53)
        ambiguous_nums = {
            r["number"] for r in report["articles"] if r["status"] == "ambiguous"
        }
        for a in doc["articles"]:
            if a["number"] in ambiguous_nums:
                self.assertNotIn("machine_readable", a)


class TestDemoBuild(unittest.TestCase):
    def test_demo_contains_index_and_coverage(self):
        from build_full_demo import build_demo

        build_demo(stamp="2026-10-14T00:00:00Z")
        html = (ROOT / "nldt/simulation/regelrecht-demo.html").read_text()
        self.assertNotIn("__INDEX_UTRECHT__", html)
        self.assertIn("article-select", html)
        self.assertIn("formalized", html.lower())
        self.assertIn('"number": "5.3"', html)


class TestBuildAll(unittest.TestCase):
    def test_idempotent_stamp(self):
        import subprocess

        cmd = [
            str(ROOT / "nldt/.venv/bin/python"),
            str(FULL / "build_all.py"),
            "--stamp",
            "2026-10-14T12:00:00Z",
        ]
        subprocess.check_call(cmd, cwd=ROOT)
        u1 = (FULL / "out/utrecht-cvdr704250.yaml").read_bytes()
        subprocess.check_call(cmd, cwd=ROOT)
        u2 = (FULL / "out/utrecht-cvdr704250.yaml").read_bytes()
        self.assertEqual(u1, u2)

    def test_smoke_articles_still_in_legacy_runs(self):
        import subprocess

        subprocess.check_call(
            [
                str(ROOT / "nldt/.venv/bin/python"),
                str(ROOT / "nldt/simulation/regelrecht/build_runs.py"),
                "--stamp",
                "2026-10-14T12:00:00Z",
            ],
            cwd=ROOT,
        )


if __name__ == "__main__":
    unittest.main()
