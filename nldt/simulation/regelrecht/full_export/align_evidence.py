"""EvidenceAligner — koppel NormCards/FormalRules/bron·doel·omzet aan artikelen."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

import paths
from split_cvdr_html import Article

_ART_NUM_RE = re.compile(r"(\d+\.\d+[a-z]?)")
_WS_RE = re.compile(r"\s+")


class Alignment(TypedDict):
    articleNumber: str
    normCards: List[dict]
    formalRules: List[dict]
    bronRegels: List[dict]
    doelRegels: List[dict]
    omzetRows: List[dict]


def normalize_article_ref(ref: Optional[str]) -> Optional[str]:
    """Map 'art. 5.3, eerste lid' / 'Artikel 22.1' → '5.3'. None for non-article locators."""
    if not ref or not isinstance(ref, str):
        return None
    s = ref.strip()
    # Reject paragraph/section locators without an article number pattern near start
    low = s.lower()
    if low.startswith(("par.", "par ", "paragraaf", "toelichting op par")):
        return None
    if "duurzame energie" in low and not re.search(r"\d+\.\d+", s):
        return None
    m = _ART_NUM_RE.search(s)
    if not m:
        return None
    # Prefer match after 'art' / 'artikel' when present
    art_m = re.search(r"(?:art\.?|artikel)\s*(\d+\.\d+[a-z]?)", s, re.I)
    if art_m:
        return art_m.group(1)
    return m.group(1)


def _norm_ws(text: str) -> str:
    return _WS_RE.sub(" ", (text or "")).strip().lower()


def _empty_alignment(number: str) -> Alignment:
    return {
        "articleNumber": number,
        "normCards": [],
        "formalRules": [],
        "bronRegels": [],
        "doelRegels": [],
        "omzetRows": [],
    }


def _load_json(path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _overlay_corpus_execution(track: str, rules: List[dict]) -> List[dict]:
    """Frozen runs predate RegelRecht execution SoT; take execution/zoneBinding
    from the live corpus (same id + normCardId) for formalized rules lacking it."""
    corpus = paths.ROOT / f"poc/corpus/formalrules-{track}.json"
    if not corpus.exists():
        return rules
    by_id = {r["id"]: r for r in _load_json(corpus)}
    out: List[dict] = []
    for rule in rules:
        src = by_id.get(rule.get("id"))
        if (
            rule.get("status") == "formalized"
            and not rule.get("execution")
            and src is not None
            and src.get("normCardId") == rule.get("normCardId")
            and src.get("execution")
        ):
            rule = dict(rule)
            rule["execution"] = src["execution"]
            if src.get("zoneBinding"):
                rule["zoneBinding"] = src["zoneBinding"]
        out.append(rule)
    return out


def _align_utrecht(
    articles: List[Article],
) -> Tuple[Dict[str, Alignment], List[dict]]:
    by_num: Dict[str, Alignment] = {
        a["number"]: _empty_alignment(a["number"]) for a in articles
    }
    text_by_num = {a["number"]: _norm_ws(a["text"]) for a in articles}
    orphans: List[dict] = []
    cards_by_id: Dict[str, dict] = {}

    for track, run_dir in paths.UTRECHT_TRACK_RUNS:
        nc_path = run_dir / "normcards.json"
        if not nc_path.exists():
            continue
        for card in _load_json(nc_path):
            cards_by_id[card["id"]] = card
            src = card.get("source") or {}
            hint = src.get("article") or card.get("article")
            num = normalize_article_ref(hint)
            if num is None:
                orphans.append(
                    {
                        "id": card["id"],
                        "articleHint": hint,
                        "reason": "non_article_locator",
                        "kind": "normcard",
                        "track": track,
                    }
                )
                continue
            if num not in by_num:
                orphans.append(
                    {
                        "id": card["id"],
                        "articleHint": hint,
                        "reason": "article_not_in_instrument",
                        "kind": "normcard",
                        "track": track,
                    }
                )
                continue
            entry = dict(card)
            quote = _norm_ws(src.get("quote") or "")
            if quote and quote not in text_by_num[num]:
                entry["alignmentNote"] = "quote_not_in_article_text"
            by_num[num]["normCards"].append(entry)

    for track, run_dir in paths.UTRECHT_TRACK_RUNS:
        fr_path = run_dir / "formalrules.json"
        if not fr_path.exists():
            # fall back to corpus for wind/zon/bos if run missing (should not happen)
            corpus = paths.ROOT / f"poc/corpus/formalrules-{track}.json"
            fr_path = corpus if corpus.exists() else fr_path
        if not fr_path.exists():
            continue
        for rule in _overlay_corpus_execution(track, _load_json(fr_path)):
            ncid = rule.get("normCardId")
            card = cards_by_id.get(ncid)
            if card is None:
                orphans.append(
                    {
                        "id": rule["id"],
                        "articleHint": ncid,
                        "reason": "unknown_normCardId",
                        "kind": "formalrule",
                        "track": track,
                    }
                )
                continue
            hint = (card.get("source") or {}).get("article")
            num = normalize_article_ref(hint)
            if num is None or num not in by_num:
                orphans.append(
                    {
                        "id": rule["id"],
                        "articleHint": hint,
                        "reason": "orphan_via_normcard",
                        "kind": "formalrule",
                        "track": track,
                    }
                )
                continue
            by_num[num]["formalRules"].append(rule)

    return by_num, orphans


def _align_eindhoven(
    articles: List[Article],
) -> Tuple[Dict[str, Alignment], List[dict]]:
    by_num: Dict[str, Alignment] = {
        a["number"]: _empty_alignment(a["number"]) for a in articles
    }
    orphans: List[dict] = []
    run = paths.EINDHOVEN_RUN
    bron_by_id: Dict[str, dict] = {}
    doel_by_id: Dict[str, dict] = {}

    for bron in _load_json(run / "bronregels.json"):
        bron_by_id[bron["id"]] = bron
        num = (bron.get("locator") or {}).get("artikel")
        if num in by_num:
            by_num[num]["bronRegels"].append(bron)
        else:
            orphans.append(
                {
                    "id": bron["id"],
                    "articleHint": num,
                    "reason": "article_not_in_instrument",
                    "kind": "bronregel",
                }
            )

    for doel in _load_json(run / "doelregels.json"):
        doel_by_id[doel["id"]] = doel
        num = (doel.get("locator") or {}).get("artikel")
        if num in by_num:
            by_num[num]["doelRegels"].append(doel)
        else:
            orphans.append(
                {
                    "id": doel["id"],
                    "articleHint": num,
                    "reason": "article_not_in_instrument",
                    "kind": "doelregel",
                }
            )

    for row in _load_json(run / "omzettabel.json"):
        linked_nums: set[str] = set()
        bron = bron_by_id.get(row.get("bronRegelId") or "")
        if bron:
            n = (bron.get("locator") or {}).get("artikel")
            if n:
                linked_nums.add(n)
        for sug in row.get("suggesties") or []:
            doel = doel_by_id.get(sug.get("doelRegelId") or "")
            if doel:
                n = (doel.get("locator") or {}).get("artikel")
                if n:
                    linked_nums.add(n)
        if not linked_nums:
            orphans.append(
                {
                    "id": row.get("id"),
                    "articleHint": row.get("bronRegelId"),
                    "reason": "omzet_unlinked",
                    "kind": "omzetrij",
                }
            )
            continue
        for n in linked_nums:
            if n in by_num:
                by_num[n]["omzetRows"].append(row)
            else:
                orphans.append(
                    {
                        "id": row.get("id"),
                        "articleHint": n,
                        "reason": "article_not_in_instrument",
                        "kind": "omzetrij",
                    }
                )

    return by_num, orphans


def align(
    poc: Literal["utrecht", "eindhoven"], articles: List[Article]
) -> Tuple[Dict[str, Alignment], List[dict]]:
    if poc == "utrecht":
        return _align_utrecht(articles)
    if poc == "eindhoven":
        return _align_eindhoven(articles)
    raise ValueError(f"unknown poc: {poc}")
