#!/usr/bin/env python3
"""Fine-tune Laya (multilingual base) on the BP->OP bronregel dataset.

Runs in deep-agents/laya_train/.venv (laya + torch + transformers, MPS).
Same high-level finetune API as deep-agents/laya_train/finetune_local.py —
RLCD objective, sigma schedule, per-type temperature calibration, held-out
eval before/after (eval.jsonl: 63 ongeziene bron-artikelen).

Usage:
  python finetune.py --dry-run    # items check only
  python finetune.py              # ~10–20 min on M3 Max (MPS)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "train.jsonl"
EVAL = HERE / "data" / "eval.jsonl"
DEFAULT_OUT = HERE / "checkpoints" / "bp2op-laya"
SEED_DEFAULT = 20261024


def resolve_base_model() -> str:
    import os

    from huggingface_hub import snapshot_download

    model_dir = snapshot_download("convaiinnovations/laya", allow_patterns=["multilingual/*"])
    base = os.path.join(model_dir, "multilingual")
    if not os.path.isdir(base):
        base = model_dir
    from laya.agent import _fix_tokenizer_config

    _fix_tokenizer_config(base)
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--micro-batch", type=int, default=8)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--seed", type=int, default=SEED_DEFAULT)
    parser.add_argument("--device", default="mps", choices=("mps", "cpu"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true",
                        help="tokenize + item build only; prints skipped reasons")
    args = parser.parse_args()

    base = resolve_base_model()
    with open(Path(base) / "rl_agent_config.json") as fh:
        cfg = json.load(fh)

    from laya.train import items_from_rows
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(Path(base) / "tokenizer"))
    rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l]
    eval_rows = [json.loads(l) for l in EVAL.read_text(encoding="utf-8").splitlines() if l]
    items, skipped = items_from_rows(tok, rows, cfg["max_len"], cfg["head_max_len"])
    eval_items, eval_skipped = items_from_rows(tok, eval_rows, cfg["max_len"], cfg["head_max_len"])
    print(f"items: train {len(items)} (skipped {skipped}) · eval {len(eval_items)} (skipped {eval_skipped})")
    if args.dry_run:
        return

    from laya.train import TrainConfig, finetune

    config = TrainConfig(
        epochs=args.epochs,
        micro_batch=args.micro_batch,
        grad_accum=args.grad_accum,
        seed=args.seed,
        calib_seed=args.seed,
        eval_data=str(EVAL),
    )
    summary = finetune(
        data=str(DATA),
        model_dir=base,
        output_dir=str(args.output_dir),
        config=config,
        device=args.device,
    )
    (HERE / "finetune-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    print("checkpoint:", args.output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str)[:1500])


if __name__ == "__main__":
    main()
