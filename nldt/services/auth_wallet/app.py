from __future__ import annotations

import hashlib
import os
import secrets
import time
from typing import Any

from fastapi import FastAPI, Form, HTTPException
from pydantic import BaseModel

from services.auth_wallet.backend import VerifierBackend, select_backend
from services.common.schema import validate_instance

app = FastAPI(title="nLDT Wallet Auth Edge", version="0.1.0")

# Verifier selection (W6a): NLDT_WALLET_VERIFIER=mock|keycloak, resolved
# lazily per request (same re-read pattern as the trust policy) so flipping
# the env needs no restart. Tests assign a backend directly; None = env.
_BACKEND: VerifierBackend | None = None


def _backend() -> VerifierBackend:
    if _BACKEND is not None:
        return _BACKEND
    return select_backend()
# SHA-256(token) -> (expires_at, claims)
_TOKENS: dict[str, tuple[float, dict[str, Any]]] = {}


class PresentRequest(BaseModel):
    presentation: dict[str, Any]


def _ttl() -> int:
    return int(os.environ.get("NLDT_WALLET_TOKEN_TTL", "300"))


@app.post("/present")
async def present(body: PresentRequest) -> dict[str, Any]:
    try:
        claims = await _backend().verify(body.presentation)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        # Unavailable verifier/registry/config: fail closed but distinguish
        # infrastructure errors from rejected presentations (503, not 401).
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    claims["exp"] = time.time() + _ttl()
    validate_instance(claims, "wallet-claims.schema.json")
    token = secrets.token_hex(16)
    _TOKENS[hashlib.sha256(token.encode()).hexdigest()] = (claims["exp"], claims)
    return {"token": token, "expiresIn": _ttl(), "claims": claims}


@app.post("/introspect")
async def introspect(token: str = Form(...)) -> dict[str, Any]:
    entry = _TOKENS.get(hashlib.sha256(token.encode()).hexdigest())
    if not entry or entry[0] <= time.time():
        return {"active": False}
    return {"active": True, **entry[1]}


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_AUTH_WALLET_PORT", "8087"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
