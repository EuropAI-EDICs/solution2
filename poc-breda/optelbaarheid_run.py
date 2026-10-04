#!/usr/bin/env python3
"""ZN-2 — optelbaarheid over twee gebieden.

Modi:
  --offline-fixtures   twee synthetische gemeenten (CI, geen netwerk)
  --live A,B           live CBS PDOK voor genoemde gemeenten (parity: CBS-only)

Voorbeeld live tweede gemeente (Tilburg naast Breda):

    nldt/.venv/bin/python poc-breda/optelbaarheid_run.py --live Breda,Tilburg
    nldt/.venv/bin/python poc-breda/optelbaarheid_run.py --live Breda,Tilburg --refresh

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

from breda import fetch, optelbaarheid  # noqa: E402

# Bekende spellings (CBS 2024 gemeentenaam). Onbekende namen worden 1:1
# doorgestuurd naar de WFS-filter — typfout → FetchError met 0 features.
DEFAULT_LIVE = "Breda,Tilburg"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_gemeenten(raw: str) -> list[str]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) < 2:
        raise SystemExit("--live vereist minstens twee gemeenten (bv. Breda,Tilburg)")
    return parts


def _load_offline_specs():
    from tests import fixtures  # noqa: WPS433

    base = fixtures.layers_dict()
    city_a = (
        "city-a-breda-fixture",
        base,
        {
            "areaId": "city-a-breda-fixture",
            "gemeente": "Breda",
            "gemeenteCode": "GM0758",
        },
    )
    pack = optelbaarheid.second_city_layers(
        base, gemeente="DemoStad", code="city-b-demo", gm="GM0999"
    )
    city_b = (
        pack["meta"]["areaId"],
        pack["layers"],
        pack["meta"],
    )
    return [city_a, city_b], "offline-fixtures"


def _load_live_specs(gemeenten: list[str], *, refresh: bool):
    specs = []
    for naam in gemeenten:
        print(f"  fetch CBS: {naam} …")
        pack = fetch.fetch_cbs_area_layers(naam, refresh=refresh)
        meta = pack["meta"]
        n = meta.get("nFeatures")
        print(f"    → {meta['gemeenteCode']} · {n} buurten · {meta['sourceId']}")
        specs.append((meta["areaId"], pack["layers"], meta))
    return specs, "live-cbs:" + ",".join(gemeenten)


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--offline-fixtures",
        action="store_true",
        help="twee synthetische gemeenten (standaard als --live ontbreekt)",
    )
    mode.add_argument(
        "--live",
        metavar="G1,G2",
        nargs="?",
        const=DEFAULT_LIVE,
        help=f"live CBS voor gemeenten (default: {DEFAULT_LIVE})",
    )
    ap.add_argument(
        "--refresh",
        action="store_true",
        help="negeer CBS-cache (alleen zinvol met --live)",
    )
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.live:
        specs, source = _load_live_specs(_parse_gemeenten(args.live), refresh=args.refresh)
    else:
        specs, source = _load_offline_specs()

    report = optelbaarheid.run_optelbaarheid(specs, generated_at=_now_iso())
    report["baselineMode"] = source
    errs = optelbaarheid.validate_report(report)
    if errs:
        print(f"FATAL: schema: {errs[0]}", file=sys.stderr)
        return 2

    tag = "zn2-live" if args.live else "zn2"
    out_dir = args.out or (
        ROOT
        / "optelbaarheid-runs"
        / f"{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{tag}"
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
        "mode": source,
        "verdict": report["validation"]["verdict"],
        "definitionsIdentical": report["definitions"]["identical"],
        "formulaFingerprint": report["definitions"]["formulaFingerprint"],
        "nAreas": report["combined"]["nAreas"],
        "areas": [
            {
                "gemeente": a["gemeente"],
                "gemeenteCode": a["gemeenteCode"],
                "nLandBuurten": a["nLandBuurten"],
            }
            for a in report["areas"]
        ],
        "artifacts": {
            name: {"sha256": _sha256(out_dir / name)}
            for name in ("optelbaarheid-report.json", "optelbaarheid-report.md")
        },
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"Run: {out_dir}")
    print(f"  mode: {source}")
    print(f"  verdict: {summary['verdict']}")
    print(f"  identical: {summary['definitionsIdentical']}")
    print(f"  fingerprint: {summary['formulaFingerprint']}")
    for a in report["areas"]:
        abs_eco = (a.get("absoluteMeans") or {}).get("onbenut_dakpotentieel")
        print(
            f"    · {a['gemeente']} ({a['gemeenteCode']}): "
            f"n={a['nLandBuurten']} abs_dak={abs_eco}"
        )
    print(
        "  combined abs_dak:",
        (report["combined"].get("absoluteMeans") or {}).get("onbenut_dakpotentieel"),
    )
    return 0 if summary["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())
