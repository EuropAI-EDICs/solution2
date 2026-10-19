#!/usr/bin/env python3
"""Bewijst beide transports van het minigim-model, met PROV-verwijzingen.

  processes : roept de nldt process-adapter aan (replay van de laatste echte
              run) — het resultaat draagt de run-summary met verdict;
  a2a       : verifieert de Agent Card-entry in de catalogus (id, port,
              defaultRecipeId) en pint de catalog-sha256.

Niet onderdeel van de offline suite (de replay pakt de laatste echte run):
    cd poc-minigim && PYTHONPATH=$PWD/../nldt ../nldt/.venv/bin/python tools/verify_transports.py
Schrijft runs/transport-verify.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import minigim  # noqa: E402,F401  (bootstrap: zet poc-fundament op sys.path)
from fundament.models import load_model_registry, model_by_id  # noqa: E402


def main() -> int:
    reg = load_model_registry(ROOT / "modelregister.json")
    m = model_by_id(reg, "minigim-gebiedscheck-run")
    report: dict = {"model": m["id"], "transports": {}}

    proc = next(t for t in m["transports"] if t["type"] == "processes")
    from services.process_adapter.poc_handlers import execute_minigim_gebiedscheck_run
    result = execute_minigim_gebiedscheck_run({"mode": "replay"})
    verdict = (result.get("summary") or {}).get("verdict") if isinstance(result, dict) else None
    ok = isinstance(result, dict) and not result.get("error") and verdict == "pass"
    report["transports"]["processes"] = {
        "processId": proc["processId"], "ok": ok, "verdict": verdict, "result": result,
    }

    catalog_path = ROOT.parent / "a2a-simulation" / "catalog" / "poc-agents.json"
    cat = json.loads(catalog_path.read_text(encoding="utf-8"))
    a2a = next(t for t in m["transports"] if t["type"] == "a2a")
    agent = next((a for a in cat["agents"] if a["id"] == a2a["agentId"]), None)
    report["transports"]["a2a"] = {
        "ok": agent is not None,
        "agentId": a2a["agentId"],
        "port": agent["port"] if agent else None,
        "defaultRecipeId": agent["defaultRecipeId"] if agent else None,
        "catalogSha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
    }

    out = ROOT / "runs" / "transport-verify.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    allemaal_ok = all(t["ok"] for t in report["transports"].values())
    print(f"transports: processes={report['transports']['processes']['ok']} "
          f"(verdict: {verdict}) a2a={report['transports']['a2a']['ok']} → {out}")
    return 0 if allemaal_ok else 1


if __name__ == "__main__":
    sys.exit(main())
