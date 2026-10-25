"""Harness-lab motor: loaders, evidence, verdict, adoptie (offline).

De lab-motor zelf kent geen adapters of modellen; die worden geïnjecteerd.
Hier worden alleen de contracten getest: luide loaders, score/verdict-
regels, canon-determinisme en de adoptiepoort (geen pass-geen adoptie,
geen fake-zonder-toestemming, precies één actief per target).
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament import harnesslab as hl  # noqa: E402

VAST = datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc)

REGISTER = {
    "poc": "testpoc",
    "harnesses": [
        {"id": "prompt-basis", "title": "Basisprompt", "component": "prompt",
         "target": "poc/alpha", "riskLevel": "low", "version": "1.0.0",
         "status": "actief",
         "artifact": {"kind": "promptFile", "path": "prompts/alpha.md",
                      "sha256": "0" * 64}},
        {"id": "pin-basis", "title": "Basispin", "component": "modelPin",
         "target": "subagent", "riskLevel": "low", "version": "1.0.0",
         "status": "actief",
         "artifact": {"kind": "envPin", "env": {"DEEP_AGENT_SUBMODEL": "test:1b"}}},
    ],
}


def _schrijf(td: Path, naam: str, doc) -> Path:
    p = Path(td) / naam
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


class TestLoaders(unittest.TestCase):
    def test_geldig_register_laadt(self):
        with tempfile.TemporaryDirectory() as td:
            reg = hl.load_harness_register(_schrijf(Path(td), "r.json", REGISTER))
            self.assertEqual(reg["poc"], "testpoc")

    def test_meerdere_actief_per_target_is_fout(self):
        bad = json.loads(json.dumps(REGISTER))
        bad["harnesses"].append(dict(bad["harnesses"][0], id="prompt-basis-2"))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(hl.HarnessLabError, "meerdere actieve"):
                hl.load_harness_register(_schrijf(Path(td), "r.json", bad))

    def test_dubbele_ids_zijn_fout(self):
        bad = json.loads(json.dumps(REGISTER))
        bad["harnesses"][1]["id"] = "prompt-basis"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(hl.HarnessLabError, "dubbele ids"):
                hl.load_harness_register(_schrijf(Path(td), "r.json", bad))

    def test_ongeldige_status_is_fout(self):
        bad = json.loads(json.dumps(REGISTER))
        bad["harnesses"][0]["status"] = "misschien"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(hl.HarnessLabError):
                hl.load_harness_register(_schrijf(Path(td), "r.json", bad))


VARIANT = {
    "id": "prompt-kort",
    "title": "Kortere prompt",
    "components": [
        {"type": "prompt", "target": "poc/alpha", "path": "files/alpha-v2.md"},
        {"type": "modelPin", "target": "subagent", "env": {"DEEP_AGENT_SUBMODEL": "test:3b"}},
    ],
}

TASKSET = {
    "id": "taskset-test",
    "adapter": "deepagents",
    "tasks": [
        {"id": "t1", "kind": "static",
         "expect": [{"check": "slotgateForbids",
                     "value": {"agent": "alpha", "tools": ["geheime_tool"]}}]},
    ],
}


class _Inrichting(unittest.TestCase):
    """Gedeelde inrichting: register + variant-prompt + taskset op disk."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        td = Path(self._td.name)
        self.td = td
        (td / "prompts").mkdir()
        (td / "prompts" / "alpha.md").write_text("basisprompt\n", encoding="utf-8")
        (td / "files").mkdir()
        (td / "files" / "alpha-v2.md").write_text("kortere prompt\n", encoding="utf-8")
        self.register_pad = _schrijf(td, "harnessregister.json", REGISTER)
        self.variant_pad = _schrijf(td, "variant.json", VARIANT)
        self.taskset_pad = _schrijf(td, "taskset.json", TASKSET)

    def tearDown(self):
        self._td.cleanup()

    def _evidence(self, *, verdict="pass", mode="llm", variant_pad=None):
        variant_pad = variant_pad or self.variant_pad
        variant = hl.load_variant(variant_pad)
        taskset = hl.load_taskset(self.taskset_pad)
        ev = hl.new_evidence(
            variant=variant, variant_path=variant_pad,
            taskset=taskset, taskset_path=self.taskset_pad,
            adapter="deepagents", mode=mode,
            probe_id="probe-vast", started_at=VAST.isoformat())
        hl.record_task(ev, task_id="t1", kind="static", checks=[
            {"check": "slotgateForbids", "pass": verdict == "pass",
             "detail": "vast", "hard": False}])
        ev["runDir"] = str(self.td / "probe-uit")
        hl.finalize_evidence(ev, duration_s=1.5)
        uit = self.td / "probe-uit"
        hl.write_evidence(ev, uit)
        return uit / hl.EVIDENCE_FILENAME


class TestEvidence(_Inrichting):
    def test_verdict_pass_bij_alle_checks_pass(self):
        ev = hl.load_evidence(self._evidence(verdict="pass"))
        self.assertEqual(ev["verdict"], "pass")
        self.assertEqual(ev["score"], {"passed": 1, "total": 1, "hardViolations": []})

    def test_verdict_fail_bij_gezakte_check(self):
        ev = hl.load_evidence(self._evidence(verdict="fail"))
        self.assertEqual(ev["verdict"], "fail")
        self.assertEqual(ev["score"]["passed"], 0)

    def test_harde_schending_komt_in_de_score(self):
        variant = hl.load_variant(self.variant_pad)
        taskset = hl.load_taskset(self.taskset_pad)
        ev = hl.new_evidence(
            variant=variant, variant_path=self.variant_pad,
            taskset=taskset, taskset_path=self.taskset_pad,
            adapter="deepagents", mode="fake",
            probe_id="probe-vast", started_at=VAST.isoformat())
        hl.record_task(ev, task_id="t1", kind="static", checks=[
            {"check": "slotgateForbids", "pass": False, "detail": "lekt", "hard": True}])
        hl.finalize_evidence(ev)
        self.assertEqual(ev["score"]["hardViolations"], ["t1:slotgateForbids"])
        self.assertEqual(ev["verdict"], "fail")

    def test_evidence_is_canon_deterministisch(self):
        pad = self._evidence()
        a = hl.canon_evidence(hl.load_evidence(pad))
        b = hl.canon_evidence(hl.load_evidence(pad))
        self.assertEqual(
            json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertNotIn("probeId", a)
        self.assertNotIn("durationS", a)


class TestRapport(_Inrichting):
    def test_rapport_is_byte_deterministisch(self):
        ev1 = hl.load_evidence(self._evidence(verdict="pass"))
        ev2 = hl.load_evidence(self._evidence(verdict="fail", mode="fake"))
        r1 = hl.render_probe_report([ev1, ev2])
        r2 = hl.render_probe_report([ev1, ev2])
        self.assertEqual(r1, r2)
        self.assertIn("prompt-kort | llm | pass | 1/1", r1)
        self.assertIn("prompt-kort | fake | fail | 0/1", r1)


class TestAdoptie(_Inrichting):
    def test_adoptie_promoveert_en_werpt_voorganger_af(self):
        pad = self._evidence(verdict="pass", mode="llm")
        hl.adopt_register(
            register_path=self.register_pad, variant_path=self.variant_pad,
            evidence_path=pad, now=VAST)
        reg = hl.load_harness_register(self.register_pad)
        by_id = {h["id"]: h for h in reg["harnesses"]}
        self.assertEqual(by_id["prompt-basis"]["status"], "verworpen")
        nieuw = by_id["prompt-kort-poc-alpha"]
        self.assertEqual(nieuw["status"], "actief")
        self.assertEqual(nieuw["adoptedFrom"], "prompt-basis")
        self.assertEqual(nieuw["artifact"]["sha256"],
                         hl.sha256_file(self.td / "files" / "alpha-v2.md"))
        self.assertEqual(len(nieuw["probeEvidence"]), 1)
        self.assertEqual(nieuw["probeEvidence"][0]["mode"], "llm")
        # adoptie schrijft de varianttekst door naar het live promptbestand
        self.assertEqual(
            (self.td / "prompts" / "alpha.md").read_text(encoding="utf-8"),
            "kortere prompt\n")

    def test_adoptie_zonder_pass_is_geweigerd(self):
        pad = self._evidence(verdict="fail")
        with self.assertRaisesRegex(hl.HarnessLabError, "geen pass"):
            hl.adopt_register(
                register_path=self.register_pad, variant_path=self.variant_pad,
                evidence_path=pad)

    def test_adoptie_fake_zonder_toestemming_is_geweigerd(self):
        pad = self._evidence(verdict="pass", mode="fake")
        with self.assertRaisesRegex(hl.HarnessLabError, "fake-modus"):
            hl.adopt_register(
                register_path=self.register_pad, variant_path=self.variant_pad,
                evidence_path=pad)
        # met expliciete toestemming gaat het wél door
        hl.adopt_register(
            register_path=self.register_pad, variant_path=self.variant_pad,
            evidence_path=pad, allow_fake=True, now=VAST)
        reg = hl.load_harness_register(self.register_pad)
        self.assertIn("prompt-kort-poc-alpha", {h["id"] for h in reg["harnesses"]})

    def test_adoptie_sha_mismatch_is_geweigerd(self):
        pad = self._evidence(verdict="pass")
        (self.td / "files" / "alpha-v2.md").write_text("anderes\n", encoding="utf-8")
        with self.assertRaisesRegex(hl.HarnessLabError, "sha256"):
            hl.adopt_register(
                register_path=self.register_pad, variant_path=self.variant_pad,
                evidence_path=pad)

    def test_adoptie_zonder_actieve_voorganger_is_geweigerd(self):
        variant = json.loads(self.variant_pad.read_text(encoding="utf-8"))
        variant["components"] = [
            {"type": "prompt", "target": "poc/bestaat-niet", "path": "files/alpha-v2.md"}]
        ander = _schrijf(self.td, "variant-anders.json", variant)
        pad = self._evidence(verdict="pass", variant_pad=ander)
        with self.assertRaisesRegex(hl.HarnessLabError, "geen actieve register-entry"):
            hl.adopt_register(
                register_path=self.register_pad, variant_path=ander,
                evidence_path=pad)

    def test_adoptie_toolgrants_is_geweigerd(self):
        variant = json.loads(self.variant_pad.read_text(encoding="utf-8"))
        variant["components"] = [
            {"type": "toolGrants", "target": "poc/alpha", "deny": {"alpha": ["x"]}}]
        ander = _schrijf(self.td, "variant-grants.json", variant)
        pad = self._evidence(verdict="pass", variant_pad=ander)
        with self.assertRaisesRegex(hl.HarnessLabError, "manifest-generatoren"):
            hl.adopt_register(
                register_path=self.register_pad, variant_path=ander,
                evidence_path=pad)

    def test_adoptie_is_eenmalig_per_variant_id(self):
        pad = self._evidence(verdict="pass")
        hl.adopt_register(
            register_path=self.register_pad, variant_path=self.variant_pad,
            evidence_path=pad, now=VAST)
        with self.assertRaisesRegex(hl.HarnessLabError, "bestaat al"):
            hl.adopt_register(
                register_path=self.register_pad, variant_path=self.variant_pad,
                evidence_path=pad, now=VAST)


if __name__ == "__main__":
    unittest.main()
