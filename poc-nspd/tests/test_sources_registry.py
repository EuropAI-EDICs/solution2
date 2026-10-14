import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REGISTRY = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))


def test_registry_vorm():
    assert REGISTRY["registryVersion"] == "2.0"
    assert isinstance(REGISTRY["sources"], list) and len(REGISTRY["sources"]) >= 8


def test_elke_bron_heeft_jurisdictie_en_status():
    for s in REGISTRY["sources"]:
        assert s["jurisdictie"] in ("nl", "be"), s["id"]
        assert s["status"] in ("pinned", "candidate"), s["id"]
        assert s["endpointType"] in (
            "ogc-api", "wfs", "wms", "wmts", "arcgis-rest", "document", "3dtiles"), s["id"]
        if s["status"] == "pinned":
            assert s.get("lastChecked"), s["id"]
            assert s.get("probeEvidence"), s["id"]


def test_oude_vlaamse_host_is_vervallen():
    for s in REGISTRY["sources"]:
        assert "geoservices.informatievlaanderen.be" not in json.dumps(s), s["id"]


def test_alle_nspd_bronnen_gepind_of_expliciet_kandidaat():
    # fase 1: geen enkele bron mag 'candidate' blijven zonder geplande taakverwijzing
    for s in REGISTRY["sources"]:
        if s["status"] == "candidate":
            assert s.get("pinnedInTask"), s["id"]
