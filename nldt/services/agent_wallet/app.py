"""Agent virtual wallet sidecar (:8088).

Holds agent credentials, enforces capability fail-closed access, and
presents credentials to the wallet auth edge (:8087) in exchange for
tokens. Started via `NLDT_START_WALLET=1 scripts/start-services.sh`.
"""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="nLDT Agent Virtual Wallet", version="0.1.0")

# W1 mock agent credential — replaced in W6 by an administration-issued
# credential (Keycloak OID4VCI, EBW-style delegation attestation; see
# nldt/16-eid-wallet-identity.md §6a + decision 10).
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


class TokenRequest(BaseModel):
    capability: str


def _find_credential(capability: str) -> dict | None:
    for cred in DEMO_CREDENTIALS:
        if capability in cred["capabilities"]:
            return cred
    return None


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
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="auth edge unavailable") from exc
    return resp.json()


@app.get("/credentials")
async def credentials() -> list[dict]:
    return [{field: cred[field] for field in _PUBLIC_FIELDS} for cred in DEMO_CREDENTIALS]


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_AGENT_WALLET_PORT", "8088"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
