#!/usr/bin/env python3
"""Deterministische generator voor de RegelRecht-PoC-simulaties.

Leest alléén echte artefacten (voorbeeld-YAML's + canonieke PoC-runs),
her-valideert de YAML's tegen het vastgepinde regelrecht-schema v0.7.1,
berekent demo-cases met reference_engine (de norm), schrijft run-JSON's
gevalideerd tegen simulation-run.schema.json, de golden set, en de
single-file demo-pagina. Zie spec 2026-09-29-simulation-regelrecht-design.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import yaml
from jsonschema import Draft202012Validator

import reference_engine

DIR = pathlib.Path(__file__).resolve().parent
ROOT = DIR.parents[2]

REGELRECHT_SCHEMA_PATH = DIR / "schema" / "regelrecht-v0.7.1.schema.json"
RUN_SCHEMA_PATH = DIR / "simulation-run.schema.json"

POC_CONFIGS = {
    "utrecht": {
        "run_file": "utrecht-wind-art5.3.json",
        "example_yaml": "docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml",
        "article_number": "5.3",
        "artifacts": [
            ("docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml", "example-yaml"),
            ("poc/corpus/normcards-wind.json", "normcard"),
            ("poc/corpus/formalrules-wind.json", "formalrule"),
            ("poc/runs/20260830T113234Z-wind/run_summary.json", "run-summary"),
        ],
        "instrument": {
            "title": "Omgevingsverordening provincie Utrecht",
            "cvdr": "CVDR704250",
            "regulatoryLayer": "PROVINCIALE_VERORDENING",
            "article": "5.3",
        },
        "abstentions": {
            "label": "ambigue FormalRules (open normen → jurist)",
            "source": "poc/corpus/formalrules-wind.json",
        },
    },
    "eindhoven": {
        "run_file": "eindhoven-bp2op-art10.2.json",
        "example_yaml": "docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml",
        "article_number": "10.2",
        "artifacts": [
            ("docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml", "example-yaml"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/bronregels.json", "bronregel"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/doelregels.json", "doelregel"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/omzettabel.json", "omzettabel"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/kennisbank.json", "kennisbank"),
        ],
        "instrument": {
            "title": "Omgevingsplan gemeente Eindhoven",
            "cvdr": "CVDR696400_4",
            "regulatoryLayer": "GEMEENTELIJKE_VERORDENING",
            "article": "10.2",
        },
        "abstentions": {
            "label": "omzettabel-rijen needs_human (jurist)",
            "source": "poc-bp2op/runs/20260830-124515-eindhoven/omzettabel.json",
        },
    },
}


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load_artifacts(poc: str) -> dict:
    cfg = POC_CONFIGS[poc]
    out = {}
    for rel, role in cfg["artifacts"]:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"ontbrekend artefact: {rel}")
        out[role] = {"path": rel, "sha256": sha256_of(p), "data": _load(p)}
    return out


def _load(p: pathlib.Path):
    if p.suffix in (".yaml", ".yml"):
        return yaml.safe_load(p.read_text())
    return json.loads(p.read_text())


def _regelrecht_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(REGELRECHT_SCHEMA_PATH.read_text()))


def _example_article(artifacts: dict, article_number: str) -> tuple[dict, dict]:
    doc = artifacts["example-yaml"]["data"]
    validator = _regelrecht_validator()
    validator.validate(doc)  # her-validatie: faalt expliciet bij afwijking
    for art in doc["articles"]:
        if art["number"] == article_number:
            return doc, art
    raise SystemExit(f"artikel {article_number} niet in voorbeeld-YAML")


def _execution_of(article: dict) -> dict:
    return article["machine_readable"]["execution"]


def _run_id(source_artifacts: list[dict]) -> str:
    h = hashlib.sha256()
    for a in sorted(source_artifacts, key=lambda x: x["path"]):
        h.update(a["path"].encode())
        h.update(a["sha256"].encode())
    return h.hexdigest()[:8]


def utrecht_cases(execution: dict) -> list[dict]:
    cases = []
    n = 0
    for ashoogte in (19, 20, 21):
        for perceel in (True, False):
            for zone in (True, False):
                n += 1
                inputs = {
                    "ashoogte_m": ashoogte,
                    "op_of_in_aansluiting_op_bestaand_bouwperceel": perceel,
                    "in_gebied_kleine_windturbine": zone,
                }
                r = reference_engine.evaluate(execution, inputs)
                cases.append({
                    "id": f"utrecht-h{ashoogte}-p{int(perceel)}-z{int(zone)}",
                    "inputs": inputs,
                    "expectedOutputs": r["outputs"],
                    "trace": r["trace"],
                })
    return cases


def build_utrecht_run(artifacts: dict, stamp: str) -> dict:
    cfg = POC_CONFIGS["utrecht"]
    _, article = _example_article(artifacts, cfg["article_number"])
    cards = artifacts["normcard"]["data"]
    quote = next(c for c in cards if c["id"] == "NC-W-03")["source"]["quote"]
    rules = artifacts["formalrule"]["data"]
    ambiguous = sum(1 for r in rules if r["status"] == "ambiguous")
    source_artifacts = [
        {"path": v["path"], "role": role, "sha256": v["sha256"]}
        for role, v in artifacts.items()
    ]
    return {
        "schemaVersion": "1",
        "runId": _run_id(source_artifacts),
        "generatedAt": stamp,
        "poc": "utrecht",
        "instrument": cfg["instrument"],
        "sourceArtifacts": source_artifacts,
        "machineReadable": article["machine_readable"],
        "articleQuote": quote,
        "demoCases": utrecht_cases(_execution_of(article)),
        "abstentions": {"count": ambiguous, **cfg["abstentions"]},
        "humanOnTheButtons": "v4_pending",
        "validations": [
            {"level": "V0", "verdict": "pass",
             "evidence": "voorbeeld-YAML gevalideerd tegen regelrecht-schema v0.7.1"},
            {"level": "V2", "verdict": "pass",
             "evidence": "articleQuote letterlijk uit NC-W-03 (poc/corpus/normcards-wind.json)"},
            {"level": "V4", "verdict": "pending", "evidence": "jurittoets staat structureel open (MC-6)"},
        ],
    }


def eindhoven_cases(execution: dict) -> list[dict]:
    cases = []
    for strijd in (True, False):
        for iwt in (True, False):
            inputs = {"strijd_met_tijdelijk_deel": strijd, "voorschriften_verbonden_voor_iwt": iwt}
            r = reference_engine.evaluate(execution, inputs)
            cases.append({
                "id": f"eindhoven-s{int(strijd)}-i{int(iwt)}",
                "inputs": inputs,
                "expectedOutputs": r["outputs"],
                "trace": r["trace"],
            })
    return cases


def build_eindhoven_run(artifacts: dict, stamp: str) -> dict:
    cfg = POC_CONFIGS["eindhoven"]
    _, article = _example_article(artifacts, cfg["article_number"])
    bronregels = artifacts["bronregel"]["data"]
    quote = next(b for b in bronregels if b["id"] == "BR-001")["tekst"]
    tabel = artifacts["omzettabel"]["data"]
    needs_human = sum(1 for r in tabel if r["status"] == "needs_human")
    source_artifacts = [
        {"path": v["path"], "role": role, "sha256": v["sha256"]}
        for role, v in artifacts.items()
    ]
    return {
        "schemaVersion": "1",
        "runId": _run_id(source_artifacts),
        "generatedAt": stamp,
        "poc": "eindhoven",
        "instrument": cfg["instrument"],
        "sourceArtifacts": source_artifacts,
        "machineReadable": article["machine_readable"],
        "articleQuote": quote,
        "demoCases": eindhoven_cases(_execution_of(article)),
        "abstentions": {"count": needs_human, **cfg["abstentions"]},
        "humanOnTheButtons": "v4_pending",
        "validations": [
            {"level": "V0", "verdict": "pass",
             "evidence": "voorbeeld-YAML gevalideerd tegen regelrecht-schema v0.7.1"},
            {"level": "V2", "verdict": "pass",
             "evidence": "articleQuote letterlijk uit BR-001 (bronregels.json canonieke run)"},
            {"level": "V4", "verdict": "pending", "evidence": "jurittoets staat structureel open (MC-6)"},
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stamp", required=True, help="ISO-timestamp voor generatedAt (herhaalbaar maken)")
    ap.add_argument("--outdir", default=None, help="optionele alternatieve uitvoermap")
    args = ap.parse_args(argv)
    outdir = pathlib.Path(args.outdir) if args.outdir else DIR
    runs_dir = outdir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run = build_utrecht_run(load_artifacts("utrecht"), args.stamp)
    Draft202012Validator(json.loads(RUN_SCHEMA_PATH.read_text())).validate(run)
    (runs_dir / POC_CONFIGS["utrecht"]["run_file"]).write_text(
        json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"OK utrecht runId={run['runId']} cases={len(run['demoCases'])}")

    run = build_eindhoven_run(load_artifacts("eindhoven"), args.stamp)
    Draft202012Validator(json.loads(RUN_SCHEMA_PATH.read_text())).validate(run)
    (runs_dir / POC_CONFIGS["eindhoven"]["run_file"]).write_text(
        json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"OK eindhoven runId={run['runId']} cases={len(run['demoCases'])}")

    cases = []
    for poc in ("utrecht", "eindhoven"):
        run = json.loads((runs_dir / POC_CONFIGS[poc]["run_file"]).read_text())
        execution = run["machineReadable"]["execution"]
        for case in run["demoCases"]:
            cases.append({
                "id": case["id"],
                "execution": execution,
                "inputs": case["inputs"],
                "expectedOutputs": case["expectedOutputs"],
                "trace": case["trace"],
            })
    engine_dir = outdir / "engine"
    engine_dir.mkdir(parents=True, exist_ok=True)
    (engine_dir / "engine-cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"OK golden set cases={len(cases)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
