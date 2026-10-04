# toolbox-sim/app/guards.py
"""Auth-dependency + herkomst-header voor alle sim-diensten."""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.jwtutil import STATIC_TOKEN, InvalidToken, verify_token

STATIC_PRINCIPAL = {
    "sub": "static-mesh",
    "groups": ["/context-data/default/User", "/data-query/timescaledb/User"],
    "toolbox-sim": True,
}


def require_bearer(authorization: str = Header(default="")) -> dict:
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :]
        if token == STATIC_TOKEN:
            return dict(STATIC_PRINCIPAL)
        try:
            return verify_token(token)
        except InvalidToken as exc:
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_token", "error_description": str(exc)},
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    raise HTTPException(
        status_code=401,
        detail={"error": "invalid_token", "error_description": "missing bearer token"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def add_provenance(app: FastAPI, solution: str) -> None:
    @app.middleware("http")
    async def _provenance(request: Request, call_next):
        response: JSONResponse = await call_next(request)
        response.headers.setdefault("X-Sim-Provenance", f"toolbox-sim/{solution}")
        return response


def provenance_detail(value: str) -> dict:
    return {"X-Sim-Provenance": value}
