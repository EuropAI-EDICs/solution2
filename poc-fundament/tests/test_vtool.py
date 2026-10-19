"""V-tool-suite (M5): de contracten van het harnas als één benoemde suite.

Assemblage van de bestaande bewijzen, per contract-familie (spec §9):
  V0      — fase-manifest en modelregister van beide pilot-PoC's zijn schema-geldig
  retrieval — een falende fetch degradeert naar not-delivered; prov blijft None (bewijs komt uit notes/riskFlags)
  computation — derivaties zijn in-run replay-identiek (byte-vergelijking op canon)
  binding — auto⇒tool en manual⇒pointer worden door het schema afgedwongen
Slotgate-contracten: zie deep-agents/tests/test_fase_slotgate.py (dependency-richting:
dit package importeert deep-agents niet).

Offline; hergebruikt de mini-registry/fixtures van de executor-tests.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.manifest import load_manifest  # noqa: E402
from fundament.models import load_model_registry  # noqa: E402

from tests import mini_registry  # noqa: E402
from fundament.executor import BindingExecutor  # noqa: E402
from fundament.ops import DEFAULT_OPS  # noqa: E402

from tests import fixtures  # noqa: E402

REPO = ROOT.parent
PILOTS = {"minigim": REPO / "poc-minigim", "nspd": REPO / "poc-nspd"}


class TestV0Schemas(unittest.TestCase):
    def test_beide_pilot_manifesten_zijn_schema_geldig(self):
        for poc, home in PILOTS.items():
            m = load_manifest(home / "fase-manifest.json")
            self.assertEqual(m["poc"], {"minigim": "minigim-gebiedscheck",
                                        "nspd": "nspd-tracks"}[poc], poc)

    def test_modelregister_is_schema_geldig(self):
        reg = load_model_registry(PILOTS["minigim"] / "modelregister.json")
        ids = [m["id"] for m in reg["models"]]
        self.assertEqual(len(ids), len(set(ids)))


class TestRetrievalContract(unittest.TestCase):
    def test_falende_fetch_degradeert_zonder_prov_met_vlaggen(self):
        reg = mini_registry.build()
        real = fixtures.fake_fetch_layer_factory()

        def failing(source, bbox=None, refresh=False, cbs_filter=None):
            if source["id"] == "pdok-nwb-wegen":
                raise RuntimeError("server onbereikbaar")
            return real(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter)

        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=failing,
                                 ops=DEFAULT_OPS)
            recs = ex.run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.clip")
        self.assertEqual(rec["deliveredStatus"], "not-delivered")
        self.assertIn("server onbereikbaar", " ".join(rec["notes"]))
        self.assertIn("hoog-prioriteit niet automatisch geleverd", rec["riskFlags"])
        self.assertIsNone(rec["prov"])


class TestComputationContract(unittest.TestCase):
    def test_derivatie_replay_is_identiek(self):
        reg = mini_registry.build()
        fn = fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=fn,
                                 ops=DEFAULT_OPS)
            first = ex.run()
            again = ex._execute(reg.item("t.clip"), reg.binding("t.clip"))
        base = next(r for r in first if r["lijstItemId"] == "t.clip")
        self.assertEqual(json.dumps(again["values"], sort_keys=True),
                         json.dumps(base["values"], sort_keys=True))


class TestBindingContract(unittest.TestCase):
    def test_auto_heeft_tool_en_manual_heeft_pointer_in_beide_manifesten(self):
        for home in PILOTS.values():
            m = load_manifest(home / "fase-manifest.json")
            for ph in m["phases"]:
                for t in (ph.get("tasks") or []):
                    if t["binding"] in ("auto", "partial"):
                        self.assertIn("tool", t, t["id"])
                    elif t["binding"] == "manual":
                        self.assertIn("manualPointer", t, t["id"])


if __name__ == "__main__":
    unittest.main()
