"""Poll identity events for the nLDT audit trail (W6a ops script).

Fetches login/admin events from the testbed Keycloak behind EU LDT Identity
Management (or the Identity tool's ``GET /events`` wrapper when
``NLDT_IDENTITY_API_URL`` is set) and appends them as JSONL under
``data/audit/identity-events/<YYYYMMDD>.jsonl`` with a ``fetchedAt``
timestamp. Read-only and idempotent per invocation; run it from cron or
manually — nothing is auto-applied (V4 doctrine).

Usage:
    PYTHONPATH=. python scripts/fetch_identity_events.py [--max 500] \\
        [--source keycloak|identity-api] [--out data/audit/identity-events]

Auth (keycloak source): ``KEYCLOAK_ADMIN_TOKEN`` or
``KEYCLOAK_ADMIN_USER``/``KEYCLOAK_ADMIN_PASSWORD`` (password grant on
``KEYCLOAK_ADMIN_REALM``, default ``master``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

TIMEOUT = 30.0


def _admin_token(base_url: str) -> str:
    explicit = os.environ.get("KEYCLOAK_ADMIN_TOKEN", "").strip()
    if explicit:
        return explicit
    user = os.environ.get("KEYCLOAK_ADMIN_USER", "").strip()
    password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")
    if not user:
        raise RuntimeError("set KEYCLOAK_ADMIN_TOKEN or KEYCLOAK_ADMIN_USER/KEYCLOAK_ADMIN_PASSWORD")
    realm = os.environ.get("KEYCLOAK_ADMIN_REALM", "master")
    resp = httpx.post(
        f"{base_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli", "username": user, "password": password},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_events(source: str, max_events: int) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {_admin_token(os.environ.get('KEYCLOAK_URL', ''))}"}
    if source == "identity-api":
        base = os.environ.get("NLDT_IDENTITY_API_URL", "").rstrip("/")
        if not base:
            raise RuntimeError("--source identity-api requires NLDT_IDENTITY_API_URL")
        resp = httpx.get(f"{base}/events", headers=headers, params={"max": max_events}, timeout=TIMEOUT)
    else:
        base = os.environ.get("KEYCLOAK_URL", "").rstrip("/")
        realm = os.environ.get("KEYCLOAK_REALM", "LDT")
        if not base:
            raise RuntimeError("--source keycloak requires KEYCLOAK_URL")
        resp = httpx.get(
            f"{base}/admin/realms/{realm}/events",
            headers=headers,
            params={"max": max_events},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    events = resp.json()
    if not isinstance(events, list):
        raise RuntimeError(f"unexpected events payload: {type(events).__name__}")
    return events


def append_jsonl(events: list[dict[str, Any]], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()
    path = os.path.join(out_dir, datetime.now(timezone.utc).strftime("%Y%m%d") + ".jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps({"fetchedAt": fetched_at, "event": event}, default=str) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=["keycloak", "identity-api"], default="keycloak")
    parser.add_argument("--max", type=int, default=500, help="maximum events per fetch")
    parser.add_argument("--out", default=os.path.join("data", "audit", "identity-events"))
    args = parser.parse_args(argv)

    try:
        events = fetch_events(args.source, args.max)
        path = append_jsonl(events, args.out)
    except (RuntimeError, httpx.HTTPError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"appended {len(events)} event(s) to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
