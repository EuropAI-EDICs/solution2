#!/usr/bin/env python3
"""PoC-5 MiniGIM: gebiedscheck volgens de MiniGIM-methodiek (minigim.nl).

Vult de Omgevingsanalyse Lijst (v0.91) voor één plangrens deterministisch in
uit sleutelloze open bronnen (PDOK OGC-API/WFS + gemeente Breda), leidt daaruit
een ILS (Input Grex) draft-gebiedsindeling af, valideert V0–V3 en schrijft een
single-file HTML-rapport. Cache-first: her-run werkt offline. Geen LLM in de
beslislijn. Exit 0 alleen bij validatorverdict ``pass``.

Uitvoeren:
    nldt/.venv/bin/python poc-minigim/run.py --aoi examples/plangrens-breda-teteringen.28992.geojson
    nldt/.venv/bin/python poc-minigim/run.py --aoi <plangrens.geojson> --refresh
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from minigim import checklist as clmod  # noqa: E402
from minigim import ils as ilsmod  # noqa: E402
from minigim import report as repmod  # noqa: E402
from minigim import validate as valmod  # noqa: E402
from minigim.fetch import load_aoi  # noqa: E402
from minigim.registry import MiniGimRegistry  # noqa: E402


def _now_compact() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="MiniGIM gebiedscheck (PoC-5)")
    ap.add_argument("--aoi", required=True,
                    help="plangrens als GeoJSON (FeatureCollection/Feature/geometry; EPSG:28992 of 4326)")
    ap.add_argument("--label", default=None, help="leesbare naam van het gebied")
    ap.add_argument("--refresh", action="store_true", help="forceer live her-download (cache negeren)")
    ap.add_argument("--runs-dir", default=str(ROOT / "runs"))
    args = ap.parse_args(argv)

    aoi_path = Path(args.aoi)
    if not aoi_path.exists():
        print(f"plangrens niet gevonden: {aoi_path}", file=sys.stderr)
        return 2

    reg = MiniGimRegistry()
    aoi_fc, aoi_sha = load_aoi(aoi_path)
    label = args.label or aoi_path.stem

    run_id = f"{_now_compact()}-minigim-gebiedscheck"
    runs_dir = Path(args.runs_dir) / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    # 1. checklist over alle lijst-items (fetch+derive, cache-first)
    runner = clmod.ChecklistRunner(reg, aoi_fc, runs_dir, refresh=args.refresh)
    records = runner.run()
    summary = clmod.summarize(records)

    # 2. ILS draft uit dezelfde (memoized) bronlagen
    ils_builder = ilsmod.IlsDraftBuilder(reg, runner)
    ils_draft, ils_geoms = ils_builder.build()

    # 3. artifacts
    run_meta = {
        "runId": run_id,
        "generatedAt": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": label,
        "miniGimVersions": {"lijst": reg.lijst["sourceVersion"], "ils": reg.ils["sourceVersion"]},
        "aoi": {
            "file": str(aoi_path),
            "btoM2": runner.bto_m2,
            "bbox28992": [round(v, 1) for v in runner.bbox],
        },
    }
    omgevingsanalyse = {
        **{k: run_meta[k] for k in ("runId", "generatedAt", "miniGimVersions", "aoi")},
        "items": records,
        "summary": summary,
    }

    # 4. validatie V0–V3
    checks: list[dict] = []
    schemas = {name: json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
               for name in ("minigim-omgevingsanalyse", "minigim-ils-draft")}
    valmod.validate_v0(omgevingsanalyse, schemas["minigim-omgevingsanalyse"], "omgevingsanalyse.json", checks)
    valmod.validate_v0(ils_draft, schemas["minigim-ils-draft"], "ils-draft.json", checks)
    layer_files = sorted((runs_dir / "layers").glob("*.geojson"))
    valmod.validate_v1(runner.aoi_geom, layer_files, checks)
    valmod.validate_v2(records, reg, checks)
    valmod.validate_v3(records, runner, reg, checks)
    validation = valmod.verdict(checks)

    # 5. schrijven
    ilsmod.IlsDraftBuilder.write(ils_draft, ils_geoms, runs_dir)
    (runs_dir / "omgevingsanalyse.json").write_text(
        json.dumps(omgevingsanalyse, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (runs_dir / "ils-draft.json").write_text(
        json.dumps(ils_draft, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (runs_dir / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    prov = {
        "runId": run_id,
        "aoi": {"file": str(aoi_path), "sha256": aoi_sha},
        "registries": {
            "minigim-lijst": {"version": reg.lijst["sourceVersion"], "sha256": reg.lijst["sourceSha256"]},
            "minigim-ils": {"version": reg.ils["sourceVersion"], "sha256": reg.ils["sourceSha256"]},
        },
        # uitsluitend manifests (urls, sha256's, fetchedAt) — nooit de volledige
        # feature-collecties: prov.json blijft klein en leesbaar
        "layers": {k: {"manifest": v["manifest"], "error": v["error"]}
                   for k, v in runner.layer_results.items() if v.get("manifest") or v.get("error")},
        "doctrine": "deterministisch; modellen propageren niet (geen LLM in de beslislijn); V4 pending",
    }
    (runs_dir / "prov.json").write_text(
        json.dumps(prov, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # 6. rapport (kaartlagen: compact gemaakt — coördinaten op cm, max 1500
    # features per laag; volledige lagen staan in layers/)
    def _compact(fc: dict, cap: int = 1500) -> dict:
        def rnd(coords):
            if isinstance(coords, (list, tuple)):
                return [rnd(c) for c in coords]
            return round(coords, 2)
        feats = []
        for f in fc.get("features", [])[:cap]:
            g = f.get("geometry")
            if g and "coordinates" in g:
                f = {**f, "geometry": {**g, "coordinates": rnd(g["coordinates"])}}
            feats.append(f)
        return {"type": "FeatureCollection", "features": feats}

    layers_geo = {"plangrens": _compact(aoi_fc)}
    try:
        ils_fc = json.loads((runs_dir / "ils-draft.features.28992.geojson").read_text(encoding="utf-8"))
        if ils_fc.get("features"):
            layers_geo["ils-draft"] = _compact(ils_fc)
    except Exception:  # noqa: BLE001
        pass
    for lf in layer_files:
        if lf.name == "plangrens.28992.geojson":
            continue
        try:
            fc = json.loads(lf.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if 0 < len(fc.get("features", [])) <= 4000:
            layers_geo[lf.name.replace(".28992.geojson", "")] = _compact(fc)

    html_report = repmod.build_report(run_meta, omgevingsanalyse, ils_draft, validation, layers_geo)
    (runs_dir / "report.html").write_text(html_report, encoding="utf-8")

    # 7. run-samenvatting
    run_summary = {
        "runId": run_id, "label": label, "verdict": validation["verdict"],
        "btoM2": runner.bto_m2,
        "summary": summary,
        "artifacts": ["report.html", "omgevingsanalyse.json", "ils-draft.json",
                      "ils-draft.features.28992.geojson", "validation.json", "prov.json",
                      f"layers/ ({len(layer_files)} lagen)"],
    }
    (runs_dir / "run_summary.json").write_text(
        json.dumps(run_summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"run: {runs_dir}")
    print(f"BTO: {runner.bto_m2:,.1f} m² | items: {summary['itemCount']} "
          f"| geleverd: {summary['deliveredStatus'].get('delivered', 0)} "
          f"| handmatig: {summary['deliveredStatus'].get('manual-action', 0)} "
          f"| niet geleverd: {summary['deliveredStatus'].get('not-delivered', 0)}")
    print(f"hoog-prioriteit auto: {summary['autoCoverageOfHoog']['delivered']}/{summary['autoCoverageOfHoog']['hoog']}"
          f" ({summary['autoCoverageOfHoog']['pct']}%)")
    for c in checks:
        print(f"  {c['level']} {'PASS' if c['ok'] else 'FAIL'}  {c['artifact']}: {c['detail'][:120]}")
    print(f"verdict: {validation['verdict']}")
    return 0 if validation["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
