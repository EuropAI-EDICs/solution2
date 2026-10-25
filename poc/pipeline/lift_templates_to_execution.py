"""Lift legacy ``zone``/``conditions`` Formalizer templates to RegelRecht ``execution``.

Templates in ``poc/tracks/_templates/*.json`` used to carry a hand-written PoC
``zone`` + ``conditions`` pair. RegelRecht ``execution`` (+ ``zoneBinding``) is
now the source of truth and the zone projector derives ``zoneSelector`` /
``conditions`` from it (dual-write). ``lift_template`` rewrites a legacy spec
into that shape without changing zone semantics:

* ``conditions[]``  -> ``execution.parameters`` + AND of ``$parameter`` operations
  (operator mapping: ``rr_ops.POC_TO_RR_OP``; ``unit`` kept on the parameter)
* ``zone``          -> one boolean geo-input ``in_{zoneId}`` + ``zoneBinding.inputs``
  (multi-zone templates share ONE input whose binding lists all ``zoneIds``;
  exclusion templates assert the input ``== false``, all others ``== true``)

Specs that already carry ``execution`` (hand-authored, e.g. W-03) and
ambiguous/reject kinds are returned unchanged.

Usage (from ``poc/``)::

    python -m pipeline.lift_templates_to_execution          # dry-run report
    python -m pipeline.lift_templates_to_execution --write  # rewrite _templates/*.json
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pipeline.rr_ops import POC_TO_RR_OP
except ImportError:  # pragma: no cover - direct script execution
    from rr_ops import POC_TO_RR_OP  # type: ignore[no-redef]

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "tracks" / "_templates"
FORMALIZED_KINDS = frozenset({"inclusion", "exclusion", "attention", "conditional", "compensation"})
#: geo-input names longer than this fall back to ``in_{first}_plus_{n-1}``
_MAX_INPUT_NAME = 48


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "string"


def _geo_input_name(zone_ids: List[str]) -> str:
    if len(zone_ids) == 1:
        return f"in_{zone_ids[0]}"
    joined = "in_" + "_".join(zone_ids)
    if len(joined) <= _MAX_INPUT_NAME:
        return joined
    return f"in_{zone_ids[0]}_plus_{len(zone_ids) - 1}"


def _output_name(key: Optional[str], kind: str) -> str:
    if key:
        return "result_" + key.lower().replace("-", "_")
    return f"result_{kind}"


def lift_template(spec: Dict[str, Any], key: Optional[str] = None) -> Dict[str, Any]:
    """Return ``spec`` lifted to ``execution`` + ``zoneBinding`` (or unchanged)."""
    if spec.get("execution") is not None:
        return spec
    kind = spec.get("kind")
    if kind not in FORMALIZED_KINDS or "zone" not in spec:
        return spec

    zone = copy.deepcopy(spec["zone"])
    zone_ids: List[str] = list(zone["zoneIds"])
    semantics = spec.get("zone_semantics", kind)

    parameters: List[Dict[str, Any]] = []
    ops: List[Dict[str, Any]] = []
    for cond in spec.get("conditions") or []:
        name = cond["parameter"]
        param: Dict[str, Any] = {
            "name": name,
            "type": _infer_type(cond["value"]),
            "description": name,
        }
        if cond.get("unit"):
            param["unit"] = cond["unit"]
        parameters.append(param)
        ops.append({
            "operation": POC_TO_RR_OP[cond["operator"]],
            "subject": f"${name}",
            "value": cond["value"],
        })

    in_name = _geo_input_name(zone_ids)
    geo_input = {
        "name": in_name,
        "type": "boolean",
        "description": "Geo-feit: locatie binnen zone " + ", ".join(zone_ids) + ".",
        "source": {"description": "Buiten wet-YAML; zone-engine / GIO."},
    }
    ops.append({
        "operation": "EQUALS",
        "subject": f"${in_name}",
        "value": semantics != "exclusion",
    })
    value: Dict[str, Any] = ops[0] if len(ops) == 1 else {"operation": "AND", "conditions": ops}

    out_name = _output_name(key, kind)
    execution = {
        "produces": {"legal_character": "TOETS"},
        "parameters": parameters,
        "input": [geo_input],
        "output": [{
            "name": out_name,
            "type": "boolean",
            "description": f"Uitkomst {key or kind} (zone-regel {semantics}).",
        }],
        "actions": [{"output": out_name, "value": value}],
    }
    zone_binding = {"inputs": {in_name: zone}}

    lifted: Dict[str, Any] = {}
    for k, v in spec.items():
        if k == "zone":
            lifted["execution"] = execution
            lifted["zoneBinding"] = zone_binding
        elif k == "conditions":
            continue
        else:
            lifted[k] = v
    return lifted


def lift_all(templates: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {k: lift_template(s, key=k) for k, s in templates.items()}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="rewrite poc/tracks/_templates/*.json")
    args = ap.parse_args(argv)
    changed = 0
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        lifted = lift_all(data)
        n = sum(1 for k in data if lifted[k] is not data[k])
        changed += n
        print(f"{path.name}: {n} lifted / {len(data)} templates")
        if args.write and n:
            path.write_text(
                json.dumps(lifted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"total lifted: {changed}" + ("" if args.write else " (dry-run; use --write)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
