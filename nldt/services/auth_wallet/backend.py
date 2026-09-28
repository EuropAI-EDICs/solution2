"""Pluggable presentation verifiers for the wallet token edge.

W1 ships the MockBackend (ARF-shaped envelopes, local trust anchor — never a
production configuration). W2 adds a real OpenID4VP backend (Keycloak toolbox
IM or pyeudiw) behind the same interface; ARF requirement IDs are pinned
there, not simulated here.

W6a adds the KeycloakBackend: machine credentials for agents via OAuth2
``client_credentials`` against the testbed Keycloak (EU LDT Identity
Management). This is the *interim* issuance path — the end state remains an
EBW-style organisational delegation attestation via OID4VCI (doc 16, decision
10), which will slot in as another backend behind the same interface.

Doctrine: fail closed. Any missing claim, inactive token, unknown client or
registry/Keycloak disagreement rejects the presentation (ValueError -> 401 at
the edge). The backend never invents claims: ``deployingOrg``/``assurance``
come from the administration-maintained agent registry, ``capabilities`` are
the *intersection* of the registry and the roles Keycloak actually granted
(defense in depth against capability drift — the risk table of doc 16 §8).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

# Administration-defined agent assurance scale (never an eIDAS human LoA).
MOCK_PRESENTATIONS: dict[str, dict[str, Any]] = {
    "mock-user-1": {
        "subject_type": "human",
        "sub": "mock-user-1",
        "loa": "substantial",
        "org": "Provincie Test",
        "roles": ["policy-officer"],
    },
    "beleidskompas-svc": {
        "subject_type": "agent",
        "agentId": "beleidskompas-svc",
        "deployingOrg": "Provincie Test",
        "capabilities": ["beleidskompas-omgevingsanalyse", "breda-scan-query"],
        "assurance": "attested",
    },
}

#: Realm roles with this prefix are the Keycloak-side capability binding; the
#: provisioning script (scripts/provision_agent_clients.py) creates
#: ``nldt-capability.<process-or-recipe-id>`` per registry capability.
CAPABILITY_ROLE_PREFIX = "nldt-capability."

_ASSURANCE_ENUM = ("basic", "attested", "audited")

_DEFAULT_REGISTRY = os.path.join("data", "agent-clients.json")


def default_registry_path() -> str:
    """Absolute path of the packaged registry (nldt/data/agent-clients.json)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), _DEFAULT_REGISTRY)


def load_agent_registry(path: str | None = None) -> dict[str, dict[str, Any]]:
    """Load the agent registry keyed by agentId (= Keycloak clientId).

    Source: ``NLDT_AGENT_CREDENTIALS_FILE`` or the packaged default. Secrets
    never live here — only the env-var *name* that holds them at runtime.
    """
    resolved = path or os.environ.get("NLDT_AGENT_CREDENTIALS_FILE", "").strip() or default_registry_path()
    with open(resolved, encoding="utf-8") as fh:
        registry = json.load(fh)
    agents = registry.get("agents", [])
    if not isinstance(agents, list):
        raise ValueError("agent registry must contain an 'agents' list")
    return {entry["agentId"]: entry for entry in agents if isinstance(entry, dict) and entry.get("agentId")}


class VerifierBackend:
    async def verify(self, presentation: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MockBackend(VerifierBackend):
    """Deterministic mock: presentation_id selects a known subject."""

    async def verify(self, presentation: dict[str, Any]) -> dict[str, Any]:
        pid = presentation.get("presentation_id")
        if pid not in MOCK_PRESENTATIONS:
            raise ValueError(f"unknown presentation: {pid}")
        return dict(MOCK_PRESENTATIONS[pid])


class KeycloakBackend(VerifierBackend):
    """Verify agent presentations backed by Keycloak client_credentials.

    Presentation shape (produced by the agent virtual wallet, W6a mode):
    ``{"subject_type": "agent", "agentId": <clientId>, "keycloak_token": ...}``.

    Verification steps (all fail closed):
    1. RFC 7662 introspection of the token with the edge's own confidential
       client (``KEYCLOAK_INTROSPECT_CLIENT_ID``/``_SECRET``, falling back to
       ``KEYCLOAK_CLIENT_ID``/``_SECRET`` — same env names as
       ``services/common/auth.py`` so one configuration serves both).
    2. ``active`` must be true and the token's authorized party (``azp``)
       must equal the presented ``agentId`` — an agent may never present
       another principal's token.
    3. Claims are assembled from the administration registry (deployingOrg,
       assurance) crossed with the realm/resource roles Keycloak actually
       granted: effective capabilities = registry ∩ granted roles. An
       intersection that comes out empty rejects the presentation.
    """

    def __init__(self, registry_path: str | None = None) -> None:
        self._registry_path = registry_path

    async def verify(self, presentation: dict[str, Any]) -> dict[str, Any]:
        if presentation.get("subject_type") != "agent":
            raise ValueError("keycloak backend verifies agent presentations only")
        agent_id = presentation.get("agentId")
        kc_token = presentation.get("keycloak_token")
        if not agent_id or not kc_token:
            raise ValueError("agent presentation requires agentId and keycloak_token")

        intro = await self.introspect(kc_token)
        if not intro.get("active"):
            raise ValueError("keycloak token not active")
        azp = intro.get("azp") or intro.get("client_id")
        if azp != agent_id:
            raise ValueError(f"token authorized party {azp!r} != agentId {agent_id!r}")

        registry = load_agent_registry(self._registry_path)
        entry = registry.get(agent_id)
        if entry is None:
            raise ValueError(f"agent client {agent_id!r} not in registry")

        granted = self._granted_capabilities(intro)
        requested = set(entry.get("capabilities") or [])
        effective = sorted(requested & granted)
        if not effective:
            raise ValueError(f"no capability roles granted for {agent_id!r} (registry/Keycloak drift)")

        assurance = entry.get("assurance", "")
        if assurance not in _ASSURANCE_ENUM:
            raise ValueError(f"registry assurance {assurance!r} not in {_ASSURANCE_ENUM}")
        deploying_org = entry.get("deployingOrg", "")
        if not deploying_org:
            raise ValueError(f"registry entry for {agent_id!r} lacks deployingOrg")

        return {
            "subject_type": "agent",
            "agentId": agent_id,
            "deployingOrg": deploying_org,
            "capabilities": effective,
            "assurance": assurance,
        }

    async def introspect(self, token: str) -> dict[str, Any]:
        """RFC 7662 introspection against the realm (or Identity tool proxy)."""
        url = os.environ.get("KEYCLOAK_URL", "").rstrip("/")
        realm = os.environ.get("KEYCLOAK_REALM", "LDT")
        client_id = os.environ.get("KEYCLOAK_INTROSPECT_CLIENT_ID", os.environ.get("KEYCLOAK_CLIENT_ID", ""))
        client_secret = os.environ.get(
            "KEYCLOAK_INTROSPECT_CLIENT_SECRET", os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
        )
        if not url or not client_id or not client_secret:
            raise RuntimeError(
                "keycloak verifier requires KEYCLOAK_URL and KEYCLOAK_(INTROSPECT_)CLIENT_ID/SECRET"
            )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{url}/realms/{realm}/protocol/openid-connect/token/introspect",
                data={"token": token, "client_id": client_id, "client_secret": client_secret},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _granted_capabilities(intro: dict[str, Any]) -> set[str]:
        """Union of capability roles across realm_access and resource_access."""
        roles: set[str] = set((intro.get("realm_access") or {}).get("roles") or [])
        for client_roles in (intro.get("resource_access") or {}).values():
            roles |= set((client_roles or {}).get("roles") or [])
        return {role[len(CAPABILITY_ROLE_PREFIX):] for role in roles if role.startswith(CAPABILITY_ROLE_PREFIX)}


def select_backend() -> VerifierBackend:
    """NLDT_WALLET_VERIFIER=mock|keycloak (default mock, offline-safe)."""
    mode = os.environ.get("NLDT_WALLET_VERIFIER", "mock").strip().lower()
    if mode == "keycloak":
        return KeycloakBackend()
    if mode == "mock":
        return MockBackend()
    raise RuntimeError(f"unknown NLDT_WALLET_VERIFIER: {mode!r} (expected mock|keycloak)")
