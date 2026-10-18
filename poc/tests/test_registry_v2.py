"""Registry v2.0-vorm (nspd-port fase 2)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))


def test_registry_is_v2_met_verplichte_velden():
    assert REG["registryVersion"] == "2.0"
    for it in REG["sources"]:
        assert it["role"] in {
            "inclusion", "exclusion", "conditional", "attention", "compensation",
            "context", "scenario-basis", "aoi"}, it["id"]
        assert it["fetchPolicy"] in {"cache", "service"}, it["id"]
        prov = it["provenance"]
        assert prov["pinned"] and len(prov["pinned"]) == 10, it["id"]  # ISO-datum
        assert prov.get("evidence"), it["id"]


def test_load_sources_werkt_nog_tegen_v2():
    import sys
    sys.path.insert(0, str(ROOT))
    from pipeline.geodata import load_sources
    src = load_sources()
    assert "agrest-ov-gebied-windenergie" in src
    assert src["netbeheerder-netcongestie"]["role"] == "scenario-basis"
