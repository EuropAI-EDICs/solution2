# toolbox-sim/tests/test_adapters_live.py
"""nldt-adapters live tegen de toolbox-sim (env eerst, dan pas importeren)."""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

for line in (SIM_ENV := (Path(__file__).resolve().parents[1] / ".env.sim").read_text().splitlines()):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key] = value

sys.path.insert(0, str(REPO / "nldt"))

from services.adapters import data_platform, keycloak_auth, play_visualise  # noqa: E402
from services.marketplace_publish import publish_recipe  # noqa: E402
from services.process_adapter.router import UCSAdapter  # noqa: E402


def test_keycloak_live_token_with_scopes(live_sim):
    keycloak_auth.clear_token_cache()
    token = keycloak_auth.get_service_token()
    assert token
    scopes = data_platform.list_scopes()
    assert any(s["scope"].endswith("default") and s["plane"] == "context-data" for s in scopes)


def test_broker_live_entities(live_sim):
    zones = data_platform.list_entities(entity_type="ldt:OpportunityZone", limit=1000)
    assert zones and zones[0]["id"].startswith("urn:ldt:utrecht:zone:")
    one = data_platform.get_entity(zones[0]["id"])
    assert one["id"] == zones[0]["id"]


def test_trino_live_readonly(live_sim):
    result = data_platform.trino_query("SELECT * FROM timescaledb.public.runs")
    assert result["rowCount"] >= 4
    assert all(row[1] == "pass" for row in result["rows"])


def test_pv_live_registration(live_sim, tmp_path):
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [5.1, 52.1]}}]}
    reg = play_visualise.register_geojson_layer(geojson=fc, name="live-adapter-test", export_store=tmp_path)
    assert reg["dataSource"].get("mock") is None
    assert reg["dataLayer"].get("mock") is None
    assert reg["dataSource"]["id"].startswith("ds-")
    assert (tmp_path / f"{reg['exportId']}.geojson").exists()


def test_ucs_live_replay(live_sim):
    adapter = UCSAdapter()
    assert adapter.available
    outputs = adapter.execute("utrecht-opportunity-map", {})
    assert outputs["verdict"] == "pass"
    assert "sim-replay://canonical/" in json.dumps(outputs) or outputs.get("runId")


def test_marketplace_live_publish(live_sim):
    recipe = {"id": "live-adapter-test", "title": "Live adapter test", "description": "sim", "version": "1.0.0"}
    result = publish_recipe(recipe, categories=["urn:ngsi-ld:category:processes"])
    assert result["offeringId"].startswith("sim-offering-")
    assert result["mock"] is False
    assert result["marketplaceLink"]
