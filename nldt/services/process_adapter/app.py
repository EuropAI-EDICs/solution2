from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from services.common import auth
from services.common.auth import require_bearer
from services.common.telemetry import init_telemetry, span
from services.common.trust_policy import GateDenied, TrustPolicyUnavailable, check_gate, load_trust_policy
from services.process_adapter.handlers import describe_process, list_processes
from services.process_adapter.jobs import create_job, get_job, job_results

logger = logging.getLogger("nldt.auth")

app = FastAPI(
    title="nLDT Process Adapter", version="1.0.0", dependencies=[Depends(require_bearer)]
)


async def approver_claims(
    request: Request, x_nldt_approver_token: str | None = Header(default=None)
) -> None:
    """Optional wallet-verified approver (X-nLDT-Approver-Token, BK-3 / W3).

    When the header is present and wallet auth mode is active, introspect it
    like the caller token and land the validated claims (minus "active") on
    request.state.approver_claims. Human/gate checks happen per-process in
    execute(); introspection failures mirror the executor path (503).
    """
    if not x_nldt_approver_token or auth.auth_mode() != "wallet":
        return
    try:
        claims = await auth.introspect_wallet(x_nldt_approver_token)
    except Exception as exc:
        logger.warning("approver token introspection failed: %s", exc)
        raise HTTPException(status_code=503, detail="token introspection unavailable") from exc
    if not claims.get("active"):
        raise HTTPException(
            status_code=401, detail="invalid approver token", headers={"WWW-Authenticate": "Bearer"}
        )
    from services.common.schema import validate_instance

    claims_no_active = {k: v for k, v in claims.items() if k != "active"}
    validate_instance(claims_no_active, "wallet-claims.schema.json")
    request.state.approver_claims = claims_no_active


class ExecutionRequest(BaseModel):
    inputs: dict[str, Any]
    backend: str = "local"
    response: str = "document"


@app.get("/")
def landing() -> dict[str, Any]:
    return {
        "title": "nLDT OGC API Processes Adapter",
        "description": "Hybrid process facade (local + UCS stub)",
        "links": [
            {"rel": "processes", "href": "/processes"},
            {"rel": "conformance", "href": "/conformance"},
        ],
    }


@app.get("/conformance")
def conformance() -> dict[str, Any]:
    return {
        "conformsTo": [
            "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/core",
        ]
    }


@app.get("/processes")
def processes() -> dict[str, Any]:
    return {"processes": list_processes()}


@app.get("/processes/{process_id}")
def process_description(process_id: str) -> dict[str, Any]:
    try:
        return describe_process(process_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/processes/{process_id}/execution")
def execute(
    process_id: str,
    body: ExecutionRequest,
    request: Request,
    _approver: None = Depends(approver_claims),
) -> dict[str, Any]:
    init_telemetry("nldt-process-adapter")
    try:
        describe_process(process_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    wallet_claims = getattr(request.state, "wallet_claims", None)
    approver_claims = getattr(request.state, "approver_claims", None)
    try:
        policy = load_trust_policy()
    except TrustPolicyUnavailable as exc:
        # Fail closed: a policy file is configured but cannot be loaded, so we
        # cannot know whether this process is gated — refuse execution.
        raise HTTPException(status_code=503, detail="trust policy unavailable") from exc
    if policy is not None:
        gated = process_id in policy.get("gates", {})
        try:
            check_gate(policy, process_id, wallet_claims)
        except GateDenied as exc:
            raise HTTPException(
                status_code=403, detail={"gate": exc.gate, "reason": exc.reason}
            ) from exc
        if approver_claims is not None:
            # The approver takes responsibility for this run: a wallet-verified
            # human who satisfies the same gate as the executor. The human
            # check applies on ungated processes too — an agent must never be
            # recorded as an approver in the audit trail.
            if approver_claims.get("subject_type") != "human":
                raise HTTPException(
                    status_code=403,
                    detail={"gate": process_id, "reason": "approver_not_human"},
                )
            if gated:
                try:
                    check_gate(policy, process_id, approver_claims)
                except GateDenied as exc:
                    raise HTTPException(
                        status_code=403,
                        detail={"gate": exc.gate, "reason": f"approver_{exc.reason}"},
                    ) from exc
    with span("process.execute", {"process.id": process_id, "backend": body.backend}):
        actor = None
        if wallet_claims:
            actor = {"executor": wallet_claims}
            if approver_claims is not None:
                actor["approver"] = approver_claims
        job = create_job(
            process_id,
            body.inputs,
            backend=body.backend,
            **({"actor": actor} if actor else {}),
        )
    return job


@app.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "jobId": job["jobId"],
        "status": job["status"],
        "processId": job["processId"],
        "links": job["links"],
    }


@app.get("/jobs/{job_id}/results")
def results(job_id: str) -> dict[str, Any]:
    res = job_results(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="job not found")
    return res


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_PROCESS_PORT", "8082"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
