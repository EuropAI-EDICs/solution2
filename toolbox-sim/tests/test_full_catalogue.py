# toolbox-sim/tests/test_full_catalogue.py
"""Contract- en determinismetests voor de catalogus-apps (7 algoritmmodellen eerst)."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))

from app.algorithms import Ground, MODEL_IDS, MissingGround, SYNTHETIC, load_ground, run_model

FIXTURES = SIM_ROOT / "fixtures"


@pytest.fixture(scope="module")
def ground():
    return load_ground(FIXTURES)


def test_model_ids_compleet():
    assert set(MODEL_IDS) == {
        "neighbourhood-energy-demand", "building-environmental-footprint", "renovation-strategies",
        "urban-planning-vulnerability", "urban-mobility", "pollution-propagation", "police-routing",
    }
    assert SYNTHETIC == {"urban-mobility", "pollution-propagation", "police-routing"}


def test_energy_eist_parameter(ground):
    with pytest.raises(ValueError):
        run_model("neighbourhood-energy-demand", {}, ground)  # geen intensiteit verzinnen


def test_energy_berekent_over_echte_areas(ground):
    out = run_model("neighbourhood-energy-demand", {"intensity_kwh_per_m2_year": 10.0}, ground)
    assert out["outputs"]["area_m2_total"] > 0
    assert abs(out["outputs"]["kwh_total"] - out["outputs"]["area_m2_total"] * 10.0) < 0.2
    assert out["provenance"]["areas"].startswith("fixtures/ngsi-ld/eubd-buildings.jsonld")


def test_footprint_en_renovatie_grondslag(ground):
    fp = run_model("building-environmental-footprint", {"carbon_kg_per_m2": 200.0}, ground)
    assert fp["outputs"]["carbon_kg_total"] > 0
    rn = run_model("renovation-strategies", {}, ground)
    assert len(rn["outputs"]["priority_by_tile"]) > 0


def test_vulnerability_uit_peilen(ground):
    out = run_model("urban-planning-vulnerability", {}, ground)
    rows = out["outputs"]["peilgebieden"]
    assert rows and 0.0 <= rows[0]["index"] <= 1.0
    assert out["provenance"]["source"] == "fixtures/dp-temporal.jsonld#peilen_latest"


def test_synthetische_modellen_gemarkeerd(ground):
    for name in sorted(SYNTHETIC):
        out = run_model(name, {}, ground)
        assert out["synthetic"] is True and out["provenance"]["syntheticSeed"] is True


def test_determinisme(ground):
    a = run_model("urban-mobility", {}, ground)
    b = run_model("urban-mobility", {}, ground)
    assert a == b


def test_missing_ground():
    with pytest.raises(MissingGround) as exc:
        run_model("urban-planning-vulnerability", {}, Ground())
    assert exc.value.need == "peilen"


def test_unknown_model():
    with pytest.raises(KeyError):
        run_model("bestaat-niet", {}, Ground())


def test_edc_stub_flow():
    from app.dataspace_ready import create_app as dsr_app

    offer = {"uid": "offer-test1", "datasetId": "gold-x.geojson",
             "lakeUri": "lake://nldt-poc-lake/gold/x.geojson", "accessClass": "open", "license": "CC0-1.0"}
    client = TestClient(dsr_app([offer], lake_root=SIM_ROOT.parent / "nldt" / "data" / "lake"))
    auth = {"Authorization": "Bearer sim-toolbox-token"}

    asset = client.post("/v3/assets", headers=auth, json={"@id": "asset-test1"})
    assert asset.status_code == 201
    catalog = client.post("/v2/catalog/request", headers=auth, json={}).json()
    assert any(o["uid"] == "offer-test1" for o in catalog["offers"])

    cn = client.post("/v2/contractnegotiations", headers=auth, json={"offerUid": "offer-test1"}).json()
    assert cn["state"] == "REQUESTED"
    assert client.get(f"/v2/contractnegotiations/{cn['id']}", headers=auth).json()["state"] == "CONFIRMED"

    tp = client.post("/v2/transferprocesses", headers=auth,
                     json={"negotiationId": cn["id"], "offerUid": "offer-test1"}).json()
    assert tp["state"] == "STARTED"
    done = client.get(f"/v2/transferprocesses/{tp['id']}", headers=auth).json()
    assert done["state"] == "COMPLETED"
    assert done["offerUid"] == "offer-test1"

    missing = client.post("/v2/contractnegotiations", headers=auth, json={"offerUid": "ontbreekt"})
    assert missing.status_code == 404 and missing.json()["error"] == "offer-not-found"


def test_participate_stub():
    import json as _json

    from app.participate import create_app as participate_app

    seed = _json.loads((FIXTURES / "participate-seed.json").read_text())
    client = TestClient(participate_app(seed))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    assert len(client.get("/api/meetings", headers=auth).json()["data"]) == 1
    created = client.post("/api/proposals", headers=auth,
                          json={"title": "Nieuwe zone", "area": "utrecht"}).json()
    assert created["id"].startswith("prop-") and created["state"] == "open"
    room = client.post("/rooms", headers=auth, json={"title": "sessie"}).json()
    assert room["roomUrl"].startswith("http://localhost:9199/rooms/")

    noauth = client.get("/api/proposals")
    assert noauth.status_code == 401


def test_federated_learning_round():
    from app.algorithms import load_ground
    from app.federated_learning import create_app as fl_app

    ground = load_ground(FIXTURES)
    client = TestClient(fl_app(ground.peilen))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    rnd = client.post("/rounds", headers=auth, json={"name": "peilen-r1"}).json()
    update = client.post(f"/rounds/{rnd['id']}/updates", headers=auth,
                         json={"municipality": "rijnland"}).json()
    assert update["metric"]["mean_waterstand_m"] < 0  # echte peilen zijn onder NAP
    result = client.get(f"/rounds/{rnd['id']}/result", headers=auth).json()
    assert result["participants"] == 1 and "mean_waterstand_m" in result["aggregate"]


def test_ai_notebook_pipeline_run():
    from app.ai_notebook import create_app as ain_app

    client = TestClient(ain_app(lake_root=SIM_ROOT.parent / "nldt" / "data" / "lake" / "nldt-poc-lake"))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    nb = client.post("/notebooks", headers=auth, json={"name": "analyse"}).json()
    assert nb["id"].startswith("nb-")
    run = client.post("/pipelines/runs", headers=auth,
                      json={"notebookId": nb["id"], "pipeline": "inventory-count"}).json()
    assert run["state"] == "SUCCEEDED"
    assert run["outputs"]["inventoryDatasets"] > 0
    again = client.get(f"/pipelines/runs/{run['id']}", headers=auth).json()
    assert again == run  # deterministisch


def test_data_modeller_registry_en_validatie():
    from app.data_modeller import create_app as dm_app

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id"],
        "properties": {"id": {"type": "string"}},
    }
    client = TestClient(dm_app({"Address": schema}))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    models = client.get("/models", headers=auth).json()
    assert "Address" in models["data"]
    ok = client.post("/models/Address/validate", headers=auth, json={"id": "adr-1"}).json()
    assert ok["valid"] is True and ok["findings"] == []
    bad = client.post("/models/Address/validate", headers=auth, json={"nope": 1}).json()
    assert bad["valid"] is False and bad["findings"]
    missing = client.post("/models/Onbekend/validate", headers=auth, json={})
    assert missing.status_code == 404 and missing.json()["error"] == "model-not-found"


def test_integrated_environment_portal():
    from app.integrated_environment import create_app as ie_app

    solutions = [{"name": "identity", "port": 9191, "status": "simulated"}]
    client = TestClient(ie_app(solutions, inventory_path=SIM_ROOT.parent / "nldt" / "data" / "lake-inventory.json"))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    listed = client.get("/solutions", headers=auth).json()
    assert listed["data"][0]["name"] == "identity" and listed["total"] == 1
    metrics = client.get("/metrics", headers=auth)
    assert metrics.status_code == 200 and "solutions_total 1" in metrics.text
    catalogue = client.get("/catalogue", headers=auth).json()
    assert catalogue["total"] >= 50  # lake-inventaris telt ruim honderd datasets


def test_cip_scenarios_en_contributions():
    from app.cip import create_app as cip_app

    client = TestClient(cip_app())
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    scenario = client.post("/scenarios", headers=auth, json={"name": "energietransitie"}).json()
    assert scenario["id"].startswith("scen-")
    contribution = client.post(f"/scenarios/{scenario['id']}/contributions", headers=auth,
                               json={"author": "buurtgroep", "text": "meer groen"}).json()
    assert contribution["id"].startswith("contrib-")
    listed = client.get(f"/scenarios/{scenario['id']}/contributions", headers=auth).json()
    assert listed["total"] == 1
