#!/usr/bin/env python3
"""Publish Breda Laya System-1 artefacts to the nLDT medallion lake.

Medallion (see ``nldt/13-data-lake-and-space.md``):

* **bronze** — CBS/PDOK + Breda open-data source manifests (as-received pointers
  + sha256 of the local cache bytes used for training).
* **silver** — Breda/proxy geo layers used as inputs + derived Laya dataset
  (``train/eval/meta.jsonl`` + dataset manifest).
* **gold** — canonieke value-scan run + ``predictions.json`` /
  ``finetune-summary.json`` after export.

Keys::

  bronze/breda/cbs-buurten-2024/{gemeente}/{retrievedAt}/source.meta.json
  bronze/breda/open-data/{layer}/{retrievedAt}/source.meta.json
  silver/breda/geo/{layer}.geojson
  silver/breda/laya/system1/{datasetId}/…
  gold/breda/runs/{canonicalRunId}/…
  gold/breda/laya/system1/{datasetId}/predictions.json

Usage::

  python lake_publish.py                 # bronze + silver geo + silver dataset
  python lake_publish.py --with-preds    # also gold predictions if present
  python lake_publish.py --with-run      # also canonical gold value-scan run
  python lake_publish.py --all           # bronze + silver + gold run + preds
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NLDT = ROOT / "nldt"
CACHE = ROOT / "poc-breda" / "data" / "cache"
CANONICAL_RUN_ID = "20260913T192628Z-breda-scan"
RUN = ROOT / "poc-breda" / "runs" / CANONICAL_RUN_ID

DATASET_ID = "20261025-breda-laya-s1"
RETRIEVED_AT = "2026-09-13T17:14:00Z"  # Breda CBS cache stamp (recon)

CBS_FILES = {
    "breda": CACHE / "cbs-buurten-2024.4326.geojson",
    "eindhoven": CACHE / "cbs-buurten-2024-eindhoven.4326.geojson",
    "tilburg": CACHE / "cbs-buurten-2024-tilburg.4326.geojson",
}

BREDA_LAYERS = [
    "breda-wijkdeals.4326.geojson",
    "breda-hoofdgroenstructuur.4326.geojson",
    "breda-bomen.4326.geojson",
    "breda-verharding.4326.geojson",
    "breda-kansenkaart.4326.geojson",
    "breda-gemeentegrens.4326.geojson",
]

# Files from the canonical run that the Laya dataset / sim actually consume.
RUN_FILES = [
    "value-scan.json",
    "run_summary.json",
    "validation.json",
    "layers.json",
    "prov.json",
    "geo-buurten.wgs84.geojson",
    "overlays.wgs84.geojson",
    "report.md",
    "report.html",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_nldt_path() -> None:
    if str(NLDT) not in sys.path:
        sys.path.insert(0, str(NLDT))


def write_dataset_manifest() -> Path:
    data = HERE / "data"
    files = {
        name: data / name
        for name in ("train.jsonl", "eval.jsonl", "meta.jsonl")
        if (data / name).is_file()
    }
    n_train = sum(1 for _ in files["train.jsonl"].open()) if "train.jsonl" in files else 0
    n_eval = sum(1 for _ in files["eval.jsonl"].open()) if "eval.jsonl" in files else 0
    manifest = {
        "datasetId": DATASET_ID,
        "poc": "breda",
        "kind": "laya-system1-dataset",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "canonicalRun": "20260913T192628Z-breda-scan",
        "canonicalRunLakeUri": (
            "lake://nldt-poc-lake/gold/breda/runs/20260913T192628Z-breda-scan/"
        ),
        "counts": {"train": n_train, "eval": n_eval},
        "sources": {
            "cbsPdok": {
                "id": "cbs-buurten-2024",
                "license": "CC0 / CBS open data",
                "gemeenten": list(CBS_FILES),
                "lakeBronzePrefix": "bronze/breda/cbs-buurten-2024/",
            },
            "bredaOpenData": {
                "layers": BREDA_LAYERS,
                "lakeBronzePrefix": "bronze/breda/open-data/",
                "lakeSilverPrefix": "silver/breda/geo/",
            },
            "valueScan": {
                "localPath": str(RUN / "value-scan.json"),
                "runId": CANONICAL_RUN_ID,
                "lakeUri": (
                    f"lake://nldt-poc-lake/gold/breda/runs/"
                    f"{CANONICAL_RUN_ID}/value-scan.json"
                ),
            },
        },
        "files": {
            name: {"bytes": p.stat().st_size, "sha256": _sha256(p)}
            for name, p in files.items()
        },
        "accessClass": "open",
    }
    out = data / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def publish_bronze_cbs(client) -> list[dict]:
    from services.lake.sync import sync_file

    uploaded = []
    for gemeente, path in CBS_FILES.items():
        if not path.is_file():
            continue
        digest = _sha256(path)
        meta = {
            "sourceId": "cbs-buurten-2024",
            "gemeente": gemeente,
            "retrievedAt": RETRIEVED_AT,
            "format": "GeoJSON",
            "crs": "EPSG:4326",
            "provider": "PDOK WFS wijkenbuurten 2024",
            "license": "CBS open data",
            "sha256": digest,
            "bytes": path.stat().st_size,
            "localCache": str(path.relative_to(ROOT)),
            "silverUri": f"lake://nldt-poc-lake/silver/breda/geo/{path.name}",
            "accessClass": "open",
            "usedBy": ["laya-system1", "value-scan"],
        }
        prefix = f"bronze/breda/cbs-buurten-2024/{gemeente}/{RETRIEVED_AT}"
        meta_path = HERE / "data" / f"bronze-cbs-{gemeente}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        uploaded.append(
            sync_file(client, meta_path, f"{prefix}/source.meta.json",
                      metadata={"poc": "breda", "accessClass": "open"})
        )
        # also land a pointer copy of the geojson into bronze (bytes as used)
        uploaded.append(
            sync_file(
                client,
                path,
                f"{prefix}/{path.name}",
                metadata={"poc": "breda", "accessClass": "open", "sha256": digest},
            )
        )
    return uploaded


def publish_bronze_breda_layers(client) -> list[dict]:
    """As-received Breda open-data layers used by the five-value scan / Laya S1."""
    from services.lake.sync import sync_file

    uploaded = []
    for name in BREDA_LAYERS:
        path = CACHE / name
        if not path.is_file():
            continue
        digest = _sha256(path)
        layer_id = name.replace(".4326.geojson", "").replace(".geojson", "")
        meta = {
            "sourceId": layer_id,
            "gemeente": "breda",
            "retrievedAt": RETRIEVED_AT,
            "format": "GeoJSON",
            "crs": "EPSG:4326",
            "provider": "Gemeente Breda open data / geo.breda.nl",
            "license": "open data (gemeente Breda)",
            "sha256": digest,
            "bytes": path.stat().st_size,
            "localCache": str(path.relative_to(ROOT)),
            "silverUri": f"lake://nldt-poc-lake/silver/breda/geo/{name}",
            "accessClass": "open",
            "usedBy": ["value-scan", "laya-system1"],
        }
        prefix = f"bronze/breda/open-data/{layer_id}/{RETRIEVED_AT}"
        meta_path = HERE / "data" / f"bronze-opendata-{layer_id}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        uploaded.append(
            sync_file(
                client,
                meta_path,
                f"{prefix}/source.meta.json",
                metadata={"poc": "breda", "accessClass": "open"},
            )
        )
        uploaded.append(
            sync_file(
                client,
                path,
                f"{prefix}/{name}",
                metadata={"poc": "breda", "accessClass": "open", "sha256": digest},
            )
        )
    return uploaded


def publish_silver_geo(client) -> list[dict]:
    """Silver copies of every geo layer the dataset/scan actually used."""
    from services.lake.sync import sync_file

    uploaded = []
    paths = list(CBS_FILES.values()) + [CACHE / n for n in BREDA_LAYERS]
    for path in paths:
        if not path.is_file():
            continue
        uploaded.append(
            sync_file(
                client,
                path,
                f"silver/breda/geo/{path.name}",
                metadata={"poc": "breda", "accessClass": "open", "zone": "silver"},
            )
        )
    return uploaded


def publish_silver_dataset(client) -> list[dict]:
    from services.lake.sync import sync_file

    write_dataset_manifest()
    uploaded = []
    prefix = f"silver/breda/laya/system1/{DATASET_ID}"
    for name in ("train.jsonl", "eval.jsonl", "meta.jsonl", "manifest.json"):
        path = HERE / "data" / name
        if not path.is_file():
            continue
        uploaded.append(
            sync_file(
                client,
                path,
                f"{prefix}/{name}",
                metadata={"poc": "breda", "accessClass": "open", "datasetId": DATASET_ID},
            )
        )
    return uploaded


def publish_gold_run(client) -> list[dict]:
    """Canonical value-scan run (gold) referenced by the Laya dataset."""
    from services.lake.sync import sync_file, sync_tree

    if not RUN.is_dir():
        return []
    uploaded = []
    prefix = f"gold/breda/runs/{CANONICAL_RUN_ID}"
    for name in RUN_FILES:
        path = RUN / name
        if path.is_file():
            uploaded.append(
                sync_file(
                    client,
                    path,
                    f"{prefix}/{name}",
                    metadata={
                        "poc": "breda",
                        "accessClass": "open",
                        "runId": CANONICAL_RUN_ID,
                        "canonical": "true",
                    },
                )
            )
    qa_dir = RUN / "qa"
    if qa_dir.is_dir():
        for r in sync_tree(client, qa_dir, f"{prefix}/qa"):
            r.setdefault("metadata", {})
            uploaded.append(r)
    return uploaded


def publish_gold_preds(client) -> list[dict]:
    from services.lake.sync import sync_file

    uploaded = []
    prefix = f"gold/breda/laya/system1/{DATASET_ID}"
    for name in ("predictions.json", "finetune-summary.json"):
        path = HERE / name
        if not path.is_file():
            continue
        uploaded.append(
            sync_file(
                client,
                path,
                f"{prefix}/{name}",
                metadata={"poc": "breda", "accessClass": "open", "datasetId": DATASET_ID},
            )
        )
    return uploaded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-preds", action="store_true")
    parser.add_argument("--with-run", action="store_true",
                        help="also publish canonical gold value-scan run")
    parser.add_argument("--all", action="store_true",
                        help="bronze + silver + gold run + predictions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    _ensure_nldt_path()
    from services.lake import get_lake_client

    client = get_lake_client()
    if args.dry_run:
        man = write_dataset_manifest()
        print(f"dry-run manifest → {man}")
        return 0

    with_preds = args.with_preds or args.all
    with_run = args.with_run or args.all

    results = []
    results.extend(publish_bronze_cbs(client))
    results.extend(publish_bronze_breda_layers(client))
    results.extend(publish_silver_geo(client))
    results.extend(publish_silver_dataset(client))
    if with_run:
        results.extend(publish_gold_run(client))
    if with_preds:
        results.extend(publish_gold_preds(client))

    n_up = sum(1 for r in results if not r.get("skipped"))
    n_skip = sum(1 for r in results if r.get("skipped"))
    report = {
        "at": datetime.now(timezone.utc).isoformat(),
        "datasetId": DATASET_ID,
        "canonicalRunId": CANONICAL_RUN_ID,
        "uploaded": n_up,
        "skipped": n_skip,
        "items": results,
    }
    report_path = HERE / "data" / "lake-publish-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"lake publish: uploaded={n_up} skipped={n_skip} → {report_path}")
    for r in results:
        flag = "skip" if r.get("skipped") else "put"
        print(f"  [{flag}] {r.get('uri') or r.get('key')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
