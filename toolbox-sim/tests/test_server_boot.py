# toolbox-sim/tests/test_server_boot.py
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

SIM_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def sim():
    proc = subprocess.Popen([sys.executable, "-m", "app.server"], cwd=SIM_ROOT)
    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:9191/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            raise AssertionError("sim kwam niet op binnen 20 s")
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _token() -> str:
    r = httpx.post(
        "http://127.0.0.1:9191/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    return r.json()["access_token"]


def test_all_five_services_healthy(sim):
    for port in (9191, 9192, 9193, 9194, 9195):
        assert httpx.get(f"http://127.0.0.1:{port}/health").json()["status"] == "UP"


def test_broker_serves_canonical_fixture_over_http(sim):
    auth = {"Authorization": f"Bearer {_token()}", "NGSILD-Tenant": "ldt"}
    r = httpx.get("http://127.0.0.1:9192/ngsi-ld/v1/entities", params={"type": "ldt:OpportunityZone", "limit": 1000}, headers=auth)
    assert r.status_code == 200
    zones = r.json()
    assert zones and all(z["id"].startswith("urn:ldt:utrecht:zone:") for z in zones)
    assert r.headers["X-Sim-Provenance"].startswith("toolbox-sim/data-platform")
