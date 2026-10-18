"""TaskRegistry: dekkingscheck en indexering van taken/bindings/bronnen."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.registers import TaskRegistry  # noqa: E402

TASKS = [{"id": "a"}, {"id": "b"}]
BINDINGS = [
    {"lijstItemId": "a", "status": "auto", "serviceRefs": ["bron-x"]},
    {"lijstItemId": "b", "status": "manual", "manualPointer": "KLIC"},
]
SOURCES = [{"id": "bron-x", "title": "Bron X", "protocol": "ogc-api-features"}]


class TestTaskRegistry(unittest.TestCase):
    def test_indexering_en_toegang(self):
        reg = TaskRegistry(TASKS, BINDINGS, SOURCES)
        self.assertEqual([t["id"] for t in reg.tasks()], ["a", "b"])
        self.assertEqual(reg.item("a")["id"], "a")
        self.assertEqual(reg.binding("b")["status"], "manual")
        self.assertEqual(reg.sources_by_id["bron-x"]["title"], "Bron X")

    def test_binding_zonder_taak_is_inconsistent(self):
        with self.assertRaises(AssertionError):
            TaskRegistry(TASKS, BINDINGS + [{"lijstItemId": "spook", "status": "auto"}], SOURCES)

    def test_taak_zonder_binding_is_inconsistent(self):
        with self.assertRaises(AssertionError):
            TaskRegistry(TASKS + [{"id": "c"}], BINDINGS, SOURCES)

    def test_onbekende_serviceref_is_inconsistent(self):
        bad = [{"lijstItemId": "a", "status": "auto", "serviceRefs": ["niet-geregistreerd"]}]
        with self.assertRaises(AssertionError):
            TaskRegistry(TASKS[:1], bad, SOURCES)


if __name__ == "__main__":
    unittest.main()
