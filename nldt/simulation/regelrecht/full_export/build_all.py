#!/usr/bin/env python3
"""Orkestratie: split → align → formalize → YAML+report → demo."""
from __future__ import annotations

import argparse
import json
import sys

import paths
from align_evidence import align
from build_full_demo import build_demo
from formalize_to_rr import formalize
from split_cvdr_html import split_instrument, write_articles_json
from write_instrument_yaml import write_instrument_yaml


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stamp", required=True, help="ISO-timestamp voor generatedAt")
    args = ap.parse_args(argv)

    paths.OUT.mkdir(parents=True, exist_ok=True)
    for poc in ("utrecht", "eindhoven"):
        arts = split_instrument(poc)
        write_articles_json(poc, arts, paths.OUT / f"{poc}-articles.json")
        al, orphans = align(poc, arts)
        form, report = formalize(poc, arts, al, orphans, stamp=args.stamp)
        write_instrument_yaml(poc, arts, form, stamp=args.stamp, report=report)
        print(
            f"OK {poc}: articles={len(arts)} "
            f"formalized={report['counts']['formalized']} "
            f"ambiguous={report['counts']['ambiguous']} "
            f"unmatched={report['counts']['unmatched']} "
            f"rejected={report['counts']['rejected']}"
        )
    build_demo(stamp=args.stamp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
