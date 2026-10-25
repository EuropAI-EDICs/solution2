"""FormalizerPass — FormalRule/evidence → RegelRecht machine_readable + report."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

import yaml

import paths
from align_evidence import Alignment
from split_cvdr_html import Article

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


def _load_smoke_mr(yaml_path, article_number: str) -> dict:
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    for art in doc["articles"]:
        if art["number"] == article_number and "machine_readable" in art:
            return art["machine_readable"]
    raise SystemExit(f"smoke YAML mist machine_readable voor art. {article_number}: {yaml_path}")


# Golden-demo parity: RegelRecht endpoint/competent authority per FormalRule id
# (FormalRule schema is closed, so these cannot live on the rule itself).
RR_OVERRIDES: Dict[str, dict] = {
    "FR-W-03": {
        "endpoint": "kleine_windturbine_bestaand_bouwperceel",
        "competent_authority": {
            "name": "Bevoegd gezag omgevingsplan (gemeente binnen het Gebied kleine windturbine)",
            "type": "CATEGORY",
        },
    },
}


def formal_rule_to_machine_readable(rule: dict, article: Article) -> dict:
    """Wrap FormalRule.execution (RegelRecht SoT) as article machine_readable."""
    if rule.get("status") != "formalized":
        raise ValueError(f"rule {rule.get('id')} is not formalized")
    execution = rule.get("execution")
    if not execution:
        raise ValueError(f"rule {rule.get('id')} missing execution (RegelRecht SoT)")
    override = RR_OVERRIDES.get(rule.get("id") or "", {})
    endpoint = (
        rule.get("rrEndpoint")
        or override.get("endpoint")
        or f"art_{article['number'].replace('.', '_')}"
    )
    return {
        "endpoint": endpoint,
        "competent_authority": rule.get("competentAuthority")
        or override.get("competent_authority")
        or {"name": "Bevoegd gezag", "type": "CATEGORY"},
        "execution": execution,
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
