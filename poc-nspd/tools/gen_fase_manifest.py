#!/usr/bin/env python3
"""Genereert poc-nspd/fase-manifest.json uit NSPD's eigen registers.

De matrix is declaratief: het corpus (normcards/formal-rules per land×track)
is leidend; de generator knoopt het aan de vijf fase-archetypen en raakt de
engine niet aan. Deterministisch; elke run schrijft dezelfde bytes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT.parent / "poc-fundament"))  # brug-conventie: append, nooit insert


def _paren(prefix: str) -> list[str]:
    """Gesorteerde '<land>-<track>'-paren uit corpus/<prefix>-<land>-<track>.json
    (rejected-varianten vallen buiten het patroon)."""
    return sorted(p.stem[len(prefix) + 1:]
                  for p in (ROOT / "corpus").glob(f"{prefix}-*.json")
                  if "rejected" not in p.name)


def _track_land(paar: str) -> str:
    land, track = paar.split("-", 1)
    return f"{track}-{land}"


def build() -> dict:
    norm = _paren("normcards")
    rules = _paren("formal-rules")
    if norm != rules:
        raise SystemExit(f"corpus-asymmetrie normcards/formal-rules: {set(norm) ^ set(rules)}")
    f1 = [{"id": f"normcards-{paar}", "from": "register:nspd-corpus", "binding": "auto",
           "tool": {"class": "retrieval", "ref": f"corpus:normcards-{paar}",
                    "transport": "in-process", "derive": ["cite-or-abstain"]}}
          for paar in norm]
    f2 = [{"id": f"formal-rules-{paar}", "from": "register:nspd-corpus", "binding": "auto",
           "tool": {"class": "computation", "ref": f"corpus:formal-rules-{paar}",
                    "transport": "in-process", "derive": ["v2b-jurisdictie-gate"]}}
          for paar in rules]
    f3 = [{"id": f"zones-{_track_land(paar)}", "from": "register:nspd-bronnen", "binding": "auto",
           "tool": {"class": "computation", "ref": "run:nspd-zone-engine",
                    "transport": "in-process", "derive": ["zone-algebra", "fr-aoi-01"]}}
          for paar in rules]
    return {
        "poc": "nspd-tracks",
        "methodiek": "nspd-tracks-v2.0",
        "aoi": {"schema": "geojson", "crs": "EPSG:28992"},
        "phases": [
            {"id": "F0-intake", "title": "Intake/scoping (use-case + AOI)",
             "agent": {"role": "intake"},
             "tasks": [{"id": "use-case-aoi", "from": "use-cases:make_aoi", "binding": "auto",
                        "tool": {"class": "validation", "ref": "use-cases:make_aoi",
                                 "transport": "in-process"}}],
             "gate": {"validate": ["V0"]}},
            {"id": "F1-normanalyse", "title": "Normanalyse (cite-or-abstain)",
             "agent": {"role": "normspecialist"}, "tasks": f1,
             "gate": {"validate": ["V0", "V2"], "onFail": "cite-or-abstain"}},
            {"id": "F2-formalisering", "title": "Formalisering (FormalRules, V2b-gate)",
             "agent": {"role": "formalizer"}, "tasks": f2,
             "gate": {"validate": ["V2"], "onFail": "formal-rule geweigerd (ledger)"}},
            {"id": "F3-geodoorrekening", "title": "Geodoorrekening (zone-algebra, cache-first)",
             "agent": {"role": "geospecialist"}, "tasks": f3,
             "gate": {"validate": ["V1", "V3"]}},
            {"id": "F4-synthese", "title": "Synthese & rapport (xborder-merge, Leia)",
             "agent": {"role": "critic + explainer"},
             "tasks": [
                 {"id": "v0-v3-verdict", "from": "run-input", "binding": "auto",
                  "tool": {"class": "validation", "ref": "fundament:validate",
                           "transport": "in-process"}},
                 {"id": "xborder-merge", "from": "pipeline:xborder", "binding": "auto",
                  "tool": {"class": "computation", "ref": "pipeline:xborder",
                           "transport": "in-process"}},
                 {"id": "rapport", "from": "run-input", "binding": "auto",
                  "tool": {"class": "report", "ref": "nspd:report", "transport": "in-process"}}],
             "gate": {"validate": ["V0", "V1", "V2", "V3"], "hitl": "v4 (mens) pending"}},
        ],
    }


def main() -> None:
    manifest = build()
    out = ROOT / "fase-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(len(p.get("tasks") or []) for p in manifest["phases"])
    print(f"fase-manifest: {len(manifest['phases'])} fasen, {n} taken → {out}")


if __name__ == "__main__":
    main()
