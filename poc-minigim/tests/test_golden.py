"""M2-bewijs: een verse offline run reproduceert de pre-refactor golden.

Dit is het hart van het bewijsmijlpaal: de refactor (taak 7) mag hier niets
aan breken. Canon-regels identiek aan tools/capture_golden.py.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_golden_core import run_and_canon  # noqa: E402  (zie stap 3b)

GOLDEN = ROOT / "tests" / "golden"
ARTIFACTS = ("omgevingsanalyse.json", "ils-draft.json",
             "ils-draft.features.28992.geojson", "validation.json", "run_summary.json")


class TestGoldenReproductie(unittest.TestCase):
    def test_offline_run_is_canonisch_identiek(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir, canon_dir = run_and_canon(Path(td))
            for name in ARTIFACTS:
                expected = (GOLDEN / name).read_text(encoding="utf-8")
                actual = (canon_dir / name).read_text(encoding="utf-8")
                self.assertEqual(actual, expected, f"artefact wijkt af: {name}")

            from minigim.canon import fase_samenvatting
            from fundament.manifest import load_manifest

            manifest = load_manifest(ROOT / "fase-manifest.json")
            docs = json.loads((canon_dir / "omgevingsanalyse.json").read_text(encoding="utf-8"))
            sam = fase_samenvatting(manifest, docs["items"])
            verwacht = json.loads((GOLDEN / "fase-samenvatting.json").read_text(encoding="utf-8"))
            self.assertEqual(sam, verwacht, "fase-samenvatting wijkt af")

            exp_layers = sorted(p.name[8:] for p in GOLDEN.glob("layers__*"))
            act_layers = sorted(p.name for p in (run_dir / "layers").glob("*.geojson"))
            self.assertEqual(act_layers, exp_layers, "lagen-set wijkt af")
            for name in exp_layers:
                self.assertEqual(
                    (run_dir / "layers" / name).read_text(encoding="utf-8"),
                    (GOLDEN / f"layers__{name}").read_text(encoding="utf-8"),
                    f"laag wijkt af: {name}")


if __name__ == "__main__":
    unittest.main()
