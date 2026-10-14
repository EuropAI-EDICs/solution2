"""Grensvergelijkende merge + rapport (spec §4.4).

``load_run`` mapt de task-9-runvorm naar merge-invoer. Mapping (gebaseerd op
de echte smoke-runs onder ``runs/<ts>-<track>-<land>/``):

- ``zones.json`` is géén FeatureCollection maar een lijst zone-records
  (``{id, jurisdictie, operation, geometry: {format, payload, crs},
  geometryValid, areaKm2, provenance, ...}``). Elk record wordt één Feature:
  ``geometry`` = ``geometry.payload`` (alleen bij ``format == "GeoJSON"``,
  anders ``null``), ``properties`` = alle overige velden van het record.
- ``decision-table.json`` is ``{id, title, columns, rows}``; ``rows`` wordt
  ``decisionRows`` (dicts per kolomnaam, bv. ``ruleId``, ``norm``,
  ``zone effect``).
- ``land``: de unieke ``jurisdictie`` uit de zone-records; bij lege/afwijkende
  zones valt het terug op het ``-nl``/``-be``-achtervoegsel van de
  directorynaam.

Zie ook ``python -m pipeline.xborder --help`` om twee bestaande runs te
combineren.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

_STDAARDEN = ("nl", "be")


def load_run(out_dir: Path) -> dict:
    """Lees één task-9-run-directory (zones.json + decision-table.json).

    Zie de module-docstring voor de zones.json → FeatureCollection-mapping.
    """
    out_dir = Path(out_dir)
    records = json.loads((out_dir / "zones.json").read_text(encoding="utf-8"))
    if isinstance(records, dict) and records.get("type") == "FeatureCollection":
        features = list(records.get("features", []))
        jurisdicties = {f.get("properties", {}).get("jurisdictie") for f in features} - {None}
    else:
        features = []
        jurisdicties: set[str] = set()
        for record in records:
            geom = record.get("geometry") or {}
            payload = geom.get("payload") if geom.get("format") == "GeoJSON" else None
            props = {k: v for k, v in record.items() if k != "geometry"}
            features.append({"type": "Feature", "properties": props, "geometry": payload})
            if record.get("jurisdictie"):
                jurisdicties.add(record["jurisdictie"])
    land = _bepaal_land(jurisdicties, out_dir)
    decision_table = json.loads((out_dir / "decision-table.json").read_text(encoding="utf-8"))
    return {"land": land, "zones": {"type": "FeatureCollection", "features": features},
            "decisionRows": list(decision_table.get("rows", []))}


def _bepaal_land(jurisdicties: set[str], out_dir: Path) -> str:
    if len(jurisdicties) == 1:
        return jurisdicties.pop()
    for standaard in _STDAARDEN:
        if out_dir.name.endswith(f"-{standaard}"):
            return standaard
    raise ValueError(
        f"Kan land niet bepalen voor {out_dir}: jurisdicties={sorted(jurisdicties) or 'leeg'} "
        f"en directorynaam eindigt niet op -{' of -'.join(_STDAARDEN)}")


def merge_xborder(nl_run: Mapping[str, Any], be_run: Mapping[str, Any], *, track: str) -> dict:
    zones = {"type": "FeatureCollection", "features": []}
    rijen: list[dict] = []
    for run in (nl_run, be_run):
        land = run["land"]
        fc = run.get("zones") or {"type": "FeatureCollection", "features": []}
        for feat in fc.get("features", []):
            props = dict(feat.get("properties", {}))
            props["land"] = land
            zones["features"].append({**feat, "properties": props})
        for rij in run.get("decisionRows", []):
            rijen.append({**rij, "land": land})
    return {"track": track, "zones": zones, "decisionRows": rijen}


def write_xborder_report(out_dir: Path, merged: Mapping[str, Any], *, track: str) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    geo_path = out_dir / f"zones-{track}-nspd.geojson"
    geo_path.write_text(json.dumps(merged["zones"], ensure_ascii=False), encoding="utf-8")
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
    html = env.get_template("xborder-report.html.j2").render(
        track=track, rows=merged["decisionRows"], geojsonName=geo_path.name)
    pad = out_dir / "report-xborder.html"
    pad.write_text(html, encoding="utf-8")
    return pad


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Grensvergelijkende merge + rapport (spec §4.4)")
    parser.add_argument("nl_run", type=Path, help="run-directory Nederland (bv. runs/<ts>-wind-nl)")
    parser.add_argument("be_run", type=Path, help="run-directory Vlaanderen (bv. runs/<ts>-wind-be)")
    parser.add_argument("out_dir", type=Path, help="uitvoerdirectory voor het xborder-artefact")
    parser.add_argument("--track", default="xborder", help="tracknaam voor bestandsnamen/titel")
    args = parser.parse_args()
    _merged = merge_xborder(load_run(args.nl_run), load_run(args.be_run), track=args.track)
    print(write_xborder_report(args.out_dir, _merged, track=args.track))
    sys.exit(0)
