#!/usr/bin/env python3
"""Literature indicator references from the shared planning_indicators dataset.

Pulls the reference indicators of the *Urban Indicators Dataset: Drinking
Water, Urban Heat, and Housing Provision* (Cardenas-Leon et al., ITC Twente,
v1.2, CC BY-NC-SA 4.0 — vendored globally under ``planning_indicators/``) for
one planning sector and writes them as a provenance-rich JSON artifact next to
the 74-item Omgevingsanalyse Lijst: each indicator with its definition, units,
calculation, system part and the literature it was extracted from.

This tool is a *reference lens*, additive-only: it reads nothing from and
writes nothing into the canonical MiniGIM run artifacts (29/74 delivered etc.
stay untouched), and it is pure stdlib + the global package — offline, no
LLM in the decision line. Dataset provenance (citation, DOI, version, upstream
commit, license, sha256 per vendored CSV) is embedded in every artifact,
because CC BY-NC-SA requires attribution on redistribution.

Usage:
    python3 poc-minigim/tools/indicator_refs.py --sector heat \
        [--query "urban heat"] [--out poc-minigim/runs/indicator-refs]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import planning_indicators as pi  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "poc-minigim" / "runs" / "indicator-refs"

# CSV's die de indicator+literatuur-join raadpleegt (prov: sha256 per bestand).
USED_TABLES = (
    "indicators",
    "objective",
    "topic",
    "planning_sector",
    "system_parts",
    "main_table",
    "paper",
)


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "alle"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(sector, query=None):
    """Bouw de indicator-referentielens voor één sector (puur, deterministisch).

    sector: 'water' | 'heat' | 'housing' (planning_indicators.SECTORS).
    query:  optionele case-insensitive substring over naam+definitie.
    """
    sector_key = sector.lower()
    if sector_key not in pi.SECTORS:
        raise SystemExit(f"--sector moet één van {sorted(pi.SECTORS)} zijn")

    hits = pi.search(query, sector=sector_key) if query else [
        ind for ind in pi.indicators() if ind["sector_id"] == pi.SECTORS[sector_key]
    ]
    hits.sort(key=lambda ind: (ind["name"] or "").lower())

    papers = {pi.as_int(row["ID"]): row for row in pi.load_table("paper")}
    links = {}
    for link in pi.indicator_papers():
        links.setdefault(link["indicator_id"], []).append(link["paper_id"])

    indicators = []
    for ind in hits:
        refs = []
        for paper_id in sorted(links.get(ind["id"], [])):
            row = papers.get(paper_id)
            if row is None:
                continue
            refs.append(
                {
                    "id": paper_id,
                    "zoteroId": row["ZoteroID"],
                    "title": pi.strip_html(row["Title"]),
                    "year": pi.as_int(row["Year"]),
                    "country": row["Country"],
                }
            )
        indicators.append(
            {
                "id": ind["id"],
                "name": ind["name"],
                "definition": ind["definition"],
                "units": ind["units"],
                "calculation": ind["calculation"],
                "systemPart": ind["system_part"],
                "objective": ind["objective"],
                "topic": ind["topic"],
                "papers": sorted(refs, key=lambda p: (p["year"] or 0, (p["title"] or "").lower())),
            }
        )

    dataset_files = {}
    for name in USED_TABLES:
        path = pi.DATASET_DIR / pi.TABLES[name]
        dataset_files[name] = {
            "file": str(path.relative_to(REPO_ROOT)),
            "sha256": _sha256(path),
            "rows": len(pi.load_table(name)),
        }

    return {
        "artifact": "minigim-indicator-refs",
        "sector": {"key": sector_key, "id": pi.SECTORS[sector_key]},
        "query": query,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": {
            "title": pi.TITLE,
            "authors": list(pi.AUTHORS),
            "version": pi.VERSION,
            "sourceUrl": pi.SOURCE_URL,
            "upstreamCommit": pi.UPSTREAM_COMMIT,
            "doi": pi.DOI,
            "license": pi.LICENSE,
            "licenseUrl": pi.LICENSE_URL,
            "citation": pi.CITATION,
            "files": dataset_files,
        },
        "count": len(indicators),
        "indicators": indicators,
    }


def write_artifact(payload, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"indicator-refs-{payload['sector']['key']}"
    if payload["query"]:
        stem += f"-{_slug(payload['query'])}"
    path = out_dir / f"{stem}.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sector", required=True, help="water | heat | housing")
    parser.add_argument("--query", default=None, help="filter op naam/definitie (substring)")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="uitvoermap (default runs/indicator-refs)")
    args = parser.parse_args(argv)

    payload = collect(args.sector, args.query)
    path = write_artifact(payload, Path(args.out))
    print(f"{path}  ({payload['count']} indicatoren, sector={args.sector}, dataset v{pi.VERSION})")
    problems = pi.validate()
    if problems:
        print("WAARSCHUWING — dataset-integriteit:", problems, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
