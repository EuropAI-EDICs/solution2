from __future__ import annotations

import os
from typing import Any

import httpx

from services.common.prov import new_job_id, prov_bundle, utc_now
from services.process_adapter.handlers import execute_local
from services.process_adapter.kubeflow_adapter import KubeflowAdapter


class UCSAdapter:
    """Hybrid adapter stub for EU LDT UCS experiment execution."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("UCS_BASE_URL", "").rstrip("/")
        self.token = os.environ.get("UCS_TOKEN", "")

    @property
    def available(self) -> bool:
        return bool(self.base_url)

    def execute(self, process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("UCS_BASE_URL not configured")
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {"processId": process_id, "inputs": inputs}
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/experiments/trigger-process",
                json=payload,
                headers=headers,
            )
            if resp.status_code == 404:
                return execute_local(process_id, inputs)
            resp.raise_for_status()
            data = resp.json()
            return data.get("outputs", data)


def route_execute(
    process_id: str,
    inputs: dict[str, Any],
    backend: str = "local",
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    job_id = new_job_id()
    started = utc_now()
    used = [f"nldt:Input/{k}" for k in inputs]

    if backend == "ucs":
        adapter = UCSAdapter()
        if adapter.available:
            outputs = adapter.execute(process_id, inputs)
            backend_used = "ucs"
        else:
            outputs = execute_local(process_id, inputs)
            backend_used = "local-fallback"
    elif backend == "kubeflow":
        kf = KubeflowAdapter()
        if kf.available:
            outputs = kf.execute(process_id, inputs)
            backend_used = "kubeflow"
        else:
            outputs = execute_local(process_id, inputs)
            backend_used = "local-fallback"
    else:
        outputs = execute_local(process_id, inputs)
        backend_used = "local"

    ended = utc_now()
    prov = prov_bundle(
        process_id=process_id,
        job_id=job_id,
        backend=backend_used,
        used=used,
        started=started,
        ended=ended,
    )
    return job_id, outputs, prov
