#!/usr/bin/env python3
"""Export real Laya predictions for all 311 bronregels -> predictions.json.

Loads the fine-tuned checkpoint (checkpoints/bp2op-laya), runs every bronregel
from the canonical BP->OP run through the model (same questions as training),
computes per-head accuracy on the held-out eval split (63 unseen artikelen),
and writes one JSON that build_simulation.py embeds into the simulation page.

Usage (in deep-agents/laya_train/.venv):
  python predict_export.py
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / "poc-bp2op" / "runs" / "20260830-124515-eindhoven"
CKPT = HERE / "checkpoints" / "bp2op-laya"
OUT = HERE / "predictions.json"

BAND_NAMES = ["geen", "zwak", "mogelijk", "sterk"]
JURIST_GATE = 0.55  # noul P(true) above this -> route to jurist (System 2)


def confidence(block: dict) -> float | None:
    for key in ("answer_confidence", "confidence", "prob", "probability"):
        v = block.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def main() -> int:
    import laya

    train_rows = [json.loads(l) for l in (HERE / "data" / "train.jsonl").read_text().splitlines() if l]
    eval_rows = [json.loads(l) for l in (HERE / "data" / "eval.jsonl").read_text().splitlines() if l]
    questions = train_rows[0]["questions"]
    meta = [json.loads(l) for l in (HERE / "data" / "meta.jsonl").read_text().splitlines() if l]
    eval_states = {id(r["state"]) for r in eval_rows}

    bron = json.loads((RUN / "bronregels.json").read_text(encoding="utf-8"))
    tabel = {r["bronRegelId"]: r for r in json.loads((RUN / "omzettabel.json").read_text(encoding="utf-8"))}
    meta_by_bron = {m["bronRegelId"]: m for m in meta}

    summary = {}
    sfile = HERE / "finetune-summary.json"
    if sfile.exists():
        summary = json.loads(sfile.read_text())

    agent = laya.Agent(str(CKPT), device="cpu")
    preds, gold = {}, {}
    lat: list[float] = []
    n = 0
    for b in bron:
        state = {"artikel": b["locator"]["label"], "tekst": b["tekst"]}
        t0 = time.perf_counter()
        res = agent.predict(state, questions)
        lat.append((time.perf_counter() - t0) * 1000)
        n += 1
        ans = res["answers"]
        h = ans["doel_hoofdstuk"]
        bd = ans["match_band"]
        ju = ans["needs_jurist"]
        probs = h.get("probabilities") or {}
        bid = b["id"]
        r = tabel[bid]
        top = r["suggesties"][0] if r["suggesties"] else None
        # score head: expected level + rounded level name
        try:
            sc = float(bd.get("score", bd.get("value", 0)))
        except (TypeError, ValueError):
            sc = 0.0
        lvl = BAND_NAMES[min(len(BAND_NAMES) - 1, max(0, round(sc)))]
        try:
            pj = float(ju.get("noul", ju.get("probabilities", {}).get("true", 0.0)))
        except (TypeError, ValueError):
            pj = 0.0
        preds[bid] = {
            "h": h.get("choice"), "p": {k: round(v, 4) for k, v in probs.items()},
            "hc": round(confidence(h) or 0, 4),
            "b": round(sc, 3), "bl": lvl,
            "j": round(pj, 4),
        }
        m = meta_by_bron[bid]
        gold[bid] = {
            "h": m["hoofdstuk"], "band": m["band"], "jurist": m["jurist"],
            "status": m["status"],
            "tabel": [top["doelRegelId"] if top else None,
                      top["band"] if top else "geen",
                      round(top["score"], 2) if top else None,
                      bool(top and top.get("kennisbankHitId"))],
        }

    # held-out accuracy per head (eval rows only)
    acc: dict = {"doel_hoofdstuk": [0, 0], "match_band": [0, 0], "needs_jurist": [0, 0]}
    conf_sum = 0.0
    abst = 0
    for row in eval_rows:
        # match state back to bronregel via (artikel, tekst)
        for b in bron:
            if b["tekst"] == row["state"]["tekst"]:
                bid = b["id"]
                break
        g = gold[bid]
        p = preds[bid]
        acc["doel_hoofdstuk"][0] += int(p["h"] == g["h"]); acc["doel_hoofdstuk"][1] += 1
        acc["match_band"][0] += int(p["bl"] == g["band"]); acc["match_band"][1] += 1
        acc["needs_jurist"][0] += int((p["j"] >= 0.5) == g["jurist"]); acc["needs_jurist"][1] += 1
        conf_sum += p["hc"]
        if p["hc"] < JURIST_GATE:
            abst += 1
    n_eval = acc["doel_hoofdstuk"][1]

    out = {
        "model": {
            "checkpoint": "simulation/laya_bp2op/checkpoints/bp2op-laya",
            "base": "convaiinnovations/laya — multilingual (mmBERT-base, 322M)",
            "framework": "laya 0.4.11 · PyTorch · fine-tuned RLCD + temperatuurkalibratie (MPS)",
            "seed": 20261024,
            "items": {"train": summary.get("train_items"), "calib": summary.get("calibration_items"),
                      "eval": summary.get("eval_items")},
            "epochs": (summary.get("training") or {}).get("epochs"),
            "latencyMs": round(sum(lat) / len(lat), 1),
            "nPred": n, "gate": JURIST_GATE,
        },
        "questions": {
            "doel_hoofdstuk": {"instructions": questions["doel_hoofdstuk"]["instructions"],
                               "options": questions["doel_hoofdstuk"]["criteria"]},
            "match_band": {"instructions": questions["match_band"]["instructions"],
                           "levels": questions["match_band"]["criteria"]},
            "needs_jurist": {"instructions": questions["needs_jurist"]["instructions"]},
        },
        "eval": {
            "n": n_eval,
            "doel_hoofdstuk": {"hit": acc["doel_hoofdstuk"][0], "n": acc["doel_hoofdstuk"][1]},
            "match_band": {"hit": acc["match_band"][0], "n": acc["match_band"][1]},
            "needs_jurist": {"hit": acc["needs_jurist"][0], "n": acc["needs_jurist"][1]},
            "meanConfidence": round(conf_sum / max(1, n_eval), 3),
            "abstentions": abst,
            "zeroShot": ((summary.get("train_report") or {}).get("before") or {}).get("accuracy"),
            "fineTuned": ((summary.get("train_report") or {}).get("after") or {}).get("accuracy"),
        },
        "preds": preds,
        "gold": gold,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB) — {n} predictions, "
          f"mean latency {out['model']['latencyMs']} ms")
    for k, v in acc.items():
        print(f"  held-out {k}: {v[0]}/{v[1]} ({100 * v[0] / max(1, v[1]):.0f}%)")
    print(f"  mean choice-confidence {out['eval']['meanConfidence']} · onder gate (<{JURIST_GATE}): {abst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
