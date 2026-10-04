#!/usr/bin/env python3
"""Plane D — integrale gebiedsafweging boven de Breda vijf-waardenscan.

Leest een baseline value-scan (of herrekent offline uit lagen), past
SpatialClaimSpecs toe (schemas/spatial-claim.schema.json) en schrijft
gebiedsafweging-report.json + .md + .html. Geen LLM in de cijferlijn;
V4 blijft pending (mens beslist).

    # Offline met fixture-lagen (tests / CI):
    nldt/.venv/bin/python poc-breda/afweging_run.py --offline-fixtures

    # Op een bestaande scan-run (cache-first lagen):
    nldt/.venv/bin/python poc-breda/afweging_run.py \\
        --run poc-breda/runs/<ts>-breda-scan \\
        --claims poc-breda/claims/demo-breda.json

Exit 0 bij verdict pass|needs_human; 1 bij fail.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POC_ROOT = ROOT.parent / "poc"
for p in (str(POC_ROOT), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from breda import claims, fetch, indicators  # noqa: E402
from breda import values as value_model  # noqa: E402

DEFAULT_CLAIMS = ROOT / "claims" / "demo-breda.json"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _baseline_from_layers(layers: dict) -> dict:
    computed = indicators.compute_scan(layers)
    values_out = {}
    for key, spec in value_model.VALUES.items():
        values_out[key] = {
            "label": spec["label"],
            "description": spec["description"],
            "quote": spec.get("quote"),
            "programmeItems": spec["programmeItems"],
            "formula": spec.get("formula"),
        }
    values_out["autonomous"]["manifest"] = value_model.SOVEREIGNTY_CRITERIA
    return {
        "scan": {
            "scanId": "breda-vijf-waardenscan",
            "generatedAt": _now_iso(),
            "gemeente": "Breda",
            "gemeenteCode": "GM0758",
            "congress": value_model.CONGRESS,
        },
        "sources": [],
        "values": values_out,
        "buurten": computed["buurten"],
        "rollup": computed["rollup"],
    }


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=None,
                    help="baseline run dir met value-scan.json")
    ap.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS,
                    help="claims-set JSON")
    ap.add_argument("--offline-fixtures", action="store_true",
                    help="gebruik synthetische test-lagen (geen netwerk/cache)")
    ap.add_argument("--out", type=Path, default=None,
                    help="output dir (default: poc-breda/afweging-runs/<ts>-breda-afw)")
    args = ap.parse_args(argv)

    claim_specs = claims.load_claims_file(args.claims)

    if args.offline_fixtures:
        from tests import fixtures  # noqa: WPS433 — alleen offline pad

        layers = fixtures.layers_dict()
        baseline = _baseline_from_layers(layers)
        baseline_source = "offline-fixtures"
    else:
        if args.run is None:
            print("FATAL: --run <dir> of --offline-fixtures vereist", file=sys.stderr)
            return 2
        baseline = json.loads(
            (args.run / "value-scan.json").read_text(encoding="utf-8")
        )
        fetched = fetch.fetch_all(include_bomen=True)
        layers = fetched["layers"]
        if layers.get("buurten") is None:
            print(
                "FATAL: CBS-buurten ontbreken (lege cache? run poc-breda/run.py)",
                file=sys.stderr,
            )
            return 2
        baseline_source = args.run.name

    report = claims.run_afweging(
        baseline,
        layers,
        claim_specs,
        baseline_source=baseline_source,
        generated_at=_now_iso(),
    )
    schema_errs = claims.validate_report(report)
    if schema_errs:
        print(f"FATAL: report schema: {schema_errs[0]}", file=sys.stderr)
        return 2

    out_dir = args.out or (
        ROOT
        / "afweging-runs"
        / f"{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-breda-afw"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / "gebiedsafweging-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (out_dir / "gebiedsafweging-report.md").write_text(
        claims.build_report_md(report), encoding="utf-8"
    )
    (out_dir / "gebiedsafweging.html").write_text(
        claims.build_report_html(report), encoding="utf-8"
    )

    summary = {
        "runId": out_dir.name,
        "generatedAt": report["generatedAt"],
        "verdict": report["validation"]["verdict"],
        "nClaims": len(report["claims"]),
        "nAccepted": sum(1 for c in report["claims"] if not c.get("rejected")),
        "baselineSource": baseline_source,
        "artifacts": {
            name: {"sha256": _sha256(out_dir / name)}
            for name in (
                "gebiedsafweging-report.json",
                "gebiedsafweging-report.md",
                "gebiedsafweging.html",
            )
        },
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"Run: {out_dir}")
    print(f"  verdict: {summary['verdict']}")
    print(f"  claims: {summary['nAccepted']}/{summary['nClaims']} accepted")
    for c in report["claims"]:
        status = "reject" if c.get("rejected") else "ok"
        print(f"    [{status}] {c.get('claimId')} ({c.get('kind')})")
    print(f"  HTML: {out_dir / 'gebiedsafweging.html'}")

    return 0 if summary["verdict"] in ("pass", "needs_human") else 1


if __name__ == "__main__":
    raise SystemExit(run())
