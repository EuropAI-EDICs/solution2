# toolbox-sim/tests/test_broker.py
from fastapi.testclient import TestClient

from app.data_platform import create_broker_app
from app.jwtutil import mint_token

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
ENTITIES = [
    {
        "id": "urn:ldt:utrecht:zone:ZR-1",
        "type": "ldt:OpportunityZone",
        "areaKm2": {"type": "Property", "value": 1.5},
        "location": {"type": "GeoProperty", "value": {"type": "Point", "coordinates": [5.1, 52.1]}},
    },
    {"id": "urn:ldt:eindhoven:row:OT-1", "type": "ldt:ConversionRow"},
]

app = create_broker_app(
    entities_by_tenant={"ldt": ENTITIES},
    provenance_by_tenant={"ldt": "toolbox-sim/data-platform; fixture=utrecht-wind; run=20260830T113234Z-wind"},
    include_proxy=True,
)
client = TestClient(app)


def test_health_open():
    assert client.get("/health").status_code == 200


def test_list_by_type_with_tenant_header():
    r = client.get("/ngsi-ld/v1/entities", params={"type": "ldt:OpportunityZone"}, headers={**AUTH, "NGSILD-Tenant": "ldt"})
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == ["urn:ldt:utrecht:zone:ZR-1"]
    assert r.headers["X-Sim-Provenance"].startswith("toolbox-sim/data-platform")


def test_unknown_tenant_empty_list():
    r = client.get("/ngsi-ld/v1/entities", headers={**AUTH, "NGSILD-Tenant": "nope"})
    assert r.status_code == 200
    assert r.json() == []


def test_get_by_id_and_404():
    ok = client.get("/ngsi-ld/v1/entities/urn:ldt:eindhoven:row:OT-1", headers=AUTH)
    assert ok.status_code == 200 and ok.json()["id"] == "urn:ldt:eindhoven:row:OT-1"
    miss = client.get("/ngsi-ld/v1/entities/urn:ldt:none:1", headers=AUTH)
    assert miss.status_code == 404


def test_upsert_then_read_back_in_same_tenant():
    new = [{"id": "urn:ldt:test:zone:Z-9", "type": "ldt:OpportunityZone"}]
    r = client.post("/ngsi-ld/v1/entityOperations/upsert", json=new, headers={**AUTH, "NGSILD-Tenant": "ldt"})
    assert r.status_code == 204
    got = client.get("/ngsi-ld/v1/entities/urn:ldt:test:zone:Z-9", headers=AUTH)
    assert got.status_code == 200


def test_proxy_envelope_shape():  # data_platform._list_via_ucs_proxy verwacht {"data": ...}
    r = client.get("/api/v1/data-platform/entities", params={"type": "ldt:ConversionRow", "scope": "urn:ngsi-ld:scope:default"}, headers=AUTH)
    assert r.status_code == 200
    assert [e["id"] for e in r.json()["data"]] == ["urn:ldt:eindhoven:row:OT-1"]
    one = client.get("/api/v1/data-platform/entities/urn:ldt:eindhoven:row:OT-1", headers=AUTH)
    assert one.json()["data"]["id"] == "urn:ldt:eindhoven:row:OT-1"


def test_broker_requires_bearer():
    assert client.get("/ngsi-ld/v1/entities").status_code == 401
