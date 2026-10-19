"""Deterministische Eindhoven-templates: doel/bron-limieten + sterk-kennisbank equivalentie."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from align_evidence import Alignment
from split_cvdr_html import Article

# Prefer specific building metrics before generic maximaal-phrases.
_BOUWHOOGTE = re.compile(
    r"bouwhoogte[^\d]{0,60}(\d+(?:[.,]\d+)?)\s*m\b", re.I
)
_GOOTHOOGTE = re.compile(
    r"goothoogte[^\d]{0,60}(\d+(?:[.,]\d+)?)\s*m\b", re.I
)
_MAXIMAAL = re.compile(
    r"(?:maximaal|ten hoogste|niet meer dan|hoogstens)\s+"
    r"(\d+(?:[.,]\d+)?)\s*(m|meter|m²|m2|%|procent)\b",
    re.I,
)
_VERBOD = re.compile(
    r"\b(?:het is verboden|is verboden|zijn verboden)\b", re.I
)
_UITZONDERING = re.compile(
    r"\b(?:uitzondering|tenzij|niet van toepassing|met dien verstande)\b", re.I
)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _collect_values(pattern: re.Pattern, text: str) -> List[float]:
    vals = [_num(m.group(1)) for m in pattern.finditer(text)]
    # unique preserving order
    out: List[float] = []
    for v in vals:
        if v not in out:
            out.append(v)
    return out


def _mr_limit(
    article_number: str,
    param: str,
    limit: float,
    *,
    source: str,
    reason: str,
    include_zone: bool = True,
) -> Dict[str, Any]:
    out_name = f"toegestaan_art_{article_number.replace('.', '_')}"
    conditions: List[dict] = [
        {
            "operation": "LESS_THAN_OR_EQUAL",
            "subject": f"${param}",
            "value": limit,
        }
    ]
    inputs: List[dict] = []
    if include_zone:
        inputs.append(
            {
                "name": "in_werkingsgebied",
                "type": "boolean",
                "description": "Geo-feit: locatie binnen werkingsgebied van de regel.",
                "source": {
                    "description": "Buiten wet-YAML; werkingsgebiedRef / zone-engine (MC-11)."
                },
            }
        )
        conditions.append(
            {
                "operation": "EQUALS",
                "subject": "$in_werkingsgebied",
                "value": True,
            }
        )
    value: Any = (
        conditions[0]
        if len(conditions) == 1
        else {"operation": "AND", "conditions": conditions}
    )
    return {
        "number": article_number,
        "status": "formalized",
        "reason": reason,
        "machineReadable": {
            "endpoint": f"art_{article_number.replace('.', '_')}",
            "competent_authority": {
                "name": "College van burgemeester en wethouders van de gemeente Eindhoven",
                "type": "INSTANCE",
            },
            "execution": {
                "produces": {"legal_character": "TOETS"},
                "parameters": [
                    {
                        "name": param,
                        "type": "number",
                        "description": f"Gemeten {param} t.o.v. limiet {limit}",
                    }
                ],
                "input": inputs,
                "output": [
                    {
                        "name": out_name,
                        "type": "boolean",
                        "description": f"Of artikel {article_number} de activiteit toelaat.",
                    }
                ],
                "actions": [{"output": out_name, "value": value}],
            },
        },
        "normCardId": None,
        "formalRuleId": None,
        "source": source,
    }


def _mr_verbod(article_number: str, *, source: str, reason: str) -> Dict[str, Any]:
    out_name = f"toegestaan_art_{article_number.replace('.', '_')}"
    return {
        "number": article_number,
        "status": "formalized",
        "reason": reason,
        "machineReadable": {
            "endpoint": f"art_{article_number.replace('.', '_')}_verbod",
            "competent_authority": {
                "name": "College van burgemeester en wethouders van de gemeente Eindhoven",
                "type": "INSTANCE",
            },
            "execution": {
                "produces": {"legal_character": "TOETS"},
                "parameters": [
                    {
                        "name": "activiteit_valt_onder_verbod",
                        "type": "boolean",
                        "description": "Of de voorgenomen activiteit onder het verbod valt.",
                    }
                ],
                "input": [
                    {
                        "name": "in_werkingsgebied",
                        "type": "boolean",
                        "description": "Geo-feit: locatie binnen werkingsgebied van de regel.",
                        "source": {
                            "description": "Buiten wet-YAML; werkingsgebiedRef / zone-engine (MC-11)."
                        },
                    }
                ],
                "output": [
                    {
                        "name": out_name,
                        "type": "boolean",
                        "description": f"Of artikel {article_number} de activiteit toelaat.",
                    }
                ],
                "actions": [
                    {
                        "output": out_name,
                        "value": {
                            "operation": "AND",
                            "conditions": [
                                {
                                    "operation": "EQUALS",
                                    "subject": "$activiteit_valt_onder_verbod",
                                    "value": False,
                                },
                                {
                                    "operation": "EQUALS",
                                    "subject": "$in_werkingsgebied",
                                    "value": True,
                                },
                            ],
                        },
                    }
                ],
            },
        },
        "normCardId": None,
        "formalRuleId": None,
        "source": source,
    }


def _mr_equivalentie(
    article_number: str, *, omzet_id: str, kb_id: Optional[str], source: str
) -> Dict[str, Any]:
    out_name = f"equivalentie_houdt_art_{article_number.replace('.', '_')}"
    reason = f"sterk omzetpaar {omzet_id}"
    if kb_id:
        reason += f" / {kb_id}"
    return {
        "number": article_number,
        "status": "formalized",
        "reason": reason,
        "machineReadable": {
            "endpoint": f"art_{article_number.replace('.', '_')}_equivalentie",
            "competent_authority": {
                "name": "College van burgemeester en wethouders van de gemeente Eindhoven",
                "type": "INSTANCE",
            },
            "execution": {
                "produces": {"legal_character": "TOETS"},
                "parameters": [],
                "input": [
                    {
                        "name": "strijd_met_tijdelijk_deel",
                        "type": "boolean",
                        "description": (
                            "Of de regel ter plaatse strijdig is met een nog "
                            "inwerkingzijnde regel uit het tijdelijke deel."
                        ),
                        "source": {
                            "description": (
                                "Buiten wet-YAML: conversieketen poc-bp2op "
                                f"(omzet {omzet_id}"
                                + (f", kennisbank {kb_id}" if kb_id else "")
                                + ")."
                            )
                        },
                    }
                ],
                "output": [
                    {
                        "name": out_name,
                        "type": "boolean",
                        "description": (
                            "Of de conversie-equivalentie voor dit artikel houdbaar is "
                            "(geen strijd met tijdelijk deel)."
                        ),
                    }
                ],
                "actions": [
                    {
                        "output": out_name,
                        "value": {
                            "operation": "IF",
                            "cases": [
                                {
                                    "when": {
                                        "operation": "EQUALS",
                                        "subject": "$strijd_met_tijdelijk_deel",
                                        "value": True,
                                    },
                                    "then": False,
                                }
                            ],
                            "default": True,
                        },
                    }
                ],
            },
        },
        "normCardId": None,
        "formalRuleId": None,
        "source": source,
    }


def _try_limit_or_verbod(
    text: str, article_number: str, source: str
) -> Optional[Dict[str, Any]]:
    """Extract bouwhoogte/goothoogte/maximaal/verbod; ambiguous on conflicting same-kind limits."""
    bouw = _collect_values(_BOUWHOOGTE, text)
    if len(bouw) > 1:
        return {
            "number": article_number,
            "status": "ambiguous",
            "reason": f"meerdere bouwhoogte-limieten: {bouw}",
            "machineReadable": None,
            "normCardId": None,
            "formalRuleId": None,
            "source": source,
        }
    if len(bouw) == 1:
        return _mr_limit(
            article_number,
            "bouwhoogte_m",
            bouw[0],
            source=source,
            reason=f"template bouwhoogte <= {bouw[0]} m",
        )

    goot = _collect_values(_GOOTHOOGTE, text)
    if len(goot) > 1:
        return {
            "number": article_number,
            "status": "ambiguous",
            "reason": f"meerdere goothoogte-limieten: {goot}",
            "machineReadable": None,
            "normCardId": None,
            "formalRuleId": None,
            "source": source,
        }
    if len(goot) == 1:
        return _mr_limit(
            article_number,
            "goothoogte_m",
            goot[0],
            source=source,
            reason=f"template goothoogte <= {goot[0]} m",
        )

    # Generic maximaal — group by unit; conflict within same unit → ambiguous
    by_unit: Dict[str, List[float]] = {}
    for m in _MAXIMAAL.finditer(text):
        unit = m.group(2).lower().replace("meter", "m").replace("procent", "%")
        if unit == "m2":
            unit = "m²"
        by_unit.setdefault(unit, [])
        v = _num(m.group(1))
        if v not in by_unit[unit]:
            by_unit[unit].append(v)
    if by_unit:
        # prefer meters
        for unit in ("m", "m²", "%"):
            if unit not in by_unit:
                continue
            vals = by_unit[unit]
            if len(vals) > 1:
                return {
                    "number": article_number,
                    "status": "ambiguous",
                    "reason": f"meerdere maximaal-limieten ({unit}): {vals}",
                    "machineReadable": None,
                    "normCardId": None,
                    "formalRuleId": None,
                    "source": source,
                }
            param = {"m": "limiet_m", "m²": "limiet_m2", "%": "limiet_pct"}[unit]
            return _mr_limit(
                article_number,
                param,
                vals[0],
                source=source,
                reason=f"template maximaal {vals[0]} {unit}",
            )

    if _VERBOD.search(text) and not _UITZONDERING.search(text):
        return _mr_verbod(
            article_number,
            source=source,
            reason="template verbod zonder uitzonderingsketen",
        )
    return None


def _joined_tekst(regels: List[dict]) -> str:
    parts = []
    for r in sorted(regels, key=lambda x: x.get("id") or ""):
        t = (r.get("tekst") or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _sterk_omzet(alignment: Alignment) -> Optional[Tuple[str, Optional[str]]]:
    """Return (omzetRowId, kennisbankHitId) for first suggestie with band=sterk."""
    for row in sorted(alignment.get("omzetRows") or [], key=lambda r: r.get("id") or ""):
        for sug in row.get("suggesties") or []:
            if sug.get("band") == "sterk":
                return row.get("id") or "?", sug.get("kennisbankHitId")
    return None


def try_formalize_eindhoven(
    article: Article, alignment: Alignment
) -> Optional[Dict[str, Any]]:
    """Try doel → bron → sterk-kennisbank templates. None = leave to unmatched fallback."""
    number = article["number"]

    doel_text = _joined_tekst(alignment.get("doelRegels") or [])
    if doel_text:
        hit = _try_limit_or_verbod(doel_text, number, source="eindhoven-doel-template")
        if hit is not None:
            return hit

    bron_text = _joined_tekst(alignment.get("bronRegels") or [])
    if bron_text:
        hit = _try_limit_or_verbod(bron_text, number, source="eindhoven-bron-template")
        if hit is not None:
            return hit

    sterk = _sterk_omzet(alignment)
    if sterk is not None:
        omzet_id, kb_id = sterk
        return _mr_equivalentie(
            number,
            omzet_id=omzet_id,
            kb_id=kb_id,
            source="eindhoven-kennisbank-equivalentie",
        )

    return None
