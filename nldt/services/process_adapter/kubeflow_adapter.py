from __future__ import annotations

import os
from typing import Any

import httpx

from services.process_adapter.handlers import execute_local


class KubeflowAdapter:
    """Hybrid adapter stub for KServe inference via AI Notebook proxy."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("KUBEFLOW_BASE_URL", "").rstrip("/")
        self.token = os.environ.get("KUBEFLOW_TOKEN", "")

    @property
    def available(self) -> bool:
        return bool(self.base_url)

    def execute(
        self, process_id: str, inputs: dict[str, Any], job_id: str | None = None
    ) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("KUBEFLOW_BASE_URL not configured")
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {"processId": process_id, "inputs": inputs}
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/inference/process",
                json=payload,
                headers=headers,
            )
            if resp.status_code in (404, 501):
                return execute_local(process_id, inputs, job_id=job_id)
            resp.raise_for_status()
            data = resp.json()
            return data.get("outputs", data)
