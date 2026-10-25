"""Idempotent filesystem → lake sync (sha256 skip)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from services.lake import (
    DEFAULT_BUCKET,
    NLDT_ROOT,
    LakeClient,
    get_lake_client,
    load_deny,
    sha256_file,
)

POC_ROOTS = {
    "utrecht": NLDT_ROOT.parent / "poc",
    "breda": NLDT_ROOT.parent / "poc-breda",
    "eindhoven": NLDT_ROOT.parent / "poc-bp2op",
    "rijnland": NLDT_ROOT.parent / "poc-rijnland",
    "nspd": NLDT_ROOT.parent / "poc-nspd",
}

#: gedeelde RegelRecht/DSO-artefacten per instrument (nldt/simulation/regelrecht)
REGELRECHT_DIR = NLDT_ROOT / "simulation" / "regelrecht"


def access_class_for_local(
    path: Path,
    poc: str,
    deny: dict[str, Any] | None = None,
    *,
    zone: str = "silver",
) -> str:
    deny = deny or load_deny()
    try:
        rel = path.resolve().relative_to(NLDT_ROOT.parent.resolve()).as_posix()
    except ValueError:
        rel = path.as_posix()
    for ov in deny.get("pathOverrides") or []:
        g = (ov.get("glob") or "").replace("**/", "").replace("**", "")
        if g and (g.rstrip("/") in rel or "peilen" in rel and "peilen" in g):
            if "poc-bp2op/corpus" in (ov.get("glob") or "") and "corpus" not in rel:
                continue
            return ov.get("accessClass", "internal")
    if "peilen" in rel and poc == "rijnland":
        return "restricted"
    defaults = (deny.get("defaultAccessClass") or {}).get(poc) or {}
    return defaults.get(zone, "internal")

def sync_file(
    client: LakeClient,
    src: Path,
    key: str,
    *,
    metadata: dict[str, str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    digest = sha256_file(src) if src.is_file() else ""
    meta_key = f"{key}.sha256"
    skipped = False
    if digest and client.exists(meta_key):
        try:
            prev = client.get_bytes(meta_key).decode("utf-8").strip()
            if prev == digest:
                skipped = True
        except Exception:
            pass
    result = {
        "key": key,
        "uri": client.uri_for(key),
        "sha256": digest,
        "bytes": src.stat().st_size if src.is_file() else 0,
        "skipped": skipped,
        "dry_run": dry_run,
    }
    if skipped or dry_run:
        return result
    client.put_file(key, src, metadata=metadata)
    if digest:
        client.put_bytes(meta_key, digest.encode("utf-8"), content_type="text/plain")
    return result


def sync_tree(
    client: LakeClient,
    src_dir: Path,
    key_prefix: str,
    *,
    dry_run: bool = False,
    glob: str = "**/*",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not src_dir.is_dir():
        return results
    for path in sorted(src_dir.glob(glob)):
        if not path.is_file():
            continue
        if path.name.endswith(".sha256") or path.name.endswith(".meta.json"):
            continue
        rel = path.relative_to(src_dir).as_posix()
        key = f"{key_prefix.rstrip('/')}/{rel}"
        results.append(sync_file(client, path, key, dry_run=dry_run))
    return results


def default_sync_plan(pocs: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Map local PoC dirs → lake keys (silver/bronze/gold).

    Een mapping-item is ``(zone, layer, path)`` of
    ``(zone, layer, path, globs)``; met ``globs`` (lijst van bestands-globs,
    relatief aan ``path``) worden alleen matchende bestanden gesynchroniseerd.
    """
    selected = list(pocs) if pocs else ["utrecht", "breda"]
    plan: list[dict[str, Any]] = []

    def _regelrecht_entries(poc: str) -> list[tuple]:
        dso_out = REGELRECHT_DIR / "dso_overlap" / "out"
        return [
            # bronze: OW-uitwisselpakket (pons, GIO's) as-received
            ("bronze", "dso-uitwisselpakket", dso_out, [f"{poc}__*.pakket.zip"]),
            # silver: Presenteren-caches, tpod-indexen, toetsen, overlap-rapporten
            (
                "silver",
                "dso-presenteren",
                dso_out,
                [
                    f"{poc}__*.annotaties.json",
                    f"{poc}__*.regeling.json",
                    f"{poc}__*.rp.json",
                    f"{poc}__*.documentstructuur.json",
                    f"{poc}__*.tpod-index.json",
                    f"{poc}__*.toets.json",
                    f"{poc}__*.overlap.json",
                    f"{poc}__*.pakket-index.json",
                    f"{poc}__*.geo-validatie.json",
                    f"{poc}__*.voorstel-sweep.json",
                ],
            ),
            # silver: RegelRecht instrument-YAML, formalization-report, artikelen
            (
                "silver",
                "regelrecht-export",
                REGELRECHT_DIR / "full_export" / "out",
                [f"{poc}-*.yaml", f"{poc}-*.json"],
            ),
            # gold: smoke-runs
            ("gold", "regelrecht-runs", REGELRECHT_DIR / "runs", [f"{poc}-*.json"]),
        ]

    mapping = {
        "utrecht": [
            ("silver", "geo", POC_ROOTS["utrecht"] / "data" / "cache"),
            ("silver", "sources", POC_ROOTS["utrecht"] / "data"),
            ("gold", "runs", POC_ROOTS["utrecht"] / "runs"),
        ]
        + _regelrecht_entries("utrecht"),
        "breda": [
            ("silver", "geo", POC_ROOTS["breda"] / "data" / "cache"),
            ("silver", "sources", POC_ROOTS["breda"] / "data"),
            ("gold", "runs", POC_ROOTS["breda"] / "runs"),
        ],
        "eindhoven": [
            ("silver", "corpus", POC_ROOTS["eindhoven"] / "corpus"),
            ("gold", "runs", POC_ROOTS["eindhoven"] / "runs"),
        ]
        + _regelrecht_entries("eindhoven"),
        "rijnland": [
            ("silver", "geo", POC_ROOTS["rijnland"] / "data" / "cache"),
            ("silver", "sources", POC_ROOTS["rijnland"] / "data"),
            ("bronze", "peilen", POC_ROOTS["rijnland"] / "data" / "peilen"),
            ("bronze", "wkp", POC_ROOTS["rijnland"] / "data" / "wkp"),
            ("bronze", "flow", POC_ROOTS["rijnland"] / "data" / "flow"),
            ("bronze", "arcgis", POC_ROOTS["rijnland"] / "data" / "arcgis"),
            ("gold", "runs", POC_ROOTS["rijnland"] / "runs"),
        ],
        "nspd": [
            # bronze: PDOK-pagina's als-ontvangen + catalogus-snapshot (fetch_pdok_layers.py)
            ("bronze", "pdok", POC_ROOTS["nspd"] / "data" / "bronze" / "pdok"),
            ("bronze", "pdok-catalog", POC_ROOTS["nspd"] / "data" / "bronze" / "pdok-catalog"),
            # silver: dual-CRS lagen (PDOK/Zeeland OVZ/Mercator GRUP), registry, corpus
            ("silver", "geo", POC_ROOTS["nspd"] / "data" / "cache"),
            ("silver", "sources", POC_ROOTS["nspd"] / "data"),
            ("silver", "corpus", POC_ROOTS["nspd"] / "corpus"),
            ("silver", "scenarios", POC_ROOTS["nspd"] / "scenarios"),
            # gold: per-track runs + grensoverschrijdende merges + what-if-sweeps
            ("gold", "runs", POC_ROOTS["nspd"] / "runs"),
            ("gold", "xborder", POC_ROOTS["nspd"] / "xborder-runs"),
            ("gold", "scenario", POC_ROOTS["nspd"] / "scenario-runs"),
        ],
    }
    for poc in selected:
        for zone, layer, path, *rest in mapping.get(poc, []):
            globs = rest[0] if rest else None
            plan.append(
                {
                    "poc": poc,
                    "zone": zone,
                    "layer": layer,
                    "path": path,
                    "globs": globs,
                }
            )
    return plan


def run_sync(
    *,
    pocs: Iterable[str] | None = None,
    dry_run: bool = False,
    client: LakeClient | None = None,
) -> dict[str, Any]:
    client = client or get_lake_client()
    deny = load_deny()
    uploaded: list[dict[str, Any]] = []
    for item in default_sync_plan(pocs):
        path: Path = item["path"]
        if not path.exists():
            continue
        prefix = f"{item['zone']}/{item['poc']}/{item['layer']}"
        if path.is_file():
            # single file (e.g. sources.json)
            if path.name in {"sources.json", "manifest.json"} or path.suffix in {".json", ".geojson"}:
                if path.parent.name == "data" and path.name.endswith(".json"):
                    key = f"silver/{item['poc']}/meta/{path.name}"
                    meta = {
                        "poc": item["poc"],
                        "accessClass": access_class_for_local(path, item["poc"], deny),
                    }
                    uploaded.append(sync_file(client, path, key, metadata=meta, dry_run=dry_run))
            continue
        # directory tree
        if item["layer"] == "sources":
            for name in ("sources.json", "manifest.json", "catalog.json"):
                f = path / name
                if f.is_file():
                    key = f"silver/{item['poc']}/meta/{name}"
                    meta = {
                        "poc": item["poc"],
                        "accessClass": access_class_for_local(f, item["poc"], deny),
                    }
                    uploaded.append(sync_file(client, f, key, metadata=meta, dry_run=dry_run))
            continue
        globs = item.get("globs") or ["**/*"]
        for g in globs:
            for result in sync_tree(client, path, prefix, dry_run=dry_run, glob=g):
                result["poc"] = item["poc"]
                result["zone"] = item["zone"]
                result["accessClass"] = access_class_for_local(
                    path / Path(result["key"].split(f"{prefix}/")[-1]),
                    item["poc"],
                    deny,
                )
                uploaded.append(result)

    summary = {
        "bucket": DEFAULT_BUCKET,
        "at": datetime.now(timezone.utc).isoformat(),
        "count": len(uploaded),
        "skipped": sum(1 for u in uploaded if u.get("skipped")),
        "uploaded": sum(1 for u in uploaded if not u.get("skipped") and not u.get("dry_run")),
        "items": uploaded,
    }
    return summary


def write_sync_report(summary: dict[str, Any], path: Path | None = None) -> Path:
    out = path or (NLDT_ROOT / "data" / "lake-sync-report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    # trim items for report size in default path
    slim = {**summary, "items": summary.get("items", [])[:500]}
    out.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    return out
