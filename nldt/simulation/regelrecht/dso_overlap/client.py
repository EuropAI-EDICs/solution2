"""HTTP-clients voor DSO Presenteren v8 en Ruimtelijke plannen V4."""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any

from instruments import CRS_DSO, CRS_RP, DEFAULT_PRESENTEREN_BASE, DEFAULT_RP_BASE


class DsoApiError(RuntimeError):
    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"HTTP {status} for {url}: {body[:400]}")
        self.status = status
        self.body = body
        self.url = url


def _env_key(name: str) -> str | None:
    val = os.environ.get(name, "").strip()
    return val or None


def presenteren_base() -> str:
    return (
        os.environ.get("DSO_PRESENTEREN_BASE", "").strip()
        or DEFAULT_PRESENTEREN_BASE
    ).rstrip("/")


def rp_base() -> str:
    return (os.environ.get("RP_API_BASE", "").strip() or DEFAULT_RP_BASE).rstrip("/")


def require_dso_key() -> str:
    key = _env_key("DSO_API_KEY")
    if not key:
        raise SystemExit(
            "Zet DSO_API_KEY (Presenteren PRE/prod). Keys niet in de repo opslaan."
        )
    return key


def optional_rp_key() -> str | None:
    return _env_key("RP_API_KEY")


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict | None = None,
    timeout: float = 120.0,
) -> tuple[dict[str, Any], bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise DsoApiError(e.code, err_body, url) from e
    if not raw:
        return {}, raw
    try:
        return json.loads(raw.decode("utf-8")), raw
    except json.JSONDecodeError as e:
        raise DsoApiError(200, f"niet-JSON response: {raw[:200]!r}", url) from e


def fetch_regeling(akn_uri: str, *, api_key: str) -> dict[str, Any]:
    url = f"{presenteren_base()}/regelingen/{akn_uri}"
    payload, _ = _request(
        "GET",
        url,
        headers={
            "X-Api-Key": api_key,
            "Accept": "application/hal+json",
        },
    )
    return payload


def fetch_regeltekstannotaties(
    akn_uri: str,
    geometry: dict[str, Any],
    *,
    api_key: str,
) -> tuple[dict[str, Any], str]:
    """Return (payload, sha256_hex of raw body)."""
    url = (
        f"{presenteren_base()}/regelingen/{akn_uri}"
        f"/regeltekstannotaties/_zoek?page=1&size=200&locatieSelectie=primair"
    )
    payload, raw = _request(
        "POST",
        url,
        headers={
            "X-Api-Key": api_key,
            "Accept": "application/hal+json",
            "Content-Type": "application/json",
            "Content-Crs": CRS_DSO,
            "Accept-Crs": CRS_DSO,
        },
        body={"geometrie": geometry},
    )
    return payload, hashlib.sha256(raw).hexdigest()


def fetch_rp_plannen(
    geometry: dict[str, Any],
    *,
    api_key: str,
    size: int = 20,
) -> tuple[dict[str, Any], str]:
    url = f"{rp_base()}/plannen/_zoek?page=1&size={size}"
    payload, raw = _request(
        "POST",
        url,
        headers={
            "x-api-key": api_key,
            "Accept": "application/hal+json",
            "Content-Type": "application/json",
            "Content-Crs": CRS_RP,
            "Accept-Crs": CRS_RP,
        },
        body={"_geo": {"intersects": geometry}},
    )
    return payload, hashlib.sha256(raw).hexdigest()
