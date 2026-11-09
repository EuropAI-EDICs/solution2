# Laya-formalisatie-poortwachter (Inzet A) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een fine-tuned Laya-checkpoint dat per artikel van een lokaal instrument (op de letterlijke tekst) een S1-hint geeft `voorspelde_status` (formalized/ambiguous/unmatched) + `heeft_evidence`, geëxporteerd als `laya-hints/v1`-artefact naast het formalization-report, plus een werklijst die template-gaps en LLM-kandidaten bovenaan zet.

**Architecture:** Drie lagen, gescheiden op venv — (1) datasetbouw (stdlib, deterministisch) uit de gecommitte formalization-reports + instrument-YAML's; (2) fine-tune + predict-export in de trainings-venv (laya+torch, mirror van `laya_bp2op`); (3) werklijst-leeslaag in `nldt/.venv` die alléén het artefact leest. De nldt-pijplijn krijgt géén laya-afhankelijkheid; het formalization-report-contract blijft onaangetast.

**Tech Stack:** Python 3.12 (trainings-venv `deep-agents/laya_train/.venv`: laya, torch, transformers, MPS), nldt/.venv (stdlib), JSON Schema draft 2020-12.

## Global Constraints

- Gold uitsluitend uit de gecommitte artefacten `nldt/simulation/regelrecht/full_export/out/{eindhoven,utrecht}-formalization-report.json` (statussen formalized/ambiguous/rejected/unmatched, `source`-veld voor evidence) — niets uitgedacht ([PLAN_LAYA_INZET.md](../../PLAN_LAYA_INZET.md), principe 1).
- Datasetbouw deterministisch: pure sorting, geen seed, geen netwerk.
- Checkpoints buiten git; wél sha256 van checkpoint én dataset in elk artefact.
- Confidence-gate 0,55; onder de gate: `door: false` en géén hint-claim.
- Elke test draait offline in `nldt/.venv` zonder checkpoints (mock/stub); geen MLX/torch in tests.
- Formalization-report (`formalization-report/v1`, `additionalProperties: false`) wordt NIET gewijzigd — hints komen in een apart artefact.

---

### Task 1: Dataset-builder `simulation/laya_formalizer/`

**Files:**
- Create: `simulation/laya_formalizer/build_dataset.py`
- Test: `simulation/test_laya_formalizer.py`

**Interfaces:**
- Produces: `simulation/laya_formalizer/data/{train,eval,meta}.jsonl` met rijen `{state: {instrument, artikel, tekst}, questions, gold, _meta}`; questions-dict exact zoals `laya_bp2op` (keys `voorspelde_status` type choice, `heeft_evidence` type noul) — Task 3 hergebruikt dit formaat 1-op-1 voor `laya.Agent.predict(state, questions)`.
- CLI: `--mode holdout` (default; per instrument elk 5e artikel held-out) of `--mode cross` (train = eindhoven-artikelen, eval = álle utrecht-artikelen).

- [ ] **Step 1: Schrijf de falende test** (in `simulation/test_laya_formalizer.py`):

```python
"""Tests voor de laya_formalizer-dataset (PLAN_LAYA_INZET.md, Inzet A).

Offline: leest de gecommitte full_export-artefacten; geen laya/torch nodig.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
NLDT_PY = ROOT / "nldt" / ".venv" / "bin" / "python"
BUILDER = HERE / "laya_formalizer" / "build_dataset.py"


class DatasetTest(unittest.TestCase):
    def _build(self, mode: str, tmp: pathlib.Path) -> dict:
        uit = subprocess.run(
            [str(NLDT_PY), str(BUILDER), "--mode", mode, "--out-dir", str(tmp)],
            capture_output=True, text=True, check=True,
        )
        print(uit.stdout)
        return {
            naam: [json.loads(l) for l in (tmp / f"{naam}.jsonl").read_text("utf-8").splitlines() if l]
            for naam in ("train", "eval", "meta")
        }

    def test_holdout_totaal_en_geen_leak(self):
        with tempfile.TemporaryDirectory() as d:
            d = self._build("holdout", pathlib.Path(d))
            self.assertEqual(len(d["train"]) + len(d["eval"]), 1074 + 427)
            seen = {}
            for split in ("train", "eval"):
                for r in d[split]:
                    key = (r["state"]["instrument"], r["state"]["artikel"])
                    self.assertNotIn(key, seen, f"artikel in beide splits: {key}")
                    seen[key] = split

    def test_cross_is_kruisinstrument(self):
        with tempfile.TemporaryDirectory() as d:
            d = self._build("cross", pathlib.Path(d))
            self.assertEqual({r["state"]["instrument"] for r in d["eval"]}, {"utrecht"})
            self.assertEqual(len(d["eval"]), 427)
            self.assertEqual({r["state"]["instrument"] for r in d["train"]}, {"eindhoven"})

    def test_gold_alleen_uit_report(self):
        with tempfile.TemporaryDirectory() as d:
            d = self._build("holdout", pathlib.Path(d))
            for r in d["train"] + d["eval"]:
                for status in r["gold"]["voorspelde_status"]["probabilities"]:
                    self.assertIn(status, r["questions"]["voorspelde_status"]["criteria"])
                ev = r["gold"]["heeft_evidence"]["probabilities"]
                self.assertAlmostEqual(sum(ev.values()), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Draai de test en zie hem falen**

Run: `nldt/.venv/bin/python simulation/test_laya_formalizer.py`
Expected: FAIL/Error — `build_dataset.py` bestaat niet.

- [ ] **Step 3: Implementeer `simulation/laya_formalizer/build_dataset.py`**

```python
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

Usage:  nldt/.venv/bin/python build_dataset.py [--mode holdout|cross] [--out-dir data]
Deterministisch (pure sorting, geen seed, geen netwerk).
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
    import yaml  # nldt/.venv heeft pyyaml; trainings-venv ook

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
    p.add_argument("--mode", choices=("holdout", "cross"), default="holdout")
    p.add_argument("--out-dir", type=Path, default=HERE / "data")
    args = p.parse_args()

    alle = {i: build_rows(i) for i in INSTRUMENTEN}
    if args.mode == "cross":
        train = alle["eindhoven"]
        evals = alle["utrecht"]
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
```

- [ ] **Step 4: Draai de test en zie hem slagen**

Run: `nldt/.venv/bin/python simulation/test_laya_formalizer.py -v`
Expected: 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git add simulation/laya_formalizer/build_dataset.py simulation/test_laya_formalizer.py
git commit -m "feat(laya): datasetbuilder formalisatie-poortwachter — gold uit formalization-reports, holdout- én kruisinstrument-split"
```

---

### Task 2: Fine-tune `simulation/laya_formalizer/finetune.py`

**Files:**
- Create: `simulation/laya_formalizer/finetune.py` (spiegel van `simulation/laya_bp2op/finetune.py`, dus geen nieuwe afhankelijkheden)
- Modify: `.gitignore` — voeg `simulation/laya_formalizer/checkpoints/` toe als dat patroon er nog niet staat (bestaand beleid: weights blijven lokaal).

**Interfaces:**
- Produces: twee checkpoints + summaries — `checkpoints/formalizer-laya/` (productie, getraind op `data/` = holdout-mode beide instrumenten) en `checkpoints/formalizer-laya-cross/` (claim-run, getraind op `data-cross/` = cross-mode: alléén Eindhoven). Nieuwe CLI-vlag t.o.v. de bp2op-spiegel: `--data-dir` (default `HERE/"data"`). `SEED_DEFAULT = 20261108`. De laya-API-aanroepen (`resolve_base_model`, `laya.train.finetune`, `TrainConfig`) blijven identiek aan `simulation/laya_bp2op/finetune.py`; alleen de paden worden argument-gedreven:

```python
    parser.add_argument("--data-dir", type=Path, default=HERE / "data")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    …
    rows = [json.loads(l) for l in (args.data_dir / "train.jsonl").read_text("utf-8").splitlines() if l]
    eval_rows = [json.loads(l) for l in (args.data_dir / "eval.jsonl").read_text("utf-8").splitlines() if l]
```

- [ ] **Step 1: Bouw beide datasets** — `nldt/.venv/bin/python simulation/laya_formalizer/build_dataset.py` (→ `data/`) en `nldt/.venv/bin/python simulation/laya_formalizer/build_dataset.py --mode cross --out-dir data-cross` (→ `data-cross/`).

- [ ] **Step 2: Dry-run (geen GPU-tijd verspillen bij typefouten)**

Run: `deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/finetune.py --dry-run`
Expected: `items: train 1120 (skipped 0) · eval 381 (skipped 0)`-orde (holdout-aantallen uit Task 1).

- [ ] **Step 3: Fine-tune beide checkpoints (~15–25 min per run op M3 Max)**

```bash
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/finetune.py
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/finetune.py \
  --data-dir data-cross --output-dir checkpoints/formalizer-laya-cross
```
Expected: beide `finetune-summary.json`-runs (de cross-run overschrijft de summary — kopieer die vóór de tweede run naar `finetune-summary-cross.json`); noteer `calibration.choice.accuracy` voor het eindrapport.

- [ ] **Step 4: Controleer .gitignore-dekking**

Run: `git status --short simulation/laya_formalizer/ | head`
Expected: géén `checkpoints/`-regels (wel `finetune.py`, `data/`, `data-cross/`, summaries).

- [ ] **Step 5: Commit**

```bash
git add .gitignore simulation/laya_formalizer/finetune.py simulation/laya_formalizer/finetune-summary.json simulation/laya_formalizer/finetune-summary-cross.json simulation/laya_formalizer/data/ simulation/laya_formalizer/data-cross/
git commit -m "feat(laya): formalizer-checkpoints (productie + kruisinstrument-claim-run) — RLCD + kalibratie, weights buiten git"
```

---

### Task 3: Predict-export met kruisinstrument-eval + `laya-hints/v1`-artefact

**Files:**
- Create: `simulation/laya_formalizer/predict_export.py` (trainings-venv; spiegel van `laya_breda/predict_export.py`)
- Create: `nldt/simulation/regelrecht/full_export/laya-hints.schema.json`

**Interfaces:**
- Consumes: beide checkpoints uit Task 2; `build_rows()` en het questions-dict uit Task 1 (geladen via `importlib`); `laya.Agent(ckpt, device="cpu").predict(state, questions) → res["answers"][qid]` met `.choice`, `.noul` en confidence via de keys `answer_confidence`/`confidence`/`prob` (helper `confidence()` exact zoals `simulation/laya_breda/predict_export.py:24-29`).
- Produces: `nldt/simulation/regelrecht/full_export/out/{eindhoven,utrecht}-laya-hints.json` (contract `laya-hints/v1`) uit het productie-checkpoint, plus `simulation/laya_formalizer/eval-holdout.json` en `eval-cross.json` (metrics). Task 4 leest alléén de hints-artefacten.

- [ ] **Step 1: Schrijf het schema** `nldt/simulation/regelrecht/full_export/laya-hints.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldttoolbox.local/laya-hints/v1",
  "title": "Laya formalisatie-hints (System-1, adviserend)",
  "type": "object",
  "required": ["contract", "instrument", "gegenereerdOp", "model", "artikelen"],
  "additionalProperties": false,
  "properties": {
    "contract": {"const": "laya-hints/v1"},
    "instrument": {"enum": ["eindhoven", "utrecht"]},
    "gegenereerdOp": {"type": "string", "minLength": 1},
    "model": {
      "type": "object",
      "required": ["checkpoint", "checkpointSha256", "datasetSha256", "gate"],
      "additionalProperties": true,
      "properties": {
        "checkpoint": {"type": "string"},
        "checkpointSha256": {"type": "string", "minLength": 64, "maxLength": 64},
        "datasetSha256": {"type": "string", "minLength": 64, "maxLength": 64},
        "gate": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "artikelen": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["number", "voorspeldeStatus", "confidence", "door"],
        "additionalProperties": false,
        "properties": {
          "number": {"type": "string"},
          "voorspeldeStatus": {"enum": ["formalized", "ambiguous", "rejected", "unmatched"]},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1},
          "door": {"type": "boolean"},
          "heeftEvidence": {"type": ["number", "null"]}
        }
      }
    }
  }
}
```

- [ ] **Step 2: Implementeer `predict_export.py` volledig:**

```python
#!/usr/bin/env python3
"""Export Laya-formalisatie-hints per instrument + eval op ongezien materiaal.

Usage (deep-agents/laya_train/.venv):
  python predict_export.py             # productie-checkpoint → hints-artefacten + holdout-eval
  python predict_export.py --cross-eval  # claim-meting: cross-checkpoint vs héél Utrecht
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


def _eval_agent(agent, eval_rows: list[dict]) -> dict:
    hit = {"voorspelde_status": [0, 0], "heeft_evidence": [0, 0]}
    abst, confs = 0, []
    for r in eval_rows:
        res = agent.predict(r["state"], r["questions"])
        a = res["answers"]
        keuze = a["voorspelde_status"].get("choice")
        conf = confidence(a["voorspelde_status"]) or 0.0
        p = r["gold"]["voorspelde_status"]["probabilities"]
        gold = max(p, key=p.get)
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
    args = p.parse_args()

    data_dir = HERE / ("data-cross" if args.cross_eval else "data")
    ckpt = CKPT_CROSS if args.cross_eval else CKPT
    data_sha = hashlib.sha256(
        (data_dir / "train.jsonl").read_bytes() + (data_dir / "eval.jsonl").read_bytes()
    ).hexdigest()
    agent = laya.Agent(str(ckpt), device="cpu")

    eval_rows = [json.loads(l) for l in (data_dir / "eval.jsonl").read_text("utf-8").splitlines() if l]
    evaluatie = _eval_agent(agent, eval_rows)
    uit = {
        "model": {"checkpoint": str(ckpt), "dataset": str(data_dir), "gate": GATE},
        "modus": ("cross: train eindhoven → eval heel utrecht" if args.cross_eval
                  else "holdout: per instrument elk 5e artikel"),
        "eval": evaluatie,
    }
    if not args.cross_eval:
        uit["hints"] = {}
        for instrument in ("eindhoven", "utrecht"):
            hints = _hints_voor(agent, instrument, data_sha, ckpt)
            pad = FULL_EXPORT_OUT / f"{instrument}-laya-hints.json"
            pad.write_text(json.dumps(hints, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            uit["hints"][instrument] = len(hints["artikelen"])
            print(f"{instrument}: {len(hints['artikelen'])} hints → {pad}")
    (HERE / ("eval-cross.json" if args.cross_eval else "eval-holdout.json")).write_text(
        json.dumps(uit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evaluatie, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Draai beide runs en valideer de artefacten tegen het schema** (jsonschema zit in nldt/.venv, niet per se in de trainings-venv):

```bash
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/predict_export.py
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/predict_export.py --cross-eval
nldt/.venv/bin/python - <<'PY'
import json, pathlib
from jsonschema import Draft202012Validator
schema = json.loads(pathlib.Path(
    "nldt/simulation/regelrecht/full_export/laya-hints.schema.json").read_text())
for poc in ("eindhoven", "utrecht"):
    d = json.loads(pathlib.Path(
        f"nldt/simulation/regelrecht/full_export/out/{poc}-laya-hints.json").read_text())
    errs = list(Draft202012Validator(schema).iter_errors(d))
    print(poc, "VALID" if not errs else errs[:3])
PY
```
Expected: beide instrumenten `VALID`; eval-print met `voorspelde_status.hit/n`, `gatePasRate`, `meanConf`.

- [ ] **Step 4: Beoordeel de gouden meetlat** — lees `eval-cross.json`: accuracy én `gatePasRate` van het op-Eindhoven-getrainde checkpoint op álle 427 Utrechtse artikelen. Beslisregel: alleen bij duidelijke afstand tot de zero-shot-baseline is de claim "nieuw instrument zonder templates triëren" geldig; anders blijft Inzet A expliciet een prioriteringshulp — noteer die eerlijke conclusie in `eval-cross.json`-taal in het eindrapport.

- [ ] **Step 5: Commit**

```bash
git add simulation/laya_formalizer/predict_export.py simulation/laya_formalizer/eval-holdout.json simulation/laya_formalizer/eval-cross.json nldt/simulation/regelrecht/full_export/laya-hints.schema.json nldt/simulation/regelrecht/full_export/out/eindhoven-laya-hints.json nldt/simulation/regelrecht/full_export/out/utrecht-laya-hints.json
git commit -m "feat(laya): predict-export met kruisinstrument-eval + laya-hints/v1-artefacten voor beide instrumenten"
```

---

### Task 4: Werklijst-leeslaag `full_export/laya_werklijst.py` (nldt/.venv, artefact-only)

**Files:**
- Create: `nldt/simulation/regelrecht/full_export/laya_werklijst.py`
- Test: `nldt/tests/test_laya_werklijst.py`

**Interfaces:**
- Consumes: `out/{poc}-formalization-report.json` + `out/{poc}-laya-hints.json` (alleen lezen).
- Produces: `bouw_werklijst(poc, out_dir=FULL_EXPORT_OUT) -> dict` met `{"instrument", "gegenereerdOp", "rijen": [{"number", "status", "voorspeldeStatus", "confidence", " categorie"}]}`; `categorie ∈ {"template_gap_kandidaat", "llm_kandidaat", "verwacht_onthouding"}`; CLI print de rijen gesorteerd (template_gap eerst, dan confidence desc). Ontbrekend hints-artefact → `{"beschikbaar": False, "oorzaak": …}` (fail-soft, géén exception).

- [ ] **Step 1: Schrijf de falende test** (`nldt/tests/test_laya_werklijst.py`):

```python
# nldt/tests/test_laya_werklijst.py
"""Tests voor de laya-werklijst (Inzet A): artefact-only, fail-soft, geen laya-import."""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from nldt.simulation.regelrecht.full_export import laya_werklijst  # noqa: E402


def _schrijf_cache(pad: pathlib.Path, *, met_hints: bool, onder_gate: bool = False) -> None:
    report = {
        "schemaVersion": "1", "poc": "eindhoven", "generatedAt": "t",
        "sourceSha256": "0" * 64,
        "counts": {"formalized": 1, "ambiguous": 0, "rejected": 0, "unmatched": 1},
        "articles": [
            {"number": "1.1", "status": "formalized", "reason": "template"},
            {"number": "2.2", "status": "unmatched", "reason": "no_template"},
        ],
        "orphanedFormalRules": [],
    }
    (pad / "eindhoven-formalization-report.json").write_text(json.dumps(report), "utf-8")
    if not met_hints:
        return
    hints = {
        "contract": "laya-hints/v1", "instrument": "eindhoven", "gegenereerdOp": "t",
        "model": {"checkpoint": "x", "checkpointSha256": "0" * 64,
                  "datasetSha256": "0" * 64, "gate": 0.55},
        "artikelen": [{
            "number": "2.2", "voorspeldeStatus": "formalized",
            "confidence": 0.4 if onder_gate else 0.8,
            "door": not onder_gate, "heeftEvidence": 0.9,
        }],
    }
    (pad / "eindhoven-laya-hints.json").write_text(json.dumps(hints), "utf-8")


class WerklijstTest(unittest.TestCase):
    def test_template_gap_kandidaat(self):
        with tempfile.TemporaryDirectory() as d:
            pad = pathlib.Path(d)
            _schrijf_cache(pad, met_hints=True)
            wl = laya_werklijst.bouw_werklijst("eindhoven", out_dir=pad)
            self.assertTrue(wl["beschikbaar"])
            self.assertEqual([r["number"] for r in wl["rijen"]], ["2.2"])
            self.assertEqual(wl["rijen"][0]["categorie"], "template_gap_kandidaat")

    def test_onder_gate_is_verwachte_onthouding(self):
        with tempfile.TemporaryDirectory() as d:
            pad = pathlib.Path(d)
            _schrijf_cache(pad, met_hints=True, onder_gate=True)
            wl = laya_werklijst.bouw_werklijst("eindhoven", out_dir=pad)
            self.assertEqual(wl["rijen"][0]["categorie"], "verwacht_onthouding")

    def test_fail_soft_zonder_hints(self):
        with tempfile.TemporaryDirectory() as d:
            pad = pathlib.Path(d)
            _schrijf_cache(pad, met_hints=False)
            wl = laya_werklijst.bouw_werklijst("eindhoven", out_dir=pad)
            self.assertFalse(wl["beschikbaar"])
            self.assertIn("predict_export", wl["oorzaak"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Draai en zie falen** — Run: `nldt/.venv/bin/python -m unittest nldt.tests.test_laya_werklijst -v` → ModuleNotFoundError (`laya_werklijst` bestaat nog niet).

- [ ] **Step 3: Implementeer `nldt/simulation/regelrecht/full_export/laya_werklijst.py`:**

```python
"""Leeslaag over laya-hints: werklijst template-gaps / LLM-kandidaten (Inzet A).

Failt zacht: geen hints-artefact → {"beschikbaar": False} — de pijplijn draait
door; hints zijn adviserend en veranderen het formalization-report niet.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from jsonschema import Draft202012Validator

DIR = pathlib.Path(__file__).resolve().parent
if str(DIR) not in sys.path:
    sys.path.insert(0, str(DIR))

import paths  # noqa: E402  (full_export/paths.py — OUT)

HINTS_SCHEMA = DIR / "laya-hints.schema.json"
_VOLGORDE = {"template_gap_kandidaat": 0, "llm_kandidaat": 1, "verwacht_onthouding": 2}


def bouw_werklijst(poc: str, *, out_dir: pathlib.Path | None = None) -> dict[str, Any]:
    out = pathlib.Path(out_dir) if out_dir else paths.OUT
    hints_pad = out / f"{poc}-laya-hints.json"
    if not hints_pad.is_file():
        return {
            "instrument": poc,
            "beschikbaar": False,
            "oorzaak": f"{hints_pad.name} ontbreekt — draai "
            "simulation/laya_formalizer/predict_export.py (Inzet A)",
        }
    hints = json.loads(hints_pad.read_text(encoding="utf-8"))
    schema = json.loads(HINTS_SCHEMA.read_text(encoding="utf-8"))
    fouten = list(Draft202012Validator(schema).iter_errors(hints))
    if fouten:
        return {"instrument": poc, "beschikbaar": False,
                "oorzaak": f"laya-hints faalt schema: {fouten[0].message}"}
    report = json.loads((out / f"{poc}-formalization-report.json").read_text(encoding="utf-8"))
    hint_by = {h["number"]: h for h in hints["artikelen"]}
    rijen = []
    for art in report["articles"]:
        if art["status"] == "formalized":
            continue
        h = hint_by.get(art["number"])
        if not h:
            continue
        if not h["door"]:
            cat = "verwacht_onthouding"
        elif h["voorspeldeStatus"] == "formalized":
            cat = "template_gap_kandidaat"
        elif h["voorspeldeStatus"] == "ambiguous":
            cat = "llm_kandidaat"
        else:
            cat = "verwacht_onthouding"
        rijen.append({
            "number": art["number"], "status": art["status"],
            "voorspeldeStatus": h["voorspeldeStatus"],
            "confidence": h["confidence"], "heeftEvidence": h.get("heeftEvidence"),
            "categorie": cat,
        })
    rijen.sort(key=lambda r: (_VOLGORDE[r["categorie"]],
                              -(r.get("heeftEvidence") or 0.0),
                              -r["confidence"]))
    return {
        "instrument": poc, "beschikbaar": True,
        "gegenereerdOp": hints["gegenereerdOp"], "model": hints["model"],
        "rijen": rijen,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="laya_werklijst", description=__doc__)
    p.add_argument("--instruments", default="eindhoven,utrecht")
    p.add_argument("--out-dir", type=pathlib.Path, default=None)
    args = p.parse_args(argv)
    for poc in [s.strip() for s in args.instruments.split(",") if s.strip()]:
        wl = bouw_werklijst(poc, out_dir=args.out_dir)
        if not wl["beschikbaar"]:
            print(f"{poc}: niet beschikbaar — {wl['oorzaak']}")
            continue
        print(f"{poc}: {len(wl['rijen'])} rijen (gegenereerdOp {wl['gegenereerdOp']})")
        for r in wl["rijen"]:
            print(f"  {r['categorie']:<24} art. {r['number']:<7} "
                  f"status={r['status']:<10} conf={r['confidence']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Draai en zie slagen** — zelfde commando → 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/regelrecht/full_export/laya_werklijst.py nldt/tests/test_laya_werklijst.py
git commit -m "feat(laya): werklijst-leeslaag over laya-hints — template-gaps en LLM-kandidaten bovenaan, fail-soft zonder artefact"
```

---

### Task 5: Inbedding — lake-sync, README, mapping

**Files:**
- Modify: `nldt/services/lake/sync.py` — in `_regelrecht_entries(poc)` één tuple: `("gold", "laya-formalizer", NLDT_ROOT.parent / "simulation" / "laya_formalizer", ["eval-holdout.json", "eval-cross.json", "finetune-summary.json", "finetune-summary-cross.json"])`. (De hints-artefacten `out/{poc}-laya-hints.json` matchen al op de bestaande `regelrecht-export`-entry via patroon `f"{poc}-*.json"` — géén aparte silver-entry, geen dubbele mapping.)
- Modify: `nldt/simulation/README.md` — sectie §RTR/STTR uitbreiden met de drie Laya-commando's (dataset/fine-tune/predict-export + werklijst).
- Modify: `docs/MAPPING_DSO_NAAR_REGELRECHT.md` — componentmapping-tabel: één rij "System-1 triage (Laya)" tussen annotatie- en executielaag, verwijzend naar [PLAN_LAYA_INZET.md](../../PLAN_LAYA_INZET.md).

- [ ] **Step 1: Voeg de gold-entry toe en droog-test:** `nldt/.venv/bin/python nldt/scripts/lake_sync.py --poc eindhoven --poc utrecht --dry-run` → plan bevat `gold/…/laya-formalizer/eval-holdout.json` e.d. (zodra Task 2/3 draaiden), en de hints zitten onder `silver/…/regelrecht-export/…-laya-hints.json` via het bestaande patroon.
- [ ] **Step 2: README + mapping-rij schrijven (verwijzingen naar dit plan en PLAN_LAYA_INZET.md).**
- [ ] **Step 3: Volledige regression:** `nldt/.venv/bin/python -m unittest nldt.tests.test_simulation_regelrecht_full nldt.tests.test_simulation_corpus_export nldt.tests.test_laya_werklijst` en `nldt/.venv/bin/python simulation/test_laya_formalizer.py` → alles OK.
- [ ] **Step 4: Commit**

```bash
git add nldt/services/lake/sync.py nldt/simulation/README.md docs/MAPPING_DSO_NAAR_REGELRECHT.md
git commit -m "feat(laya): formalisme-poortwachter ingebed — lake-sync, README, mapping-rij (Inzet A)"
```

---

## Zelfreview-checklist (na afronding)

- [ ] Gold uitsluitend uit reports (grep `_meta` vs report-bron).
- [ ] Geen laya/torch-import in nldt-code (`grep -r "import laya" nldt/` → leeg).
- [ ] Formalization-report-contract onaangetast (`git diff …formalization-report.schema.json` → leeg).
- [ ] Checkpoints buiten git (`git status simulation/laya_formalizer/` → geen weights).
- [ ] Kruisinstrument-cijfers genoteerd in `eval-cross.json` én het eindrapport.
