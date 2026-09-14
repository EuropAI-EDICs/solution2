from __future__ import annotations

import os
from typing import Any

import httpx

PROCESS_URL = os.environ.get("NLDT_PROCESS_URL", "http://localhost:8082")


class ProcessClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or PROCESS_URL).rstrip("/")

    def execute(
        self, process_id: str, inputs: dict[str, Any], backend: str = "local"
    ) -> dict[str, Any]:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self.base_url}/processes/{process_id}/execution",
                json={"inputs": inputs, "backend": backend},
            )
            resp.raise_for_status()
            return resp.json()
