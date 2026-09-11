#!/usr/bin/env python3
"""PoC-3 Rijnland: peilgebied × peilafwijking H3 conflict (MVP).

Reuses PoC-1 ``geodata`` (ArcGIS fetch/cache) and ``h3step``/``h3report``
(nldt H3 processes + Leaflet heatmap). See
docs/superpowers/specs/2026-09-10-poc3-rijnland-h3-design.md.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POC_ROOT = ROOT.parent / "poc"
for p in (str(ROOT), str(POC_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from rijnland import krw_quality, peil_conflict, water_quality  # noqa: E402
from pipeline import geodata, h3report, h3step  # noqa: E402  — PoC-1

SOURCES_PATH = ROOT / "data" / "sources.json"
CACHE_DIR = ROOT / "data" / "cache"
PEIL_ID = "rijnland-peilgebied-vigerend"
AFWIJK_ID = "rijnland-peilafwijking-praktijk"
MEET_ID = "rijnland-meetpunt-waterkwaliteit-routine"

# Leiden / Haarlemmermeer slice — default demo AOI (full area via --full).
DEFAULT_BBOX = "90000,455000,105000,470000"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None,
                    help="output directory (default: poc-rijnland/runs/<ts>)")
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch geo layers (ignore geo cache)")
    ap.add_argument("--refresh-h3", action="store_true",
                    help="force live nldt H3 re-invocation")
    ap.add_argument("--no-h3", action="store_true",
                    help="skip H3 overlay (polygon headline only)")
    ap.add_argument("--no-krw", action="store_true",
                    help="skip KRW monitoring-coverage overlay (fase 2)")
    ap.add_argument("--no-wq", action="store_true",
                    help="skip gemeten waterkwaliteit overlay (fase 2b)")
    ap.add_argument("--wkp-year", type=int, default=2025,
                    help="year of the WKP measurement fixture (default 2025; "
                         "2026 levert thans slechts 6 metingen)")
    ap.add_argument("--parameter", default="CONCTTE|chloride|mg/l",
                    help="parameter key from the WKP fixture "
                         "(default chloride; bijv. 'VERZDGGD|zuurstof|%%')")
    ap.add_argument("--h3-resolution", type=int, default=8,
                    choices=range(0, 16), metavar="{0..15}",
                    help="H3 resolution for the overlay")
    ap.add_argument("--simplify-m", type=float, default=25.0,
                    help="ArcGIS maxAllowableOffset metres (default 25)")
    ap.add_argument("--bbox", default=DEFAULT_BBOX,
                    help="xmin,ymin,xmax,ymax in EPSG:28992 "
                         f"(default demo slice {DEFAULT_BBOX})")
    ap.add_argument("--full", action="store_true",
                    help="fetch entire Rijnland layers (no bbox filter)")
    ap.add_argument("--timeout", type=int, default=180)
    return ap


def dump_json(path: Path, doc: dict, *, indent: int = 1) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=indent) + "\n",
                    encoding="utf-8")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{ts}-rijnland-peil"
    out_dir = Path(args.out) if args.out else ROOT / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = geodata.load_sources(SOURCES_PATH)
    bbox = None if args.full else args.bbox
    simplify = args.simplify_m if args.simplify_m and args.simplify_m > 0 else None

    print(f"[poc-rijnland] {run_id} -> {out_dir}")
    print(f"[poc-rijnland] bbox={'FULL' if bbox is None else bbox} "
          f"simplify_m={simplify}")

    peil = geodata.fetch_layer(
        PEIL_ID, bbox=bbox, refresh=args.refresh, sources=sources,
        cache_dir=CACHE_DIR, simplify_m=simplify, timeout=args.timeout)
    afwijk = geodata.fetch_layer(
        AFWIJK_ID, bbox=bbox, refresh=args.refresh, sources=sources,
        cache_dir=CACHE_DIR, simplify_m=simplify, timeout=args.timeout)
    meet = None
    if not args.no_krw:
        meet = geodata.fetch_layer(
            MEET_ID, bbox=bbox, refresh=args.refresh, sources=sources,
            cache_dir=CACHE_DIR, timeout=args.timeout)  # points: no simplify

    dump_json(out_dir / "peilgebied.28992.geojson", peil)
    dump_json(out_dir / "peilafwijking.28992.geojson", afwijk)

    report = peil_conflict.empty_report(run_id=run_id)
    report["bbox"] = bbox
    report["sources"] = {
        "peilgebied": PEIL_ID,
        "peilafwijking": AFWIJK_ID,
        "galleryUrl": json.loads(SOURCES_PATH.read_text(encoding="utf-8")).get(
            "galleryUrl"),
    }
    report["featureCounts"] = {
        "peilgebied": len(peil.get("features") or []),
        "peilafwijking": len(afwijk.get("features") or []),
        **({"meetpuntenRoutine": len(meet.get("features") or [])}
           if meet is not None else {}),
    }

    written = [
        "peilgebied.28992.geojson",
        "peilafwijking.28992.geojson",
    ]
    h3_artifact = None
    if not args.no_h3:
        def _h3_call(process_id, inputs):
            return h3step.call(process_id, inputs, refresh=args.refresh_h3)

        try:
            h3_artifact = peil_conflict.attach_peil_h3_overlay(
                report,
                peil_fc_rd=peil,
                afwijk_fc_rd=afwijk,
                resolution=args.h3_resolution,
                call=_h3_call,
            )
        except Exception as exc:  # decision support only
            report.setdefault("degradations", []).append({
                "kind": "h3-error",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"[poc-rijnland] WARNING h3 overlay degraded: {exc}")

    if h3_artifact is not None:
        dump_json(out_dir / "h3-peil-conflict.json", h3_artifact)
        written.append("h3-peil-conflict.json")
        try:
            cells_fc = h3step.call(
                "h3-cells-to-geojson",
                {"cells": [r["cell"] for r in h3_artifact["cells"]]},
                refresh=args.refresh_h3,
            )["features"]
            by_cell = {r["cell"]: r for r in h3_artifact["cells"]}
            for feat in cells_fc["features"]:
                feat["properties"].update(by_cell[feat["properties"]["cell"]])
            (out_dir / "h3-peil-conflict.html").write_text(
                h3report.render_hex_map(
                    cells_fc,
                    title=f"Peil-conflictheatmap Rijnland — {report['id']}",
                    value_property="conflictFraction",
                    value_label="Peilafwijking in peilgebied",
                    zone_label="Aandeel in peilgebied",
                    intro=(
                        "Elke hexagon dekt een stukje van het vigerend peilgebied. "
                        "De kleur laat zien welk deel van die hex ook peilafwijking "
                        "(praktijk) kent — hoe roder, hoe groter het verschil tussen "
                        "formeel peilbesluit en praktijkbeheer."
                    ),
                    legend_intro="Van groen (geen afwijking) naar rood (volledige afwijking):",
                    stops=[
                        (0.0, "Geen afwijking — alleen vigerend peil"),
                        (0.25, "Lichte peilafwijking"),
                        (0.5, "Gedeeld gebied"),
                        (0.75, "Sterke peilafwijking"),
                        (1.0, "Volledig in praktijkafwijking"),
                    ],
                    call=_h3_call,
                ),
                encoding="utf-8",
            )
            written.append("h3-peil-conflict.html")
        except Exception as exc:
            report.setdefault("degradations", []).append({
                "kind": "h3-map-error",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"[poc-rijnland] WARNING hex map degraded: {exc}")

    if h3_artifact is not None and meet is not None and not args.no_krw:
        try:
            krw_artifact = krw_quality.attach_krw_monitoring(
                report,
                peil_cells=h3_artifact["cells"],
                meet_fc_rd=meet,
                resolution=args.h3_resolution,
                call=_h3_call,
            )
            if krw_artifact is not None:
                dump_json(out_dir / "h3-krw-monitoring.json", krw_artifact)
                written.append("h3-krw-monitoring.json")
                try:
                    cells_fc = h3step.call(
                        "h3-cells-to-geojson",
                        {"cells": [r["cell"] for r in krw_artifact["rows"]]},
                        refresh=args.refresh_h3,
                    )["features"]
                    by_cell = {r["cell"]: r for r in krw_artifact["rows"]}
                    for feat in cells_fc["features"]:
                        feat["properties"].update(
                            by_cell[feat["properties"]["cell"]])
                    (out_dir / "h3-krw-blindspots.html").write_text(
                        h3report.render_hex_map(
                            cells_fc,
                            title=f"Peilconflict zonder waterkwaliteitsmonitoring — {report['id']}",
                            value_property="blindSpotScore",
                            value_label="Blinde vlekken",
                            zone_label="Aandeel in peilgebied",
                            intro=(
                                "Rood = cel met peilafwijking-conflict én "
                                "géén routine waterkwaliteits-meetlocatie in "
                                "de cel of de directe buurt: het praktijkpeil "
                                "wijkt daar af zonder dat de waterkwaliteit "
                                "routinematig gemeten wordt. Groen = elders "
                                "in het peilgebied."
                            ),
                            legend_intro=(
                                "Rood: conflict zonder monitoringdekking. "
                                "Groen: gedekt of geen conflict:"
                            ),
                            stops=[
                                (0.0, "Gedekt — monitoring in cel of buurt, of geen conflict"),
                                (0.5, "Conflict, deels ongedekt (score 0.5)"),
                                (1.0, "Conflict, volledig ongedekt (blinde vlek)"),
                            ],
                            call=_h3_call,
                        ),
                        encoding="utf-8",
                    )
                    written.append("h3-krw-blindspots.html")
                except Exception as exc:  # map is a convenience
                    report.setdefault("degradations", []).append({
                        "kind": "krw-map-error",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    print(f"[poc-rijnland] WARNING krw map degraded: {exc}")
        except Exception as exc:  # decision support only
            report.setdefault("degradations", []).append({
                "kind": "krw-error",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"[poc-rijnland] WARNING krw overlay degraded: {exc}")

    if h3_artifact is not None and not args.no_wq:
        wkp_path = ROOT / "data" / "wkp" / f"waterkwaliteit-{args.wkp_year}.json"
        try:
            if not wkp_path.is_file():
                raise FileNotFoundError(
                    f"{wkp_path} — run scripts/fetch_wkp.py --year "
                    f"{args.wkp_year} first")
            fixture = json.loads(wkp_path.read_text(encoding="utf-8"))
            wq_artifact = water_quality.attach_water_quality(
                report,
                fixture=fixture,
                parameter_key=args.parameter,
                peil_cells=h3_artifact["cells"],
                resolution=args.h3_resolution,
                call=_h3_call,
            )
            if wq_artifact is not None:
                dump_json(out_dir / "h3-waterkwaliteit.json", wq_artifact)
                written.append("h3-waterkwaliteit.json")
                try:
                    cells_fc = h3step.call(
                        "h3-cells-to-geojson",
                        {"cells": [r["cell"] for r in wq_artifact["rows"]]},
                        refresh=args.refresh_h3,
                    )["features"]
                    by_cell = {r["cell"]: r for r in wq_artifact["rows"]}
                    for feat in cells_fc["features"]:
                        feat["properties"].update(
                            by_cell[feat["properties"]["cell"]])
                    label = wq_artifact["label"]
                    (out_dir / "h3-waterkwaliteit.html").write_text(
                        h3report.render_hex_map(
                            cells_fc,
                            title=f"{label} in peilgebied — {report['id']}",
                            value_property="value01",
                            value_label=label,
                            zone_label="Aandeel in peilgebied",
                            intro=(
                                "Elke hexagon toont de mediaan van de "
                                f"gemeten {label} (jaar {args.wkp_year}, "
                                "Waterkwaliteitsportaal) over de meetlocaties "
                                "in die cel, geschaald op het P10–P90-bereik "
                                "van alle Rijnland-meetlocaties: hoe roder, "
                                "hoe ongunstiger binnen het eigen gemeten "
                                "bereik. Groen-grijze cellen hebben "
                                "peilafwijking-conflict; zie het JSON-artefact "
                                "voor de combinatie."
                            ),
                            legend_intro=(
                                "Van gunstig (groen) naar ongunstig (rood) "
                                "binnen het eigen gemeten bereik:"
                            ),
                            stops=[
                                (0.0, "Gunstigste kwart van het gemeten bereik"),
                                (0.5, "Midden van het gemeten bereik"),
                                (1.0, "Ongunstigste kwart van het gemeten bereik"),
                            ],
                            call=_h3_call,
                        ),
                        encoding="utf-8",
                    )
                    written.append("h3-waterkwaliteit.html")
                except Exception as exc:  # map is a convenience
                    report.setdefault("degradations", []).append({
                        "kind": "wq-map-error",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    print(f"[poc-rijnland] WARNING wq map degraded: {exc}")
        except Exception as exc:  # decision support only
            report.setdefault("degradations", []).append({
                "kind": "wq-error",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"[poc-rijnland] WARNING waterkwaliteit degraded: {exc}")

    dump_json(out_dir / "peil-conflict-report.json", report)
    md = peil_conflict.conflict_markdown(report)
    (out_dir / "peil-conflict-report.md").write_text(md, encoding="utf-8")
    written += ["peil-conflict-report.json", "peil-conflict-report.md"]

    peil = report.get("peil") or {}
    h = report.get("h3Overlay")
    print("")
    print("=" * 70)
    print(f"POC-3 RIJNLAND {run_id} — verdict: {report['verdict'].upper()}")
    print("=" * 70)
    if peil:
        print(f"  peilgebied     {peil.get('peilgebiedAreaKm2')} km2")
        print(f"  peilafwijking  {peil.get('peilafwijkingAreaKm2')} km2")
        print(f"  overlap        {peil.get('overlapAreaKm2')} km2 "
              f"({peil.get('overlapShareOfPeilPct')}% of peil)")
    if h:
        print(f"  H3             {h['conflictCells']}/{h['cells']} cells, "
              f"weighted {h['weightedConflictSharePct']}%")
    k = report.get("krw")
    if k:
        print(f"  KRW monitoring {k['meetpuntenRoutine']} routine-meetpunten, "
              f"Moran's I {k['moransI']} (p={k['pValue']}); "
              f"{k['blindSpotCells']}/{k['conflictCells']} conflictcellen "
              f"zonder dekking ({k['blindSpotShareOfConflictPct']}%)")
    w = report.get("waterkwaliteit")
    if w:
        print(f"  Waterkwaliteit {w['label']}: {w['locationsInCells']} locaties "
              f"in {w['cellsWithData']} cellen, P10-P90 {w['p10']}-{w['p90']}, "
              f"Moran's I {w['moransI']} (p={w['pValue']})")
    print(f"  artifacts: {', '.join(written)}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
