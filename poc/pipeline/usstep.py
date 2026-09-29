"""Cache-first bridge from the poc pipeline to nldt Urban Strategy processes.

Urban Strategy client + stiltegebied kernel live once in nldt (spec
2026-09-29-urbanstrategy-stiltegebied-design). This module is the only
poc-side coupling:

* cache-first — ``poc/data/cache/us/<sha256>.json`` makes every replay
  offline and byte-stable (same pattern as ``h3step``);
* on miss, the nldt CLI runs the process as a subprocess;
* ``POC_US_OFFLINE=1`` turns a cache miss into an error so unittest
  runs never spawn a subprocess or touch the network.
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
CACHE_DIR = POC_ROOT / "data" / "cache" / "us"
REQ_DIR = CACHE_DIR / "req"

DEFAULT_RECEPTOR_SOURCE = "fixture://receptors-stiltegebied-utrecht.geojson"


class UsUnavailableError(RuntimeError):
    """No cached US response and offline mode forbids invoking nldt."""


def fingerprint(process_id: str, inputs: Dict[str, Any]) -> str:
    payload = json.dumps({"processId": process_id, "inputs": inputs},
                         sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def call(process_id: str, inputs: Dict[str, Any], *,
         refresh: bool = False) -> Dict[str, Any]:
    """Invoke one nldt us-* process; returns its ``outputs`` dict."""
    fp = fingerprint(process_id, inputs)
    cache = CACHE_DIR / f"{fp}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))["outputs"]

    if os.environ.get("POC_US_OFFLINE") == "1":
        raise UsUnavailableError(
            f"US process {process_id!r} not in cache ({cache.name}) and "
            "POC_US_OFFLINE=1 forbids invocation — regenerate fixtures with "
            "poc/tests/make_us_fixtures.py")

    REQ_DIR.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, "-m", "services.cli", "run-process", process_id]
    for key, value in sorted(inputs.items()):
        if isinstance(value, (dict, list)):
            req = REQ_DIR / f"{fp}-{key}.json"
            req.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            argv += ["--input", f"{key}=file://{req}"]
        elif value is None:
            continue
        else:
            argv += ["--input", f"{key}={value}"]
    proc = subprocess.run(argv, cwd=str(NLDT_ROOT), capture_output=True,
                          text=True, check=False)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-2000:]
        raise RuntimeError(
            f"nldt process {process_id!r} failed (exit {proc.returncode}): "
            f"{tail or 'no output'}")
    job = json.loads(proc.stdout)
    outputs = job["outputs"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    record = {"processId": process_id, "fingerprint": fp, "outputs": outputs,
              "prov": job.get("prov")}
    cache.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    return outputs


def _fc_from_layer(layer: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not layer or not isinstance(layer, dict):
        return {"type": "FeatureCollection", "features": []}
    if layer.get("type") == "FeatureCollection":
        return layer
    return {"type": "FeatureCollection", "features": []}


def stiltegebied_noise_screen(
    stiltegebied_4326: Dict[str, Any],
    *,
    bufferzone_4326: Optional[Dict[str, Any]] = None,
    receptor_source: str = DEFAULT_RECEPTOR_SOURCE,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Fetch receptors + evaluate against stiltegebied polygons (4326).

    When ``bufferzone_4326`` is omitted, the combined stiltegebied layer is
    screened at the stricter art. 9.26 stille-kern threshold (40 dB).
    """
    fetch_out = call(
        "us-fetch-noise-receptors",
        {"source": receptor_source},
        refresh=refresh,
    )
    receptors = fetch_out["receptors"]
    stille = _fc_from_layer(stiltegebied_4326)
    bufferzone = _fc_from_layer(bufferzone_4326)
    eval_inputs: Dict[str, Any] = {
        "receptors": receptors,
        "stilleKern": stille,
        "bufferzone": bufferzone,
    }
    eval_out = call("us-stiltegebied-noise-eval", eval_inputs, refresh=refresh)
    return eval_out["evaluation"]
