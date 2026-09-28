"""OAuth2 client-credentials access to EU LDT Identity Management (Keycloak).

Two principals exist since W6a:

- the *service* principal (nLDT's own service account) via
  ``get_service_token()`` — unchanged behavior, cached module-wide;
- *agent* principals (virtual-wallet clients, one per agent in
  ``data/agent-clients.json``) via ``get_client_token(client_id, secret)`` —
  cached per client id so several agents can hold tokens side by side.

Both post ``grant_type=client_credentials`` to the realm token endpoint
(``KEYCLOAK_URL`` may be raw Keycloak or the Identity tool's
``/protocol/openid-connect`` proxy — same paths).
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}
_client_token_cache: dict[str, dict[str, Any]] = {}


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


def _realm_token_url(cfg: dict[str, str]) -> str:
    return f"{cfg['url']}/realms/{cfg['realm']}/protocol/openid-connect/token"


def _request_token(client_id: str, client_secret: str) -> tuple[str, float]:
    """POST client_credentials; returns (access_token, expires_at)."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            _realm_token_url(_config()),
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
    return data["access_token"], time.time() + float(data.get("expires_in", 300))


def get_client_token(client_id: str, client_secret: str, *, force_refresh: bool = False) -> str:
    """OAuth2 client_credentials token for an arbitrary principal (W6a agents).

    Cached per client id with the same 30 s expiry headroom as the service
    token. Raises when Keycloak is unreachable or rejects the credentials —
    callers (the agent virtual wallet) fail closed on any error.
    """
    now = time.time()
    cached = _client_token_cache.get(client_id)
    if not force_refresh and cached and cached["expires_at"] > now + 30:
        return cached["token"]
    if not _config()["url"]:
        raise RuntimeError("Keycloak not configured (KEYCLOAK_URL)")
    token, expires_at = _request_token(client_id, client_secret)
    _client_token_cache[client_id] = {"token": token, "expires_at": expires_at}
    return token


def get_service_token(force_refresh: bool = False) -> str:
    """OAuth2 client_credentials token for nLDT service accounts (EU LDT IM)."""
    now = time.time()
    if not force_refresh and _token_cache["token"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["token"]

    cfg = _config()
    if not is_configured():
        raise RuntimeError("Keycloak not configured (KEYCLOAK_URL, CLIENT_ID, CLIENT_SECRET)")

    token, expires_at = _request_token(cfg["client_id"], cfg["client_secret"])
    _token_cache["token"] = token
    _token_cache["expires_at"] = expires_at
    return token


def auth_headers(token: str | None = None) -> dict[str, str]:
    if token:
        return {"Authorization": f"Bearer {token}"}
    if is_configured():
        return {"Authorization": f"Bearer {get_service_token()}"}
    return {}


def clear_token_cache() -> None:
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0.0
    _client_token_cache.clear()
