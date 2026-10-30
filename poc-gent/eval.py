#!/usr/bin/env python3
"""Golden-set evaluatie: routing-uitkomsten per scenario + determinisme
(KPI-01 routingnauwkeurigheid / KPI-02 regelcorrectheid / KPI-04-basis)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from core import catalog, pipeline, runs  # noqa: E402


def evaluate(package_id: str) -> int:
    pkg = catalog.load_package(POC_ROOT, package_id)
    geslaagd = 0
    gefaald: list[str] = []
    for scenario in pkg.golden:
        run, _log = pipeline.run_replay(POC_ROOT, package_id, scenario["persona"],
                                        scenario.get("overrideSlots"))
        routing = run["transaction"]["routing"]
        expect = scenario["expect"]
        ok = (routing["outcome"] == expect["outcome"]
              and routing["paths"]["transactions"] == expect["transactions"]
              and routing["paths"]["info"] == expect["info"])
        print(f"{'OK  ' if ok else 'FAAL'} {scenario['scenarioId']}: "
              f"{routing['outcome']} {routing['paths']['transactions']}")
        if ok:
            geslaagd += 1
        else:
            gefaald.append(scenario["scenarioId"])

    r1, _ = pipeline.run_replay(POC_ROOT, package_id, "sanne")
    r2, _ = pipeline.run_replay(POC_ROOT, package_id, "sanne")
    deterministisch = runs.canonical(r1) == runs.canonical(r2)
    print(f"determinisme: {'OK' if deterministisch else 'FAAL'}")
    print(f"golden: {geslaagd}/{len(pkg.golden)} geslaagd")
    return 0 if (not gefaald and deterministisch) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden-set evaluatie poc-gent")
    ap.add_argument("--package", default="gent-mobiliteit-ondernemer")
    return evaluate(ap.parse_args().package)


if __name__ == "__main__":
    raise SystemExit(main())
