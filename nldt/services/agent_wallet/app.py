"""Agent virtual wallet sidecar (:8088).

Holds agent credentials, enforces capability fail-closed access, and
presents credentials to the wallet auth edge (:8087) in exchange for
tokens. Started via `NLDT_START_WALLET=1 scripts/start-services.sh`.

W6a: credentials come from the agent registry
(``NLDT_AGENT_CREDENTIALS_FILE`` or the packaged ``data/agent-clients.json``)
— the W1 mock list remains the built-in default so offline dev/tests are
unchanged. With ``NLDT_AGENT_WALLET_BACKEND=keycloak`` the sidecar first
obtains a real OAuth2 ``client_credentials`` token from the testbed Keycloak
(EU LDT Identity Management) using the per-agent secret from the env var
named in the registry (``secretEnv``), then presents it to the edge's
KeycloakBackend for verification. Every failure mode is fail-closed: no
secret, unreachable Keycloak or a rejected presentation never falls back to
the mock credential.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.auth_wallet.backend import load_agent_registry

app = FastAPI(title="nLDT Agent Virtual Wallet", version="0.2.0")

# W1 mock agent credentials — fallback when no registry resolves (offline
# dev without the packaged data file; tests rely on this shape).
DEMO_CREDENTIALS: list[dict] = [
    {
        "agentId": "beleidskompas-svc",
        "deployingOrg": "Provincie Test",
        "assurance": "attested",
        "capabilities": [
            "beleidskompas-omgevingsanalyse",
            "breda-scan-qa",
            "fetch-features",
            "spatial-intersection",
            "compute-area-statistics",
            "breda-scan-query",
        ],
    }
]

# Redaction allow-list: only these credential fields are ever exposed.
_PUBLIC_FIELDS = ("agentId", "deployingOrg", "assurance", "capabilities")


def _load_credentials() -> list[dict]:
    try:
        registry = load_agent_registry()
    except (OSError, ValueError, KeyError):
        return DEMO_CREDENTIALS
    return list(registry.values()) if registry else DEMO_CREDENTIALS


_CREDENTIALS: list[dict] = _load_credentials()


def _wallet_backend() -> str:
    return os.environ.get("NLDT_AGENT_WALLET_BACKEND", "mock").strip().lower()


def _agent_secret_env(cred: dict) -> str:
    if cred.get("secretEnv"):
        return cred["secretEnv"]
    # Derive a stable env name: NLDT_AGENT_<AGENTID>_CLIENT_SECRET
    return "NLDT_AGENT_" + str(cred.get("agentId", "")).upper().replace("-", "_") + "_CLIENT_SECRET"


def _find_credential(capability: str) -> dict | None:
    for cred in _CREDENTIALS:
        if capability in cred["capabilities"]:
            return cred
    return None


class TokenRequest(BaseModel):
    capability: str


@app.post("/token")
async def token(body: TokenRequest) -> dict:
    cred = _find_credential(body.capability)
    if cred is None:
        raise HTTPException(
            status_code=403,
            detail=f"no credential covers capability {body.capability!r}",
        )
    base_url = os.environ.get("NLDT_AUTH_WALLET_URL")
    if not base_url:
        raise HTTPException(
            status_code=503,
            detail="NLDT_AUTH_WALLET_URL not configured; failing closed",
        )
    if _wallet_backend() == "keycloak":
        presentation = await _keycloak_presentation(cred)
    else:
        presentation = {
            "subject_type": "agent",
            "presentation_id": cred["agentId"],
            "credential_issuer": cred["deployingOrg"],
        }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/present", json={"presentation": presentation}
            )
            if resp.status_code >= 400:
                # Status checked explicitly: the edge's 401/503 (rejected
                # presentation / unavailable verifier) must not leak as an
                # unhandled httpx exception type across httpx versions.
                raise HTTPException(
                    status_code=502,
                    detail=f"auth edge rejected presentation (HTTP {resp.status_code})",
                )
    except HTTPException:
        raise
    except Exception as exc:  # transport errors (connection refused, timeouts)
        raise HTTPException(status_code=502, detail="auth edge unavailable") from exc
    return resp.json()


async def _keycloak_presentation(cred: dict) -> dict[str, Any]:
    """Obtain a Keycloak client_credentials token and build the W6a presentation.

    Fail closed on any missing configuration or transport error — the mock
    credential is never a fallback in keycloak mode.
    """
    secret_env = _agent_secret_env(cred)
    secret = os.environ.get(secret_env, "")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail=f"{secret_env} not configured; failing closed",
        )
    if not os.environ.get("KEYCLOAK_URL", "").strip():
        raise HTTPException(
            status_code=503,
            detail="KEYCLOAK_URL not configured; failing closed",
        )
    try:
        kc_token = await _fetch_client_token(cred["agentId"], secret)
    except HTTPException:
        raise
    except Exception as exc:  # httpx errors, non-2xx from Keycloak
        raise HTTPException(status_code=502, detail=f"keycloak unavailable: {exc}") from exc
    return {
        "subject_type": "agent",
        "agentId": cred["agentId"],
        "keycloak_token": kc_token,
    }


async def _fetch_client_token(client_id: str, secret: str) -> str:
    """Async wrapper so tests can monkeypatch one seam (sync token fetch)."""
    from services.adapters.keycloak_auth import get_client_token

    return get_client_token(client_id, secret)


@app.get("/credentials")
async def credentials() -> list[dict]:
    return [{field: cred[field] for field in _PUBLIC_FIELDS} for cred in _CREDENTIALS]


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_AGENT_WALLET_PORT", "8088"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
