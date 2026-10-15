# toolbox-sim/tests/test_broker.py
import json
from pathlib import Path

import pytest
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


# --- Taak 2: NGSI-LD subscriptions, registrations en temporal ---
SUB = {
    "type": "Subscription",
    "entities": [{"type": "ldt:OpportunityZone"}],
    "notification": {"endpoint": {"uri": "http://localhost:1/none"}},
}

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_entities = {}
for name in json.loads((FIXTURES / "manifest.json").read_text())["batches"]:
    _entities.setdefault("ldt", []).extend(json.loads((FIXTURES / "ngsi-ld" / f"{name}.jsonld").read_text()))
_temporal = json.loads((FIXTURES / "dp-temporal.jsonld").read_text())
_broker_client = TestClient(create_broker_app(
    entities_by_tenant={"ldt": _entities["ldt"]},
    provenance_by_tenant={"ldt": "toolbox-sim/data-platform; fixtures=test"},
    include_proxy=True,
    temporal=_temporal,
))


@pytest.fixture
def broker_client() -> TestClient:
    return _broker_client


def test_subscription_lifecycle(broker_client):
    r = broker_client.post("/ngsi-ld/v1/subscriptions/", json=SUB, headers=AUTH)
    assert r.status_code == 201
    sid = r.headers["Location"].rsplit("/", 1)[-1]
    assert r.text == ""  # 201 zonder body, alleen Location-header
    listing = broker_client.get("/ngsi-ld/v1/subscriptions/", headers=AUTH)
    assert any(s["id"] == sid for s in listing.json())
    assert listing.json()[0]["status"] == "active"
    assert broker_client.delete(f"/ngsi-ld/v1/subscriptions/{sid}", headers=AUTH).status_code == 204
    assert broker_client.get(f"/ngsi-ld/v1/subscriptions/{sid}", headers=AUTH).status_code == 404


def test_subscription_onbekend_top_level_error(broker_client):  # review F1: foutcontract is top-level
    r = broker_client.get("/ngsi-ld/v1/subscriptions/urn:ngsi-ld:Subscription:onbekend", headers=AUTH)
    assert r.status_code == 404 and r.json()["error"] == "NotFound"
    assert r.json()["description"] == "urn:ngsi-ld:Subscription:onbekend"


def test_subscription_validatie(broker_client):
    r = broker_client.post("/ngsi-ld/v1/subscriptions/", json={"type": "Subscription"}, headers=AUTH)
    assert r.status_code == 400 and r.json()["error"] == "BadRequest"


def test_notify_outbox_deterministisch(broker_client):
    sid = broker_client.post("/ngsi-ld/v1/subscriptions/", json=SUB, headers=AUTH).headers["Location"].rsplit("/", 1)[-1]
    a = broker_client.post(f"/ngsi-ld/v1/subscriptions/{sid}/notify", headers=AUTH).json()
    b = broker_client.post(f"/ngsi-ld/v1/subscriptions/{sid}/notify", headers=AUTH).json()
    assert a["subscriptionId"] == sid and a["data"], "notificatie moet gematchte entiteiten bevatten"
    assert a["notifiedAt"] != b["notifiedAt"]  # sim-klok telt
    assert a["data"] == b["data"]  # zelfde entiteiten, deterministisch
    outbox = broker_client.get(f"/ngsi-ld/v1/subscriptions/{sid}/notifications", headers=AUTH).json()
    assert len(outbox["data"]) == 2


def test_registrations_crud(broker_client):
    reg = {"type": "ContextSourceRegistration", "information": [{"entities": [{"type": "WeatherObserved"}]}],
           "endpoint": "http://localhost:9199/ngsi-ld/v1"}
    r = broker_client.post("/ngsi-ld/v1/registrations/", json=reg, headers=AUTH)
    assert r.status_code == 201
    rid = r.headers["Location"].rsplit("/", 1)[-1]
    assert any(x["id"] == rid for x in broker_client.get("/ngsi-ld/v1/registrations/", headers=AUTH).json())
    assert broker_client.delete(f"/ngsi-ld/v1/registrations/{rid}", headers=AUTH).status_code == 204


def test_temporal_between(broker_client):
    r = broker_client.get(
        "/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:WeatherObserved:knmi-260",
        params={"timerel": "between", "time": "2024-01-05T00:00:00Z", "endTime": "2024-02-01T00:00:00Z"},
        headers=AUTH,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "urn:ngsi-ld:WeatherObserved:knmi-260"
    instances = body["rainfall"][0]["instances"]
    assert instances and all("2024-01-05" <= i["observedAt"] <= "2024-02-01" for i in instances)


def test_temporal_zonder_endtime_tussen_gaat_fout(broker_client):
    r = broker_client.get(
        "/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:WeatherObserved:knmi-260",
        params={"timerel": "between", "time": "2024-01-05T00:00:00Z"},
        headers=AUTH,
    )
    assert r.status_code == 400 and r.json()["error"] == "BadRequest"


def test_temporal_onbekende_entity(broker_client):
    r = broker_client.get(
        "/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:Onbekend:1",
        params={"timerel": "after", "time": "2024-01-01T00:00:00Z"},
        headers=AUTH,
    )
    assert r.status_code == 404 and r.json()["error"] == "NotFound"
