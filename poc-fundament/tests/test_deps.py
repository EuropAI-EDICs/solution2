"""Dependency-richting (spec §12): fundament importeert nooit deep-agents/poc's."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VERBODEN = ("deep_agents", "deep-agents", "minigim", "poc", "nldt")


class TestDependencyRichting(unittest.TestCase):
    def test_geen_verboden_imports_in_de_package_brondaad(self):
        hits = []
        for py in (ROOT / "fundament").rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), start=1):
                s = line.strip()
                if not (s.startswith("import ") or s.startswith("from ")):
                    continue
                if any(v in s for v in VERBODEN):
                    hits.append(f"{py.relative_to(ROOT)}:{i}: {s}")
        self.assertEqual(hits, [], "fundament mag de agent-/poc-laag niet importeren")


if __name__ == "__main__":
    unittest.main()
