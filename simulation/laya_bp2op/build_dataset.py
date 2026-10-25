#!/usr/bin/env python3
"""Build the Laya System-1 training set for the BP->OP chain (PoC-2, Eindhoven).

One case per bronregel from the canonical run
(poc-bp2op/runs/20260830-124515-eindhoven). State = the bronregel's verbatim
tekst; gold comes from the run's own omzettabel/kennisbank artifacts — the
distilled judgment of the real matcher, nothing invented:

  doel_hoofdstuk  choice  which hoofdstuk of the new omgevingsplan the regel
                          maps to (or geen_match -> nieuwe regel)
  match_band      score   ordinal rubric: geen < zwak < mogelijk < sterk
  needs_jurist    noul    does this regel need the jurist (V4) before any
                          coupling becomes official?

Split is by bron-artikel (every 5th artikel held out) so evaluation measures
generalisation to unseen artikelen, not memorised parapgraphs.

Usage:  python3 build_dataset.py          # writes data/train.jsonl, data/eval.jsonl
Deterministic (no seed needed — pure sorting).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / "poc-bp2op" / "runs" / "20260830-124515-eindhoven"

BAND_LEVELS = [
    "geen — geen passende doelregel, nieuwe regel voorstellen",
    "zwak — slechts deels vergelijkbaar, jurist nodig",
    "mogelijk — redelijk vergelijkbaar",
    "sterk — goed vergelijkbaar, direct voorstelbaar",
]
BAND_IDX = {"geen": 0, "zwak": 1, "mogelijk": 2, "sterk": 3}


def hoofdstukken(doel: list) -> dict:
    """hoofdstukNr -> short label from the doelregels themselves."""
    out = {}
    for d in doel:
        loc = d["locator"]
        out.setdefault(loc["hoofdstukNr"], loc["hoofdstukTitel"])
    return out


def main() -> int:
    bron = json.loads((RUN / "bronregels.json").read_text(encoding="utf-8"))
    doel = json.loads((RUN / "doelregels.json").read_text(encoding="utf-8"))
    tabel = json.loads((RUN / "omzettabel.json").read_text(encoding="utf-8"))
    doel_map = {d["id"]: d for d in doel}

    hfds = hoofdstukken(doel)
    # only hoofdstukken that actually occur as a top-1 target keep their own
    # option; the rest would be near-impossible distractors for 311 rows
    tabel_by_bron = {r["bronRegelId"]: r for r in tabel}
    used_h: Counter = Counter()
    for b in bron:
        r = tabel_by_bron[b["id"]]
        top = r["suggesties"][0] if r["suggesties"] else None
        if top and top.get("doelRegelId") in doel_map:
            used_h[doel_map[top["doelRegelId"]]["locator"]["hoofdstukNr"]] += 1
        else:
            used_h["geen"] += 1
    options = {}
    for h in sorted(k for k in used_h if k != "geen"):
        options[f"hfd{h}"] = f"hoofdstuk {h} — {hfds[h].lower()}"
    options["geen_match"] = "geen passend hoofdstuk — nieuwe regel of bronregel laten"

    questions = {
        "doel_hoofdstuk": {
            "type": "choice",
            "instructions": "In which chapter of the new omgevingsplan (doelregeling) does `tekst` belong after conversion from old-law bronregel?",
            "criteria": options,
        },
        "match_band": {
            "type": "score",
            "instructions": "How confidently does `tekst` map onto an existing doelregel in that chapter?",
            "criteria": BAND_LEVELS,
        },
        "needs_jurist": {
            "type": "noul",
            "instructions": "Does `tekst` need jurist review (V4) before any coupling may become official?",
        },
    }

    rows, n_jurist = [], 0
    for b in bron:
        r = tabel_by_bron[b["id"]]
        top = r["suggesties"][0] if r["suggesties"] else None
        if top and top.get("doelRegelId") in doel_map:
            h = doel_map[top["doelRegelId"]]["locator"]["hoofdstukNr"]
            hgold = f"hfd{h}"
            band = top["band"]
        else:
            hgold = "geen_match"
            band = "geen"
        jurist = r["status"] in ("needs_human", "nieuwe_regel_voorgesteld")
        n_jurist += int(jurist)
        rows.append({
            "state": {
                "artikel": b["locator"]["label"],
                "tekst": b["tekst"],
            },
            "questions": questions,
            "gold": {
                "doel_hoofdstuk": {"probabilities": {hgold: 1.0}},
                "match_band": {"probabilities": {str(BAND_IDX[band]): 1.0}},
                "needs_jurist": {"probabilities": {"true": float(jurist), "false": float(not jurist)}},
            },
            "_meta": {"bronRegelId": b["id"], "band": band, "status": r["status"],
                      "hoofdstuk": hgold, "jurist": jurist},
        })

    # hold out every 5th bron-artikel (grouped so no artikel leaks across splits)
    artikelen = sorted({r["state"]["artikel"] for r in rows})
    eval_arts = {a for i, a in enumerate(artikelen) if i % 5 == 0}
    train = [r for r in rows if r["state"]["artikel"] not in eval_arts]
    evalr = [r for r in rows if r["state"]["artikel"] in eval_arts]

    data = HERE / "data"
    data.mkdir(exist_ok=True)
    strip = lambda rs: [{k: v for k, v in r.items() if k != "_meta"} for r in rs]
    (data / "train.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in strip(train)), encoding="utf-8")
    (data / "eval.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in strip(evalr)), encoding="utf-8")
    (data / "meta.jsonl").write_text(
        "".join(json.dumps({"split": "train" if r in train else "eval", **r["_meta"]},
                           ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    print(f"cases: {len(rows)} bronregels  (train {len(train)} · eval {len(evalr)} — "
          f"{len(eval_arts)}/{len(artikelen)} artikelen held out)")
    print(f"doel_hoofdstuk options ({len(options)}): " + ", ".join(
        f"{o}={used_h.get(0 if o == 'geen_match' else int(o[3:]), 0) if o != 'geen_match' else used_h['geen']}"
        for o in options))
    print(f"match_band levels: " + ", ".join(
        f"{k}={sum(1 for r in rows if r['_meta']['band'] == k)}" for k in BAND_IDX))
    print(f"needs_jurist: true={n_jurist} / false={len(rows) - n_jurist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
