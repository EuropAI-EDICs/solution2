"""Fine-tune Laya (multilingual checkpoint) on the nLDT scenario routing dataset.

Wraps the canonical laya.train.finetune primitives (RLCD objective, sigma
schedule, per-type calibration fit, checkpoint save) for a single MPS device.
First run downloads the `multilingual` subfolder of convaiinnovations/laya.

Usage:
  python finetune_local.py --dry-run   # build items only, no weights loaded
  python finetune_local.py             # full fine-tune (Apple Silicon, MPS)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "scenarios-train.jsonl"
EVAL = HERE / "data" / "scenarios-eval.jsonl"
DEFAULT_OUT = HERE / "checkpoints" / "nldt-router"
BASE_REPO = "convaiinnovations/laya"


def resolve_base_model() -> str:
    """Download (or reuse) the multilingual base checkpoint and return its path."""
    from huggingface_hub import snapshot_download

    model_dir = snapshot_download(BASE_REPO, allow_patterns=["multilingual/*"])
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

    with open(Path(resolve_base_model()) / "rl_agent_config.json") as fh:
        cfg = json.load(fh)

    from laya.train import TrainConfig, items_from_rows, split_calibration
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(os.path.join(resolve_base_model(), "tokenizer"))
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    items, skipped = items_from_rows(tok, rows, cfg["max_len"], cfg["head_max_len"])
    print(f"items: {len(items)} (skipped {skipped}) from {len(rows)} cases")

    if args.dry_run:
        return

    from laya.train import finetune

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
        model_dir=resolve_base_model(),
        output_dir=str(args.output_dir),
        config=config,
        device=args.device,
    )
    (HERE / "finetune-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str)[:2000])


SEED_DEFAULT = 20261018


if __name__ == "__main__":
    main()
