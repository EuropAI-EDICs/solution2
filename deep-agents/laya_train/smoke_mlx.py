"""Convert the fine-tuned nLDT router to MLX and smoke-test it via laya-mlx.

Runs under the deep-agents venv (laya-mlx + Metal):
  cd deep-agents && python laya_train/smoke_mlx.py

1. laya_mlx.convert(): PyTorch checkpoint -> MLX checkpoint (checkpoints/nldt-router-mlx)
2. laya_mlx.Router with the fine-tuned checkpoint wired as `multilingual`
3. predict on held-out-style requests; print the routing hint the orchestrator sees
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TORCH_CKPT = HERE / "checkpoints" / "nldt-router"
MLX_CKPT = HERE / "checkpoints" / "nldt-router-mlx"

DEEP_AGENTS = HERE.parent
sys.path.insert(0, str(DEEP_AGENTS))

from laya_router import format_routing_hint  # noqa: E402

SMOKE_REQUESTS = [
    # scenario-set stijl (NL, unseen track-combinatie in de train-set)
    "Bouw de world scene voor scenario run 20261013T193449Z-bos-scen en toon de visual demo.",
    # vergelijk/geo stijl
    "Vergelijk control met scenario 'Natura 2000-exclusie verbreed met 500 m' — geo-deltas in km².",
    # andere POC's: mogen niet naar utrecht vallen
    "Delegeer naar rijnland: voer de peilen what-if uit met de tool run_rijnland_live.",
    "Delegeer naar breda: voer de vijf-waardenscan uit met de tool run_breda_scan.",
    "Wat is nLDT en hoe verhoudt de toolbox zich tot de omgevingswet-praktijk?",
]


def main() -> None:
    if not TORCH_CKPT.is_dir():
        raise SystemExit(f"geen fine-tuned checkpoint: {TORCH_CKPT} — draai eerst finetune_local.py")
    if not MLX_CKPT.is_dir():
        from laya_mlx.convert import convert

        print(f"converteren {TORCH_CKPT.name} → {MLX_CKPT.name} …")
        convert(str(TORCH_CKPT), str(MLX_CKPT))
    else:
        print(f"hergebruik bestaande MLX-convert: {MLX_CKPT.name}")

    from laya_mlx import Router
    from laya_router import custom_model_override

    router = Router(models=custom_model_override(), default="english")
    for req in SMOKE_REQUESTS:
        lang = "nl" if any(w in req.lower() for w in ("de ", "het ", "een ", "voor ", "gebied")) else None
        result = router.predict({"request": req}, _questions(), lang=lang)
        answers = result.get("answers", {})
        poc = _short(answers.get("primary_poc"))
        wf = _short(answers.get("workflow"))
        print(f"\n> {req}\n  primary_poc={poc}  workflow={wf}")
        print("  " + format_routing_hint(result).replace("\n", "\n  "))


def _short(block: dict | None) -> str:
    if not isinstance(block, dict):
        return "?"
    choice = block.get("choice") or block.get("label")
    if block.get("noul") is not None:
        choice = "ja" if float(block["noul"]) >= 0.5 else "nee"
    conf = block.get("confidence")
    return f"{choice} ({conf:.2f})" if conf is not None else str(choice)


def _questions() -> dict:
    from laya_router import nldt_orchestrator_questions

    return nldt_orchestrator_questions()


if __name__ == "__main__":
    main()
