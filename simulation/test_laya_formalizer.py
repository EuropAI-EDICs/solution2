# simulation/test_laya_formalizer.py
"""Tests voor de laya_formalizer-dataset (PLAN_LAYA_INZET.md, Inzet A).

Offline: leest de gecommitte full_export-artefacten; geen laya/torch nodig.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
NLDT_PY = ROOT / "nldt" / ".venv" / "bin" / "python"
BUILDER = HERE / "laya_formalizer" / "build_dataset.py"


class DatasetTest(unittest.TestCase):
    def _build(self, mode: str, tmp: pathlib.Path) -> dict:
        uit = subprocess.run(
            [str(NLDT_PY), str(BUILDER), "--mode", mode, "--out-dir", str(tmp)],
            capture_output=True, text=True, check=True,
        )
        print(uit.stdout)
        return {
            naam: [json.loads(l) for l in (tmp / f"{naam}.jsonl").read_text("utf-8").splitlines() if l]
            for naam in ("train", "eval", "meta")
        }

    def test_holdout_totaal_en_geen_leak(self):
        with tempfile.TemporaryDirectory() as d:
            d = self._build("holdout", pathlib.Path(d))
            self.assertEqual(len(d["train"]) + len(d["eval"]), 1074 + 427)
            seen = {}
            for split in ("train", "eval"):
                for r in d[split]:
                    key = (r["state"]["instrument"], r["state"]["artikel"])
                    self.assertNotIn(key, seen, f"artikel in beide splits: {key}")
                    seen[key] = split

    def test_cross_is_kruisinstrument(self):
        with tempfile.TemporaryDirectory() as d:
            d = self._build("cross", pathlib.Path(d))
            self.assertEqual({r["state"]["instrument"] for r in d["eval"]}, {"utrecht"})
            self.assertEqual(len(d["eval"]), 427)
            self.assertEqual({r["state"]["instrument"] for r in d["train"]}, {"eindhoven"})

    def test_gold_alleen_uit_report(self):
        with tempfile.TemporaryDirectory() as d:
            d = self._build("holdout", pathlib.Path(d))
            for r in d["train"] + d["eval"]:
                for status in r["gold"]["voorspelde_status"]["probabilities"]:
                    self.assertIn(status, r["questions"]["voorspelde_status"]["criteria"])
                ev = r["gold"]["heeft_evidence"]["probabilities"]
                self.assertAlmostEqual(sum(ev.values()), 1.0, places=5)

    def _build_bijscholing(self, tmp: pathlib.Path, sample: int) -> dict:
        uit = subprocess.run(
            [str(NLDT_PY), str(BUILDER), "--mode", "bijscholing", "--sample", str(sample),
             "--out-dir", str(tmp)],
            capture_output=True, text=True, check=True,
        )
        print(uit.stdout)
        return {
            naam: [json.loads(l) for l in (tmp / f"{naam}.jsonl").read_text("utf-8").splitlines() if l]
            for naam in ("train", "eval")
        }

    def test_bijscholing_steekproef(self):
        for sample in (50, 150):
            with tempfile.TemporaryDirectory() as d:
                d = self._build_bijscholing(pathlib.Path(d), sample)
                utrein = [r for r in d["train"] if r["state"]["instrument"] == "utrecht"]
                self.assertEqual(len(utrein), sample)
                self.assertEqual(len(d["train"]), 1074 + sample)
                # eval = de rest van utrecht, geen overlap met de steekproef
                self.assertEqual(len(d["eval"]), 427 - sample)
                self.assertEqual(
                    {r["state"]["instrument"] for r in d["eval"]}, {"utrecht"}
                )
                getraind = {r["state"]["artikel"] for r in utrein}
                self.assertFalse(
                    getraind & {r["state"]["artikel"] for r in d["eval"]}
                )

    def test_bijscholing_deterministisch(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            a = self._build_bijscholing(pathlib.Path(d1), 50)
            b = self._build_bijscholing(pathlib.Path(d2), 50)
            self.assertEqual(
                sorted(r["state"]["artikel"] for r in a["train"] if r["state"]["instrument"] == "utrecht"),
                sorted(r["state"]["artikel"] for r in b["train"] if r["state"]["instrument"] == "utrecht"),
            )

    def _build_derde(self, tmp: pathlib.Path, sample: int) -> dict:
        uit = subprocess.run(
            [str(NLDT_PY), str(BUILDER), "--mode", "derde", "--sample", str(sample),
             "--out-dir", str(tmp)],
            capture_output=True, text=True, check=True,
        )
        print(uit.stdout)
        return {
            naam: [json.loads(l) for l in (tmp / f"{naam}.jsonl").read_text("utf-8").splitlines() if l]
            for naam in ("train", "eval")
        }

    def test_derde_instrument_veenendaal(self):
        with tempfile.TemporaryDirectory() as d:
            d = self._build_derde(pathlib.Path(d), 160)
            vd_train = [r for r in d["train"] if r["state"]["instrument"] == "veenendaal"]
            vd_eval = [r for r in d["eval"] if r["state"]["instrument"] == "veenendaal"]
            # productiebasis volledig + steekproef erbij; rest = eval
            self.assertEqual(len(d["train"]), 1074 + 427 + 160)
            self.assertEqual(len(vd_train), 160)
            self.assertEqual(len(d["eval"]), 485 - 160)
            self.assertEqual(
                {r["state"]["instrument"] for r in d["eval"]}, {"veenendaal"}
            )
            self.assertFalse(
                {r["state"]["artikel"] for r in vd_train}
                & {r["state"]["artikel"] for r in vd_eval}
            )

    def test_veenendaal_labels_zijn_template_deterministisch(self):
        from collections import Counter
        with tempfile.TemporaryDirectory() as d:
            d = self._build_derde(pathlib.Path(d), 160)
            stat = Counter(
                max(r["gold"]["voorspelde_status"]["probabilities"],
                    key=r["gold"]["voorspelde_status"]["probabilities"].get)
                for r in d["train"] + d["eval"]
                if r["state"]["instrument"] == "veenendaal"
            )
            # vastgepind op de gecommitte HTML: 43 template-formalized, 4 ambiguous,
            # 438 unmatched — bijdrift = bron- of templatewijziging, nooit stil
            self.assertEqual(dict(stat), {"formalized": 43, "ambiguous": 4, "unmatched": 438})


if __name__ == "__main__":
    unittest.main()
