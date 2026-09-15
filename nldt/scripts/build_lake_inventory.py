#!/usr/bin/env python3
"""Generate nldt/data/lake-inventory.json from PoC sources + run dirs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NLDT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = NLDT_ROOT.parent
OUT = NLDT_ROOT / "data" / "lake-inventory.json"
DENY = json.loads((NLDT_ROOT / "data" / "lake-deny.json").read_text(encoding="utf-8"))

POC_MAP = {
    "utrecht": WORKSPACE / "poc",
    "breda": WORKSPACE / "poc-breda",
    "eindhoven": WORKSPACE / "poc-bp2op",
    "rijnland": WORKSPACE / "poc-rijnland",
    "donl": NLDT_ROOT / "data" / "lake" / "nldt-poc-lake",
}


def _sha256(path: Path, limit: int = 1 << 20) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(limit)
            if not chunk:
                break
            h.update(chunk)
            if path.stat().st_size > limit * 8:
                # sample hash for huge files: first 8 MiB + size
                h.update(str(path.stat().st_size).encode())
                break
    return h.hexdigest()


def _access_for(poc: str, zone: str, rel: str) -> str:
    for ov in DENY.get("pathOverrides", []):
        g = ov["glob"].replace("**/", "").replace("**", "")
        if g.rstrip("/") in rel.replace("\\", "/") or rel.endswith(g.split("/")[-1].replace("*", "")):
            if "peilen" in rel and "peilen" in ov["glob"]:
                return ov["accessClass"]
            if "poc-bp2op/corpus" in ov["glob"] and "corpus" in rel and poc == "eindhoven":
                return ov["accessClass"]
            if "cache/h3" in ov["glob"] and "/h3/" in rel.replace("\\", "/"):
                return ov["accessClass"]
    if "peilen" in rel.replace("\\", "/") and poc == "rijnland":
        return "restricted"
    defaults = DENY.get("defaultAccessClass", {}).get(poc, {})
    return defaults.get(zone, "internal")


def _entry(
    *,
    poc: str,
    zone: str,
    kind: str,
    local_path: Path,
    lake_key: str,
    source_id: str | None = None,
    license_: str | None = None,
    crs: str | None = None,
    run_type: str | None = None,
) -> dict[str, Any]:
    rel = str(local_path.relative_to(WORKSPACE)) if local_path.exists() else lake_key
    return {
        "id": lake_key.replace("/", "-").replace(".", "_"),
        "poc": poc,
        "zone": zone,
        "kind": kind,
        "localPath": rel,
        "lakeKey": lake_key,
        "lakeUri": f"lake://nldt-poc-lake/{lake_key}",
        "accessClass": _access_for(poc, zone, rel),
        "license": license_,
        "crs": crs,
        "sourceId": source_id,
        "runType": run_type,
        "sha256": _sha256(local_path) if local_path.is_file() else None,
        "bytes": local_path.stat().st_size if local_path.is_file() else (
            sum(f.stat().st_size for f in local_path.rglob("*") if f.is_file())
            if local_path.is_dir() else None
        ),
        "exists": local_path.exists(),
    }


def invent_utrecht() -> list[dict[str, Any]]:
    root = POC_MAP["utrecht"]
    items: list[dict[str, Any]] = []
    sources_path = root / "data" / "sources.json"
    if sources_path.is_file():
        items.append(_entry(
            poc="utrecht", zone="silver", kind="manifest",
            local_path=sources_path,
            lake_key="silver/utrecht/sources/sources.json",
            license_="open-government",
        ))
        data = json.loads(sources_path.read_text(encoding="utf-8"))
        for src in data.get("sources", [])[:80]:
            sid = src.get("id") or "unknown"
            for crs_suffix, crs in (("28992", "EPSG:28992"), ("4326", "EPSG:4326")):
                p = root / "data" / "cache" / f"{sid}.{crs_suffix}.geojson"
                if p.is_file():
                    items.append(_entry(
                        poc="utrecht", zone="silver", kind="layer",
                        local_path=p,
                        lake_key=f"silver/utrecht/layers/{sid}/{sid}.{crs_suffix}.geojson",
                        source_id=sid, crs=crs, license_="open-government",
                    ))
    corpus = root / "corpus"
    if corpus.is_dir():
        for p in corpus.glob("*.json"):
            items.append(_entry(
                poc="utrecht", zone="silver", kind="corpus",
                local_path=p,
                lake_key=f"silver/utrecht/corpus/{p.name}",
                license_="open-government",
            ))
    for run_root, run_type in (
        (root / "runs", "run"),
        (root / "scenario-runs", "scenario"),
        (root / "crosstrack-runs", "crosstrack"),
    ):
        if not run_root.is_dir():
            continue
        for d in sorted(run_root.iterdir()):
            if not d.is_dir():
                continue
            items.append(_entry(
                poc="utrecht", zone="gold", kind="run",
                local_path=d,
                lake_key=f"gold/utrecht/{run_type}/{d.name}/",
                run_type=run_type, license_="open-government",
            ))
    return items


def invent_breda() -> list[dict[str, Any]]:
    root = POC_MAP["breda"]
    items: list[dict[str, Any]] = []
    cache = root / "data" / "cache"
    if cache.is_dir():
        for p in sorted(cache.glob("*.geojson")):
            crs = "EPSG:28992" if "28992" in p.name else ("EPSG:4326" if "4326" in p.name else None)
            sid = p.name.split(".")[0]
            items.append(_entry(
                poc="breda", zone="silver", kind="layer",
                local_path=p,
                lake_key=f"silver/breda/layers/{sid}/{p.name}",
                source_id=sid, crs=crs, license_="CC-BY / open",
            ))
    for d in sorted((root / "runs").glob("*-breda-scan")) if (root / "runs").is_dir() else []:
        items.append(_entry(
            poc="breda", zone="gold", kind="run",
            local_path=d,
            lake_key=f"gold/breda/run/{d.name}/",
            run_type="run", license_="CC-BY / open",
        ))
    scen = root / "scenario-runs"
    if scen.is_dir():
        for d in sorted(scen.iterdir()):
            if d.is_dir():
                items.append(_entry(
                    poc="breda", zone="gold", kind="run",
                    local_path=d,
                    lake_key=f"gold/breda/scenario/{d.name}/",
                    run_type="scenario", license_="CC-BY / open",
                ))
    return items


def invent_eindhoven() -> list[dict[str, Any]]:
    root = POC_MAP["eindhoven"]
    items: list[dict[str, Any]] = []
    corpus = root / "corpus"
    if corpus.is_dir():
        for p in corpus.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".html", ".md", ".json", ".txt"}:
                rel = p.relative_to(corpus).as_posix()
                items.append(_entry(
                    poc="eindhoven", zone="silver", kind="corpus",
                    local_path=p,
                    lake_key=f"silver/eindhoven/corpus/{rel}",
                    license_="public-regulation-snapshot",
                ))
    runs = root / "runs"
    if runs.is_dir():
        for d in sorted(runs.iterdir()):
            if d.is_dir():
                items.append(_entry(
                    poc="eindhoven", zone="gold", kind="run",
                    local_path=d,
                    lake_key=f"gold/eindhoven/run/{d.name}/",
                    run_type="run",
                ))
    return items


def invent_rijnland() -> list[dict[str, Any]]:
    root = POC_MAP["rijnland"]
    items: list[dict[str, Any]] = []
    sources = root / "data" / "sources.json"
    if sources.is_file():
        items.append(_entry(
            poc="rijnland", zone="silver", kind="manifest",
            local_path=sources,
            lake_key="silver/rijnland/sources/sources.json",
        ))
    cache = root / "data" / "cache"
    if cache.is_dir():
        for p in cache.glob("*.geojson"):
            items.append(_entry(
                poc="rijnland", zone="silver", kind="layer",
                local_path=p,
                lake_key=f"silver/rijnland/layers/{p.stem}/{p.name}",
            ))
    peilen = root / "data" / "peilen"
    if peilen.is_dir():
        for p in peilen.rglob("*"):
            if p.is_file():
                items.append(_entry(
                    poc="rijnland", zone="bronze", kind="restricted-archive",
                    local_path=p,
                    lake_key=f"bronze/rijnland/peilen/{p.relative_to(peilen).as_posix()}",
                ))
    wkp = root / "data" / "wkp"
    if wkp.is_dir():
        for p in wkp.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".json", ".zip"}:
                items.append(_entry(
                    poc="rijnland", zone="bronze", kind="wkp",
                    local_path=p,
                    lake_key=f"bronze/rijnland/wkp/{p.relative_to(wkp).as_posix()}",
                ))
    flow = root / "data" / "flow"
    if flow.is_dir():
        for p in flow.rglob("*"):
            if p.is_file():
                items.append(_entry(
                    poc="rijnland", zone="bronze", kind="flow",
                    local_path=p,
                    lake_key=f"bronze/rijnland/flow/{p.relative_to(flow).as_posix()}",
                ))
    arcgis = root / "data" / "arcgis"
    catalog = arcgis / "catalog.json"
    if catalog.is_file():
        items.append(_entry(
            poc="rijnland", zone="bronze", kind="arcgis-catalog",
            local_path=catalog,
            lake_key="bronze/rijnland/arcgis/catalog.json",
            source_id="rijnland.enl-mcs.nl",
        ))
    layers_dir = arcgis / "layers"
    if layers_dir.is_dir():
        # One inventory row for the bulk static snapshot (avoid 180+ entries).
        n = sum(1 for _ in layers_dir.glob("*.geojson"))
        if n:
            items.append(_entry(
                poc="rijnland", zone="bronze", kind="arcgis-static-bulk",
                local_path=layers_dir,
                lake_key="bronze/rijnland/arcgis/layers/",
                source_id="rijnland.enl-mcs.nl",
                license_="unknown-open-gov-geo",
            ))
            items[-1]["layerCount"] = n
            items[-1]["notes"] = (
                "Static MapServer layers with featureCount<=10000, "
                "simplified maxAllowableOffset=5m; see catalog.json"
            )
    runs = root / "runs"
    if runs.is_dir():
        for d in sorted(runs.iterdir()):
            if d.is_dir():
                items.append(_entry(
                    poc="rijnland", zone="gold", kind="run",
                    local_path=d,
                    lake_key=f"gold/rijnland/run/{d.name}/",
                    run_type="run",
                ))
    return items


def invent_donl() -> list[dict[str, Any]]:
    """Inventory DONL harvest artifacts under the local lake mirror."""
    lake_root = POC_MAP["donl"]
    items: list[dict[str, Any]] = []
    cat_dir = lake_root / "catalog" / "dcat"
    if cat_dir.is_dir():
        for p in sorted(cat_dir.glob("*.json")):
            dataset_id = p.stem
            key = f"catalog/dcat/{p.name}"
            items.append(_entry(
                poc="donl",
                zone="catalog",
                kind="dcat-dataset",
                local_path=p,
                lake_key=key,
                source_id="data.overheid.nl",
                license_="http://creativecommons.org/publicdomain/zero/1.0/",
            ))
    svc_dir = lake_root / "silver" / "donl" / "services"
    if svc_dir.is_dir():
        for p in sorted(svc_dir.glob("*/manifest.json")):
            dataset_id = p.parent.name
            key = f"silver/donl/services/{dataset_id}/manifest.json"
            items.append(_entry(
                poc="donl",
                zone="silver",
                kind="data-service-manifest",
                local_path=p,
                lake_key=key,
                source_id="data.overheid.nl",
                license_="http://creativecommons.org/publicdomain/zero/1.0/",
            ))
    bronze_ckan = lake_root / "bronze" / "donl" / "ckan"
    if bronze_ckan.is_dir():
        for pkg_dir in sorted(bronze_ckan.iterdir()):
            if not pkg_dir.is_dir():
                continue
            snapshots = sorted(pkg_dir.iterdir())
            if not snapshots:
                continue
            latest = snapshots[-1]
            pkg_json = latest / "package.json"
            if pkg_json.is_file():
                rel_key = f"bronze/donl/ckan/{pkg_dir.name}/{latest.name}/package.json"
                items.append(_entry(
                    poc="donl",
                    zone="bronze",
                    kind="ckan-snapshot",
                    local_path=pkg_json,
                    lake_key=rel_key,
                    source_id="data.overheid.nl",
                    license_="http://creativecommons.org/publicdomain/zero/1.0/",
                ))
    files_root = lake_root / "bronze" / "donl"
    if files_root.is_dir():
        for p in sorted(files_root.rglob("*")):
            if not p.is_file() or p.name.endswith(".sha256") or p.name.endswith(".meta.json"):
                continue
            if "ckan" in p.parts and p.name == "package.json":
                continue
            rel = p.relative_to(lake_root).as_posix()
            if "/files/" not in rel:
                continue
            items.append(_entry(
                poc="donl",
                zone="bronze",
                kind="download",
                local_path=p,
                lake_key=rel,
                source_id="data.overheid.nl",
                license_="http://creativecommons.org/publicdomain/zero/1.0/",
            ))
    return items


def main() -> int:
    datasets = (
        invent_utrecht()
        + invent_breda()
        + invent_eindhoven()
        + invent_rijnland()
        + invent_donl()
    )
    inv = {
        "version": "1.0",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspace": str(WORKSPACE),
        "bucket": "nldt-poc-lake",
        "counts": {
            "total": len(datasets),
            "byPoc": {},
            "byZone": {},
            "byAccessClass": {},
        },
        "datasets": datasets,
    }
    for d in datasets:
        inv["counts"]["byPoc"][d["poc"]] = inv["counts"]["byPoc"].get(d["poc"], 0) + 1
        inv["counts"]["byZone"][d["zone"]] = inv["counts"]["byZone"].get(d["zone"], 0) + 1
        inv["counts"]["byAccessClass"][d["accessClass"]] = (
            inv["counts"]["byAccessClass"].get(d["accessClass"], 0) + 1
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({inv['counts']['total']} datasets)")
    print(json.dumps(inv["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
