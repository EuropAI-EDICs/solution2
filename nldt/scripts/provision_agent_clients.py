"""Provision agent service-account clients in the testbed Keycloak (W6a).

Reads the declarative agent registry (default ``data/agent-clients.json``,
same file the agent virtual wallet and the auth-edge KeycloakBackend use)
and makes the realm match it, idempotently:

1. one Keycloak client per agent — ``serviceAccountsEnabled: true``, secret
   kept in the env var named by the registry's ``secretEnv`` (never printed
   to the registry, only to the operator on creation/rotation);
2. one *realm role* per capability, named ``nldt-capability.<capability>``
   (the prefix the auth-edge backend strips when computing effective
   capabilities — see ``services/auth_wallet/backend.py``);
3. those roles assigned to the client's service-account user, so the roles
   appear in the tokens the agent presents;
4. client attributes ``nldt:deployingOrg`` / ``nldt:assurance`` mirroring
   the registry (documentation/audit; enforcement reads the registry).

Authentication: ``KEYCLOAK_ADMIN_TOKEN`` directly, or
``KEYCLOAK_ADMIN_USER``/``KEYCLOAK_ADMIN_PASSWORD`` (password grant on
``KEYCLOAK_ADMIN_REALM``, default ``master``). ``KEYCLOAK_URL`` points at
the Keycloak behind EU LDT Identity Management (the realm the Identity
tool manages); the tool's Spring wrapper is intentionally not used because
role-to-service-account assignment needs the Admin API.

Usage:
    PYTHONPATH=. python scripts/provision_agent_clients.py [--dry-run] \\
        [--rotate-secret] [--registry data/agent-clients.json]

Never auto-applies anything beyond this registry, never disables or deletes
existing clients, and exits non-zero on the first failed call.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

from services.auth_wallet.backend import CAPABILITY_ROLE_PREFIX, default_registry_path

ADMIN_TIMEOUT = 30.0


class AdminAPI:
    def __init__(self, base_url: str, realm: str, token: str) -> None:
        self.base = base_url.rstrip("/")
        self.realm = realm
        self.headers = {"Authorization": f"Bearer {token}"}

    def _url(self, path: str) -> str:
        return f"{self.base}/admin/realms/{self.realm}{path}"

    def get(self, path: str) -> Any:
        resp = httpx.get(self._url(path), headers=self.headers, timeout=ADMIN_TIMEOUT)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def post(self, path: str, body: dict | None = None) -> httpx.Response:
        return httpx.post(self._url(path), headers=self.headers, json=body, timeout=ADMIN_TIMEOUT)

    def put(self, path: str, body: dict | None = None) -> httpx.Response:
        return httpx.put(self._url(path), headers=self.headers, json=body, timeout=ADMIN_TIMEOUT)


def _admin_token(base_url: str) -> str:
    explicit = os.environ.get("KEYCLOAK_ADMIN_TOKEN", "").strip()
    if explicit:
        return explicit
    user = os.environ.get("KEYCLOAK_ADMIN_USER", "").strip()
    password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")
    if not user:
        raise RuntimeError("set KEYCLOAK_ADMIN_TOKEN or KEYCLOAK_ADMIN_USER/KEYCLOAK_ADMIN_PASSWORD")
    realm = os.environ.get("KEYCLOAK_ADMIN_REALM", "master")
    resp = httpx.post(
        f"{base_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli", "username": user, "password": password},
        timeout=ADMIN_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_client_internal_id(api: AdminAPI, client_id: str) -> str | None:
    found = api.get(f"/clients?clientId={client_id}")
    for client in found or []:
        if client.get("clientId") == client_id:
            return client["id"]
    return None


def _get_realm_role(api: AdminAPI, role_name: str) -> dict | None:
    resp = httpx.get(
        f"{api.base}/admin/realms/{api.realm}/roles/{role_name}",
        headers=api.headers,
        timeout=ADMIN_TIMEOUT,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _assigned_realm_role_names(api: AdminAPI, user_id: str) -> set[str]:
    mappings = api.get(f"/users/{user_id}/role-mappings/realm") or []
    return {m["name"] for m in mappings}


def provision_agent(api: AdminAPI, entry: dict, dry_run: bool, rotate_secret: bool) -> list[str]:
    """Converge one agent entry; returns the actions taken (or that a dry run would take)."""
    agent_id = entry["agentId"]
    capabilities = entry.get("capabilities") or []
    attributes = {
        "nldt:deployingOrg": [entry.get("deployingOrg", "")],
        "nldt:assurance": [entry.get("assurance", "")],
    }
    actions: list[str] = []

    internal_id = _get_client_internal_id(api, agent_id)
    if internal_id is None:
        actions.append(f"create client {agent_id} (service account enabled)")
        if dry_run:
            return actions
        resp = api.post(
            "/clients",
            {
                "clientId": agent_id,
                "enabled": True,
                "serviceAccountsEnabled": True,
                "publicClient": False,
                "attributes": attributes,
                "description": "nLDT agent (W6a), registry-managed",
            },
        )
        resp.raise_for_status()
        internal_id = _get_client_internal_id(api, agent_id)
        if internal_id is None:
            raise RuntimeError(f"client {agent_id} not found after creation")

    # Role set: one realm role per capability.
    role_objects: list[dict] = []
    for capability in capabilities:
        role_name = CAPABILITY_ROLE_PREFIX + capability
        role = _get_realm_role(api, role_name)
        if role is None:
            actions.append(f"create realm role {role_name}")
            if not dry_run:
                resp = api.post("/roles", {"name": role_name})
                resp.raise_for_status()
                role = _get_realm_role(api, role_name)
                if role is None:
                    raise RuntimeError(f"role {role_name} not found after creation")
        role_objects.append(role)

    # Assign the roles to the client's service-account user.
    sa_user = api.get(f"/clients/{internal_id}/service-account-user")
    if not sa_user or not sa_user.get("id"):
        raise RuntimeError(f"service-account user missing for {agent_id} (serviceAccountsEnabled?)")
    assigned = _assigned_realm_role_names(api, sa_user["id"])
    missing = [r for r in role_objects if r["name"] not in assigned]
    if missing:
        actions.append(
            "assign roles " + ", ".join(r["name"] for r in missing) + f" to service-account of {agent_id}"
        )
        if not dry_run:
            resp = api.post(f"/users/{sa_user['id']}/role-mappings/realm", missing)
            resp.raise_for_status()

    # Mirror registry metadata into client attributes (audit/documentation).
    existing_attrs = (api.get(f"/clients/{internal_id}") or {}).get("attributes") or {}
    if {k: v for k, v in attributes.items() if existing_attrs.get(k) != v}:
        actions.append(f"update attributes on {agent_id} (deployingOrg/assurance)")
        if not dry_run:
            merged = {**existing_attrs, **attributes}
            resp = api.put(f"/clients/{internal_id}", {"attributes": merged})
            resp.raise_for_status()

    if rotate_secret:
        secret_env = entry.get("secretEnv") or (
            "NLDT_AGENT_" + agent_id.upper().replace("-", "_") + "_CLIENT_SECRET"
        )
        actions.append(f"rotate client secret for {agent_id} (store in {secret_env})")
        if not dry_run:
            resp = httpx.post(
                f"{api.base}/admin/realms/{api.realm}/clients/{internal_id}/client-secret",
                headers=api.headers,
                timeout=ADMIN_TIMEOUT,
            )
            resp.raise_for_status()
            # Shown once on stderr (operator terminal only); never written to
            # any file, never printed to stdout where logs usually capture it.
            print(f"SECRET {secret_env}={resp.json().get('value', '')}", file=sys.stderr)

    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", default=default_registry_path(), help="agent registry JSON path")
    parser.add_argument("--realm", default=os.environ.get("KEYCLOAK_REALM", "LDT"))
    parser.add_argument("--dry-run", action="store_true", help="print actions, change nothing")
    parser.add_argument("--rotate-secret", action="store_true", help="(re)generate client secrets; prints env var names")
    args = parser.parse_args(argv)

    base_url = os.environ.get("KEYCLOAK_URL", "").rstrip("/")
    if not base_url:
        print("KEYCLOAK_URL is required", file=sys.stderr)
        return 2

    with open(args.registry, encoding="utf-8") as fh:
        registry = json.load(fh)
    agents = registry.get("agents", [])
    if not agents:
        print(f"no agents in {args.registry}", file=sys.stderr)
        return 2

    api = AdminAPI(base_url, args.realm, _admin_token(base_url))

    if args.dry_run:
        print(f"DRY RUN against {base_url} realm {args.realm} ({len(agents)} agent(s))")
        for entry in agents:
            for action in provision_agent(api, entry, dry_run=True, rotate_secret=args.rotate_secret):
                print(f"  [{entry['agentId']}] {action}")
        return 0

    total = 0
    for entry in agents:
        actions = provision_agent(api, entry, dry_run=False, rotate_secret=args.rotate_secret)
        total += len(actions)
        for action in actions or ["up to date"]:
            print(f"  [{entry['agentId']}] {action}")
    print(f"done: {total} action(s) across {len(agents)} agent(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
