#!/usr/bin/env python3
"""ZN-2 — optelbaarheid over twee gebieden (offline fixtures MVP).

Draait dezelfde Breda-indicatorformules op twee synthetische gemeenten
en schrijft een optelbaarheid-report (gewogen combined means).

    nldt/.venv/bin/python poc-breda/optelbaarheid_run.py --offline-fixtures

Exit 0 bij verdict pass.
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

from breda import optelbaarheid  # noqa: E402


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--offline-fixtures",
        action="store_true",
        default=True,
        help="twee synthetische gemeenten (standaard)",
    )
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    from tests import fixtures  # noqa: WPS433

    base = fixtures.layers_dict()
    city_a = {
        "layers": base,
        "meta": {
            "areaId": "city-a-breda-fixture",
            "gemeente": "Breda",
            "gemeenteCode": "GM0758",
        },
    }
    city_b_pack = optelbaarheid.second_city_layers(
        base, gemeente="DemoStad", code="city-b-demo", gm="GM0999"
    )

    report = optelbaarheid.run_optelbaarheid(
        [
            (city_a["meta"]["areaId"], city_a["layers"], city_a["meta"]),
            (
                city_b_pack["meta"]["areaId"],
                city_b_pack["layers"],
                city_b_pack["meta"],
            ),
        ],
        generated_at=_now_iso(),
    )
    errs = optelbaarheid.validate_report(report)
    if errs:
        print(f"FATAL: schema: {errs[0]}", file=sys.stderr)
        return 2

    out_dir = args.out or (
        ROOT
        / "optelbaarheid-runs"
        / f"{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-zn2"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "optelbaarheid-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (out_dir / "optelbaarheid-report.md").write_text(
        optelbaarheid.build_report_md(report), encoding="utf-8"
    )
    summary = {
        "runId": out_dir.name,
        "generatedAt": report["generatedAt"],
        "verdict": report["validation"]["verdict"],
        "definitionsIdentical": report["definitions"]["identical"],
        "formulaFingerprint": report["definitions"]["formulaFingerprint"],
        "nAreas": report["combined"]["nAreas"],
        "artifacts": {
            name: {"sha256": _sha256(out_dir / name)}
            for name in ("optelbaarheid-report.json", "optelbaarheid-report.md")
        },
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"Run: {out_dir}")
    print(f"  verdict: {summary['verdict']}")
    print(f"  identical: {summary['definitionsIdentical']}")
    print(f"  fingerprint: {summary['formulaFingerprint']}")
    for a in report["areas"]:
        print(
            f"    · {a['gemeente']} ({a['gemeenteCode']}): "
            f"n={a['nLandBuurten']} eco={a['means']['economic']}"
        )
    print(f"  combined eco: {report['combined']['means']['economic']}")
    return 0 if summary["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())
