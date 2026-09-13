#!/usr/bin/env python3
"""PoC-4 Breda: vijf-waardenscan — AI in the City 2026 (indestad.ai).

Per buurt van gemeente Breda vier percentielscores (democratisch, ruimtelijk,
economisch, sociaal) plus een aantoonbaar soevereiniteitsmanifest (autonoom),
gegrond in CBS 2024-buurtstatistiek (PDOK WFS) en de open lagen van de gemeente
Breda (data.breda.nl / geo.breda.nl). Zie
docs/superpowers/specs/2026-09-13-poc4-breda-five-value-scan-design.md.

Deterministisch, cache-first (her-run offline), geen API-sleutels, geen LLM at
runtime. Exit 0 alleen bij validatorverdict ``pass``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POC_ROOT = ROOT.parent / "poc"
for p in (str(POC_ROOT), str(ROOT)):  # ROOT laatst -> index 0 (poc/run.py schaduwt niet)
    if p not in sys.path:
        sys.path.insert(0, p)

from breda import fetch, indicators, report, validate  # noqa: E402
from breda import values as value_model  # noqa: E402
from pipeline import geodata  # noqa: E402  — PoC-1


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sources_table(layers: dict, sources_registry: dict) -> list[dict]:
    """Brontabel voor het scan-artifact: registry + live fetchprovenance."""
    reg_by_id = {s["id"]: s for s in sources_registry["sources"]}
    rows = [dict(
        id=sources_registry["cbsWfs"]["id"],
        title=sources_registry["cbsWfs"]["title"],
        url=sources_registry["cbsWfs"]["baseUrl"],
        role=sources_registry["cbsWfs"]["role"],
        authoritative=sources_registry["cbsWfs"]["authoritative"],
        licenseNote=sources_registry["cbsWfs"]["licenseNote"],
        lastChecked=sources_registry["cbsWfs"].get("lastChecked"),
        fetchedAt=(layers.get("buurten") or {}).get("properties", {}).get("fetchedAt"),
        featureCount=(layers.get("buurten") or {}).get("properties", {}).get("featureCount"),
    )]
    key_to_id = {
        "gemeentegrens": "breda-gemeentegrens",
        "wijkdeals": "breda-wijkdeals",
        "hoofdgroenstructuur": "breda-hoofdgroenstructuur",
        "verharding": "breda-verharding",
        "kansenkaart": "breda-kansenkaart",
        "bomen": "breda-bomen",
    }
    for key, sid in key_to_id.items():
        reg = reg_by_id.get(sid, {})
        props = (layers.get(key) or {}).get("properties", {})
        rows.append(dict(
            id=sid,
            title=reg.get("title", sid),
            url=reg.get("serviceUrl", ""),
            role=reg.get("role"),
            authoritative=reg.get("authoritative"),
            licenseNote=reg.get("licenseNote"),
            lastChecked=reg.get("lastChecked"),
            fetchedAt=props.get("fetchedAt"),
            featureCount=props.get("featureCount"),
        ))
    return rows


def build_scan(layers: dict, degradations: list, sources_registry: dict) -> dict:
    computed = indicators.compute_scan(layers)
    values_out = {}
    for key, spec in value_model.VALUES.items():
        values_out[key] = {
            "label": spec["label"],
            "description": spec["description"],
            "quote": spec.get("quote"),
            "programmeItems": spec["programmeItems"],
            "formula": spec.get("formula"),
        }
    values_out["autonomous"]["manifest"] = value_model.SOVEREIGNTY_CRITERIA

    return {
        "scan": {
            "scanId": "breda-vijf-waardenscan",
            "generatedAt": _now_iso(),
            "gemeente": "Breda",
            "gemeenteCode": sources_registry["cbsWfs"]["gemeenteCode"],
            "congress": value_model.CONGRESS,
        },
        "sources": _sources_table(layers, sources_registry),
        "values": values_out,
        "buurten": computed["buurten"],
        "rollup": computed["rollup"],
    }


def build_prov(scan: dict, artifacts: dict, layers: dict) -> dict:
    entities = [
        {"name": name, "sha256": sha}
        for name, sha in sorted(artifacts.items())
    ]
    activities = [
        {"name": "intake", "agent": f"breda.run:{_module_version()}"},
        {"name": "fetch", "agent": f"breda.fetch:{_module_version()}"},
        {"name": "indicators", "agent": f"breda.indicators:{_module_version()}"},
        {"name": "validate", "agent": f"breda.validate:{_module_version()}"},
        {"name": "report", "agent": f"breda.report:{_module_version()}"},
    ]
    primary = [
        {
            "sourceId": s["id"],
            "url": s["url"],
            "fetchedAt": s.get("fetchedAt"),
            "featureCount": s.get("featureCount"),
            "licenseNote": s.get("licenseNote"),
        }
        for s in scan["sources"]
    ]
    return {
        "agents": [{"name": "poc-breda", "version": _module_version()}],
        "entities": entities,
        "activities": activities,
        "hadPrimarySource": primary,
        "generatedAt": scan["scan"]["generatedAt"],
    }


def _module_version() -> str:
    import breda

    return breda.__version__


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None,
                    help="uitvoermap (default: poc-breda/runs/<ts>-breda-scan)")
    ap.add_argument("--refresh", action="store_true",
                    help="forceer live her-download van elke laag")
    ap.add_argument("--no-bomen", action="store_true",
                    help="sla de bomenlaag over (117k punten; scheelt fetchtijd)")
    args = ap.parse_args(argv)

    out_dir = args.out or (
        ROOT / "runs" / f"{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-breda-scan"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. fetch (cache-first; falende lagen -> degradatie)
    registry = fetch.load_sources()
    fetched = fetch.fetch_all(
        refresh=args.refresh,
        sources=registry,
        include_bomen=not args.no_bomen,
    )
    layers, degradations = fetched["layers"], fetched["degradations"]
    if layers.get("buurten") is None:
        print("FATAAL: CBS-buurtvlakken ontbreken — scan niet mogelijk", file=sys.stderr)
        for d in degradations:
            print(f"  degradatie: {d['sourceId']}: {d['error']}", file=sys.stderr)
        return 2

    # 2. indicatoren
    scan = build_scan(layers, degradations, registry)

    # 3. validatie
    validation = validate.validate_scan(scan, degradations)

    # 4. artefacten wegschrijven
    scan_path = out_dir / "value-scan.json"
    scan_path.write_text(json.dumps(scan, ensure_ascii=False, indent=1), encoding="utf-8")
    validation_path = out_dir / "validation.json"
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    layers_manifest = {k: (v or {}).get("properties", {}) for k, v in layers.items()}
    (out_dir / "layers.json").write_text(
        json.dumps(layers_manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    report_out = report.build_reports(scan, layers, validation, {}, out_dir)
    prov = build_prov(scan, report_out["artifacts"], layers)
    (out_dir / "prov.json").write_text(
        json.dumps(prov, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    artifacts = dict(report_out["artifacts"])
    artifacts["value-scan.json"] = _sha256_bytes(scan_path.read_bytes())
    artifacts["validation.json"] = _sha256_bytes(validation_path.read_bytes())
    run_summary = {
        "runId": out_dir.name,
        "generatedAt": scan["scan"]["generatedAt"],
        "verdict": validation["verdict"],
        "nBuurten": len(scan["buurten"]),
        "nLandBuurten": sum(1 for b in scan["buurten"] if b.get("water") == "NEE"),
        "scoresComputed": {
            v: sum(
                1 for b in scan["buurten"] if b["scores"][v]["score"] is not None
            )
            for v in ("democratic", "spatial", "economic", "social")
        },
        "degradations": degradations,
        "artifacts": {
            name: {
                "sha256": sha,
                "bytes": (out_dir / name).stat().st_size if (out_dir / name).exists() else None,
            }
            for name, sha in sorted(artifacts.items())
        },
        "tunings": {
            "displaySimplifyDeg": report.DISPLAY_SIMPLIFY_DEG,
            "accessMinPresent": indicators.ACCESS_MIN_PRESENT,
            "inputSimplifyM": indicators.INPUT_SIMPLIFY_M,
            "percentileWithin": "Breda (alle buurten met geldige input)",
        },
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # 5. navertelling
    print(f"Run: {out_dir}")
    print(f"  buurten: {run_summary['nBuurten']} ({run_summary['nLandBuurten']} land)")
    print(f"  scores: {run_summary['scoresComputed']}")
    print(f"  degradaties: {len(degradations)}")
    for d in degradations:
        print(f"    - {d['sourceId']}: {d['error']}")
    print(f"  verdict: {validation['verdict']}")
    print(f"  rapport: {out_dir / 'report.html'}")
    return 0 if validation["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())
