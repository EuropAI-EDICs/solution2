#!/usr/bin/env python3
"""poc-gent CLI — F1: deterministische replay per persona.

Voorbeeld: python3 run.py --persona jeroen
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from core import pipeline, runs  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Gent transactionele assistent — F1 replay")
    ap.add_argument("--package", default="gent-mobiliteit-ondernemer")
    ap.add_argument("--persona", default="sanne")
    ap.add_argument("--list-personas", action="store_true")
    args = ap.parse_args()

    personas = pipeline.load_personas(POC_ROOT)
    if args.list_personas:
        for pid, p in personas.items():
            regel = f"{pid}: {p['label']['nl']}"
            if p.get("edge"):
                regel += f"  [edge: {p['edge']}]"
            print(regel)
        return 0
    if args.persona not in personas:
        print(f"onbekende persona: {args.persona} (probeer --list-personas)", file=sys.stderr)
        return 2

    run, events = pipeline.run_replay(POC_ROOT, args.package, args.persona)
    try:
        runs.validate(run, POC_ROOT)
    except ImportError:
        print("waarschuwing: jsonschema niet beschikbaar — schema-validatie overgeslagen "
              "(draai onder nldt/.venv voor volledige controle)")
    runs.write_run(POC_ROOT, run, events)

    routing = run["transaction"]["routing"]
    print(f"run:        {run['runId']}")
    print(f"uitkomst:   {routing['outcome']}")
    for sv in routing["paths"]["transactions"]:
        print(f"  transactie: {sv}")
    for sv in routing["paths"]["info"]:
        print(f"  informatie: {sv}")
    for u in routing["uitleg"]:
        print(f"  waarom: {u['tekst']}  [{u['bron']}]")
    if routing["outcome"] == "escalatie":
        print("  overname: Gentinfo-medewerker (geen regel van toepassing)")
    print(f"events:     {len(events)} (hash-chained, events.jsonl)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
