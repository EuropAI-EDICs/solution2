from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

SCHEME_ID = "euLdtToolboxBearer"
CHALLENGE = {"WWW-Authenticate": "Bearer"}


def auth_mode() -> str:
    return os.environ.get("A2A_SIM_AUTH", "off").strip().lower()


def static_tokens() -> list[str]:
    raw = os.environ.get("NLDT_STATIC_TOKENS", "sim-toolbox-token")
    return [t.strip() for t in raw.split(",") if t.strip()]


def extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def token_valid(token: str | None) -> bool:
    if auth_mode() != "static":
        return True
    if not token:
        return False
    return token in static_tokens()


def path_requires_auth(path: str) -> bool:
    return path.startswith("/a2a/")


class ToolboxBearerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if auth_mode() != "static" or not path_requires_auth(request.url.path):
            return await call_next(request)
        token = extract_bearer(request.headers.get("Authorization"))
        if not token_valid(token):
            return JSONResponse(
                status_code=401,
                content={"error": "Bearer token required (EU LDT Toolbox IM)"},
                headers=CHALLENGE,
            )
        return await call_next(request)
