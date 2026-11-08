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
