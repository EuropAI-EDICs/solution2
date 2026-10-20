"""Join DSO-annotaties op RegelRecht formalization-report."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

_ART_FROM_WID = re.compile(r"__art_([\d.]+)")


def article_numbers_from_annotaties(payload: dict[str, Any]) -> list[str]:
    """Unieke artikelnummers uit regelteksten.wId (volgorde: eerste voorkomen)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for rt in payload.get("regelteksten") or []:
        wid = rt.get("wId") or ""
        m = _ART_FROM_WID.search(wid)
        if not m:
            continue
        num = m.group(1)
        if num not in seen:
            seen.add(num)
            ordered.append(num)
    return ordered


def load_report_status(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["number"]: a for a in report.get("articles") or []}


def build_overlap(
    *,
    instrument_id: str,
    location: dict[str, Any],
    regeling: dict[str, Any] | None,
    annotaties: dict[str, Any],
    annotaties_sha256: str,
    report: dict[str, Any],
    rp_plannen: dict[str, Any] | None = None,
    rp_sha256: str | None = None,
) -> dict[str, Any]:
    dso_arts = article_numbers_from_annotaties(annotaties)
    by_num = load_report_status(report)
    report_nums = set(by_num)

    status_counts: Counter[str] = Counter()
    articles_out: list[dict[str, Any]] = []
    for num in dso_arts:
        meta = by_num.get(num)
        if meta is None:
            status = "missing_in_report"
            reason = "artikel in DSO-hit, niet in formalization-report"
            source = None
        else:
            status = meta.get("status") or "unknown"
            reason = meta.get("reason")
            source = meta.get("source")
        status_counts[status] += 1
        articles_out.append(
            {
                "number": num,
                "rrStatus": status,
                "reason": reason,
                "source": source,
                "executable": status == "formalized",
            }
        )

    executable = [a["number"] for a in articles_out if a["executable"]]
    abstain = [a["number"] for a in articles_out if not a["executable"]]

    rp_summary = None
    if rp_plannen is not None:
        plans = (rp_plannen.get("_embedded") or {}).get("plannen") or []
        rp_summary = {
            "sha256": rp_sha256,
            "count": len(plans),
            "plans": [
                {
                    "id": p.get("id"),
                    "naam": p.get("naam"),
                    "planStatus": p.get("planStatus"),
                    "typePlan": p.get("typePlan"),
                }
                for p in plans[:50]
            ],
        }

    return {
        "schemaVersion": "1",
        "instrument": instrument_id,
        "location": {
            "id": location["id"],
            "label": location.get("label"),
            "notes": location.get("notes"),
            "geometry": location["geometry"],
            "source": location.get("source"),
        },
        "dso": {
            "regelingIdentificatie": (regeling or {}).get("identificatie"),
            "officieleTitel": (regeling or {}).get("officieleTitel")
            or (regeling or {}).get("citeerTitel"),
            "annotatiesSha256": annotaties_sha256,
            "counts": {
                "regelteksten": len(annotaties.get("regelteksten") or []),
                "activiteiten": len(annotaties.get("activiteiten") or []),
                "locaties": len(annotaties.get("locaties") or []),
                "gebiedsaanwijzingen": len(annotaties.get("gebiedsaanwijzingen") or []),
                "regelsVoorIedereen": len(annotaties.get("regelsVoorIedereen") or []),
                "instructieregels": len(annotaties.get("instructieregels") or []),
                "uniqueArticleNumbers": len(dso_arts),
            },
        },
        "regelrecht": {
            "reportGeneratedAt": report.get("generatedAt"),
            "reportCounts": report.get("counts"),
            "reportArticleTotal": len(report_nums),
        },
        "overlap": {
            "statusCounts": dict(status_counts),
            "executableCount": len(executable),
            "abstainCount": len(abstain),
            "dsoOnlyCount": status_counts.get("missing_in_report", 0),
            "coverageExecutable": (
                round(len(executable) / len(dso_arts), 4) if dso_arts else None
            ),
            "executableArticles": executable,
            "abstainArticles": abstain,
            "articles": articles_out,
        },
        "ruimtelijkePlannen": rp_summary,
        "interpretation": {
            "dso": (
                "Presenteren levert toepasselijke annotaties op de geometrie "
                "(deterministische retrieval), geen uitvoeringsbesluit."
            ),
            "regelrecht": (
                "Alleen rrStatus=formalized is uitvoerbaar via reference_engine; "
                "overige artikelen blijven onthouding (tekst-only)."
            ),
            "next": (
                "Pin activiteitparameters + in_werkingsgebied / "
                "strijd_met_tijdelijk_deel en evalueer formalized artikelen."
            ),
        },
    }
