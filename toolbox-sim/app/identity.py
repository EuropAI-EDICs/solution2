# toolbox-sim/app/identity.py
"""EU LDT Identity Management-sim: OIDC client_credentials, realm LDT."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import JSONResponse

from app.guards import add_provenance
from app.jwtutil import mint_token

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TTL_S = 300


def _clients() -> dict:
    return json.loads((FIXTURES / "clients.json").read_text())["clients"]


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim identity", docs_url=None, openapi_url=None)
    add_provenance(app, "identity")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/realms/{realm}/protocol/openid-connect/token")
    def token(
        realm: str,
        grant_type: str = Form(default=""),
        client_id: str = Form(default=""),
        client_secret: str = Form(default=""),
    ) -> dict:
        if realm != "LDT":
            raise HTTPException(status_code=404, detail={"error": "realm_not_found"})
        known = _clients().get(client_id)
        if grant_type != "client_credentials" or not known or known["secret"] != client_secret:
            # Top-level {"error": ...} zoals Keycloak; HTTPException-detail wordt in
            # {"detail": ...} gewrapped en breekt daarmee de tokenendpoint-contracten.
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_client", "error_description": "Client not found or invalid secret"},
            )
        return {
            "access_token": mint_token(client_id, known["groups"], ttl_s=TTL_S),
            "expires_in": TTL_S,
            "token_type": "Bearer",
        }

    return app
