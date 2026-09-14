from __future__ import annotations

from typing import Any

from services.common.prov import utc_now
from services.process_adapter.router import route_execute

_JOBS: dict[str, dict[str, Any]] = {}


def create_job(
    process_id: str,
    inputs: dict[str, Any],
    backend: str = "local",
    actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    job_id, outputs, prov = route_execute(process_id, inputs, backend=backend)
    record = {
        "jobId": job_id,
        "processId": process_id,
        "status": "successful",
        "startedAt": prov["startedAtTime"],
        "finishedAt": prov["endedAtTime"],
        "outputs": outputs,
        "prov": prov,
        "links": [
            {"rel": "self", "href": f"/jobs/{job_id}"},
            {"rel": "results", "href": f"/jobs/{job_id}/results"},
        ],
    }
    if actor is not None:
        record["actor"] = actor
    _JOBS[job_id] = record
    return record


def get_job(job_id: str) -> dict[str, Any] | None:
    return _JOBS.get(job_id)


def job_results(job_id: str) -> dict[str, Any] | None:
    job = _JOBS.get(job_id)
    if not job:
        return None
    return {"jobId": job_id, "outputs": job["outputs"], "prov": job["prov"]}
