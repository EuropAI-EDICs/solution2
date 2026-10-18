#!/usr/bin/env python3
"""Genereert poc-minigim/fase-manifest.json uit de bestaande registries.

De matrix is hiermee declaratief: de bindings (taakregister) zijn leidend;
de generator knoopt ze aan fasen/agents/tools volgens de mapping van de
spec (§8). Deterministisch; elke run schrijft dezelfde bytes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from minigim.registry import MiniGimRegistry  # noqa: E402

COMPUTATION_OPS = {"proxy_ratio", "proxy_entropy"}


def _task(item: dict, binding: dict) -> dict:
    t = {"id": item["id"], "from": "register:minigim-lijst", "binding": binding["status"]}
    if binding["status"] in ("auto", "partial"):
        op = (binding.get("derivation") or {}).get("op")
        klasse = "computation" if op in COMPUTATION_OPS else "retrieval"
        transport = "in-process"
        t["tool"] = {
            "class": klasse,
            "ref": ",".join(binding.get("serviceRefs") or []) or "run-input",
            "transport": transport,
            "derive": [op] if op else [],
        }
    else:
        t["manualPointer"] = binding.get("manualPointer")
    if binding.get("proxyNote"):
        t["proxyNote"] = binding["proxyNote"]
    if binding.get("notes"):
        t["notes"] = binding["notes"]
    return t


def build() -> dict:
    reg = MiniGimRegistry()
    f1, f3 = [], []
    for item in reg.tasks():
        b = reg.binding(item["id"])
        op = (b.get("derivation") or {}).get("op")
        (f3 if op in COMPUTATION_OPS else f1).append(_task(item, b))
    return {
        "poc": "minigim-gebiedscheck",
        "methodiek": "minigim-v0.91",
        "aoi": {"schema": "geojson", "crs": "EPSG:28992|WGS84"},
        "phases": [
            {"id": "F0-intake", "title": "Intake/scoping",
             "agent": {"role": "intake", "llm": True},
             "tasks": [{"id": "request-schema", "from": "run-input", "binding": "auto",
                        "tool": {"class": "validation", "ref": "schema:OpportunityMapRequest",
                                 "transport": "in-process"}}],
             "gate": {"validate": ["V0"]}},
            {"id": "F1-omgevingsanalyse", "title": "Omgevingsanalyse (informatie ophalen)",
             "agent": {"role": "minigim-specialist"},
             "tasks": f1,
             "gate": {"validate": ["V0", "V2"], "onFail": "degradeer-taak"}},
            {"id": "F2-gebiedsindeling", "title": "ILS-draft gebiedsindeling",
             "agent": {"role": "geospecialist"},
             "tasks": [{"id": "ils-classificatie", "from": "register:minigim-ils",
                        "binding": "auto",
                        "tool": {"class": "computation", "ref": "register:minigim-ils",
                                 "transport": "in-process", "derive": ["ils_bgt_mapping"]}}],
             "gate": {"validate": ["V1"], "hitl": "draft-keuze (v4 pending by design)"}},
            {"id": "F3-doorrekening", "title": "Doorrekening (rekenmodel aanroepen)",
             "agent": {"role": "minigim-specialist"},
             "tasks": f3,
             "gate": {"validate": ["V3"]}},
            {"id": "F4-synthese", "title": "Synthese & rapport",
             "agent": {"role": "critic + explainer"},
             "tasks": [{"id": "v0-v3-verdict", "from": "run-input", "binding": "auto",
                        "tool": {"class": "validation", "ref": "fundament:validate",
                                 "transport": "in-process"}},
                       {"id": "rapport", "from": "run-input", "binding": "auto",
                        "tool": {"class": "report", "ref": "minigim:report",
                                 "transport": "in-process"}}],
             "gate": {"validate": ["V0", "V1", "V2", "V3"], "hitl": "v4 (mens) pending"}},
        ],
    }


def main() -> None:
    manifest = build()
    out = ROOT / "fase-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(len(p.get("tasks") or []) for p in manifest["phases"])
    print(f"fase-manifest: {len(manifest['phases'])} fasen, {n} taken → {out}")


if __name__ == "__main__":
    main()
