#!/usr/bin/env python3
"""Export real Laya predictions for all 84 unique Utrecht NormCards -> predictions.json.

Loads the fine-tuned checkpoint (checkpoints/utrecht-laya), runs every unique
card (same dedupe as build_dataset.py) through the model, computes per-head
accuracy on the held-out runs (water · mobiliteit · werken · recreatie ·
biomassa — 18 cards the model never saw), and writes the JSON that
build_simulation.py embeds into the simulation page.

Usage (in deep-agents/laya_train/.venv):  python predict_export.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = ROOT / "poc" / "runs"
CKPT = HERE / "checkpoints" / "utrecht-laya"
OUT = HERE / "predictions.json"

FORCE_NAMES = ["niet-bindend", "interpreterend", "bindend"]
JURIST_GATE = 0.55

#: canonical tracks first — their cards are what the simulation page shows
CANONICAL = ["20260830T113234Z-wind", "20260830T142439Z-zon", "20260830T142446Z-bos"]
SKIP = {"20260830T111940Z-wind", "20260830T112317Z-wind"}
EVAL_RUNS = {"20261004T185116Z-water", "20261005T072839Z-mobiliteit",
             "20261006T121921Z-werken", "20261006T114934Z-recreatie",
             "20261006T120133Z-biomassa"}


def confidence(block: dict) -> float | None:
    for key in ("answer_confidence", "confidence", "prob", "probability"):
        v = block.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def main() -> int:
    import laya

    rows = [json.loads(l) for l in (HERE / "data" / "train.jsonl").read_text().splitlines() if l]
    eval_rows = [json.loads(l) for l in (HERE / "data" / "eval.jsonl").read_text().splitlines() if l]
    questions = rows[0]["questions"]
    meta_rows = [json.loads(l) for l in (HERE / "data" / "meta.jsonl").read_text().splitlines() if l]
    summary = {}
    sfile = HERE / "finetune-summary.json"
    if sfile.exists():
        summary = json.loads(sfile.read_text())

    # rebuild the unique-case list exactly like build_dataset.py
    run_names = CANONICAL + sorted(
        d.name for d in RUNS.iterdir()
        if d.is_dir() and d.name not in CANONICAL and d.name not in SKIP
    )
    cases, seen = [], set()
    for name in run_names:
        try:
            cards = json.loads((RUNS / name / "normcards.json").read_text(encoding="utf-8"))
            rules = json.loads((RUNS / name / "formalrules.json").read_text(encoding="utf-8"))
            dt = json.loads((RUNS / name / "decision-table.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        dt_rows = dt if isinstance(dt, list) else dt.get("rows", dt)
        rules_by_card = {r.get("normCardId"): r for r in rules}
        dt_by_rule = {r["ruleId"]: r for r in dt_rows}
        for c in cards:
            fr = rules_by_card.get(c["id"])
            if fr is None:
                continue
            key = " ".join(c["claim"].split())
            if key in seen:
                continue
            seen.add(key)
            track = name.split("-", 1)[1]
            status = fr["status"]
            effect = "ambiguous" if status == "ambiguous" else \
                dt_by_rule.get(fr["id"], {}).get("zone effect", "not_applicable")
            cases.append({
                "key": f"{c['id']}@{track}", "run": name, "track": track,
                "card": c, "status": status, "effect": effect,
                "force": {"non_binding": 0, "interpretive": 1, "binding": 2}.get(c.get("legalForce"), 2),
                "jurist": status == "ambiguous",
            })

    agent = laya.Agent(str(CKPT), device="cpu")
    preds, gold, cards = {}, {}, {}
    lat = []
    for c in cases:
        state = {"track": c["track"], "claim": c["card"]["claim"], "quote": c["card"]["source"]["quote"]}
        t0 = time.perf_counter()
        res = agent.predict(state, questions)
        lat.append((time.perf_counter() - t0) * 1000)
        a = res["answers"]
        rs, ze, ju, lf = a["regelstatus"], a["zone_effect"], a["needs_human"], a["legal_force"]
        try:
            fsc = float(lf.get("score", lf.get("value", 0)))
        except (TypeError, ValueError):
            fsc = 0.0
        fsc = min(2.0, max(0.0, fsc))
        try:
            pj = float(ju.get("noul", ju.get("probabilities", {}).get("true", 0.0)))
        except (TypeError, ValueError):
            pj = 0.0
        preds[c["key"]] = {
            "s": rs.get("choice"), "sp": {k: round(v, 4) for k, v in (rs.get("probabilities") or {}).items()},
            "sc": round(confidence(rs) or 0, 4),
            "e": ze.get("choice"), "ep": {k: round(v, 4) for k, v in (ze.get("probabilities") or {}).items()},
            "ec": round(confidence(ze) or 0, 4),
            "f": round(fsc, 3), "fl": FORCE_NAMES[int(round(fsc))],
            "j": round(pj, 4),
        }
        gold[c["key"]] = {"s": c["status"], "e": c["effect"], "f": c["force"],
                          "j": c["jurist"], "art": c["card"]["source"]["article"]}
        src = c["card"]["source"]
        cards[c["key"]] = [c["track"], c["card"]["id"], src["article"],
                           " ".join(c["card"]["claim"].split())[:150],
                           " ".join(src["quote"].split())[:150], src.get("uri", "")]

    eval_keys = {c["key"] for c in cases if c["run"] in EVAL_RUNS}
    acc = {"regelstatus": [0, 0], "zone_effect": [0, 0], "needs_human": [0, 0], "legal_force": [0, 0]}
    conf_sum, abst = 0.0, 0
    for k in eval_keys:
        p, g = preds[k], gold[k]
        acc["regelstatus"][0] += int(p["s"] == g["s"]); acc["regelstatus"][1] += 1
        acc["zone_effect"][0] += int(p["e"] == g["e"]); acc["zone_effect"][1] += 1
        acc["needs_human"][0] += int((p["j"] >= 0.5) == g["j"]); acc["needs_human"][1] += 1
        acc["legal_force"][0] += int(p["fl"] == FORCE_NAMES[g["f"]]); acc["legal_force"][1] += 1
        conf_sum += p["sc"]
        if p["sc"] < JURIST_GATE:
            abst += 1
    n_eval = acc["regelstatus"][1]

    out = {
        "model": {
            "checkpoint": "simulation/laya_utrecht/checkpoints/utrecht-laya",
            "base": "convaiinnovations/laya — multilingual (mmBERT-base, 322M)",
            "framework": "laya 0.4.11 · PyTorch · fine-tuned RLCD + temperatuurkalibratie (MPS)",
            "seed": 20261025,
            "items": {"train": summary.get("train_items"), "calib": summary.get("calibration_items"),
                      "eval": summary.get("eval_items")},
            "epochs": (summary.get("training") or {}).get("epochs"),
            "latencyMs": round(sum(lat) / len(lat), 1),
            "nPred": len(cases), "gate": JURIST_GATE,
        },
        "questions": {
            "regelstatus": {"instructions": questions["regelstatus"]["instructions"],
                            "options": questions["regelstatus"]["criteria"]},
            "zone_effect": {"instructions": questions["zone_effect"]["instructions"],
                            "options": questions["zone_effect"]["criteria"]},
            "needs_jurist": {"instructions": questions["needs_human"]["instructions"]},
            "legal_force": {"instructions": questions["legal_force"]["instructions"],
                            "levels": questions["legal_force"]["criteria"]},
        },
        "eval": {
            "n": n_eval,
            "regelstatus": {"hit": acc["regelstatus"][0], "n": acc["regelstatus"][1]},
            "zone_effect": {"hit": acc["zone_effect"][0], "n": acc["zone_effect"][1]},
            "needs_human": {"hit": acc["needs_human"][0], "n": acc["needs_human"][1]},
            "legal_force": {"hit": acc["legal_force"][0], "n": acc["legal_force"][1]},
            "meanConfidence": round(conf_sum / max(1, n_eval), 3),
            "abstentions": abst,
            "heldOutRuns": sorted(EVAL_RUNS),
        },
        "preds": preds,
        "gold": gold,
        "cards": cards,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB) — {len(cases)} predictions, "
          f"mean latency {out['model']['latencyMs']} ms")
    for k, v in acc.items():
        print(f"  held-out {k}: {v[0]}/{v[1]} ({100 * v[0] / max(1, v[1]):.0f}%)")
    print(f"  mean status-confidence {out['eval']['meanConfidence']} · onder gate: {abst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
