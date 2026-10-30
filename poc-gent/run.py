#!/usr/bin/env python3
"""poc-gent CLI — fase 1+2+3: deterministische replay per persona, met
ontvangstbewijs (FR-16), vervolgsamenvatting en statusraadpleging (FR-19-mock).

Voorbeeld: python3 run.py --persona jeroen
Statusraadpleging: python3 run.py --status --persona jeroen
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from core import catalog, pipeline, runs  # noqa: E402


def _transactiestatussen(run: dict) -> list[tuple[dict, str | None]]:
    """Per transactie het ontvangstresultaat; bij niet-ingediend de reden.

    Het run-artefact bevat alleen service-id's (titels staan in het manifest),
    dus de CLI print service-id's — consistent met de transactie-regels in de
    routing-uitvoer. Een per-transactie reden bestaat niet in het artefact:
    bij niet-ingediend nemen we de eerste open-regel uit de vervolgsamenvatting
    (volledige lijst staat onder 'nog te doen')."""
    submission = run["transaction"]["submission"]
    open_regels = submission["vervolgsamenvatting"]["open"]
    statussen: list[tuple[dict, str | None]] = []
    for tr in submission["ontvangst"]["transacties"]:
        if tr["status"] == "niet-ingediend":
            statussen.append((tr, open_regels[0] if open_regels else "geen reden vastgelegd"))
        else:
            statussen.append((tr, None))
    return statussen


def main() -> int:
    ap = argparse.ArgumentParser(description="Gent transactionele assistent — replay fase 1+2+3")
    ap.add_argument("--package", default="gent-mobiliteit-ondernemer")
    ap.add_argument("--persona", default="sanne")
    ap.add_argument("--auth", choices=["eudi", "acmidm"], default="eudi",
                    help="authenticatieroute: EUDI-wallet-mock (standaard) of ACM/IDM-mock")
    ap.add_argument("--status", action="store_true",
                    help="statusraadpleging (FR-19-mock): herhaalt de replay en toont "
                         "per transactie de inzendingsstatus")
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

    try:
        run, events = pipeline.run_replay(POC_ROOT, args.package, args.persona,
                                          auth_methode=args.auth)
    except catalog.PackageError as err:
        print(f"pakketfout: {err}", file=sys.stderr)
        return 2
    try:
        runs.validate(run, POC_ROOT)
    except ImportError:
        print("waarschuwing: jsonschema niet beschikbaar — schema-validatie overgeslagen "
              "(draai onder nldt/.venv voor volledige controle)", file=sys.stderr)
    runs.write_run(POC_ROOT, run, events)

    if args.status:
        print(f"statusraadpleging ({args.persona}):")
        statussen = _transactiestatussen(run)
        if not statussen:
            open_regels = run["transaction"]["submission"]["vervolgsamenvatting"]["open"]
            reden = open_regels[0] if open_regels else "geen aanvragen in dit scenario"
            print(f"  niets ingediend ({reden})")
        for tr, reden in statussen:
            if reden is None:
                print(f"  {tr['service']}: ingediend als {tr['referentie']} · {tr['status']}")
            else:
                print(f"  {tr['service']}: niet ingediend ({reden})")
        return 0

    routing = run["transaction"]["routing"]
    print(f"run:        {run['runId']}")
    print(f"uitkomst:   {routing['outcome']}")
    for sv in routing["paths"]["transactions"]:
        print(f"  transactie: {sv}")
    for sv in routing["paths"]["info"]:
        print(f"  informatie: {sv}")
    for u in routing["uitleg"]:
        print(f"  waarom: {u['tekst']}  [{u['bron']}]")
    status = run["transaction"]["status"]
    print(f"status:     {status}")
    auth = run["transaction"]["auth"]
    if auth["authenticatie"] == "uitgevoerd":
        regel = f"auth:       {auth.get('methode', 'acm-idm')}"
        if "loa" in auth:
            regel += f" (loa {auth['loa']}, onthuld: {', '.join(auth['onthuldeClaims'])})"
        print(regel)
    for uitslag in run["transaction"]["validatie"]["transacties"]:
        for bevinding in uitslag["bevindingen"]:
            print(f"  {bevinding['ernst']}: {bevinding['melding']}")
    if run["transaction"]["auth"]["toestemming"] == "geweigerd":
        print("  gestopt: je gaf geen toestemming om je gegevens op te halen")
    if routing["outcome"] == "escalatie":
        print("  overname: Gentinfo-medewerker (geen regel van toepassing)")
    for tr, reden in _transactiestatussen(run):
        if reden is None:
            print(f"  ontvangst: {tr['service']} → {tr['referentie']} ({tr['status']})")
        else:
            print(f"  ontvangst: {tr['service']} → niet ingediend ({reden})")
    open_regels = run["transaction"]["submission"]["vervolgsamenvatting"]["open"]
    if open_regels:
        print("  nog te doen:")
        for regel in open_regels:
            print(f"    {regel}")
    if run["transaction"]["submission"]["h4"]["verdict"] == "geweigerd":
        print("  gestopt: je bevestigde de inzending niet — er is niets ingediend")
    print(f"events:     {len(events)} (hash-chained, events.jsonl)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
