# laya_train — Laya fine-tunen op de POC-scenariovoorbeelden

Fine-tune-pipeline voor de nLDT Laya routing-head (`deep-agents/laya_router.py`):
het multilingual-checkpoint van `convaiinnovations/laya` wordt bijgeschoold op
routing-cases die **deterministisch uit de scenariovoorbeelden van de POC's**
worden gegenereerd.

## Waar komen de trainingsvoorbeelden vandaan?

| Bron | Wat | Gold-labels |
|---|---|---|
| `poc/scenarios/*.json` | 13 Utrecht-track scenario-sets (+ wonen/werken what-ifs) | utrecht × workflow-mode |
| `poc-nspd/scenarios/*.json` | 20 NSPD NL/BE scenario-sets | idem, region NL/Vlaanderen |
| `poc/scenario-runs/`, `poc-nspd/scenario-runs/` | échte run-ids (bijv. `20261013T193408Z-wind-scen`) in de request-tekst | — |
| `deep-agents/poc_demos.py` | demo-catalogus-phrasings voor breda / rijnland / minigim / eindhoven / inventaris / unclear | afwijkende primary_poc |

Elke scenario-set levert cases op over de utrecht-workflow-modes uit de
demo-catalogus (execute / plan / kritische toets / control-vs-scenario /
geo+critic / normketen / volledige keten / uitdaging-overzicht), met de eigen
objectTypen en scenario-namen van die set. Cross-track-cases (wind × zon × bos,
water × bodem, …) gronden de `crosstrack`-POC. De verdeling is bewust
scenario-zwaar: deze fine-tune maakt de router scherper op scenarioverzoeken,
de overige POC-labels blijven via de controls vertegenwoordigd.

Split: 4 scenario-sets + 8 controls zijn **compleet** held-out
(`data/scenarios-eval.jsonl`) — evaluatie meet dus generalisatie naar ongezien
sets, niet geleerde parafrases. Manifest met per-case herkomst:
`data/manifest.jsonl`.

**Fine-tune-resultaat (run 2026-10-18, held-out split 50 cases / 250 items —
ongeziene scenario-sets + controls):**

| vraag | zero-shot multilingual | fine-tuned |
|---|---|---|
| primary_poc | 0.46 | **0.96** |
| workflow | 0.66 | **0.96** |
| needs_intake / build / critic | 0.82 / 0.82 / 0.76 | **1.00 / 1.00 / 1.00** |
| hints door confidence-gate (≥0.55) | 38% | **96%** |

ECE 0.149 → 0.005; de drie resterende fouten zitten in conceptuele
 controle-vragen (breda/eindhoven/unclear), niet in scenario-routing —
alle scenario-cases uit ongeziene sets routeerden correct. Volledig rapport:
`eval-report.json`; run-log: `finetune-run2.log`.

## Pipeline

```bash
cd deep-agents/laya_train

# 1. trainings-venv (apart van deep-agents/.venv: heeft torch, geen MLX)
python3.12 -m venv .venv && ./.venv/bin/pip install laya torch transformers

# 2. dataset bouwen (deterministisch, seed 20261018)
../../deep-agents/.venv/bin/python build_dataset.py   # elke stdlib-python werkt

# 3. fine-tunen op MPS (multilingual-checkpoint, RLCD + kalibratie inklusief)
./.venv/bin/python finetune_local.py --dry-run       # items-check zonder weights
./.venv/bin/python finetune_local.py                 # ~15–25 min op M3 Max
#    → checkpoints/nldt-router/ (PyTorch) + finetune-summary.json

# 4. evalueren: zero-shot multilingual vs fine-tuned op de held-out split
./.venv/bin/python evaluate_local.py                 # → eval-report.json

# 5. converteren naar MLX + rooktest via laya-mlx (deep-agents-venv!)
../.venv/bin/python smoke_mlx.py                     # → checkpoints/nldt-router-mlx/
```

## Checkpoint gebruiken in de deep-agents orchestrator

```bash
export LAYA_MODEL_DIR="$PWD/deep-agents/laya_train/checkpoints/nldt-router-mlx"
python live.py
```

`laya_router.custom_model_override()` zet het checkpoint op **beide** routes
(english én multilingual): het fine-tuned multilingual-model dekt Engelse
parafrases af, en korte NL-tekst zonder stopwoord-trigger zou anders terugvallen
op het stock english-checkpoint. Zonder `LAYA_MODEL_DIR` gedraagt de router
zich onveranderd. De confidence-gate (`LAYA_MIN_CONFIDENCE`, default 0.55)
werkt idem — het fine-tune omvat de per-vragetype temperatuurkalibratie, dus de
gate is betrouwbaarder dan bij het stock-checkpoint (zie de blog:
stock-checkpoints zijn over-confident).

## Bestanden

| Bestand | Functie |
|---|---|
| `build_dataset.py` | scenario-sets → routing-cases (train/eval/manifest) |
| `finetune_local.py` | `laya.train.finetune` op MPS (+ `--dry-run`) |
| `evaluate_local.py` | held-out eval: accuracy per vraag, gate-pass-rate, base vs fine-tuned |
| `smoke_mlx.py` | PyTorch→MLX-conversie + Router-rooktest (deep-agents-venv) |
| `data/` | gegenereerde JSONL's (train/eval/manifest) |
| `checkpoints/` | `nldt-router/` (PyTorch) en `nldt-router-mlx/` (inference) |

Het dataset-schema is `{state, questions, gold}` per case (docs/finetune.md
van upstream laya); `questions` is exact het schema uit
`laya_router.nldt_orchestrator_questions()`, zodat trainen en infereren
question-compatibel zijn.
