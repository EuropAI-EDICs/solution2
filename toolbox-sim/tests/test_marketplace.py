# toolbox-sim/tests/test_marketplace.py
from fastapi.testclient import TestClient

from app.jwtutil import mint_token
from app.marketplace import create_app

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
client = TestClient(create_app())


def test_upload_and_publish_flow():  # vorm van nldt/services/marketplace_publish.py
    up = client.post(
        "/api/v1/agent/assets",
        files={"file": ("recipe-utrecht-opportunity-map-v1.0.0.json", b'{"recipe": {}}', "application/json")},
        headers=AUTH,
    )
    assert up.status_code == 200
    asset_id = up.json()["id"]
    pub = client.post(
        f"/api/v1/agent/assets/{asset_id}/publish",
        json={"name": "Utrecht opportunity map", "description": "sim", "categories": ["urn:ngsi-ld:category:processes"], "licence": "EUPL-1.2"},
        headers=AUTH,
    )
    assert pub.status_code == 200
    body = pub.json()
    assert body["status"] == "published"
    assert body["publishState"]["offering_id"] == f"sim-offering-{asset_id}"


def test_listing_after_publish():
    # Zelfstandig: eigen asset uploaden + publiceren, dan de listing op dít asset controleren
    # (voorheen afhankelijk van test_upload_and_publish_flow die eerst draaide).
    up = client.post(
        "/api/v1/agent/assets",
        files={"file": ("recipe-utrecht-selfcontained-v1.0.0.json", b'{"recipe": {}}', "application/json")},
        headers=AUTH,
    )
    assert up.status_code == 200
    asset_id = up.json()["id"]
    pub = client.post(
        f"/api/v1/agent/assets/{asset_id}/publish",
        json={"name": "Zelfstandige listing-test", "description": "sim", "categories": ["urn:ngsi-ld:category:processes"], "licence": "EUPL-1.2"},
        headers=AUTH,
    )
    assert pub.status_code == 200
    listing = client.get("/api/v1/agent/assets", headers=AUTH)
    assert listing.status_code == 200
    mine = [a for a in listing.json()["data"] if a.get("id") == asset_id]
    assert mine and mine[0].get("status") == "published"


def test_publish_unknown_asset_404():
    r = client.post("/api/v1/agent/assets/asset-999/publish", json={"name": "x", "description": "y", "categories": [], "licence": "EUPL-1.2"}, headers=AUTH)
    assert r.status_code == 404


def test_requires_bearer():
    assert client.get("/api/v1/agent/assets").status_code == 401
