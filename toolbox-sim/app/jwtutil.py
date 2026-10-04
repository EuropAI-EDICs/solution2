# toolbox-sim/app/jwtutil.py
"""HS256-JWTs voor de sim-IM. Dev-geheim, uitsluitend localhost-verkeer."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

SIGNING_SECRET = os.environ.get("TOOLBOX_SIM_JWT_SECRET", "toolbox-sim-dev-secret")
STATIC_TOKEN = "sim-toolbox-token"
ISSUER = "http://127.0.0.1:9191/realms/LDT"


class InvalidToken(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def mint_token(client_id: str, groups: list[str], ttl_s: int = 300) -> str:
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "sub": client_id,
        "iat": now,
        "exp": now + ttl_s,
        "groups": list(groups),
        "toolbox-sim": True,
    }
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = hmac.new(SIGNING_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64(sig)}"


def verify_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidToken("malformed token")
    header, body, sig = parts
    expected = hmac.new(SIGNING_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    try:
        sig_bytes = _unb64(sig)
    except ValueError as exc:  # non-ASCII/ongeldige base64 in de signature — 401, geen 500
        raise InvalidToken("bad signature") from exc
    if not hmac.compare_digest(sig_bytes, expected):
        raise InvalidToken("bad signature")
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidToken("bad payload") from exc
    if payload.get("exp", 0) < time.time():
        raise InvalidToken("expired")
    return payload
