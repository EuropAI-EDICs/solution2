#!/usr/bin/env python3
"""Build the Laya System-1 training set for the Utrecht zone chain (PoC-1).

One case per unique NormCard across the PoC-1 runs (canonical wind/zon/bos
first, then the 12 track runs; duplicate claims from the two superseded wind
runs are dropped). State = the card's claim + verbatim quote; gold comes from
the run artifacts themselves — nothing invented:

  regelstatus    choice  formalized / ambiguous (-> V4) / rejected      formalrules.json
  zone_effect    choice  included/excluded/conditional/attention/       decision-table.json
                         compensation/ambiguous/not_applicable
  needs_human    noul    ambiguous -> true (jurist, V4)                 "
  legal_force    score   niet-bindend < interpreterend < bindend        normcards.legalForce

Split holds out ENTIRE runs (water · mobiliteit · werken · recreatie ·
biomassa) so evaluation measures generalisation to unseen tracks, not
memorised cards.

Usage:  python3 build_dataset.py    # -> data/{train,eval,meta}.jsonl
Deterministic (pure sorting).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = ROOT / "poc" / "runs"

#: canonical tracks first (their card ids are what the simulation page shows),
#: then every other track run by name; the two superseded wind runs are skipped
CANONICAL = ["20260830T113234Z-wind", "20260830T142439Z-zon", "20260830T142446Z-bos"]
SKIP = {"20260830T111940Z-wind", "20260830T112317Z-wind"}   # exact claim duplicates
EVAL_RUNS = {"20261004T185116Z-water", "20261005T072839Z-mobiliteit",
             "20261006T121921Z-werken", "20261006T114934Z-recreatie",
             "20261006T120133Z-biomassa"}

FORCE_LEVELS = ["niet-bindend — informatief", "interpreterend — uitleggevend",
                "bindend — verorderend"]
FORCE_IDX = {"non_binding": 0, "interpretive": 1, "binding": 2}

questions = {
    "regelstatus": {
        "type": "choice",
        "instructions": "Is `claim` — a norm from the Omgevingsverordening provincie Utrecht — directly executable as a formal zone rule, or does it need the jurist?",
        "criteria": {
            "formalized": "closed norm — directly executable as a zone rule",
            "ambiguous": "open norm — interpretation needed, routed to the V4 jurist",
            "rejected": "non-binding or out of scope — no rule",
        },
    },
    "zone_effect": {
        "type": "choice",
        "instructions": "What is the zone effect of `claim` on the opportunity map?",
        "criteria": {
            "included": "adds area to the zone (inclusion)",
            "excluded": "carves area out (hard exclusion)",
            "conditional": "conditional obligation attached — area unchanged",
            "attention": "attention marker only — area unchanged",
            "compensation": "compensation marker only — area unchanged",
            "ambiguous": "ambiguous — no zone effect until the jurist decides",
            "not_applicable": "not applicable — no zone effect",
        },
    },
    "needs_human": {
        "type": "noul",
        "instructions": "Does `claim` require human jurist review (V4) before it may steer the zone?",
    },
    "legal_force": {
        "type": "score",
        "instructions": "How strong is the legal force of `claim`?",
        "criteria": FORCE_LEVELS,
    },
}


def run_rows(run: Path):
    """(cards, rules_by_card, dt_by_rule) or None when artifacts are missing."""
    try:
        cards = json.loads((run / "normcards.json").read_text(encoding="utf-8"))
        rules = json.loads((run / "formalrules.json").read_text(encoding="utf-8"))
        dt = json.loads((run / "decision-table.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    dt_rows = dt if isinstance(dt, list) else dt.get("rows", dt)
    return cards, {r.get("normCardId"): r for r in rules}, {r["ruleId"]: r for r in dt_rows}


def main() -> int:
    run_names = CANONICAL + sorted(
        d.name for d in RUNS.iterdir()
        if d.is_dir() and d.name not in CANONICAL and d.name not in SKIP
    )

    cases, seen = [], set()
    for name in run_names:
        got = run_rows(RUNS / name)
        if not got:
            continue
        cards, rules_by_card, dt_by_rule = got
        for c in cards:
            fr = rules_by_card.get(c["id"])
            if fr is None:
                continue
            key = " ".join(c["claim"].split())
            if key in seen:            # superseded run duplicate of the same claim
                continue
            seen.add(key)
            status = fr["status"]
            if status == "ambiguous":
                effect = "ambiguous"
            else:
                effect = (dt_by_rule.get(fr["id"]) or {}).get("zone effect", "not_applicable")
            force = FORCE_IDX.get(c.get("legalForce", "binding"), 2)
            jurist = status == "ambiguous"
            cases.append({
                "state": {"track": name.split("-", 1)[1], "claim": c["claim"],
                          "quote": c["source"]["quote"]},
                "questions": questions,
                "gold": {
                    "regelstatus": {"probabilities": {status: 1.0}},
                    "zone_effect": {"probabilities": {effect: 1.0}},
                    "needs_human": {"probabilities": {"true": float(jurist), "false": float(not jurist)}},
                    "legal_force": {"probabilities": {str(force): 1.0}},
                },
                "_meta": {"run": name, "cardId": c["id"], "claimKey": key[:80],
                          "status": status, "effect": effect, "force": force,
                          "article": c["source"]["article"], "jurist": jurist},
            })

    train = [c for c in cases if c["_meta"]["run"] not in EVAL_RUNS]
    evalr = [c for c in cases if c["_meta"]["run"] in EVAL_RUNS]
    strip = lambda rs: [{k: v for k, v in r.items() if k != "_meta"} for r in rs]

    data = HERE / "data"
    data.mkdir(exist_ok=True)
    (data / "train.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in strip(train)), encoding="utf-8")
    (data / "eval.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in strip(evalr)), encoding="utf-8")
    (data / "meta.jsonl").write_text(
        "".join(json.dumps(r["_meta"], ensure_ascii=False) + "\n" for r in cases), encoding="utf-8")

    from collections import Counter
    st = Counter(c["_meta"]["status"] for c in cases)
    ef = Counter(c["_meta"]["effect"] for c in cases)
    tracks = Counter(c["_meta"]["run"] for c in cases)
    print(f"cases: {len(cases)} uniek (train {len(train)} · eval {len(evalr)} — "
          f"held-out runs: water, mobiliteit, werken, recreatie, biomassa)")
    print(f"regelstatus: {dict(st)}")
    print(f"zone_effect: {dict(ef)}")
    print(f"legal_force: {dict(Counter(c['_meta']['force'] for c in cases))}")
    print("runs:", dict(tracks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
