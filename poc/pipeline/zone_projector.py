"""Project RegelRecht execution (+ zoneBinding) into PoC zoneSelector/conditions."""
from __future__ import annotations
from typing import Any
from pipeline.rr_ops import RR_TO_POC_OP

class ProjectionError(ValueError):
    pass

def _walk_conditions(node: Any) -> list[dict]:
    if not isinstance(node, dict):
        return []
    op = node.get("operation")
    if op == "AND":
        out: list[dict] = []
        for c in node.get("conditions") or []:
            out.extend(_walk_conditions(c))
        return out
    if op in RR_TO_POC_OP:
        subject = str(node.get("subject") or "")
        if not subject.startswith("$"):
            raise ProjectionError(f"subject must be $ref, got {subject!r}")
        return [{"parameter": subject[1:], "operator": RR_TO_POC_OP[op], "value": node.get("value")}]
    if op:
        raise ProjectionError(f"unsupported operation {op!r}")
    return []

def project_zone(
    execution: dict,
    zone_binding: dict | None,
    *,
    zone_semantics: str,
    rule_type: str,
) -> dict:
    actions = execution.get("actions") or []
    if not actions:
        raise ProjectionError("execution.actions empty")
    leafs: list[dict] = []
    for act in actions:
        leafs.extend(_walk_conditions(act.get("value") or act))

    geo_names = {i["name"] for i in (execution.get("input") or []) if i.get("type") == "boolean"}
    binding_inputs = (zone_binding or {}).get("inputs") or {}
    for name in geo_names:
        if name not in binding_inputs:
            raise ProjectionError(f"geo input {name!r} missing from zoneBinding.inputs")

    conditions = []
    for leaf in leafs:
        if leaf["parameter"] in geo_names:
            continue  # encoded in zoneSelector
        conditions.append(leaf)

    zone_selector = None
    if geo_names:
        # one primary geo input for v1 (AND of equals-true already filtered)
        primary = sorted(geo_names)[0]
        zb = binding_inputs[primary]
        zone_selector = {
            "zoneIds": list(zb["zoneIds"]),
            "selection": zb.get("selection", "within"),
            "geometrySource": zb["geometrySource"],
        }
        for k in ("gioJoinId", "bufferDistanceM", "derivedFrom", "caveat"):
            if zb.get(k) is not None:
                zone_selector[k] = zb[k]

    return {
        "zoneSelector": zone_selector,
        "conditions": conditions,
        "zoneSemantics": zone_semantics,
        "ruleType": rule_type,
    }
