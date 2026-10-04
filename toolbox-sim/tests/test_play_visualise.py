# toolbox-sim/tests/test_play_visualise.py
from fastapi.testclient import TestClient

from app.jwtutil import mint_token
from app.play_visualise import create_app

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
client = TestClient(create_app())

DS_PAYLOAD = {  # exact de vorm uit nldt/services/adapters/play_visualise.py
    "name": "utrecht-wind-source",
    "sourceConfiguration": {"type": "EXTERNAL", "url": "http://localhost:8084/exports/wind.geojson", "headers": []},
    "securityConfiguration": {"type": "OTHER", "headers": []},
}
DL_PAYLOAD = {"name": "utrecht-wind", "dataSource": "", "type": "SCENARIO", "configuration": {}}


def test_create_data_source_and_layer():
    ds = client.post("/api/dataSources", json=DS_PAYLOAD, headers=AUTH)
    assert ds.status_code == 200 and ds.json()["id"].startswith("ds-")
    payload = dict(DL_PAYLOAD, dataSource=ds.json()["id"])
    dl = client.post("/api/dataLayers", json=payload, headers=AUTH)
    assert dl.status_code == 200 and dl.json()["id"].startswith("dl-")
    fetched = client.get(f"/api/dataLayers/{dl.json()['id']}", headers=AUTH)
    assert fetched.status_code == 200 and fetched.json()["type"] == "SCENARIO"


def test_layer_unknown_datasource_404():
    r = client.post("/api/dataLayers", json=dict(DL_PAYLOAD, dataSource="ds-nope"), headers=AUTH)
    assert r.status_code == 404


def test_datasource_requires_url_422():
    bad = dict(DS_PAYLOAD, sourceConfiguration={"type": "EXTERNAL", "headers": []})
    assert client.post("/api/dataSources", json=bad, headers=AUTH).status_code == 422


def test_requires_bearer():
    assert client.post("/api/dataSources", json=DS_PAYLOAD).status_code == 401
