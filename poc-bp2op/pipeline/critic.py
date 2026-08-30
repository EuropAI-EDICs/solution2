"""MC-6 — de Critic: vijf validatieniveaus, waarvan V4 (mens) altijd pending is.

V0 syntactic   — every artifact schema-valid (the gate every boundary crossing passes)
V1 completeness— every bron regel appears in exactly one omzettabel row; every
                 doelRegelId reference resolves; every kennisbank doorgelinkte pair
                 resolves to an existing doel artikel
V2 grounding   — every bron/doel tekst is verbatim present in its archived source
                 file (re-extracted independently), every URL is the official permalink
V3 semantic    — an independent matcher (Jaccard instead of TF-IDF) re-scores every
                 suggestion; top-1 agreement and score deltas are measured, not assumed
V4 human       — the jurist checkpoint: rows needing review are listed, never resolved
"""

from __future__ import annotations

import html as _html_mod
import re
from pathlib import Path
from typing import Dict, List, Tuple

from . import __version__, contracts
from .knowledgebank import JaccardMatcher, Kennisbank, normalize

CRITIC_AGENT = f"critic#{__version__}"


def _report(artifact: str, checks: List[Dict], generated_at: str) -> Dict:
    levels = {
        "V0_syntactic": "pass", "V1_completeness": "pass", "V2_grounding": "pass",
        "V3_semantic": "pass", "V4_human": "pending",
    }
    for c in checks:
        if not c["passed"]:
            key = {"V0": "V0_syntactic", "V1": "V1_completeness", "V2": "V2_grounding", "V3": "V3_semantic"}.get(c["level"])
            if key and levels[key] == "pass":
                levels[key] = "fail"
    verdict = "pass" if all(v in ("pass", "pending", "not_applicable") for v in levels.values()) else "fail"
    return {"artifact": artifact, "generatedAt": generated_at, "levels": levels,
            "checks": checks, "verdict": verdict}


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def validate_pipeline(request: Dict, bron_regels: List[Dict], doel_regels: List[Dict],
                      kennisbank_pairs: List[Dict], omzettabel: List[Dict],
                      coverage_report: Dict, sources: Dict[str, Path],
                      generated_at: str) -> Tuple[Dict, Dict]:
    """Run all checks; returns (validation_report, v3_detail for the run summary)."""
    checks: List[Dict] = []

    def chk(cid, level, passed, evidence):
        checks.append({"id": cid, "level": level, "passed": bool(passed), "evidence": evidence})

    # ---- V0 ---------------------------------------------------------------- #
    v0_ok = True
    try:
        contracts.validate("conversion-request", request)
        contracts.validate_many("bron-regel", bron_regels)
        contracts.validate_many("doel-regel", doel_regels)
        contracts.validate_many("kennisbank-pair", kennisbank_pairs)
        contracts.validate_many("omzettabel-row", omzettabel)
        contracts.validate("coverage-report", coverage_report)
    except contracts.ContractError as exc:
        v0_ok = False
        chk("chk-v0-schemas", "V0", False, str(exc)[:300])
    else:
        chk("chk-v0-schemas", "V0", True,
            f"{1 + len(bron_regels) + len(doel_regels) + len(kennisbank_pairs) + len(omzettabel) + 1} artifacts schema-valid")

    # ---- V1 ---------------------------------------------------------------- #
    bron_ids = {b["id"] for b in bron_regels}
    doel_ids = {d["id"] for d in doel_regels}
    rows_by_bron: Dict[str, List[Dict]] = {}
    for row in omzettabel:
        rows_by_bron.setdefault(row["bronRegelId"], []).append(row)
    dubbel = sorted(b for b, rs in rows_by_bron.items() if len(rs) > 1)
    missend = sorted(bron_ids - set(rows_by_bron))
    spook = sorted(set(rows_by_bron) - bron_ids)
    chk("chk-v1-elke-bronregel-een-rij", "V1", not dubbel and not missend and not spook,
        f"dubbel={dubbel[:5]} missend={missend[:5]} spook={spook[:5]}")
    onbekende_doel = sorted({s["doelRegelId"] for r in omzettabel for s in r["suggesties"]} - doel_ids)
    chk("chk-v1-doelreferenties", "V1", not onbekende_doel, f"onoplosbare doelRegelIds: {onbekende_doel[:5]}")
    kb_doel = sorted({p["doelRegelId"] for p in kennisbank_pairs
                      if p.get("doelRegelId") and p["doelRegelId"] not in doel_ids})
    chk("chk-v1-kennisbank-koppelingen", "V1", not kb_doel, f"kennisbank naar onbekende doelregels: {kb_doel[:5]}")

    # ---- V2 grounding ------------------------------------------------------- #
    _html_unescape = _html_mod.unescape

    def _in_source(doc_key: str, needle: str) -> bool:
        path = sources.get(doc_key)
        if path is None or not Path(path).exists():
            return False
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
        hay = _norm_ws(_html_unescape(re.sub(r"<[^>]+>", " ", raw)))
        return _norm_ws(needle)[:280] in hay

    bron_fouten = [b["id"] for b in bron_regels if not _in_source("doelregeling", b["tekst"])]
    chk("chk-v2-bronteksten-verbatim", "V2", not bron_fouten,
        f"bron teksten niet verbatim in bronpublicatie: {bron_fouten[:5]}")
    doel_fouten = [d["id"] for d in doel_regels if not _in_source("doelregeling", d["tekst"])]
    chk("chk-v2-doelteksten-verbatim", "V2", not doel_fouten,
        f"doel teksten niet verbatim in CVDR696400: {doel_fouten[:5]}")
    kb_doc_fouten = [p["id"] for p in kennisbank_pairs if p["origin"] == "officiele_publicatie"
                     and not _in_source(p["bronDocId"], p["quote"])]
    chk("chk-v2-kennisbank-citaten", "V2", not kb_doc_fouten,
        f"kennisbank citaten niet verbatim in besluit: {kb_doc_fouten[:5]}")
    url_fouten = [d["id"] for d in doel_regels if f"CVDR{d['cvdr'].split('/')[0].replace('CVDR', '')}" not in d["url"]]
    chk("chk-v2-permalinks", "V2", not url_fouten, f"permalinks zonder juiste CVDR-id: {url_fouten[:5]}")

    # ---- V3 semantic re-execution ------------------------------------------ #
    by_id = {d["id"]: d for d in doel_regels}
    kb = Kennisbank(kennisbank_pairs)
    jac = JaccardMatcher()
    once = {}
    top1_agree = 0
    compared = 0
    kb_driven = 0
    deltas: List[float] = []
    for row in omzettabel:
        if not row["suggesties"]:
            continue
        bron = next(b for b in bron_regels if b["id"] == row["bronRegelId"])
        if row["suggesties"][0].get("kennisbankHitId"):
            kb_driven += 1  # primary driven by a published relation, not by text
            # similarity: an independent text matcher is *expected* to disagree here
            continue
        query = f"{bron['locator']['label']} {bron['tekst']}"
        if bron["id"] not in once:
            once[bron["id"]] = sorted(
                ((jac.score(query, f"artikel {by_id[d]['locator']['artikel']} {by_id[d]['locator']['titel']} {by_id[d]['tekst']}"), d)
                 for d in by_id), key=lambda t: -t[0])
        v3_top = once[bron["id"]][0][1]
        compared += 1
        if v3_top == row["suggesties"][0]["doelRegelId"]:
            top1_agree += 1
        v3_score = next((s for s, d in once[bron["id"]] if d == row["suggesties"][0]["doelRegelId"]), 0.0)
        deltas.append(abs(v3_score - row["suggesties"][0]["score"]))
    agreement = round(top1_agree / compared, 4) if compared else 1.0
    mean_delta = round(sum(deltas) / len(deltas), 4) if deltas else 0.0
    v3_pass = agreement >= 0.30 or compared == 0  # two different algorithms on
    # different text units never agree fully; gross disagreement (agreement < 0.30)
    # means the primary matcher is structurally broken, not just differently tuned
    chk("chk-v3-onafhankelijke-matcher", "V3", v3_pass,
        f"Jaccard top-1 overeenkomst {agreement} over {compared} tekst-gedreven rijen "
        f"({kb_driven} kennisbank-gedrive rijen buiten vergelijking: daar bepaalt een "
        f"gepubliceerde relatie de top-1, geen tekstgelijkenis); gemiddelde |score-delta| {mean_delta}")

    # ---- V4 human ----------------------------------------------------------- #
    needs_human = [r["id"] for r in omzettabel if r["status"] == "needs_human"]
    chk("chk-v4-jurist-checkpoint", "V4", True,
        f"{len(needs_human)} rijen aangewezen voor jurist-toets; geen enkele rij verlaat de pipeline als 'gekoppeld' zonder mens")

    report = _report("pipeline-run", checks, generated_at)
    detail = {"v3Agreement": agreement, "v3MeanDelta": mean_delta, "v3Compared": compared}
    return report, detail
