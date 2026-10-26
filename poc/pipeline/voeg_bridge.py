"""poc/pipeline/voeg_bridge.py — de dunne wrapper die de Rust-harness
`voeg` (../rustharness) injecteert als llm_call in LLMTransport.

Subprocess-contract (docs/superpowers/plans/2026-10-25-voeg.md, Task 8):
stdout is precies één JSON-regel; exit 0 ok, 2 transport, 3 contract-faal
na repair. VOEG_BIN is het voeg-commando (pad of "wrapper args…").

Contract-notities uit de Rust-reviews: `receipt` is OPTIONEEL op
`ok:false`-payloads (deze bridge leest het dus nooit op het fout-pad);
system/user gaan via stdin en moeten ALTIJD JSON-strings zijn.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from pipeline.llm_transport import LLMTransportError


class VoegUnavailable(LLMTransportError):
    """voeg niet gevonden of niet draaiend (fail-soft: seam valt terug)."""


class VoegTransportError(LLMTransportError):
    """exit 2: endpoint onbereikbaar/timeout."""


class VoegRejected(LLMTransportError):
    """exit 3: contract-faal na repair — de rejection staat in voeg' ledger."""


def _voeg_cmd() -> list[str]:
    raw = os.environ.get("VOEG_BIN", "").strip()
    if not raw:
        raise VoegUnavailable("VOEG_BIN niet gezet (pad naar de voeg-binary)")
    return shlex.split(raw)


def llm_call(
    endpoint: str,
    model: str,
    system: str,
    user: str,
    timeout: Optional[float],
    *,
    seam: str = "S2",
    contract_path: str = "",
    runs_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """LLMTransport._llm_call-compatibel: geeft het contract-gevalideerde
    data-object terug (dict), of raiset. endpoint/model/timeout worden aan
    voeg doorgegeven via env — voeg leest VOEG_ENDPOINT/VOEG_MODEL zelf."""
    cmd = _voeg_cmd() + [
        "call", "--seam", seam,
        "--contract", contract_path or _default_contract(seam),
        "--system-file", "-", "--user-file", "-",
    ]
    if runs_dir:
        cmd += ["--runs-dir", runs_dir]
    env = dict(os.environ)
    env.setdefault("VOEG_ENDPOINT", endpoint or "")
    env.setdefault("VOEG_MODEL", model or "unknown")
    # stdin-variant: system/user moeten ALTIJD JSON-strings zijn (contract).
    stdin_payload = json.dumps({"system": str(system), "user": str(user)})
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=timeout or 120.0,
            env=env,
        )
    except FileNotFoundError as exc:
        raise VoegUnavailable(f"voeg-binary niet gevonden: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise VoegTransportError(f"voeg timeout: {exc}") from exc

    stdout = (proc.stdout or "").strip()
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        raise VoegUnavailable(f"voeg gaf geen JSON-regel (exit {proc.returncode})")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise VoegUnavailable(f"voeg stdout geen JSON: {exc}: {lines[-1][:200]}") from exc
    if not isinstance(payload, dict):
        raise VoegUnavailable(f"voeg stdout geen JSON-object: {lines[-1][:200]}")
    if proc.returncode == 0 and payload.get("ok"):
        data = payload.get("data")
        if not isinstance(data, dict):
            raise VoegRejected("voeg gaf ok zonder data-dict")
        return data
    # `receipt` is optioneel op ok:false — niet afhankelijk zijn van die key.
    errors = payload.get("errors") or [f"exit {proc.returncode}"]
    if proc.returncode == 2 or any(str(e).startswith("transport:") for e in errors):
        raise VoegTransportError("; ".join(map(str, errors)))
    raise VoegRejected("; ".join(map(str, errors)))


def _default_contract(seam: str) -> str:
    # S2-formalisatievoorstellen zijn de eerste consumer (spec §10);
    # andere seams geven hun eigen contract_path mee.
    root = Path(__file__).resolve().parents[1]
    return str(root / "schemas" / "norm-card.schema.json")
