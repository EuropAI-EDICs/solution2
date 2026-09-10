"""Cache-first bridge from the poc pipeline to the nldt H3 processes.

The H3 kernel lives once, in nldt (spec 2026-09-09-h3-integration,
architecture C). This module is the only poc-side coupling:

* cache-first — ``poc/data/cache/h3/<sha256>.json`` makes every replay
  offline and byte-stable (same pattern as the geodata dual-CRS cache);
* on miss, the nldt CLI runs the process as a subprocess (no service, no
  python-path coupling — the process boundary IS the architecture);
* ``POC_H3_OFFLINE=1`` turns a cache miss into an error, so unittest
  runs can never spawn a subprocess or touch the network.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

POC_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = POC_ROOT.parent
NLDT_ROOT = WORKSPACE / "nldt"
NLDT_CLI = NLDT_ROOT / "services" / "cli.py"
CACHE_DIR = POC_ROOT / "data" / "cache" / "h3"
REQ_DIR = CACHE_DIR / "req"


class H3UnavailableError(RuntimeError):
    """No cached H3 response and offline mode forbids invoking nldt."""


def fingerprint(process_id: str, inputs: Dict[str, Any]) -> str:
    payload = json.dumps({"processId": process_id, "inputs": inputs},
                         sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def call(process_id: str, inputs: Dict[str, Any], *,
         refresh: bool = False) -> Dict[str, Any]:
    """Invoke one nldt h3-* process; returns its ``outputs`` dict."""
    fp = fingerprint(process_id, inputs)
    cache = CACHE_DIR / f"{fp}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))["outputs"]

    if os.environ.get("POC_H3_OFFLINE") == "1":
        raise H3UnavailableError(
            f"H3 process {process_id!r} not in cache ({cache.name}) and "
            "POC_H3_OFFLINE=1 forbids invocation — regenerate fixtures with "
            "poc/tests/make_h3_fixtures.py")

    REQ_DIR.mkdir(parents=True, exist_ok=True)
    # NB: the CLI must run as a module (README form ``python -m services.cli``):
    # ``python services/cli.py`` leaves the nldt root off sys.path and the
    # ``from services...`` imports in cli.py fail. cwd=NLDT_ROOT makes the
    # ``services`` package importable for ``-m``.
    argv = [sys.executable, "-m", "services.cli", "run-process", process_id]
    for key, value in sorted(inputs.items()):
        if isinstance(value, (dict, list)):
            req = REQ_DIR / f"{fp}-{key}.json"
            req.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            argv += ["--input", f"{key}=file://{req}"]
        else:
            argv += ["--input", f"{key}={value}"]
    proc = subprocess.run(argv, cwd=str(NLDT_ROOT), capture_output=True,
                          text=True, check=True)
    job = json.loads(proc.stdout)
    outputs = job["outputs"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    record = {"processId": process_id, "fingerprint": fp, "outputs": outputs,
              "prov": job.get("prov")}
    cache.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    return outputs


def scenario_metrics(geometry_payload_4326: Dict[str, Any],
                     control_cells: Optional[set] = None,
                     resolution: int = 8, *,
                     refresh: bool = False) -> Dict[str, Any]:
    """Hex summary for one scenario zone (Task 9 wiring): cell set (centre
    + ≥50% coverage), Moran's I over coverage fractions, and cell deltas
    vs the control when ``control_cells`` is given."""
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": geometry_payload_4326}]}
    cov = call("h3-polygon-to-cells",
               {"polygon": fc, "resolution": resolution}, refresh=refresh)["coverage"]
    cells = {r["cell"] for r in cov["cells"] if r["coverageFraction"] >= 0.5}
    stats = call("h3-morans-i",
                 {"values": {"perCell": cov["cells"]}}, refresh=refresh)["statistics"]
    out: Dict[str, Any] = {
        "resolution": resolution,
        "cellCount": len(cells),
        "moransI": stats["moransI"],
        "pValue": stats.get("pValue"),
    }
    if control_cells is None:
        out["cells"] = sorted(cells)
        out["cellsGainedVsControl"] = None
        out["cellsLostVsControl"] = None
    else:
        out["cellsGainedVsControl"] = len(cells - control_cells)
        out["cellsLostVsControl"] = len(control_cells - cells)
    return out
