from __future__ import annotations

import os
import time
from typing import Any

import httpx

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def _config() -> dict[str, str]:
    return {
        "url": os.environ.get("KEYCLOAK_URL", os.environ.get("KEYCLOAK_HOST", "")).rstrip("/"),
        "realm": os.environ.get("KEYCLOAK_REALM", "LDT"),
        "client_id": os.environ.get("KEYCLOAK_CLIENT_ID", os.environ.get("NLDT_SERVICE_CLIENT_ID", "")),
        "client_secret": os.environ.get("KEYCLOAK_CLIENT_SECRET", os.environ.get("NLDT_SERVICE_CLIENT_SECRET", "")),
    }


def is_configured() -> bool:
    cfg = _config()
    return bool(cfg["url"] and cfg["client_id"] and cfg["client_secret"])


def get_service_token(force_refresh: bool = False) -> str:
    """OAuth2 client_credentials token for nLDT service accounts (EU LDT IM)."""
    now = time.time()
    if not force_refresh and _token_cache["token"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["token"]

    cfg = _config()
    if not is_configured():
        raise RuntimeError("Keycloak not configured (KEYCLOAK_URL, CLIENT_ID, CLIENT_SECRET)")

    token_url = f"{cfg['url']}/realms/{cfg['realm']}/protocol/openid-connect/token"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + float(data.get("expires_in", 300))
    return _token_cache["token"]


def auth_headers(token: str | None = None) -> dict[str, str]:
    if token:
        return {"Authorization": f"Bearer {token}"}
    if is_configured():
        return {"Authorization": f"Bearer {get_service_token()}"}
    return {}


def clear_token_cache() -> None:
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0.0
