#!/usr/bin/env python3
"""harness-lab CLI: stel harness-varianten voor, probeer ze, adopteer winnaars.

De methode (naar google-research/harness2, maar met onze eigen deterministische
rechter in plaats van een LLM-jury):

  propose  — variantbestanden (schema's: poc-fundament/schemas/harness-variant)
  probe    — `probe`: elke variant × taskset door de adapter, deterministische
             checks, evidence per probe (fake = offline montuur, llm = echt model)
  compose  — probe-rapport (vergelijkingsmatrix over varianten)
  adopt    — `adopt`: menselijke knop; promoveert een variant naar het
             harnessregister, alleen met voldoend llm-bewijs

Voorbeelden:
  harness_lab.py scaffold --adapter deepagents \
      --register deep-agents/harnessregister.json \
      --out deep-agents/harness-lab/variants/baseline.json
  harness_lab.py probe --adapter deepagents --mode fake \
      --taskset deep-agents/harness-lab/tasksets/routing.json \
      --variant deep-agents/harness-lab/variants/*.json \
      --out harness-lab-runs/<ts>
  harness_lab.py adopt --register deep-agents/harnessregister.json \
      --variant .../variants/prompt-kort.json --evidence harness-lab-runs/<ts>/prompt-kort
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.append(str(HERE.parent))  # poc-fundament-root: fundament-package (append, nooit insert(0) — M2-les)

from fundament import harnesslab as hl  # noqa: E402

ADAPTERS = {"deepagents": REPO / "deep-agents"}


def _adapter(name: str):
    pad = ADAPTERS.get(name)
    if pad is None:
        raise hl.HarnessLabError(f"onbekende adapter {name!r} (kies uit: {sorted(ADAPTERS)})")
    sys.path.append(str(pad))
    modulenaam = {"deepagents": "harness_lab_adapter"}[name]
    import importlib

    return importlib.import_module(modulenaam)


def cmd_scaffold(args) -> int:
    ad = _adapter(args.adapter)
    if args.register:
        basis = ad.snapshot_register_basis()
        doc = json.loads(json.dumps(basis))
        Path(args.register).write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"register-baselijn: {args.register} ({len(doc['harnesses'])} entries)")
    if args.out:
        uit = ad.snapshot_variant_basis(Path(args.out))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(uit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"baselijn-variant: {args.out} ({len(uit['components'])} componenten)")
    return 0


def cmd_probe(args) -> int:
    ad = _adapter(args.adapter)
    taskset_pad = Path(args.taskset)
    taskset = hl.load_taskset(taskset_pad)
    varianten = [(hl.load_variant(Path(v)), Path(v)) for v in args.variant]
    uit = Path(args.out)
    evidences = []
    for variant, pad in varianten:
        subdir = uit / f"{variant['id']}"
        print(f"probe {variant['id']} × {taskset['id']} ({args.mode}) → {subdir}")
        ev = ad.run_probe(variant=variant, variant_path=pad, taskset=taskset,
                          taskset_path=taskset_pad, mode=args.mode, out_dir=subdir)
        evidences.append(ev)
        print(f"  verdict: {ev['verdict']} ({ev['score']['passed']}/{ev['score']['total']} taken)")
    (uit / "probe-report.md").write_text(
        hl.render_probe_report(evidences), encoding="utf-8")
    print(f"rapport: {uit / 'probe-report.md'}")
    return 0


def cmd_adopt(args) -> int:
    evidence_pad = Path(args.evidence)
    if evidence_pad.is_dir():
        evidence_pad = evidence_pad / hl.EVIDENCE_FILENAME
    reg = hl.adopt_register(
        register_path=Path(args.register),
        variant_path=Path(args.variant),
        evidence_path=evidence_pad,
        allow_fake=args.allow_fake,
        version=args.version,
        actor=args.actor,
    )
    by_id = {h["id"]: h for h in reg["harnesses"]}
    variant = hl.load_variant(Path(args.variant))
    for comp in variant["components"]:
        entry_id = f"{variant['id']}-{comp['target'].replace('/', '-')}"
        print(f"geadopteerd: {entry_id} (status {by_id[entry_id]['status']})")
    print(f"register: {args.register}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness_lab", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold", help="baselijn: register + identiteits-variant")
    sc.add_argument("--adapter", default="deepagents", choices=sorted(ADAPTERS))
    sc.add_argument("--register", help="pad voor het harnessregister")
    sc.add_argument("--out", help="pad voor de baselijn-variant")
    sc.set_defaults(func=cmd_scaffold)

    pr = sub.add_parser("probe", help="varianten × taskset proberen")
    pr.add_argument("--adapter", default="deepagents", choices=sorted(ADAPTERS))
    pr.add_argument("--mode", default="fake", choices=["fake", "llm"])
    pr.add_argument("--taskset", required=True)
    pr.add_argument("--variant", action="append", required=True,
                    help="variantbestand (herhaalbaar)")
    pr.add_argument("--out", required=True, help="uitvoermap voor de probe-runs")
    pr.set_defaults(func=cmd_probe)

    ad = sub.add_parser("adopt", help="menselijke knop: variant adopteren")
    ad.add_argument("--register", required=True)
    ad.add_argument("--variant", required=True)
    ad.add_argument("--evidence", required=True,
                    help="probe-map of probe-evidence.json")
    ad.add_argument("--allow-fake", action="store_true",
                    help="fake-modus-bewijs accepteren (alleen voor montuur-tests)")
    ad.add_argument("--version", default="1.0.0")
    ad.add_argument("--actor", default="harness-lab")
    ad.set_defaults(func=cmd_adopt)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except hl.HarnessLabError as exc:
        print(f"harness-lab: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
