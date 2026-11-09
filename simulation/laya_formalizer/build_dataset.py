#!/usr/bin/env python3
"""Build de Laya System-1 trainingset voor de formalisatie-triage (Inzet A).

Eén case per artikel van de twee PoC-instrumenten. State = de letterlijke
artikeltekst; gold komt uit het eigen formalization-report — nothing invented
(docs/PLAN_LAYA_INZET.md, principe 1):

  voorspelde_status  choice  formalized / ambiguous / rejected / unmatched
                          (alleen statussen die daadwerkelijk voorkomen)
  heeft_evidence     noul    source != "none" in het report

Splits:
  --mode holdout  per instrument elk 5e artikel held-out (geen artikel-leak)
  --mode cross    train = eindhoven, eval = héél utrecht — de
                  generalisatieclaim "werkt ook voor een nieuwe provincie/gemeente"
  --mode bijscholing --sample N   ronde 3: train = eindhoven + N utrechtse
                  artikelen (deterministische sha-steekproef), eval = de rest van
                  utrecht — de leercurve "hoeveel labels heeft een nieuw
                  instrument nodig?" als antwoord op de cross-bevinding
                  (44,8% < majority-baseline; zie eval-cross.json)

Usage:  nldt/.venv/bin/python build_dataset.py [--mode holdout|cross|bijscholing] [--sample N] [--out-dir data]
Deterministisch (pure sorting/sha-volgorde, geen seed, geen netwerk).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FULL_EXPORT_OUT = ROOT / "nldt" / "simulation" / "regelrecht" / "full_export" / "out"

INSTRUMENTEN = {
    "eindhoven": {
        "report": FULL_EXPORT_OUT / "eindhoven-formalization-report.json",
        "yaml": FULL_EXPORT_OUT / "eindhoven-cvdr696400.yaml",
    },
    "utrecht": {
        "report": FULL_EXPORT_OUT / "utrecht-formalization-report.json",
        "yaml": FULL_EXPORT_OUT / "utrecht-cvdr704250.yaml",
    },
}


def _artikel_tekst(yaml_pad: Path) -> dict[str, str]:
    import yaml  # nldt/.venv heeft pyyaml; trainings-venv ook (transformers-dep)

    doc = yaml.safe_load(yaml_pad.read_text(encoding="utf-8"))
    return {a["number"]: a["text"] for a in doc["articles"]}


def build_rows(instrument: str) -> list[dict]:
    report = json.loads(INSTRUMENTEN[instrument]["report"].read_text(encoding="utf-8"))
    teksten = _artikel_tekst(INSTRUMENTEN[instrument]["yaml"])
    statussen = sorted({r["status"] for r in report["articles"]})
    criteria = {
        "formalized": "direct executable als formele regel (limiet/verbod/equivalentie)",
        "ambiguous": "open norm of dubbelzinnig — jurist (V4) nodig",
        "rejected": "niet-bindend of buiten scope",
        "unmatched": "geen template/evidence-match (nog) — tekst-only of nieuwe template",
    }
    questions = {
        "voorspelde_status": {
            "type": "choice",
            "instructions": "Is `tekst` — an article of a Dutch local instrument (omgevingsplan/omgevingsverordening) — directly executable as a formal rule, or does it need the jurist?",
            "criteria": {s: criteria[s] for s in statussen},
        },
        "heeft_evidence": {
            "type": "noul",
            "instructions": "Does `tekst` have grounded evidence (normcard, formalrule, bron/doel-regel) in the PoC alignment?",
        },
    }
    rows = []
    for r in report["articles"]:
        tekst = teksten.get(r["number"])
        if not tekst:
            continue
        evidence = bool(r.get("source")) and r.get("source") != "none"
        rows.append({
            "state": {"instrument": instrument, "artikel": r["number"], "tekst": tekst},
            "questions": questions,
            "gold": {
                "voorspelde_status": {"probabilities": {r["status"]: 1.0}},
                "heeft_evidence": {"probabilities": {"true": float(evidence), "false": float(not evidence)}},
            },
            "_meta": {"instrument": instrument, "artikel": r["number"],
                      "status": r["status"], "reason": r.get("reason", ""),
                      "source": r.get("source", "")},
        })
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("holdout", "cross", "bijscholing"), default="holdout")
    p.add_argument("--sample", type=int, default=100,
                   help="bijscholing: aantal utrechtse artikelen in de trainset")
    p.add_argument("--out-dir", type=Path, default=HERE / "data")
    args = p.parse_args()

    alle = {i: build_rows(i) for i in INSTRUMENTEN}
    if args.mode == "cross":
        train = alle["eindhoven"]
        evals = alle["utrecht"]
    elif args.mode == "bijscholing":
        # Deterministische steekproef: sha-volgorde over instrument|artikel —
        # reproduceerbaar zonder seed, ongevoelig voor hoofdstuk-volgorde.
        def _sha_artikel(r: dict) -> str:
            return hashlib.sha256(
                f"utrecht|{r['state']['artikel']}".encode("utf-8")
            ).hexdigest()

        geordend = sorted(alle["utrecht"], key=_sha_artikel)
        steekproef = {r["state"]["artikel"] for r in geordend[: args.sample]}
        train = alle["eindhoven"] + [
            r for r in alle["utrecht"] if r["state"]["artikel"] in steekproef
        ]
        evals = [r for r in alle["utrecht"] if r["state"]["artikel"] not in steekproef]
    else:
        train, evals = [], []
        for instr, rows in alle.items():
            artikelen = sorted({r["state"]["artikel"] for r in rows})
            eval_arts = {a for n, a in enumerate(artikelen) if n % 5 == 0}
            train += [r for r in rows if r["state"]["artikel"] not in eval_arts]
            evals += [r for r in rows if r["state"]["artikel"] in eval_arts]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for naam, rows in (("train", train), ("eval", evals)):
        with (args.out_dir / f"{naam}.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (args.out_dir / "meta.jsonl").write_text(
        "".join(json.dumps(r["_meta"], ensure_ascii=False) + "\n" for r in train + evals),
        encoding="utf-8")
    for naam, bron in (("eindhoven-formalization-report.json", "eindhoven"),
                       ("utrecht-formalization-report.json", "utrecht")):
        sha = hashlib.sha256((FULL_EXPORT_OUT / naam).read_bytes()).hexdigest()
        print(f"bron {bron}: sha256 {sha[:16]}…")
    print(f"mode={args.mode}: train {len(train)} · eval {len(evals)} → {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
