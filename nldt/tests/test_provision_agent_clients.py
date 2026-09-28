from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

NLDT = Path(__file__).resolve().parents[1]


def _load_script():
    path = NLDT / "scripts" / "provision_agent_clients.py"
    spec = importlib.util.spec_from_file_location("provision_agent_clients", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["provision_agent_clients"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _path():
    if str(NLDT) not in sys.path:
        sys.path.insert(0, str(NLDT))


class FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.content = json.dumps(payload).encode() if payload is not None else b""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeKeycloak:
    """Minimal Keycloak Admin API state machine for the provisioning flow."""

    def __init__(self):
        self.clients = {}  # clientId -> internal id
        self.roles = {}  # role name -> role object
        self.mappings = {"sa-1": []}  # user id -> [role objects]
        self.attrs = {}  # internal id -> attributes dict
        self.requests = []

    def handle(self, method: str, url: str, body=None) -> FakeResp:
        self.requests.append((method, url, body))
        if method == "GET":
            if "/clients?clientId=" in url:
                cid = url.split("clientId=", 1)[1]
                matches = [
                    {"clientId": other, "id": internal}
                    for other, internal in self.clients.items()
                    if other == cid
                ]
                return FakeResp(payload=matches)
            if "/service-account-user" in url:
                return FakeResp(payload={"id": "sa-1"})
            if "/role-mappings/realm" in url:
                return FakeResp(payload=self.mappings["sa-1"])
            if "/roles/" in url:
                name = url.rsplit("/roles/", 1)[1]
                return FakeResp(payload=self.roles[name]) if name in self.roles else FakeResp(status_code=404)
            if "/clients/" in url:
                internal = url.rsplit("/clients/", 1)[1]
                return FakeResp(payload={"id": internal, "attributes": self.attrs.get(internal, {})})
            raise AssertionError(f"unexpected GET {url}")
        if method == "POST":
            if url.endswith("/clients"):
                internal = f"uuid-{len(self.clients) + 1}"
                self.clients[body["clientId"]] = internal
                self.attrs[internal] = dict(body.get("attributes") or {})
                return FakeResp(status_code=201)
            if url.endswith("/roles"):
                self.roles[body["name"]] = {"id": f"role-{len(self.roles) + 1}", "name": body["name"]}
                return FakeResp(status_code=201)
            if "/role-mappings/realm" in url:
                self.mappings["sa-1"].extend(body)
                return FakeResp(status_code=204)
            if url.endswith("/client-secret"):
                return FakeResp(payload={"value": "new-secret"})
            raise AssertionError(f"unexpected POST {url}")
        if method == "PUT":
            if "/clients/" in url:
                internal = url.rsplit("/clients/", 1)[1]
                self.attrs[internal] = {**self.attrs.get(internal, {}), **(body or {}).get("attributes", {})}
                return FakeResp(status_code=204)
            raise AssertionError(f"unexpected PUT {url}")
        raise AssertionError(f"unexpected {method} {url}")


@pytest.fixture
def fake_keycloak(monkeypatch):
    prov = _load_script()
    state = FakeKeycloak()

    def fake_get(url, headers=None, timeout=None):
        return state.handle("GET", url)

    def fake_post(url, headers=None, json=None, timeout=None):
        return state.handle("POST", url, json)

    def fake_put(url, headers=None, json=None, timeout=None):
        return state.handle("PUT", url, json)

    monkeypatch.setattr(prov.httpx, "get", fake_get)
    monkeypatch.setattr(prov.httpx, "post", fake_post)
    monkeypatch.setattr(prov.httpx, "put", fake_put)
    monkeypatch.setattr(prov, "_admin_token", lambda base_url: "admin-token")
    return prov, state


REGISTRY_ENTRY = {
    "agentId": "test-agent",
    "deployingOrg": "Provincie Test",
    "assurance": "attested",
    "capabilities": ["breda-scan-query", "crosstrack-overlay"],
}


def _api(prov):
    return prov.AdminAPI("http://kc.test", "LDT", "admin-token")


def test_first_run_creates_client_roles_assignments(fake_keycloak):
    prov, state = fake_keycloak
    actions = prov.provision_agent(_api(prov), REGISTRY_ENTRY, dry_run=False, rotate_secret=False)
    joined = " | ".join(actions)
    assert "create client test-agent" in joined
    assert "nldt-capability.breda-scan-query" in joined
    assert "nldt-capability.crosstrack-overlay" in joined
    assert "assign roles" in joined
    # Creation already carries the registry attributes (Keycloak stores them
    # on POST /clients), so no attribute update is needed on the first run.
    assert "update attributes" not in joined
    assert state.clients == {"test-agent": "uuid-1"}
    assert set(state.roles) == {
        "nldt-capability.breda-scan-query",
        "nldt-capability.crosstrack-overlay",
    }
    assert {r["name"] for r in state.mappings["sa-1"]} == set(state.roles)
    assert state.attrs["uuid-1"]["nldt:assurance"] == ["attested"]


def test_attribute_drift_converges(fake_keycloak):
    prov, state = fake_keycloak
    api = _api(prov)
    prov.provision_agent(api, REGISTRY_ENTRY, dry_run=False, rotate_secret=False)
    # Simulate drift: someone edited the deployingOrg attribute out-of-band.
    state.attrs["uuid-1"]["nldt:deployingOrg"] = ["Gemeente Anders"]
    actions = prov.provision_agent(api, REGISTRY_ENTRY, dry_run=False, rotate_secret=False)
    joined = " | ".join(actions)
    assert "update attributes" in joined
    assert state.attrs["uuid-1"]["nldt:deployingOrg"] == ["Provincie Test"]


def test_second_run_is_idempotent(fake_keycloak):
    prov, _ = fake_keycloak
    api = _api(prov)
    prov.provision_agent(api, REGISTRY_ENTRY, dry_run=False, rotate_secret=False)
    actions = prov.provision_agent(api, REGISTRY_ENTRY, dry_run=False, rotate_secret=False)
    assert actions == []


def test_dry_run_changes_nothing(fake_keycloak):
    prov, state = fake_keycloak
    actions = prov.provision_agent(_api(prov), REGISTRY_ENTRY, dry_run=True, rotate_secret=False)
    assert actions, "dry run should list the actions it would take"
    assert state.clients == {}
    assert state.roles == {}
    assert state.mappings == {"sa-1": []}


def test_rotate_secret_prints_env_hint(fake_keycloak, capsys, monkeypatch):
    prov, _ = fake_keycloak
    entry = {**REGISTRY_ENTRY, "secretEnv": "NLDT_AGENT_TEST_SECRET"}
    prov.provision_agent(_api(prov), entry, dry_run=False, rotate_secret=True)
    err = capsys.readouterr().err
    assert "NLDT_AGENT_TEST_SECRET=new-secret" in err


def test_main_dry_run_smoke(fake_keycloak, tmp_path, capsys, monkeypatch):
    prov, _ = fake_keycloak
    monkeypatch.setenv("KEYCLOAK_URL", "http://kc.test")
    registry = tmp_path / "agents.json"
    registry.write_text(json.dumps({"agents": [REGISTRY_ENTRY]}))
    code = prov.main(["--registry", str(registry), "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "[test-agent] create client test-agent" in out
