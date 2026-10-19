"""Modelregister-loader: schema-validatie, dubbele ids, opzoeken."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.models import ModelRegistryError, load_model_registry, model_by_id  # noqa: E402

VALID = {
    "poc": "p",
    "models": [
        {"id": "m1", "title": "M1", "class": "computation", "riskLevel": "low",
         "version": "1.0.0",
         "transports": [{"type": "processes", "processId": "p1"},
                        {"type": "a2a", "catalogRef": "cat.json", "agentId": "a1"}]},
    ],
}


def _write(td: Path, doc) -> Path:
    p = Path(td) / "modelregister.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


class TestModelRegistry(unittest.TestCase):
    def test_geldig_register_laadt(self):
        with tempfile.TemporaryDirectory() as td:
            reg = load_model_registry(_write(Path(td), VALID))
            self.assertEqual(model_by_id(reg, "m1")["title"], "M1")

    def test_processes_zonder_processid_is_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"][0]["transports"][0].pop("processId")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_a2a_zonder_agentid_is_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"][0]["transports"][1].pop("agentId")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_onbekende_risklevel_is_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"][0]["riskLevel"] = "extreem"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_dubbele_ids_zijn_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"].append(json.loads(json.dumps(bad["models"][0])))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_model_by_id_raakt_naast(self):
        with tempfile.TemporaryDirectory() as td:
            reg = load_model_registry(_write(Path(td), VALID))
            with self.assertRaises(KeyError):
                model_by_id(reg, "bestaat-niet")


if __name__ == "__main__":
    unittest.main()
