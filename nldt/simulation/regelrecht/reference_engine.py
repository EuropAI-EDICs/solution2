# nldt/simulation/regelrecht/reference_engine.py  — definitieve versie
"""Deterministische referentie-executor voor machine_readable-secties (regelrecht-subset).

Ondersteunt precies de vier operaties die de voorbeeld-YAML's gebruiken
(AND, EQUALS, LESS_THAN_OR_EQUAL, IF) plus letterlijke waarden en
$-referenties. Alles buiten die subset is een EngineError: nooit gissen.
Deze module is de norm voor de golden set; mini-engine.js moet haar
uitkomsten exact reproduceren.
"""
from __future__ import annotations


class EngineError(Exception):
    pass


def evaluate(execution: dict, inputs: dict) -> dict:
    """Voer execution.actions uit over inputs; elke actie krijgt trace-stappen."""
    scope = dict(inputs)
    trace: list = []
    for action in execution.get("actions", []):
        scope[action["output"]] = _resolve(action["value"], scope, trace, action["output"])
    outputs = {o["name"]: scope.get(o["name"]) for o in execution.get("output", [])}
    return {"outputs": outputs, "trace": trace}


def _resolve(node, scope, trace, label):
    if isinstance(node, str) and node.startswith("$"):
        if node[1:] not in scope:
            raise EngineError(f"onbekende referentie: {node}")
        return scope[node[1:]]
    if isinstance(node, (bool, int, float)):
        return node
    if isinstance(node, dict) and "operation" in node:
        return _apply(node, scope, trace, label)  # opslag in scope doet evaluate (top-level)
    if isinstance(node, str):
        return node
    raise EngineError(f"niet-ondersteunde operand: {node!r}")


def _apply(op, scope, trace, label):
    name = op["operation"]
    if name == "AND":
        condition_results = []
        for cond in op["conditions"]:
            condition_results.append(bool(_eval_condition(cond, scope, trace, label)))
        result = all(condition_results)
        trace.append({"action": label, "operation": "AND",
                      "operands": {"conditions": op["conditions"]}, "result": result})
        return result
    if name in ("EQUALS", "LESS_THAN_OR_EQUAL"):
        subject = _operand(op["subject"], scope)
        value = _operand(op["value"], scope)
        result = (subject == value) if name == "EQUALS" else (subject <= value)
        trace.append({"action": label, "operation": name,
                      "operands": {"subject": op["subject"], "value": op["value"]}, "result": result})
        return result
    if name == "IF":
        for case in op.get("cases", []):
            if bool(_eval_condition(case["when"], scope, trace, label)):
                result = _operand(case["then"], scope)
                _trace_if(trace, label, op, result, fired=len(trace))
                return result
        if "default" not in op:
            raise EngineError("IF zonder passerende case en zonder default")
        result = _operand(op["default"], scope)
        _trace_if(trace, label, op, result, fired=0)
        return result
    raise EngineError(f"niet-ondersteunde operatie: {name}")


def _eval_condition(cond, scope, trace, label):
    return _apply(cond, scope, trace, label)


def _trace_if(trace, label, op, result, fired):
    trace.append({"action": label, "operation": "IF",
                  "operands": {"cases": len(op.get("cases", [])), "default": op.get("default"), "firedCase": fired},
                  "result": result})


def _operand(node, scope):
    if isinstance(node, str) and node.startswith("$"):
        if node[1:] not in scope:
            raise EngineError(f"onbekende referentie: {node}")
        return scope[node[1:]]
    return node
