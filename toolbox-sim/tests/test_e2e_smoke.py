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


def test_full_catalogue_smoke_per_app():
    from fastapi.testclient import TestClient

    from app.server import build_apps

    auth = {"Authorization": "Bearer sim-toolbox-token"}
    apps = build_apps(full=True, eubd=False)
    # één request per nieuwe app (health-checks zitten al in test_build_apps_full_omvat_alle_veertien)
    probes = {
        "dataspace": lambda c: c.post("/v2/catalog/request", headers=auth, json={}),
        "algorithms": lambda c: c.get("/models", headers=auth),
        "participate": lambda c: c.get("/api/proposals", headers=auth),
        "fl": lambda c: c.post("/rounds", headers=auth, json={"name": "smoke"}),
        "ain": lambda c: c.post("/notebooks", headers=auth, json={"name": "smoke"}),
        "dm": lambda c: c.get("/models", headers=auth),
        "ie": lambda c: c.get("/solutions", headers=auth),
        "cip": lambda c: c.get("/scenarios", headers=auth),
    }
    for name, probe in probes.items():
        response = probe(TestClient(apps[name]))
        # 200 OK of 201 Created (create-endpoints: fl /rounds en ain /notebooks)
        assert response.status_code in (200, 201), f"{name}: {response.status_code} {response.text[:120]}"
        assert response.headers.get("x-sim-provenance", "").startswith("toolbox-sim/"), name
