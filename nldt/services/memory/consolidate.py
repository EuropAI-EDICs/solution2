"""Consolidatie: observaties → decision trails (idempotent) + afhandelacties.

    python -m services.memory.consolidate                          # nieuwe observaties → trails
    python -m services.memory.consolidate --handle dt-xxxx --note "…"
    python -m services.memory.consolidate --promote dt-xxxx --level organisatie
"""
from __future__ import annotations

import argparse

from services.memory.observations import collect_observations, to_trail
from services.memory.store import append_trails, update_trail


def consolidate() -> int:
    trails = [to_trail(o) for o in collect_observations()]
    written = append_trails(trails)
    print(f"{len(trails)} observatie(n), {written} nieuwe trail-record(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="services.memory.consolidate")
    parser.add_argument("--handle", metavar="TRAIL_ID", help="trail afhandelen (status → handled)")
    parser.add_argument("--note", metavar="NOTE", help="didItHelp-waarde bij --handle")
    parser.add_argument("--promote", metavar="TRAIL_ID", help="trail promoten naar hoger leerniveau")
    parser.add_argument("--level", choices=["organisatie", "institutioneel"], help="doel-niveau bij --promote")
    args = parser.parse_args(argv)

    if args.handle:
        if not args.note:
            parser.error("--handle vereist --note")
        updated = update_trail(args.handle, status="handled", did_it_help=args.note)
        if updated is None:
            print(f"trail {args.handle} niet gevonden")
            return 1
        print(f"handled: {updated['trailId']} → didItHelp: {updated['didItHelp']}")
        return 0

    if args.promote:
        if not args.level:
            parser.error("--promote vereist --level")
        updated = update_trail(args.promote, learning_level=args.level)
        if updated is None:
            print(f"trail {args.promote} niet gevonden")
            return 1
        print(f"promoted: {updated['trailId']} → {updated['learningLevel']}")
        return 0

    return consolidate()


if __name__ == "__main__":
    raise SystemExit(main())
