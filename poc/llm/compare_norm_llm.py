#!/usr/bin/env python3
"""Golden-set S1/S2 regression: deterministic replay vs the LLM norm seams.

Analog of ``poc/scenarios/compare_authors.py`` for the PoC-1 norm seams
(docs/GENAI_SEAMS.md S1/S2): run the Norm Analyst and Norm Formalizer over a
track's corpus shard twice — once deterministic (the reproducible golden
set), once with the live LLM hooks — and compare what changed. Proposals
only; no zone fetching or re-execution, so this is cheap and offline for the
deterministic leg. The LLM legs need ``LDT_NORM_LLM_ENDPOINT`` (local open
model, temperature 0).

    python3 poc/llm/compare_norm_llm.py                  # wind
    python3 poc/llm/compare_norm_llm.py --use-case zon
    python3 poc/llm/compare_norm_llm.py --use-case bos

Output: ``poc/llm-runs/<ts>-<use-case>-normcmp/comparison.json`` + console
table. Regression signals: claim drift on S1 (count + examples), S2
proposals accepted/rejected per gate, and — the hard invariant — zero
changes to citations, legal force, geo bindings, and to cards/rules the
hooks never touched.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import agents, contracts, norm_llm  # noqa: E402

OUT_ROOT = POC_ROOT / "llm-runs"

TRACK_SHARDS = {
    "wind": "corpus/evidence-wind.json",
    "zon": "corpus/evidence-zon.json",
    "bos": "corpus/evidence-bos.json",
}

# run.py owns ZONE_SOURCES; to keep this script import-light we mirror the
# allowed-zone derivation used there (registry is imported lazily).
sys.path.insert(0, str(POC_ROOT.parent))


def _allowed_zone_ids() -> List[str]:
    allowed = set()
    for _eid, spec in agents.TEMPLATE_SPECS.items():
        allowed.update((spec.get("zone") or {}).get("zoneIds") or [])
    try:
        import run as poc_run  # noqa: E402  (poc/run.py)

        allowed.update(poc_run.ZONE_SOURCES)
    except Exception:
        pass
    return sorted(allowed)


def _deterministic_leg(shard: Path) -> Dict[str, Any]:
    analyst = agents.NormAnalyst()
    cards = [c.to_dict() for c in analyst.read(shard)]
    formalizer = agents.NormFormalizer()
    rules = [r.to_dict() for r in formalizer.formalize(cards)]
    return {"cards": cards, "rules": rules, "coverage": formalizer.last_coverage}


def _llm_leg(shard: Path, analyst_hook, formalizer_hook) -> Dict[str, Any]:
    analyst = agents.NormAnalyst(llm_hook=analyst_hook)
    cards = [c.to_dict() for c in analyst.read(shard)]
    formalizer = agents.NormFormalizer(llm_hook=formalizer_hook)
    rules = [r.to_dict() for r in formalizer.formalize(cards)]
    return {"cards": cards, "rules": rules, "coverage": formalizer.last_coverage}


def _compare(det: Dict[str, Any], llm: Dict[str, Any]) -> Dict[str, Any]:
    det_cards = {c["id"]: c for c in det["cards"]}
    llm_cards = {c["id"]: c for c in llm["cards"]}
    claims_changed: List[Dict[str, Any]] = []
    invariant_violations: List[Dict[str, Any]] = []
    for cid, card in llm_cards.items():
        base = det_cards.get(cid)
        if base is None:
            invariant_violations.append({"cardId": cid, "reason": "card not in deterministic leg"})
            continue
        if card.get("claim") != base.get("claim"):
            claims_changed.append({"cardId": cid})
        for field in ("source", "legalForce", "theme", "geoBinding", "instrument"):
            if card.get(field) != base.get(field):
                invariant_violations.append({"cardId": cid, "field": field,
                                             "reason": "hook must not touch this field"})
        if set(card.get("appliesTo", {}).get("contextTags") or ()) != set(
            base.get("appliesTo", {}).get("contextTags") or ()
        ):
            invariant_violations.append({"cardId": cid, "field": "appliesTo.contextTags",
                                         "reason": "hook must not touch this field"})

    det_rules = {r["id"]: r for r in det["rules"]}
    llm_rules = {r["id"]: r for r in llm["rules"]}
    newly_formalized, reverted = [], []
    for rid, rule in llm_rules.items():
        base = det_rules.get(rid)
        if base is None:
            invariant_violations.append({"ruleId": rid, "reason": "rule not in deterministic leg"})
            continue
        if base["status"] != "formalized" and rule["status"] == "formalized":
            newly_formalized.append(rid)
        if base["status"] == "formalized" and rule["status"] != "formalized":
            reverted.append(rid)

    return {
        "cards": len(llm_cards),
        "claimsChanged": len(claims_changed),
        "claimsChangedIds": [c["cardId"] for c in claims_changed],
        "newlyFormalizedRules": newly_formalized,
        "revertedRules": reverted,
        "invariantViolations": invariant_violations,
        "deterministicCoverage": det["coverage"],
        "llmCoverage": llm["coverage"],
    }


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--use-case", default="wind", choices=sorted(TRACK_SHARDS))
    args = ap.parse_args(argv)

    shard = POC_ROOT / TRACK_SHARDS[args.use_case]
    det = _deterministic_leg(shard)

    try:
        analyst_hook = norm_llm.build_analyst_hook()
        formalizer_hook = norm_llm.build_formalizer_hook(_allowed_zone_ids())
    except norm_llm.NormLLMError as exc:
        raise SystemExit(f"cannot run the LLM leg: {exc}")

    llm = _llm_leg(shard, analyst_hook, formalizer_hook)
    comparison = _compare(det, llm)
    comparison["analystRejected"] = analyst_hook.rejected
    comparison["formalizerRejected"] = formalizer_hook.rejected
    comparison["stamps"] = {"analyst": analyst_hook.stamp, "formalizer": formalizer_hook.stamp}

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUT_ROOT / f"{ts}-{args.use_case}-normcmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=1, ensure_ascii=False),
                                             encoding="utf-8")

    print(f"[normcmp] use-case={args.use_case} -> {out_dir / 'comparison.json'}")
    print(f"  cards={comparison['cards']}  claimsChanged={comparison['claimsChanged']}  "
          f"newlyFormalized={len(comparison['newlyFormalizedRules'])}  "
          f"reverted={len(comparison['revertedRules'])}")
    print(f"  analyst: accepted={analyst_hook.accepted} rejected={len(analyst_hook.rejected)}  "
          f"formalizer: proposed={comparison['llmCoverage'].get('llm_proposed')} "
          f"rejected={comparison['llmCoverage'].get('llm_rejected')}")
    if comparison["invariantViolations"]:
        print(f"  INVARIANT VIOLATIONS: {comparison['invariantViolations'][:5]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
