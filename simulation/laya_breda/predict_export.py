#!/usr/bin/env python3
"""Export Laya predictions for all 56 Breda buurten -> predictions.json.

Usage (deep-agents/laya_train/.venv):  python predict_export.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / "poc-breda" / "runs" / "20260913T192628Z-breda-scan"
CKPT = HERE / "checkpoints" / "breda-laya"
OUT = HERE / "predictions.json"

BAND_NAMES = ["laag", "midden", "hoog"]
GATE = 0.55
VALUES = ("democratic", "spatial", "economic", "social")
EVAL_WIJKEN = {"WK075804", "WK075808", "WK075809", "WK075807", "WK075810"}


def confidence(block: dict) -> float | None:
    for key in ("answer_confidence", "confidence", "prob", "probability"):
        v = block.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _scores(b: dict) -> dict[str, float]:
    raw = b.get("scores") or {}
    return {k: float((raw.get(k) or {}).get("score") or 0.0) for k in VALUES}


def _primary(scores: dict[str, float]) -> str:
    return min(VALUES, key=lambda k: scores[k])


def main() -> int:
    import laya

    rows = [json.loads(l) for l in (HERE / "data" / "train.jsonl").read_text().splitlines() if l]
    questions = rows[0]["questions"]
    meta_rows = [json.loads(l) for l in (HERE / "data" / "meta.jsonl").read_text().splitlines() if l]
    meta_by = {m["buurtcode"]: m for m in meta_rows}
    summary = {}
    sfile = HERE / "finetune-summary.json"
    if sfile.exists():
        summary = json.loads(sfile.read_text())

    vs = json.loads((RUN / "value-scan.json").read_text(encoding="utf-8"))
    cases = []
    for b in vs["buurten"]:
        sc = _scores(b)
        m = meta_by[b["buurtcode"]]
        cases.append({
            "key": b["buurtcode"],
            "state": {
                "buurtcode": b["buurtcode"],
                "buurtnaam": b["buurtnaam"],
                "wijkcode": b.get("wijkcode") or "",
                "aantalInwoners": b.get("aantalInwoners") or 0,
                "scores": sc,
                "missing": b.get("missing") or [],
            },
            "meta": m,
            "card": [
                b.get("wijkcode") or "",
                b["buurtcode"],
                b["buurtnaam"],
                f"scores d={sc['democratic']:.1f} s={sc['spatial']:.1f} "
                f"e={sc['economic']:.1f} so={sc['social']:.1f}",
                "missing: " + (", ".join(b.get("missing") or []) or "geen"),
            ],
        })

    agent = laya.Agent(str(CKPT), device="cpu")
    preds, gold, cards = {}, {}, {}
    lat = []
    for c in cases:
        t0 = time.perf_counter()
        res = agent.predict(c["state"], questions)
        lat.append((time.perf_counter() - t0) * 1000)
        a = res["answers"]
        pv, ab, ju, ao = (
            a["primary_value"],
            a["attention_band"],
            a["needs_human"],
            a["autonomous_ok"],
        )
        try:
            band_sc = float(ab.get("score", ab.get("value", 0)))
        except (TypeError, ValueError):
            band_sc = 0.0
        band_sc = min(2.0, max(0.0, band_sc))
        try:
            pj = float(ju.get("noul", ju.get("probabilities", {}).get("true", 0.0)))
        except (TypeError, ValueError):
            pj = 0.0
        preds[c["key"]] = {
            "v": pv.get("choice"),
            "vp": {k: round(v, 4) for k, v in (pv.get("probabilities") or {}).items()},
            "vc": round(confidence(pv) or 0, 4),
            "b": round(band_sc, 3),
            "bl": BAND_NAMES[int(round(band_sc))],
            "j": round(pj, 4),
            "a": ao.get("choice"),
            "ap": {k: round(v, 4) for k, v in (ao.get("probabilities") or {}).items()},
            "ac": round(confidence(ao) or 0, 4),
        }
        m = c["meta"]
        gold[c["key"]] = {
            "v": m["primary"],
            "b": m["band"],
            "j": m["needs_human"],
            "a": m["autonomous_ok"],
            "wijk": m["wijkcode"],
        }
        cards[c["key"]] = c["card"]

    eval_keys = {c["key"] for c in cases if c["meta"]["wijkcode"] in EVAL_WIJKEN}
    acc = {
        "primary_value": [0, 0],
        "attention_band": [0, 0],
        "needs_human": [0, 0],
        "autonomous_ok": [0, 0],
    }
    conf_sum, abst = 0.0, 0
    for k in eval_keys:
        p, g = preds[k], gold[k]
        acc["primary_value"][0] += int(p["v"] == g["v"])
        acc["primary_value"][1] += 1
        acc["attention_band"][0] += int(p["bl"] == BAND_NAMES[g["b"]])
        acc["attention_band"][1] += 1
        acc["needs_human"][0] += int((p["j"] >= 0.5) == g["j"])
        acc["needs_human"][1] += 1
        acc["autonomous_ok"][0] += int(p["a"] == g["a"])
        acc["autonomous_ok"][1] += 1
        conf_sum += p["vc"]
        if p["vc"] < GATE:
            abst += 1
    n_eval = acc["primary_value"][1] or 1

    out = {
        "model": {
            "checkpoint": "simulation/laya_breda/checkpoints/breda-laya",
            "base": "convaiinnovations/laya — multilingual (mmBERT-base, 322M)",
            "framework": "laya · PyTorch · fine-tuned RLCD + kalibratie",
            "seed": 20261025,
            "items": {
                "train": summary.get("train_items"),
                "calib": summary.get("calibration_items"),
                "eval": summary.get("eval_items"),
            },
            "epochs": (summary.get("training") or {}).get("epochs"),
            "latencyMs": round(sum(lat) / max(len(lat), 1), 1),
            "nPred": len(cases),
            "gate": GATE,
        },
        "questions": {
            "primary_value": {"type": "choice", "options": list(VALUES)},
            "attention_band": {"type": "score", "options": BAND_NAMES},
            "needs_human": {"type": "noul"},
            "autonomous_ok": {"type": "choice", "options": ["ok", "review"]},
        },
        "eval": {
            "n": n_eval,
            "primary_value": {
                "hit": acc["primary_value"][0],
                "n": acc["primary_value"][1],
            },
            "attention_band": {
                "hit": acc["attention_band"][0],
                "n": acc["attention_band"][1],
            },
            "needs_human": {
                "hit": acc["needs_human"][0],
                "n": acc["needs_human"][1],
            },
            "autonomous_ok": {
                "hit": acc["autonomous_ok"][0],
                "n": acc["autonomous_ok"][1],
            },
            "abstentions": abst,
            "meanConf": round(conf_sum / n_eval, 4),
            "heldOutWijken": sorted(EVAL_WIJKEN),
        },
        "preds": preds,
        "gold": gold,
        "cards": cards,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(preds)} preds, eval n={n_eval})")
    try:
        from lake_publish import main as lake_publish_main

        lake_publish_main(["--all"])
    except Exception as exc:  # pragma: no cover
        print(f"warn: lake publish skipped ({type(exc).__name__}: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
