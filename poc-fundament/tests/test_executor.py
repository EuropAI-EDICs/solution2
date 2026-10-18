"""BindingExecutor: auto/manual/broken-bindingen, faal-isolatie, V3-replay-seam."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import mini_registry  # noqa: E402
from fundament.executor import BindingExecutor  # noqa: E402
from fundament.ops import DEFAULT_OPS  # noqa: E402

from tests import fixtures  # noqa: E402


class TestExecutor(unittest.TestCase):
    def _run(self, fetch_fn=None, **kw):
        reg = mini_registry.build()
        fn = fetch_fn or fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=fn,
                                 ops=DEFAULT_OPS, **kw)
            recs = ex.run()
        return recs

    def test_auto_echo_levert_met_derived_prov(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.echo")
        self.assertEqual(rec["deliveredStatus"], "delivered")
        self.assertEqual(rec["prov"]["protocol"], "derived")
        self.assertIn("btoM2", rec["values"])

    def test_manual_krijgt_pointer_en_geen_getallen(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.man")
        self.assertEqual(rec["deliveredStatus"], "manual-action")
        self.assertEqual(rec["values"]["route"], "bevoegde bron")
        self.assertEqual(rec["prov"], None)

    def test_clip_levert_met_bron_prov_en_laag(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.clip")
        self.assertEqual(rec["deliveredStatus"], "delivered")
        self.assertEqual(rec["values"]["featureCount"], 1)  # NWB-wegvakkenlijn ligt binnen de AOI
        self.assertTrue(rec["layerRef"].startswith("layers/"))
        self.assertEqual(rec["prov"]["protocol"], "ogc-api-features")

    def test_falende_bron_degradeert_niet_breekt(self):
        real = fixtures.fake_fetch_layer_factory()

        def failing(source, bbox=None, refresh=False, cbs_filter=None):
            if source["id"] == "pdok-nwb-wegen":
                raise RuntimeError("server onbereikbaar")
            return real(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter)

        recs = self._run(fetch_fn=failing)
        rec = next(r for r in recs if r["lijstItemId"] == "t.clip")
        self.assertEqual(rec["deliveredStatus"], "not-delivered")
        self.assertIn("server onbereikbaar", " ".join(rec["notes"]))
        # hoog-prioriteitsvlag staat erbij (doctrine: zichtbaar, nooit stil)
        self.assertIn("hoog-prioriteit niet automatisch geleverd", rec["riskFlags"])

    def test_onbekende_op_is_not_delivered_met_note(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.broken-op")
        self.assertEqual(rec["deliveredStatus"], "not-delivered")
        self.assertIn("onbekende derivation-op", " ".join(rec["notes"]))

    def test_replay_via_execute_is_deterministisch(self):
        reg = mini_registry.build()
        fn = fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=fn, ops=DEFAULT_OPS)
            first = ex.run()
            again = ex._execute(reg.item("t.clip"), reg.binding("t.clip"))
        base = next(r for r in first if r["lijstItemId"] == "t.clip")
        self.assertEqual(json.dumps(again["values"], sort_keys=True),
                         json.dumps(base["values"], sort_keys=True))


if __name__ == "__main__":
    unittest.main()
