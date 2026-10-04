# toolbox-sim/tests/test_trino.py
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.data_platform import create_broker_app
from app.jwtutil import mint_token

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
TABLES = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "trino" / "tables.json").read_text())

app = create_broker_app(
    entities_by_tenant={"ldt": []},
    provenance_by_tenant={"ldt": "toolbox-sim/data-platform"},
    include_trino=True,
)
client = TestClient(app)


def test_show_schemas():
    r = client.post("/v1/statement", content="SHOW SCHEMAS FROM timescaledb", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert [c["name"] for c in body["columns"]] == ["Schema"]
    assert body["data"] == [[s] for s in TABLES["catalogs"]["timescaledb"]]
    assert body["nextUri"] is None  # adapter-stopping while-lus


def test_show_tables():
    r = client.post("/v1/statement", content="show tables from timescaledb.public", headers=AUTH)
    assert r.status_code == 200
    assert [row[0] for row in r.json()["data"]] == ["runs"]


def test_select_star_with_limit():
    r = client.post("/v1/statement", content="SELECT * FROM timescaledb.public.runs LIMIT 2", headers={**AUTH, "X-Trino-User": "nldt-agent"})
    assert r.status_code == 200
    body = r.json()
    assert [c["name"] for c in body["columns"]] == ["run_id", "verdict"]
    assert len(body["data"]) == 2
    assert all(row[1] == "pass" for row in body["data"])  # echte canonieke verdicts


def test_write_forbidden_403():
    r = client.post("/v1/statement", content="DELETE FROM timescaledb.public.runs", headers=AUTH)
    assert r.status_code == 403
    assert r.json()["error"] == "write-forbidden"


def test_unsupported_400():
    r = client.post("/v1/statement", content="SELECT count(*) FROM x", headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error"] == "unsupported-statement"


def test_requires_bearer():
    assert client.post("/v1/statement", content="SHOW SCHEMAS FROM timescaledb").status_code == 401
