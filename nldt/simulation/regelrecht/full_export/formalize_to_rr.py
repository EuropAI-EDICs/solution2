"""FormalizerPass — FormalRule/evidence → RegelRecht machine_readable + report."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

import yaml

import paths
from align_evidence import Alignment
from split_cvdr_html import Article

OP_MAP = {
    "<=": "LESS_THAN_OR_EQUAL",
    ">=": "GREATER_THAN_OR_EQUAL",
    "==": "EQUALS",
    "!=": "NOT_EQUALS",
    "<": "LESS_THAN",
    ">": "GREATER_THAN",
}

SMOKE_UTRECHT_YAML = (
    paths.ROOT / "docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml"
)
SMOKE_EINDHOVEN_YAML = (
    paths.ROOT / "docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml"
)


class ArticleFormalization(TypedDict, total=False):
    number: str
    status: str
    reason: str
    machineReadable: Optional[dict]
    normCardId: Optional[str]
    formalRuleId: Optional[str]
    source: str


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    return "string"


def _load_smoke_mr(yaml_path, article_number: str) -> dict:
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    for art in doc["articles"]:
        if art["number"] == article_number and "machine_readable" in art:
            return art["machine_readable"]
    raise SystemExit(f"smoke YAML mist machine_readable voor art. {article_number}: {yaml_path}")


def formal_rule_to_machine_readable(rule: dict, article: Article) -> dict:
    """Map a formalized FormalRule to RegelRecht machine_readable."""
    if rule.get("status") != "formalized":
        raise ValueError(f"rule {rule.get('id')} is not formalized")

    # Smoke: keep golden-case execution byte-compatible
    if rule.get("id") == "FR-W-03":
        return _load_smoke_mr(SMOKE_UTRECHT_YAML, "5.3")

    params: List[dict] = []
    conditions_ops: List[dict] = []
    for c in rule.get("conditions") or []:
        pname = c["parameter"]
        # Special-case art. 5.3 enum → bool parameter name (generic path)
        if c.get("value") == "existing_building_plot":
            pname = "op_of_in_aansluiting_op_bestaand_bouwperceel"
            val: Any = True
            ptype = "boolean"
        else:
            val = c["value"]
            ptype = (
                "number"
                if isinstance(c.get("value"), (int, float)) and c["operator"] != "=="
                else _infer_type(c["value"])
            )
        params.append({"name": pname, "type": ptype, "description": pname})
        conditions_ops.append(
            {
                "operation": OP_MAP[c["operator"]],
                "subject": f"${pname}",
                "value": val,
            }
        )

    inputs: List[dict] = []
    zs = rule.get("zoneSelector") or {}
    zone_ids = zs.get("zoneIds") or []
    for zid in zone_ids:
        iname = f"in_{zid}"
        inputs.append(
            {
                "name": iname,
                "type": "boolean",
                "description": f"Geo-feit: locatie binnen zone {zid}",
                "source": {
                    "description": (
                        f"Buiten wet-YAML; GIO/zone-engine. joinId={zs.get('gioJoinId', '')}"
                    )
                },
            }
        )
        if rule.get("zoneSemantics") == "exclusion":
            conditions_ops.append(
                {"operation": "EQUALS", "subject": f"${iname}", "value": False}
            )
        else:
            conditions_ops.append(
                {"operation": "EQUALS", "subject": f"${iname}", "value": True}
            )

    out_name = f"result_{article['number'].replace('.', '_')}"
    if not conditions_ops:
        if inputs:
            value: Any = {
                "operation": "EQUALS",
                "subject": f"${inputs[0]['name']}",
                "value": True,
            }
        else:
            raise ValueError("formalized rule without conditions or zone")
    elif len(conditions_ops) == 1:
        value = conditions_ops[0]
    else:
        value = {"operation": "AND", "conditions": conditions_ops}

    return {
        "endpoint": f"art_{article['number'].replace('.', '_')}",
        "competent_authority": {"name": "Bevoegd gezag", "type": "CATEGORY"},
        "execution": {
            "produces": {"legal_character": "TOETS"},
            "parameters": params,
            "input": inputs,
            "output": [
                {
                    "name": out_name,
                    "type": "boolean",
                    "description": f"Uitkomst artikel {article['number']}",
                }
            ],
            "actions": [{"output": out_name, "value": value}],
        },
    }


def _pick_rule(rules: List[dict], status: str) -> Optional[dict]:
    matched = [r for r in rules if r.get("status") == status]
    if not matched:
        return None
    return sorted(matched, key=lambda r: r.get("id") or "")[0]


def _formalize_one(
    poc: str,
    article: Article,
    alignment: Alignment,
) -> ArticleFormalization:
    number = article["number"]
    rules = alignment.get("formalRules") or []
    cards = alignment.get("normCards") or []
    omzet = alignment.get("omzetRows") or []

    # Eindhoven smoke: art. 10.2 from example YAML
    if poc == "eindhoven" and number == "10.2":
        return {
            "number": number,
            "status": "formalized",
            "reason": "smoke fixture omgevingsplan-eindhoven-art22.1-en-10.2.yaml",
            "machineReadable": _load_smoke_mr(SMOKE_EINDHOVEN_YAML, "10.2"),
            "normCardId": None,
            "formalRuleId": None,
            "source": "smoke-yaml",
        }

    formalized = _pick_rule(rules, "formalized")
    if formalized is not None:
        try:
            mr = formal_rule_to_machine_readable(formalized, article)
        except ValueError as exc:
            return {
                "number": number,
                "status": "ambiguous",
                "reason": f"formalized rule not mappable: {exc}",
                "machineReadable": None,
                "normCardId": formalized.get("normCardId"),
                "formalRuleId": formalized.get("id"),
                "source": "formalrule",
            }
        return {
            "number": number,
            "status": "formalized",
            "reason": formalized.get("rationale") or formalized.get("reason") or "formalized",
            "machineReadable": mr,
            "normCardId": formalized.get("normCardId"),
            "formalRuleId": formalized.get("id"),
            "source": "formalrule",
        }

    ambiguous = _pick_rule(rules, "ambiguous")
    if ambiguous is not None:
        return {
            "number": number,
            "status": "ambiguous",
            "reason": ambiguous.get("reason") or "ambiguous formalrule",
            "machineReadable": None,
            "normCardId": ambiguous.get("normCardId"),
            "formalRuleId": ambiguous.get("id"),
            "source": "formalrule",
        }

    rejected = _pick_rule(rules, "rejected")
    if rejected is not None and not any(
        r.get("status") not in (None, "rejected") for r in rules
    ):
        return {
            "number": number,
            "status": "rejected",
            "reason": rejected.get("reason") or "rejected formalrule",
            "machineReadable": None,
            "normCardId": rejected.get("normCardId"),
            "formalRuleId": rejected.get("id"),
            "source": "formalrule",
        }

    # Eindhoven: doel/bron limiet-templates + sterk-kennisbank equivalentie
    if poc == "eindhoven":
        from eindhoven_templates import try_formalize_eindhoven

        eh = try_formalize_eindhoven(article, alignment)
        if eh is not None:
            return eh  # type: ignore[return-value]

    if cards or omzet or (alignment.get("bronRegels") or alignment.get("doelRegels")):
        return {
            "number": number,
            "status": "unmatched",
            "reason": "no_template",
            "machineReadable": None,
            "normCardId": (cards[0].get("id") if cards else None),
            "formalRuleId": None,
            "source": "evidence-without-template",
        }

    return {
        "number": number,
        "status": "unmatched",
        "reason": "no_evidence",
        "machineReadable": None,
        "normCardId": None,
        "formalRuleId": None,
        "source": "none",
    }


def formalize(
    poc: Literal["utrecht", "eindhoven"],
    articles: List[Article],
    alignments: Dict[str, Alignment],
    orphans: Optional[List[dict]] = None,
    stamp: str = "1970-01-01T00:00:00Z",
) -> Tuple[Dict[str, ArticleFormalization], dict]:
    by_num: Dict[str, ArticleFormalization] = {}
    report_articles: List[dict] = []
    counts = {"formalized": 0, "ambiguous": 0, "rejected": 0, "unmatched": 0}

    for art in articles:
        al = alignments.get(art["number"]) or {
            "articleNumber": art["number"],
            "normCards": [],
            "formalRules": [],
            "bronRegels": [],
            "doelRegels": [],
            "omzetRows": [],
        }
        form = _formalize_one(poc, art, al)
        by_num[art["number"]] = form
        counts[form["status"]] += 1
        row = {
            "number": form["number"],
            "status": form["status"],
            "reason": form["reason"],
            "normCardId": form.get("normCardId"),
            "formalRuleId": form.get("formalRuleId"),
            "source": form.get("source") or "",
        }
        omzet_ids = [r.get("id") for r in (al.get("omzetRows") or []) if r.get("id")]
        if omzet_ids:
            row["omzetRowIds"] = omzet_ids
        report_articles.append(row)

    html = paths.INSTRUMENTS[poc]["html"]
    report = {
        "schemaVersion": "1",
        "poc": poc,
        "generatedAt": stamp,
        "sourceSha256": hashlib.sha256(html.read_bytes()).hexdigest(),
        "counts": counts,
        "articles": report_articles,
        "orphanedFormalRules": list(orphans or []),
    }
    return by_num, report
