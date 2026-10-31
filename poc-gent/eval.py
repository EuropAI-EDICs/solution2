#!/usr/bin/env python3
"""Golden-set evaluatie + KPI-harness (F4): routing-uitkomsten per scenario,
determinisme (KPI-01/02/04-basis) en het go/no-go-rapport met drempels uit de
function-baseline (KPI-01/02/03/04/06, H-event-controle; ontwerp §8.1/§8.3)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from core import catalog, kpis, pipeline, runs  # noqa: E402


def evaluate(package_id: str, rapport_pad: str | None = None) -> int:
    pkg = catalog.load_package(POC_ROOT, package_id)
    passed = 0
    failed: list[str] = []
    golden_runs: list[tuple[dict, list, dict]] = []
    for scenario in pkg.golden:
        run, log = pipeline.run_replay(POC_ROOT, package_id, scenario["persona"],
                                        scenario.get("overrideSlots"))
        golden_runs.append((run, log, scenario["expect"]))
        routing = run["transaction"]["routing"]
        expect = scenario["expect"]
        ok = (routing["outcome"] == expect["outcome"]
              and routing["paths"]["transactions"] == expect["transactions"]
              and routing["paths"]["info"] == expect["info"]
              and run["transaction"]["status"] == expect.get("status", "gereed"))
        print(f"{'OK  ' if ok else 'FAAL'} {scenario['scenarioId']}: "
              f"{routing['outcome']} {routing['paths']['transactions']} "
              f"[status {run['transaction']['status']}]")
        if not ok:
            print(f"  verwachte status: {expect.get('status', 'gereed')}")
        if ok:
            passed += 1
        else:
            failed.append(scenario["scenarioId"])

    first_persona = pkg.golden[0]["persona"]
    r1, _ = pipeline.run_replay(POC_ROOT, package_id, first_persona)
    r2, _ = pipeline.run_replay(POC_ROOT, package_id, first_persona)
    deterministic = runs.canonical(r1) == runs.canonical(r2)
    print(f"determinisme: {'OK' if deterministic else 'FAAL'}")
    print(f"golden: {passed}/{len(pkg.golden)} geslaagd")
    if failed:
        print("gefaald: " + ", ".join(failed))

    rapport = kpis.rapport(golden_runs, pkg.manifest)
    for naam, info in rapport["kpis"].items():
        if naam == "KPI-06":
            regel = (f"KPI-06 once-only (retourvragen): {info['authentieke_slot_vragen']} vragen "
                     f"om authentieke slots, {info['vragen_totaal']} vragen totaal")
        elif naam == "H-events":
            regel = f"H-events: {info['correct']}/{info['totaal']} correct gelogd ({info['waarde']}%)"
        else:
            doel = f", doel {info['doel']}" if "doel" in info else ""
            regel = f"{naam}: {info['waarde']}% — drempel {info['drempel']}{doel}"
        print(f"{regel} [{'OK' if info['ok'] else 'FAAL'}]")
    for bevinding in rapport["belemmeringen"]:
        print(f"  belemmering: {bevinding}")
    print(f"go/no-go: {rapport['goNoGo']}")
    if rapport_pad:
        pad = Path(rapport_pad)
        pad.parent.mkdir(parents=True, exist_ok=True)
        pad.write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"rapport:   {pad}")
    return 0 if (not failed and deterministic and rapport["goNoGo"] == "GO") else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden-set evaluatie poc-gent")
    ap.add_argument("--package", default="gent-mobiliteit-ondernemer")
    ap.add_argument("--rapport", metavar="PAD", help="schrijf het KPI/go-no-go-rapport als JSON naar dit pad")
    return evaluate(ap.parse_args().package, ap.parse_args().rapport)


if __name__ == "__main__":
    raise SystemExit(main())
