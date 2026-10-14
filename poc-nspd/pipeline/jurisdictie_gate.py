"""V2b: jurisdictie-match — geen claim over de grens (spec §4.6)."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

_BE_NL_TYPES = {
    "nl": {"omgevingsverordening-nl", "omgevingsvisie-nl"},
    "be": {"rup-be", "gewestplan-be", "vcro-be", "vlarem-be"},
}


class JurisdictieError(RuntimeError):
    pass


def run_v2b(
    *,
    normcards: Sequence[Mapping[str, Any]],
    formal_rules: Sequence[Mapping[str, Any]],
    sources_registry: Mapping[str, Any],
    jurisdictie: str,
    strict: bool = False,
    document_registry: Mapping[str, Any] | None = None,
) -> dict:
    reg = sources_registry.get("sources", [])
    bron_jur: dict[str, str] = {s.get("id", ""): s.get("jurisdictie", "") for s in reg}
    checks: list[dict] = []
    for k in normcards:
        if k.get("jurisdictie") != jurisdictie:
            checks.append({"id": "V2B-KAART", "status": "fail",
                           "detail": f"{k.get('id')}: jurisdictie {k.get('jurisdictie')} in run {jurisdictie}"})
        itype = k.get("instrumentType", "")
        if itype and itype not in _BE_NL_TYPES[jurisdictie]:
            checks.append({"id": "V2B-INSTRUMENT", "status": "fail",
                           "detail": f"{k.get('id')}: instrumentType {itype} niet thuis in {jurisdictie}"})
    for fr in formal_rules:
        if fr.get("jurisdictie") != jurisdictie:
            checks.append({"id": "V2B-RULE", "status": "fail",
                           "detail": f"{fr.get('id')}: jurisdictie {fr.get('jurisdictie')} in run {jurisdictie}"})
        kaart = next((k for k in normcards if k.get("id") == fr.get("normCardId")), None)
        if kaart and kaart.get("jurisdictie") != jurisdictie:
            checks.append({"id": "V2B-RULEKAART", "status": "fail",
                           "detail": f"{fr.get('id')}: linkt naar {kaart.get('id')} ({kaart.get('jurisdictie')})"})
    if document_registry is not None:
        for k in normcards:
            src = k.get("source") or {}
            doc_id = src.get("docId", "") if isinstance(src, Mapping) else ""
            doc = document_registry.get(doc_id)
            doc_jur = doc.get("jurisdictie") if isinstance(doc, Mapping) else None
            if doc is None or doc_jur != jurisdictie:
                checks.append({"id": "V2B-BRON", "status": "fail",
                               "detail": f"{k.get('id')}: bron {doc_id} heeft jurisdictie {doc_jur} in run {jurisdictie}"})
    status = "pass" if not any(c["status"] == "fail" for c in checks) else "fail"
    if status == "fail" and strict:
        raise JurisdictieError("; ".join(c["detail"] for c in checks if c["status"] == "fail"))
    return {"status": status, "checks": checks}
