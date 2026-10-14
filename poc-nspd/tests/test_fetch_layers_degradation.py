"""fetch_layers-None-degradatie (fase 2, task 1B).

Bug: bij een eerder gefaalde sourceId cachet ``fetch_layers`` ``by_source[sid]
= None``; een tweede zone met een alias naar dezelfde bron crashte daarna met
AttributeError (``None.get``). Verwacht gedrag: degradation
``cached fetch failure for sourceId`` per extra zone, geen uitzondering,
geen laag — degradatie, nooit een crash.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run  # noqa: E402
from pipeline import geodata  # noqa: E402


def test_tweede_zone_op_gefaalde_bron_degradeert_zonder_crash(monkeypatch):
    """Twee zones met aliassen naar dezelfde falende bron: precies 2
    degradations, geen AttributeError, geen laag, geen manifest-entry."""
    monkeypatch.setattr(run, "ZONE_SOURCES", {
        "zone-a": {"sourceId": "test-bron-x", "note": "testalias a"},
        "zone-b": {"sourceId": "test-bron-x", "note": "testalias b"},
    })

    def _faal(source_id, **kwargs):
        raise ValueError(f"kapotte bron {source_id}")

    monkeypatch.setattr(geodata, "fetch_layer", _faal)
    layers, manifest, degradations, source_of_zone = run.fetch_layers(
        ["zone-a", "zone-b"], refresh=False, bbox=(0.0, 0.0, 1.0, 1.0))

    assert layers == {} and manifest == {}
    assert source_of_zone == {"zone-a": "test-bron-x", "zone-b": "test-bron-x"}
    assert len(degradations) == 2
    # eerste zone: de fetch-fout zelf
    assert degradations[0]["kind"] == "layer-fetch"
    assert degradations[0]["zone"] == "zone-a"
    assert degradations[0]["sourceId"] == "test-bron-x"
    assert "kapotte bron" in degradations[0]["error"]
    # tweede zone: de gecachte falende bron, zonder opnieuw te fetchen
    assert degradations[1] == {"kind": "layer-fetch", "zone": "zone-b",
                               "sourceId": "test-bron-x",
                               "error": "cached fetch failure for sourceId"}
