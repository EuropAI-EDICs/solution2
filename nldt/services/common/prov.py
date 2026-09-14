from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prov_bundle(
    *,
    process_id: str,
    job_id: str,
    backend: str,
    used: list[str] | None = None,
    started: str | None = None,
    ended: str | None = None,
) -> dict[str, Any]:
    started = started or utc_now()
    ended = ended or utc_now()
    return {
        "activity": f"nldt:ProcessExecution/{process_id}",
        "agent": f"nldt:ProcessAdapter/{backend}",
        "generated": f"nldt:JobResult/{job_id}",
        "used": used or [],
        "startedAtTime": started,
        "endedAtTime": ended,
    }


def new_job_id() -> str:
    return str(uuid4())
