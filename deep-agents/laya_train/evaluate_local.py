"""Evaluate the fine-tuned nLDT router against the zero-shot multilingual base.

Runs the held-out eval split (unseen scenario sets + controls) through both
checkpoints and reports per-question argmax accuracy, gold-probability, and
the confidence-gate pass rate that laya_router applies (min of primary_poc and
workflow confidence vs LAYA_MIN_CONFIDENCE, default 0.55).

Usage:
  python evaluate_local.py                       # base vs fine-tuned
  python evaluate_local.py --only finetuned      # skip the base run
  python evaluate_local.py --checkpoint <dir>    # custom checkpoint
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE / "data" / "scenarios-eval.jsonl"
DEFAULT_CKPT = HERE / "checkpoints" / "nldt-router"
ROUTING_QUESTIONS = ("primary_poc", "workflow")
GATE_THRESHOLD = 0.55


def _confidence(block: dict) -> float | None:
    if not isinstance(block, dict):
        return None
    for key in ("confidence", "prob", "probability"):
        if block.get(key) is not None:
            try:
                return float(block[key])
            except (TypeError, ValueError):
                pass
    return None


def _argmax_label(block: dict) -> str | None:
    if not isinstance(block, dict):
        return None
    if block.get("type") == "noul" or "noul" in block:
        val = block.get("noul")
        try:
            return "true" if float(val) >= 0.5 else "false"
        except (TypeError, ValueError):
            pass
    for key in ("choice", "label", "value"):
        if block.get(key) is not None:
            return str(block[key])
    probs = block.get("probabilities")
    if isinstance(probs, dict) and probs:
        return max(probs, key=probs.get)
    return None


def gold_answer(qid: str, gold_q: dict) -> str:
    probs = gold_q["probabilities"]
    if qid.startswith("needs_"):
        return "true" if probs.get("true", 0.0) >= 0.5 else "false"
    return max(probs, key=probs.get)


def evaluate(agent, rows: list[dict]) -> dict:
    per_q_acc: Counter = Counter()
    per_q_n: Counter = Counter()
    per_q_goldprob: dict[str, list[float]] = {}
    gate_pass = gate_total = 0
    wf_conf: list[float] = []
    for row in rows:
        state, gold = row["state"], row["gold"]
        result = agent.predict(state, row["questions"])
        answers = result.get("answers") or result
        confs = {}
        for qid in gold:
            block = answers.get(qid)
            pred = _argmax_label(block)
            truth = gold_answer(qid, gold[qid])
            per_q_n[qid] += 1
            per_q_acc[qid] += int(pred == truth)
            conf = _confidence(block)
            if conf is not None:
                per_q_goldprob.setdefault(qid, []).append(conf if pred == truth else 0.0)
            if qid in ROUTING_QUESTIONS and conf is not None:
                confs[qid] = conf
                if qid == "workflow":
                    wf_conf.append(conf)
        if confs:
            gate_total += 1
            gate_pass += int(min(confs.values()) >= GATE_THRESHOLD)
    n = len(rows)
    return {
        "cases": n,
        "gate_pass_rate": gate_pass / max(1, gate_total),
        "workflow_conf_mean": sum(wf_conf) / max(1, len(wf_conf)),
        "questions": {
            qid: {
                "accuracy": per_q_acc[qid] / per_q_n[qid],
                "gold_prob_mean": (sum(v) / len(v)) if (v := per_q_goldprob.get(qid)) else None,
            }
            for qid in sorted(per_q_n)
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("base", "finetuned"))
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CKPT)
    args = parser.parse_args()

    import laya

    rows = [json.loads(l) for l in EVAL.read_text(encoding="utf-8").splitlines() if l]
    report: dict = {"cases": len(rows), "gate_threshold": GATE_THRESHOLD}

    if args.only in (None, "base"):
        base = laya.Agent("convaiinnovations/laya", subfolder="multilingual", device="cpu")
        report["zero_shot_multilingual"] = evaluate(base, rows)
        del base
    if args.only in (None, "finetuned"):
        ft = laya.Agent(str(args.checkpoint), device="cpu")
        report["finetuned"] = evaluate(ft, rows)

    out = HERE / "eval-report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def row(label: str, r: dict) -> str:
        qs = "  ".join(f"{q}: {m['accuracy']:.2f}" for q, m in r["questions"].items())
        return (f"{label:22s} gate≥{GATE_THRESHOLD}: {r['gate_pass_rate']:.2f}  "
                f"wf-conf: {r['workflow_conf_mean']:.2f}  | {qs}")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    for label in ("zero_shot_multilingual", "finetuned"):
        if label in report:
            print(row(label, report[label]))


if __name__ == "__main__":
    main()
