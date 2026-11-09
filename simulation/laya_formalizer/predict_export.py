#!/usr/bin/env python3
"""Export Laya-formalisatie-hints per instrument + eval op ongezien materiaal.

Usage (deep-agents/laya_train/.venv):
  python predict_export.py             # productie-checkpoint → hints-artefacten + holdout-eval
  python predict_export.py --cross-eval  # claim-meting: cross-checkpoint vs héél Utrecht
  python predict_export.py --bijscholing N  # ronde 3: N utrechtse train-artikelen erbij, eval op de rest
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FULL_EXPORT_OUT = ROOT / "nldt" / "simulation" / "regelrecht" / "full_export" / "out"
GATE = 0.55
CKPT = HERE / "checkpoints" / "formalizer-laya"
CKPT_CROSS = HERE / "checkpoints" / "formalizer-laya-cross"

_spec = importlib.util.spec_from_file_location("lf_build_dataset", HERE / "build_dataset.py")
bd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bd)


def confidence(block: dict) -> float | None:
    for key in ("answer_confidence", "confidence", "prob", "probability"):
        v = block.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _dir_sha(pad: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in pad.rglob("*") if p.is_file()):
        h.update(f.name.encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


def _eval_agent(agent, eval_rows: list[dict], *, artikelen_uit: list | None = None) -> dict:
    hit = {"voorspelde_status": [0, 0], "heeft_evidence": [0, 0]}
    abst, confs = 0, []
    verwarring: dict[str, dict[str, int]] = {}
    for r in eval_rows:
        res = agent.predict(r["state"], r["questions"])
        a = res["answers"]
        keuze = a["voorspelde_status"].get("choice") or "(geen)"
        conf = confidence(a["voorspelde_status"]) or 0.0
        p = r["gold"]["voorspelde_status"]["probabilities"]
        gold = max(p, key=p.get)
        verwarring.setdefault(gold, {}).setdefault(keuze, 0)
        verwarring[gold][keuze] += 1
        if artikelen_uit is not None:
            artikelen_uit.append({
                "number": r["state"]["artikel"],
                "voorspeldeStatus": keuze,
                "goud": gold,
                "confidence": round(conf, 4),
                "door": conf >= GATE,
            })
        hit["voorspelde_status"][0] += int(keuze == gold)
        hit["voorspelde_status"][1] += 1
        ev = float(a["heeft_evidence"].get("noul", 0.0))
        gold_ev = r["gold"]["heeft_evidence"]["probabilities"]["true"] >= 0.5
        hit["heeft_evidence"][0] += int((ev >= 0.5) == gold_ev)
        hit["heeft_evidence"][1] += 1
        confs.append(conf)
        abst += int(conf < GATE)
    n = hit["voorspelde_status"][1] or 1
    return {
        "voorspelde_status": {"hit": hit["voorspelde_status"][0], "n": hit["voorspelde_status"][1]},
        "heeft_evidence": {"hit": hit["heeft_evidence"][0], "n": hit["heeft_evidence"][1]},
        "verwarring": verwarring,
        "abstentions": abst,
        "gatePasRate": round(1 - abst / n, 4),
        "meanConf": round(sum(confs) / n, 4),
    }


def _hints_voor(agent, instrument: str, data_sha: str, ckpt_pad: Path) -> dict:
    rows = bd.build_rows(instrument)
    vragen = rows[0]["questions"]
    artikelen, lat = [], []
    for r in rows:
        t0 = time.perf_counter()
        res = agent.predict(r["state"], vragen)
        lat.append((time.perf_counter() - t0) * 1000)
        a = res["answers"]
        conf = confidence(a["voorspelde_status"]) or 0.0
        artikelen.append({
            "number": r["state"]["artikel"],
            "voorspeldeStatus": a["voorspelde_status"].get("choice"),
            "confidence": round(conf, 4),
            "door": conf >= GATE,
            "heeftEvidence": round(float(a["heeft_evidence"].get("noul", 0.0)), 4),
        })
    return {
        "contract": "laya-hints/v1",
        "instrument": instrument,
        "gegenereerdOp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "model": {
            "checkpoint": str(ckpt_pad), "checkpointSha256": _dir_sha(ckpt_pad),
            "datasetSha256": data_sha, "gate": GATE,
            "latencyMs": round(sum(lat) / max(len(lat), 1), 1),
        },
        "artikelen": artikelen,
    }


def main() -> int:
    import laya

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cross-eval", action="store_true",
                   help="claim-meting: cross-checkpoint (getraind op Eindhoven) vs héél Utrecht")
    p.add_argument("--bijscholing", type=int, metavar="N", default=None,
                   help="ronde 3: checkpoint getraind met N utrechtse artikelen erbij, "
                        "eval op de rest van Utrecht")
    p.add_argument("--derde", type=int, metavar="N", default=None,
                   help="derde-instrument-toets: productiebasis + N veenendaalse "
                        "artikelen (template-labels), eval op de rest van Veenendaal")
    args = p.parse_args()

    if args.derde is not None:
        n = args.derde
        data_dir = HERE / f"data-derde-{n}"
        ckpt = HERE / "checkpoints" / f"formalizer-laya-derde-{n}"
        eval_naam = f"eval-derde-{n}.json"
        modus = (f"derde: eindhoven + utrecht + {n} veenendaal (template-labels) "
                 f"→ eval resterende veenendaal")
    elif args.bijscholing is not None:
        n = args.bijscholing
        data_dir = HERE / f"data-bijscholing-{n}"
        ckpt = HERE / "checkpoints" / f"formalizer-laya-bijscholing-{n}"
        eval_naam = f"eval-bijscholing-{n}.json"
        modus = f"bijscholing: eindhoven + {n} utrecht → eval {427 - n} resterende utrecht"
    elif args.cross_eval:
        data_dir = HERE / "data-cross"
        ckpt = CKPT_CROSS
        eval_naam = "eval-cross.json"
        modus = "cross: train eindhoven → eval heel utrecht"
    else:
        data_dir = HERE / "data"
        ckpt = CKPT
        eval_naam = "eval-holdout.json"
        modus = "holdout: per instrument elk 5e artikel"
    data_sha = hashlib.sha256(
        (data_dir / "train.jsonl").read_bytes() + (data_dir / "eval.jsonl").read_bytes()
    ).hexdigest()
    agent = laya.Agent(str(ckpt), device="cpu")

    eval_rows = [json.loads(l) for l in (data_dir / "eval.jsonl").read_text("utf-8").splitlines() if l]
    artikelen_uit: list = [] if args.derde is not None else None
    evaluatie = _eval_agent(agent, eval_rows, artikelen_uit=artikelen_uit)
    uit = {
        "model": {"checkpoint": str(ckpt), "dataset": str(data_dir), "gate": GATE},
        "modus": modus,
        "eval": evaluatie,
    }
    if artikelen_uit is not None:
        # werklijst-substantie voor het derde instrument (géén laya-hints/v1-contractwijziging)
        uit["artikelen"] = artikelen_uit
    if not args.cross_eval and args.bijscholing is None and args.derde is None:
        uit["hints"] = {}
        for instrument in ("eindhoven", "utrecht"):
            hints = _hints_voor(agent, instrument, data_sha, ckpt)
            pad = FULL_EXPORT_OUT / f"{instrument}-laya-hints.json"
            pad.write_text(json.dumps(hints, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            uit["hints"][instrument] = len(hints["artikelen"])
            print(f"{instrument}: {len(hints['artikelen'])} hints → {pad}")
    (HERE / eval_naam).write_text(
        json.dumps(uit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evaluatie, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
