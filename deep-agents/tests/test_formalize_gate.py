"""Schema + zone-projection gate van validate_formal_rule (offline)."""

from __future__ import annotations

import copy
import json

import pytest

from tools import formalize

CORPUS = sorted(formalize.CORPUS_DIR.glob("formalrules-*.json"))


def _formalized_rules():
    out = []
    for path in CORPUS:
        data = json.loads(path.read_text(encoding="utf-8"))
        for rule in data if isinstance(data, list) else data.get("rules", []):
            if rule.get("status") == "formalized":
                out.append(rule)
    return out


def _geo_rule():
    for rule in _formalized_rules():
        if rule.get("zoneSelector"):
            return rule
    pytest.skip("no formalized rule with zoneSelector in corpus")


def test_corpus_formalized_rules_pass_gate():
    rules = _formalized_rules()
    assert rules
    for rule in rules:
        res = formalize.validate_formal_rule(json.dumps(rule))
        assert res["passed"], (rule["id"], res["errors"])


def test_handauthored_zone_selector_rejected():
    rule = copy.deepcopy(_geo_rule())
    rule["zoneSelector"]["zoneIds"] = ["HAND-AUTHORED"]
    res = formalize.validate_formal_rule(json.dumps(rule))
    assert not res["passed"]
    assert any("zone_projector" in e for e in res["errors"])


def test_missing_execution_rejected():
    rule = copy.deepcopy(_geo_rule())
    rule.pop("execution")
    res = formalize.validate_formal_rule(json.dumps(rule))
    assert not res["passed"]


def test_missing_zone_binding_rejected():
    rule = copy.deepcopy(_geo_rule())
    rule.pop("zoneBinding", None)
    res = formalize.validate_formal_rule(json.dumps(rule))
    assert not res["passed"]
    assert any("zoneBinding" in e or "projection" in e for e in res["errors"])
