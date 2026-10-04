# toolbox-sim/tests/test_e2e_smoke.py
"""E2E: sim op → brug over adapters → alles geregistreerd, niets gemockt."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

for line in (Path(__file__).resolve().parents[1] / ".env.sim").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key] = value

sys.path.insert(0, str(REPO / "nldt"))

from services.adapters import data_platform, keycloak_auth  # noqa: E402
from services.hybrid_bridge import post_execution_hooks  # noqa: E402
from services.marketplace_publish import publish_recipe  # noqa: E402

FC = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"note": "e2e"}, "geometry": {"type": "Point", "coordinates": [5.11, 52.09]}}]}


def test_full_offline_story(live_sim, tmp_path):
    keycloak_auth.clear_token_cache()
    assert keycloak_auth.get_service_token()

    zones = data_platform.list_entities(entity_type="ldt:OpportunityZone", limit=1000)
    assert zones, "canonieke zones moeten in de broker zitten"

    execution = {"recipeId": "toolbox-sim-e2e", "outputs": {"intersection": FC}}
    hooks = post_execution_hooks(execution, run_id="toolbox-sim-e2e")
    reg = hooks["visualization"]
    assert reg["dataSource"].get("mock") is None and reg["dataLayer"]["id"].startswith("dl-")

    result = publish_recipe(
        {"id": "toolbox-sim-e2e", "title": "Toolbox-sim e2e", "description": "smoke", "version": "1.0.0"},
        categories=["urn:ngsi-ld:category:processes"],
    )
    assert result["mock"] is False and result["offeringId"].startswith("sim-offering-") and result["marketplaceLink"]
