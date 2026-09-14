"""Shared bearer-token gate for nLDT FastAPI services (beleidskompas BK-1).

NLDT_AUTH_MODE: off (default, dev/tests) | static (NLDT_STATIC_TOKENS,
comma-separated, fail closed) | keycloak (RFC 7662 introspection against
EU LDT Identity Management).
"""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import HTTPException, Request

_CHALLENGE = {"WWW-Authenticate": "Bearer"}

logger = logging.getLogger("nldt.auth")


def auth_mode() -> str:
    return os.environ.get("NLDT_AUTH_MODE", "off").strip().lower()


def _static_tokens() -> list[str]:
    raw = os.environ.get("NLDT_STATIC_TOKENS", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


async def introspect_keycloak(token: str) -> bool:
    url = os.environ.get("KEYCLOAK_URL", "").rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "LDT")
    client_id = os.environ.get("KEYCLOAK_INTROSPECT_CLIENT_ID", os.environ.get("KEYCLOAK_CLIENT_ID", ""))
    client_secret = os.environ.get(
        "KEYCLOAK_INTROSPECT_CLIENT_SECRET", os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
    )
    if not url or not client_id or not client_secret:
        raise RuntimeError("keycloak auth mode requires KEYCLOAK_URL, KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{url}/realms/{realm}/protocol/openid-connect/token/introspect",
            data={"token": token, "client_id": client_id, "client_secret": client_secret},
        )
    resp.raise_for_status()
    return bool(resp.json().get("active"))


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers=_CHALLENGE)


async def require_bearer(request: Request) -> None:
    mode = auth_mode()
    if mode == "off":
        return
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("missing bearer token")
    if mode == "static":
        if token not in _static_tokens():
            raise _unauthorized("invalid token")
        return
    if mode == "keycloak":
        try:
            active = await introspect_keycloak(token)
        except Exception as exc:
            logger.warning("token introspection failed: %s", exc)
            raise HTTPException(status_code=503, detail="token introspection unavailable") from exc
        if not active:
            raise _unauthorized("invalid token")
        return
    raise HTTPException(status_code=500, detail=f"unknown NLDT_AUTH_MODE: {mode}")
