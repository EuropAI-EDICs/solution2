"""MC-8 — de bulk-analyse ("Plangids-analyse") voor de conversieplanning.

Per bron document: how many rules matched sterk / mogelijk / zwak / geenMatch, the
match ratio, and a conversie-gereedheid band. Plus the needs-new-rule clusters
(themes where rules found no doelregeling home — 'de doelregeling eerst uitbreiden')
and the plan-portfolio statistics from the inventory.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List

from . import __version__

ANALYSER_AGENT = f"analyser#{__version__}"


def _gereedheid(match_ratio: float) -> str:
    if match_ratio >= 0.75:
        return "conversie_gereed"
    if match_ratio >= 0.40:
        return "deels_gereed"
    return "doelregeling_uitbreiden_eerst"


def coverage(bron_regels: List[Dict], omzettabel: List[Dict], docs: Dict[str, str],
             vandaag: str) -> Dict:
    rows_by_bron = {r["bronRegelId"]: r for r in omzettabel}
    per_doc: Dict[str, Dict] = {}
    thema_zonder_match: Counter = Counter()
    thema_voorbeelden: Dict[str, List[str]] = defaultdict(list)

    for bron in bron_regels:
        doc_id = bron["docId"]
        row = rows_by_bron.get(bron["id"])
        d = per_doc.setdefault(doc_id, {
            "docId": doc_id, "naam": docs.get(doc_id, doc_id), "nRegels": 0,
            "sterk": 0, "mogelijk": 0, "zwak": 0, "geenMatch": 0,
        })
        d["nRegels"] += 1
        if row is None:
            d["geenMatch"] += 1
            continue
        bands = [s["band"] for s in row["suggesties"]]
        if not bands or row["status"] in ("geen_match", "nieuwe_regel_voorgesteld"):
            d["geenMatch"] += 1
            thema_zonder_match[bron["thema"]] += 1
            if len(thema_voorbeelden[bron["thema"]]) < 5:
                thema_voorbeelden[bron["thema"]].append(bron["id"])
        elif "sterk" in bands:
            d["sterk"] += 1
        elif "mogelijk" in bands:
            d["mogelijk"] += 1
        else:
            d["zwak"] += 1

    per_bron = []
    for doc_id in sorted(per_doc):
        d = per_doc[doc_id]
        matchbaar = d["sterk"] + d["mogelijk"]
        d["matchRatio"] = round(matchbaar / d["nRegels"], 4) if d["nRegels"] else 0.0
        d["gereedheid"] = _gereedheid(d["matchRatio"])
        per_bron.append(d)

    return {
        "perBronDocument": per_bron,
        "needsNewRules": [
            {"thema": t, "nRegels": n, "voorbeeldBronRegelIds": thema_voorbeelden[t]}
            for t, n in thema_zonder_match.most_common() if n >= 1
        ],
        "portfolio": {},  # filled by run.py from the Planviewer inventory
        "methodTrace": ["MC-8", "MC-1"],
    }
