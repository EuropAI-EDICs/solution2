#!/usr/bin/env python3
"""CLI orchestrator for the NSPD opportunity-map PoC (plan section 3.2, agent #1).

Tracks: per jurisdictie ``wind``, ``zon`` en ``energietoets`` aan de NL-kant
(Omgevingsverordening Zeeland, CVDR709135) en de BE-kant van het North Sea
Port District (GRUP Zeehavengebied Gent fase 2, gewestplan, VCRO) — dezelfde
agent-architectuur als PoC-1, maar met per jurisdictie gecureerde corpus-shards
(normcards + formal rules uit taken 6–7; de run herleeft ze deterministisch in
plaats van de Utrecht-replay) en jurisdictie-gesplitste AOI-use-cases
(bbox-snede op 3.73°E).

Wires the planning plane end-to-end:

    Intake (use-case request) -> NormAnalyst (curated corpus load) ->
    NormFormalizer (curated shard + AOI-basisrule) -> V2b jurisdictie-gate ->
    Geo Analyst (geodata fetch of every zone referenced by a formalized rule)
    -> zone engine -> Cartographer -> Critic (V0-V3 + V4 pending) -> Explainer
    (decision table + PROV) -> single-file HTML report -> run summary.

Every agent boundary emits JSON validated against poc-nspd/schemas/*.schema.json
(the V0 gate); every legal claim stays chained to its NormCard citation
(cite-or-abstain); every artifact lands in the run directory with PROV.

Zone-semantiek (taak 9): alle inclusion-regels van de fase-1-shards zijn
zone-loos (V4-markers); de run gebruikt de request-AOI als inclusion-union via
de deterministische AOI-basisrule FR-AOI-01 (run_summary.inclusionBasis = "aoi")
en voert alleen de gepinde exclusions uit (NL: natura2000-nl via PDOK; BE:
geen gepinde exclusies → finale zone = BE-AOI).

Usage (no install, from the workspace root):

    python3 poc-nspd/run.py                        # wind-nl use case, cache-first
    python3 poc-nspd/run.py --use-case wind-be     # Vlaamse kant (haven Gent/Zelzate)
    python3 poc-nspd/run.py --use-case zon-nl      # zonnevelden NL-kant
    python3 poc-nspd/run.py --use-case zon-be      # zonnevelden BE-kant
    python3 poc-nspd/run.py --use-case energietoets-nl   # energietoets NL-kant
    python3 poc-nspd/run.py --use-case energietoets-be   # energietoets BE-kant
    python3 poc-nspd/run.py --refresh              # re-download live layers
    python3 poc-nspd/run.py --bbox 20000,338000,45000,390000  # EPSG:28992 clip
    python3 poc-nspd/run.py --out poc-nspd/runs/demo

Exit code 0 only when the Critic's pipeline-run verdict is ``pass``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

NSPD_ROOT = Path(__file__).resolve().parent
WORKSPACE = NSPD_ROOT.parent
if str(NSPD_ROOT) not in sys.path:
    sys.path.insert(0, str(NSPD_ROOT))

from shapely.geometry import box, mapping, shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from bbox import nspd_bbox_l72, nspd_bbox_rd  # noqa: E402
from pipeline import agents, cartographer, contracts, critic, engine, explainer, geodata, norm_llm, report  # noqa: E402
from pipeline.contracts import OpportunityMapRequest  # noqa: E402
from pipeline.jurisdictie_gate import JurisdictieError, run_v2b  # noqa: E402

RUN_VERSION = "poc-nspd-run/1.0"
ORCHESTRATOR_AGENT = {"id": "orchestrator", "name": "run.py orchestrator", "version": RUN_VERSION,
                      "role": "plan -> dispatch -> verify -> synthesize (plan section 3.2 agent #1)"}

# --------------------------------------------------------------------------- #
# zone -> open-data alias registry: de gepinde zone-aliases van fase 1
# (taak 5-probes; zoneIds in de formal-rules-shards moeten hier voorkomen —
# acceptatie-eis taken 6/7)
# --------------------------------------------------------------------------- #

ZONE_SOURCES: Dict[str, Dict[str, Any]] = {
    "natura2000-nl": {"sourceId": "pdok-natura2000",
                       "note": "Natura 2000-gebieden NL (PDOK OGC API) — exclusion"},
    "natura2000-be": {"sourceId": "mercator-sbz-wms",
                       "note": "SBZ/Natura2000-Vlaanderen (Mercator) — exclusion"},
    "gebouwen-be": {"sourceId": "geopunt-grb-wfs",
                     "note": "GRB gebouwen BE — inclusion/context"},
}

INSTRUMENTS: Dict[str, str] = {
    "nl": "Omgevingsverordening provincie Zeeland, CVDR709135 geldend 02-06-2026 t/m heden",
    "be": "GRUP Zeehavengebied Gent fase 2 / gewestplan / VCRO (Vlaanderen)",
}

# --------------------------------------------------------------------------- #
# per-track configuration: gecureerde corpus-shards (taken 6-7), report texts
# and track-specific limitations. Every use case shares the jurisdiction
# instrument and the zone-alias registry above. Tabelgedreven: geen lege entries.
# --------------------------------------------------------------------------- #

_NSPD_TRACKS: list[Dict[str, str]] = [
    # (key, land, dt-id, titel)
    ("wind-nl", "nl", "DT-wind-nl-nspd",
     "Where can wind turbines be sited in the Dutch part of the NSPD?"),
    ("wind-be", "be", "DT-wind-be-nspd",
     "Where can wind turbines be sited in the Flemish part of the NSPD (haven Gent/Zelzate)?"),
    ("zon-nl", "nl", "DT-zon-nl-nspd",
     "Where can zonnevelden be sited in the Dutch part of the NSPD?"),
    ("zon-be", "be", "DT-zon-be-nspd",
     "Where can zonnevelden be sited in the Flemish part of the NSPD?"),
    ("energietoets-nl", "nl", "DT-energietoets-nl-nspd",
     "Energy-transition screening for the Dutch part of the NSPD"),
    ("energietoets-be", "be", "DT-energietoets-be-nspd",
     "Energy-transition screening for the Flemish part of the NSPD"),
    # fase 2: overige 10 tracks (plan 2026-10-14-poc-nspd-fase2)
    ("bos-nl", "nl", "DT-bos-nl-nspd",
     "Where can forest planting occur in the Dutch part of the NSPD?"),
    ("bos-be", "be", "DT-bos-be-nspd",
     "Where can forest planting occur in the Flemish part of the NSPD?"),
    ("water-nl", "nl", "DT-water-nl-nspd",
     "Where can riparian development occur in the Dutch part of the NSPD?"),
    ("water-be", "be", "DT-water-be-nspd",
     "Where can riparian development occur in the Flemish part of the NSPD?"),
    ("bodem-nl", "nl", "DT-bodem-nl-nspd",
     "Where can soil activity occur in the Dutch part of the NSPD?"),
    ("bodem-be", "be", "DT-bodem-be-nspd",
     "Where can soil activity occur in the Flemish part of the NSPD?"),
    ("mobiliteit-nl", "nl", "DT-mobiliteit-nl-nspd",
     "Where can roadside development occur in the Dutch part of the NSPD?"),
    ("mobiliteit-be", "be", "DT-mobiliteit-be-nspd",
     "Where can roadside development occur in the Flemish part of the NSPD?"),
    ("landschap-nl", "nl", "DT-landschap-nl-nspd",
     "Where can landscape intervention occur in the Dutch part of the NSPD?"),
    ("landschap-be", "be", "DT-landschap-be-nspd",
     "Where can landscape intervention occur in the Flemish part of the NSPD?"),
    ("landbouw-nl", "nl", "DT-landbouw-nl-nspd",
     "Where can agricultural expansion occur in the Dutch part of the NSPD?"),
    ("landbouw-be", "be", "DT-landbouw-be-nspd",
     "Where can agricultural expansion occur in the Flemish part of the NSPD?"),
    ("wonen-nl", "nl", "DT-wonen-nl-nspd",
     "Where can housing development occur in the Dutch part of the NSPD?"),
    ("wonen-be", "be", "DT-wonen-be-nspd",
     "Where can housing development occur in the Flemish part of the NSPD?"),
    ("werken-nl", "nl", "DT-werken-nl-nspd",
     "Where can business development occur in the Dutch part of the NSPD?"),
    ("werken-be", "be", "DT-werken-be-nspd",
     "Where can business development occur in the Flemish part of the NSPD?"),
    ("recreatie-nl", "nl", "DT-recreatie-nl-nspd",
     "Where can recreation development occur in the Dutch part of the NSPD?"),
    ("recreatie-be", "be", "DT-recreatie-be-nspd",
     "Where can recreation development occur in the Flemish part of the NSPD?"),
    ("biomassa-nl", "nl", "DT-biomassa-nl-nspd",
     "Where can biomass installations be sited in the Dutch part of the NSPD?"),
    ("biomassa-be", "be", "DT-biomassa-be-nspd",
     "Where can biomass installations be sited in the Flemish part of the NSPD?"),
]

_LAND_LABEL = {"nl": "NL", "be": "BE"}
_TRACK_SHARD = {key.split("-")[0]: key.split("-")[0] for key, _, _, _ in _NSPD_TRACKS}

TRACKS: Dict[str, Dict[str, Any]] = {
    key: {
        "shard": f"corpus/formal-rules-{land}-{_TRACK_SHARD[key.split('-')[0]]}.json",
        "evidence": f"corpus/evidence-{land}-{_TRACK_SHARD[key.split('-')[0]]}.json",
        "normcards": f"corpus/normcards-{land}-{_TRACK_SHARD[key.split('-')[0]]}.json",
        "jurisdictie": land,
        "report_title": titel,
        "decision_table_id": dt_id,
        "decision_table_title": f"{titel} Decision table (programming stage)",
        "prov_namespace": f"ldttoolbox:poc-nspd:{key}:",
        "headline_note": (
            f"{_LAND_LABEL[land]}-side of the NSPD; semantics follow the formalized "
            + ("rules from the Omgevingsverordening Zeeland (CVDR709135)."
               if land == "nl" else
               "stedenbouwkundige voorschriften (RUP/Gewestplan) and algemene regels (VCRO).")
        ),
        "limitations": lambda cov, abst: [
            "programming-stage screening artifact; per-location permission assessment remains required."
        ],
    }
    for key, land, dt_id, titel in _NSPD_TRACKS
}

# fetch/clip-werkkader is RD (EPSG:28992) voor beide jurisdicties: de zone-engine
# en de geodata-connector rekenen in RD (inSR/outSR 28992); het L72-kader
# (nspd_bbox_l72) blijft gereserveerd voor toekomstige BE-diensten die
# Lambert72-query's willen. Een L72-bbox in de RD-queryparameters zou stil
# verkeerd filteren — daarom hier bewust één RD-kader.
DEFAULT_BBOX = {"nl": nspd_bbox_rd(), "be": nspd_bbox_rd()}
_LIMITATIONS = [
    "Zone geometry comes from pinned national open-data aliases (NL: PDOK OGC API natura2000; "
    "BE sources registered in ZONE_SOURCES are not exercised by any formalized phase-1 rule); "
    "the provincial GIO/DSO download chain is not used in this PoC.",
    "No inclusion rule in the phase-1 shards carries executable zone geometry: the NL "
    "bijlage-XIV wind-concentratielocaties and the BE RUP-deelgebieden/gewestplan-SV zones have "
    "no pinned open-data alias, so every inclusion norm is routed to the V4 human-expert "
    "checkpoint and the run uses the request AOI as inclusion union (inclusionBasis=aoi).",
    "Re-run the legal recon and this pipeline before using results after a new consolidation "
    "of the cited instruments (NL: CVDR709135; BE: RUP/gewestplan/VCRO).",
    "Map geometry in this report is display-simplified; authoritative full-resolution geometry is "
    "zones.geojson / zones.gml in the run directory.",
    "Zone algebra inputs are Douglas-Peucker simplified (tolerance recorded per run in run_summary.json "
    "tunings and per layer in the engine provenance) so district-scale GEOS overlays stay tractable.",
]

# engine operation -> zone-result contract operation
_OP_MAP = {
    "intersection": "intersection",
    "inclusion_union": "union",
    "union": "union",
    "difference": "difference",
    "final": "difference",
    "attention_mark": "buffer",
    "conditional_mark": "union",
    "compensation_mark": "union",
}


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump_json(path: Path, obj: Any, indent: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    return path


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class RunLog:
    """Collects PROV activities (stages) with wall-clock timestamps."""

    def __init__(self) -> None:
        self.activities: List[Dict[str, Any]] = []

    def stage(self, name: str, label: str, agent: str, used: Sequence[str] = (), generated: Sequence[str] = ()):
        log = self

        class _Ctx:
            def __enter__(self2):
                self2.started = time.time()
                self2.started_iso = utcnow()
                return self2

            def __exit__(self2, *exc):
                log.activities.append(
                    {
                        "id": name,
                        "label": label,
                        "type": name,
                        "agent": agent,
                        "startedAt": self2.started_iso,
                        "endedAt": utcnow(),
                        "durationS": round(time.time() - self2.started, 3),
                        "used": list(used),
                        "generated": list(generated),
                    }
                )
                return False

        return _Ctx()


# --------------------------------------------------------------------------- #
# stage implementations
# --------------------------------------------------------------------------- #

def load_request(use_case: str, bbox=None) -> Dict[str, Any]:
    path = NSPD_ROOT / "use-cases" / f"{use_case}.json"
    if not path.is_file():
        raise SystemExit(f"unknown use case {use_case!r}: {path} not found")
    request = json.loads(path.read_text(encoding="utf-8"))
    contracts.validate(request, "opportunity-map-request")
    OpportunityMapRequest.from_dict(request)  # round-trip check
    if bbox is not None:
        aoi = shape(request["areaOfInterest"]["geometry"])
        clipped = aoi.intersection(box(*bbox))
        # __geo_interface__ yields tuples; the JSON Schema requires arrays
        clipped_geojson = json.loads(json.dumps(clipped.__geo_interface__))
        request = dict(request)
        request["areaOfInterest"] = {
            "geometry": clipped_geojson,
            "crs": request["areaOfInterest"].get("crs", "EPSG:28992"),
        }
        request.setdefault("parameters", {})
        request["parameters"]["bboxClip"] = list(bbox)
        contracts.validate(request, "opportunity-map-request")
    return request


def fetch_layers(
    zone_ids: Sequence[str],
    *,
    refresh: bool,
    bbox=None,
    timeout: float = 120.0,
    geo_bindings: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    """Fetch every zone layer; returns (layers, manifest, degradations, source_of_zone)."""
    sources_registry = geodata.load_sources()
    by_source: Dict[str, Dict[str, Any]] = {}
    layers: Dict[str, Dict[str, Any]] = {}
    manifest: Dict[str, Dict[str, Any]] = {}
    degradations: List[Dict[str, Any]] = []
    source_of_zone: Dict[str, str] = {}

    for zone in zone_ids:
        spec = ZONE_SOURCES.get(zone)
        if spec is None:
            degradations.append(
                {"kind": "zone-alias", "zone": zone,
                 "error": f"no open-data alias registered for zone {zone!r}"}
            )
            continue
        sid = spec["sourceId"]
        source_of_zone[zone] = sid
        if sid in by_source and by_source[sid] is None:
            # eerder gefaalde fetch voor deze sourceId (cache van de mislukking):
            # degradeer deze zone ook — nooit een crash op de gecachte None
            # (fase-2-reviewfix: tweede zone op dezelfde bron)
            degradations.append({"kind": "layer-fetch", "zone": zone, "sourceId": sid,
                                 "error": "cached fetch failure for sourceId"})
            continue
        if sid in by_source:
            layers[zone] = by_source[sid]
        else:
            try:
                fc = geodata.fetch_layer(sid, bbox=bbox, refresh=refresh, sources=sources_registry, timeout=timeout)
            except geodata.GeoDataError as exc:
                by_source[sid] = None  # remember failure
                degradations.append({"kind": "layer-fetch", "zone": zone, "sourceId": sid, "error": str(exc)})
                continue
            except Exception as exc:  # unexpected transport failure -> degrade, never crash
                by_source[sid] = None
                degradations.append({"kind": "layer-fetch", "zone": zone, "sourceId": sid,
                                     "error": f"{type(exc).__name__}: {exc}"})
                continue
            by_source[sid] = fc
            layers[zone] = fc
        fc = layers[zone]
        props = fc.get("properties") or {}
        reg = sources_registry.get(sid, {})
        binding = (geo_bindings or {}).get(zone) or {}
        manifest[zone] = {
            "zoneId": zone,
            "aliasSourceId": sid,
            "serviceUrl": props.get("serviceUrl"),
            "layerId": props.get("layerId"),
            "title": props.get("title") or reg.get("title"),
            "role": props.get("role") or reg.get("role"),
            "authoritative": props.get("authoritative", reg.get("authoritative")),
            "licenseNote": props.get("licenseNote") or reg.get("licenseNote"),
            "where": props.get("where"),
            "featureCount": props.get("featureCount"),
            "pages": props.get("pages"),
            "fetchedAt": props.get("fetchedAt"),
            "lastChecked": props.get("lastChecked") or reg.get("lastChecked"),
            "cachePath": str(geodata.DEFAULT_CACHE_DIR / f"{sid}.28992.geojson"),
            "aliasNote": spec["note"],
            "geoBinding": {
                "geometrySource": binding.get("geometrySource"),
                "gioJoinId": binding.get("gioJoinId"),
                "caveat": binding.get("caveat"),
            },
        }
    return layers, manifest, degradations, source_of_zone


def rule_zones(rule: Mapping[str, Any]) -> List[str]:
    zs = rule.get("zoneSelector") or {}
    zones = list(zs.get("zoneIds") or [])
    if zs.get("derivedFrom"):
        zones.append(zs["derivedFrom"])
    seen: set = set()
    out = []
    for z in zones:
        if z not in seen:
            seen.add(z)
            out.append(z)
    return out


def wrap_contract_zones(
    rich_zones: Sequence[Mapping[str, Any]], request_id: str, jurisdictie: str = "nl"
) -> List[Dict[str, Any]]:
    now = utcnow()
    out = []
    for z in rich_zones:
        op = str(z.get("operation", "none"))
        mapped = _OP_MAP.get(op, "none")
        if op == "final":
            mapped = "difference" if any(z2.get("operation") == "difference" for z2 in rich_zones) else "union"
        rid = str(z.get("id", "zr-?"))
        if rid.startswith("zr-"):
            rid = "ZR-" + rid[3:]
        payload = (z.get("geometry") or {}).get("payload")
        out.append(
            {
                "id": rid,
                "requestId": request_id,
                "ruleIds": list(z.get("ruleIds") or []),
                "operation": mapped,
                "jurisdictie": jurisdictie,
                "geometry": {
                    "format": "GeoJSON",
                    "payload": payload,
                    "crs": "EPSG:4326",
                },
                "geometryValid": bool(z.get("geometryValid")),
                "areaKm2": z.get("areaKm2"),
                "operands": [str(o) for o in (z.get("layers") or z.get("operands") or [])],
                "provenance": str(z.get("prov") or z.get("provenance") or ""),
                "computedBy": "geo-analyst#poc-zone-engine-0.1",
                "computedAt": now,
            }
        )
    for zone in out:
        contracts.validate(zone, "zone-result")
    return out


def per_rule_stats(rules: Sequence[Mapping[str, Any]], layers: Mapping[str, Any], aoi) -> List[Dict[str, Any]]:
    """Informational per-rule footprint (zone union, buffered, intersected with AOI)."""
    stats = []
    for r in rules:
        zs = r.get("zoneSelector") or {}
        lids = [z for z in (zs.get("zoneIds") or []) if z in layers]
        if zs.get("derivedFrom") and zs["derivedFrom"] in layers:
            lids.append(zs["derivedFrom"])
        if not lids:
            continue
        geoms = []
        for lid in lids:
            for f in layers[lid].get("features", []):
                g = f.get("geometry")
                if g is not None:
                    geoms.append(shape(g))
        if not geoms:
            continue
        u = unary_union(geoms)
        dist = float(zs.get("bufferDistanceM") or 0)
        if dist > 0:
            u = u.buffer(dist, quad_segs=engine.BUFFER_RESOLUTION)
        clipped = u.intersection(aoi) if aoi is not None else u
        stats.append(
            {
                "ruleId": r["id"],
                "zoneSemantics": r.get("zoneSemantics"),
                "zones": lids,
                "bufferM": dist or None,
                "features": len(geoms),
                "zoneAreaKm2": round(u.area / 1e6, 3),
                "zoneIntersectAoiKm2": round(clipped.area / 1e6, 3),
            }
        )
    return stats


def count_repairs(steps: Sequence[str]) -> int:
    total = 0
    for step in steps or []:
        for m in re.finditer(r"make_valid_repairs=(\d+)", str(step)):
            total += int(m.group(1))
    return total


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--use-case", default="wind-nl",
                    choices=sorted(TRACKS),
                    help="use case id (default: wind-nl; <track>-<nl|be> over alle "
                         "13 tracks per jurisdictie)")
    ap.add_argument("--refresh", action="store_true", help="ignore the layer cache and re-download live layers")
    ap.add_argument("--bbox", default=None,
                    help="optional clip xmin,ymin,xmax,ymax in EPSG:28992 applied to the AOI "
                         "(default: the NSPD RD-kader as service-side fetch filter)")
    ap.add_argument("--out", default=None, help="output directory (default: poc-nspd/runs/<timestamp>-<usecase>)")
    ap.add_argument("--display-tolerance-m", type=float, default=report.DEFAULT_DISPLAY_TOLERANCE_M,
                    help="Douglas-Peucker tolerance (m) for report display geometry (default 25)")
    ap.add_argument("--input-simplify-m", type=float, default=2.0,
                    help="Douglas-Peucker tolerance (m, EPSG:28992) applied to fetched layer geometries "
                         "before the zone algebra so district-scale overlays stay tractable; recorded "
                         "per layer in the engine provenance and in the run summary (0 = full resolution)")
    ap.add_argument("--timeout", type=float, default=120.0, help="per-page HTTP timeout for layer fetches")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.time()
    run_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{run_ts}-{args.use_case}"
    run_dir = Path(args.out) if args.out else NSPD_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log = RunLog()
    tunings: List[Dict[str, Any]] = [
        {"k": "display_tolerance_m", "v": args.display_tolerance_m},
        {"k": "input_simplify_m", "v": args.input_simplify_m},
        {"k": "payload_coord_decimals", "v": 6},
        {"k": "buffer_resolution_quad_segs", "v": engine.BUFFER_RESOLUTION},
    ]
    degradations: List[Dict[str, Any]] = []

    print(f"[run] {run_id} -> {run_dir}")

    # ---------------- 1. intake ------------------------------------------- #
    with log.stage("intake", "Intake: load + validate OpportunityMapRequest", "run.py-orchestrator",
                  used=[f"use-cases/{args.use_case}.json"], generated=["request.json"]):
        bbox = None
        if args.bbox:
            parts = [float(p) for p in args.bbox.split(",")]
            if len(parts) != 4:
                raise SystemExit("--bbox must be xmin,ymin,xmax,ymax")
            bbox = parts
        request = load_request(args.use_case, bbox=bbox)
        dump_json(run_dir / "request.json", request)
        aoi = shape(request["areaOfInterest"]["geometry"])
        print(f"[intake] request {request['id']} objectType={request['objectType']} "
              f"stage={request['policyStage']} AOI={aoi.area/1e6:.3f} km2")

    # ---------------- 2. Norm Analyst: curated corpus load ----------------- #
    track_cfg = TRACKS.get(args.use_case)
    if track_cfg is None:
        raise SystemExit(f"unknown use case {args.use_case!r}: no track registered (known: {sorted(TRACKS)})")
    shard_rel = track_cfg["shard"]
    land = track_cfg["jurisdictie"]

    with log.stage("norm-analyst", "Norm Analyst: load curated NormCards (taak 6/7 corpus)",
                   agents.NormAnalyst.agent_name,
                   used=[track_cfg["normcards"], "corpus/sources.json"],
                   generated=["normcards.json", "normcards-rejected.json"]):
        cards = json.loads((NSPD_ROOT / track_cfg["normcards"]).read_text(encoding="utf-8"))
        for c in cards:
            contracts.validate(c, "norm-card")
        # Kruisverwijzingen tussen tracks (relatedNormCardIds / normCardId in de
        # formal-rules-shard, bijv. FR-BEW-04 -> NC-BEE-02) worden opgelost tegen
        # de volledige jurisdictie-curatie: gerefereerde kaarten worden als
        # citatie meegeleverd zodat de V2-keten (rule-card-linkage) verifieerbaar
        # blijft. Het blijft een citatie: de regels van die kaart horen bij een
        # andere track en worden in deze run niet uitgevoerd.
        card_ids = {c["id"] for c in cards}
        shard_rules_raw = json.loads((NSPD_ROOT / shard_rel).read_text(encoding="utf-8"))
        needed_ids = {r.get("normCardId") for r in shard_rules_raw}
        needed_ids.update(rel for r in shard_rules_raw for rel in (r.get("relatedNormCardIds") or []))
        needed_ids.discard(None)
        cross_track_citations: List[str] = []
        for other in sorted(NSPD_ROOT.glob(f"corpus/normcards-{land}-*.json")):
            if card_ids >= needed_ids:
                break
            for c in json.loads(other.read_text(encoding="utf-8")):
                if c["id"] in needed_ids and c["id"] not in card_ids:
                    contracts.validate(c, "norm-card")
                    cards.append(c)
                    card_ids.add(c["id"])
                    cross_track_citations.append(c["id"])
        ledger_path = NSPD_ROOT / "corpus" / f"normcards-rejected-{land}.json"
        if ledger_path.is_file():
            rejected_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        else:
            # BE-fase-1-curatie kende geen afwijzingen: alle kaarten zijn gedragen;
            # zone-loze normen zijn ambigue V4-markers, geen cite-or-abstain-afwijzingen.
            rejected_ledger = {
                "abstentions": [],
                "description": (
                    f"no cite-or-abstain abstentions curated for jurisdictie {land!r} "
                    "(every card was carried; zone-loos norms are ambiguous V4-markers)"
                ),
                "generatedBy": "run.py#poc-nspd-task9",
            }
        rejected_ledger["analystRejectedThisRun"] = []
        dump_json(run_dir / "normcards.json", cards, indent=1)
        dump_json(run_dir / "normcards-rejected.json", rejected_ledger, indent=1)
        print(f"[norm-analyst] {len(cards)} curated NormCards, "
              f"{len(rejected_ledger.get('abstentions', []))} abstentions"
              + (f"; cross-track citaties: {', '.join(sorted(cross_track_citations))}"
                 if cross_track_citations else ""))

    # ---------------- 3. Norm Formalizer: curated shard + AOI-basisrule ---- #
    with log.stage("norm-formalizer", "Norm Formalizer: load curated FormalRules (taak 6/7 shards)",
                   agents.NormFormalizer.agent_name, used=[shard_rel], generated=["formalrules.json"]):
        rules = json.loads((NSPD_ROOT / shard_rel).read_text(encoding="utf-8"))
        for r in rules:
            contracts.validate(r, "formal-rule")
        # Zone-semantiek taak 9: de inclusion-regels van de fase-1-shards zijn
        # zone-loos (V4-markers, géén geometrie). Zonder executabele inclusion
        # gebruikt de zone-engine de request-AOI als inclusion-union; die basis
        # wordt hier als deterministische, expliciet gedocumenteerde FormalRule
        # (FR-AOI-01) aan de shard toegevoegd zodat zones.json regel-herleidbaar
        # blijft (V2-zone-rule-traceability) — een uitvoeringsconstructie van de
        # orchestrator, nooit een inhoudelijke norm.
        if not any(
            r.get("status") == "formalized" and r.get("zoneSemantics") == "inclusion"
            for r in rules
        ):
            v4_inclusions = [r["id"] for r in rules if r.get("zoneSemantics") == "inclusion"]
            basis_rule = {
                "id": "FR-AOI-01",
                "normCardId": cards[0]["id"],
                "status": "formalized",
                "ruleType": "zone_inclusion",
                "zoneSemantics": "inclusion",
                "instrumentType": cards[0].get("instrumentType"),
                "jurisdictie": land,
                "appliesTo": {
                    "objectType": request["objectType"],
                    "contextTags": ["inclusion_basis_aoi", "zone_loze_inclusions_v4",
                                    "taak9_zone_semantiek"],
                },
                "executableRef": "engine.zone.within@poc-v1",
                "zoneSelector": {
                    "zoneIds": ["aoi"],
                    "selection": "within",
                    "geometrySource": "request_aoi",
                    "caveat": (
                        "inclusion-basis is de request-AOI: geen inclusion-regel in deze "
                        "shard is executabel (zone-loos, V4); de AOI is de conservatieve "
                        "inclusion-union, geen positief geschiktheidsmodel"
                    ),
                },
                "conditions": [],
                "rationale": (
                    "Taak-9-zone-semantiek: de inclusion-regels van deze track/jurisdictie "
                    f"({', '.join(v4_inclusions) or 'geen'}) zijn zone-loos naar V4 gerouteerd; "
                    "de run gebruikt de request-AOI als inclusion-union "
                    "(run_summary.inclusionBasis=aoi) zodat V4-markers en exclusions op een "
                    "gedefinieerd werkvlak worden uitgevoerd. Deze regel is een "
                    "uitvoeringsconstructie van de orchestrator, geen inhoudelijke norm."
                ),
                "formalizedBy": "run-orchestrator#poc-nspd-task9-aoi-basis",
                "formalizedAt": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d"),
            }
            contracts.validate(basis_rule, "formal-rule")
            rules.append(basis_rule)
        dump_json(run_dir / "formalrules.json", rules, indent=1)
        cov = {
            "output_rules": len(rules),
            "formalized": sum(1 for r in rules if r.get("status") == "formalized"),
            "ambiguous": sum(1 for r in rules if r.get("status") == "ambiguous"),
            "rejected": sum(1 for r in rules if r.get("status") == "rejected"),
        }
        print(f"[norm-formalizer] {cov['output_rules']} rules: {cov['formalized']} formalized, "
              f"{cov['ambiguous']} ambiguous, {cov['rejected']} rejected")

    # ---------------- 3b. V2b jurisdictie-gate ------------------------------ #
    with log.stage("v2b-jurisdictie", "V2b: jurisdictie-match (geen claim over de grens)",
                   "jurisdictie-gate",
                   used=[track_cfg["normcards"], shard_rel, "corpus/sources.json", "data/sources.json"],
                   generated=["v2b.json"]):
        try:
            v2b = run_v2b(
                normcards=cards,
                formal_rules=rules,
                sources_registry=json.loads(
                    (NSPD_ROOT / "data" / "sources.json").read_text(encoding="utf-8")),
                document_registry=json.loads(
                    (NSPD_ROOT / "corpus" / "sources.json").read_text(encoding="utf-8")),
                jurisdictie=land,
                strict=True,
            )
        except JurisdictieError as exc:
            raise SystemExit(f"[v2b] jurisdictie-gate FAILED (strict): {exc}")
        dump_json(run_dir / "v2b.json", v2b, indent=1)
        print(f"[v2b] status={v2b['status']} checks={len(v2b['checks'])}")

    # geo bindings per zone (provenance aliases for the GIO join-ids)
    geo_bindings: Dict[str, Dict[str, Any]] = {}
    for c in cards:
        gb = c.get("geoBinding") or {}
        for z in gb.get("zoneIds", []):
            geo_bindings.setdefault(
                z,
                {
                    "geometrySource": gb.get("geometrySource"),
                    "gioJoinId": gb.get("gioJoinId"),
                    "caveat": gb.get("caveat"),
                },
            )

    # ---------------- 4. Geo Analyst: fetch layers ------------------------ #
    formalized = [r for r in rules if r.get("status") == "formalized"]
    needed_zones: List[str] = []
    for r in formalized:
        for z in rule_zones(r):
            if z not in needed_zones:
                needed_zones.append(z)
    # Sentinel zoneId 'aoi' = request AOI (inclusion-basis FR-AOI-01 en eventuele
    # province-wide markers zonder GIO). Not fetched — seeded from the use-case
    # geometry after input simplification.
    fetch_zones = [z for z in needed_zones if z != "aoi"]
    # fetch-filter: --bbox wint, anders het NSPD RD-kader van de jurisdictie
    # (DEFAULT_BBOX; RD werkframe voor beide landen, zie de opmerking daar).
    fetch_bbox = bbox if bbox is not None else DEFAULT_BBOX[land]
    with log.stage("geo-analyst-fetch", "Geo Analyst: fetch zone layers (cache-first, registry sources)",
                   geodata.USER_AGENT.split(" ")[0], used=["data/sources.json"],
                   generated=["layers.json"]):
        layers, manifest, fetch_degrades, source_of_zone = fetch_layers(
            fetch_zones, refresh=args.refresh, bbox=fetch_bbox, timeout=args.timeout, geo_bindings=geo_bindings
        )
        degradations.extend(fetch_degrades)
        dump_json(run_dir / "layers.json", manifest, indent=1)
        total_feats = sum((fc.get("properties") or {}).get("featureCount", 0) for fc in layers.values())
        print(f"[geo] {len(layers)}/{len(fetch_zones)} zone layers resolved "
              f"({total_feats} features); {len(fetch_degrades)} degradation(s)"
              f"{'; + aoi-sentinel' if 'aoi' in needed_zones else ''}")

    # ---------------- 5. zone engine --------------------------------------- #
    # Recorded tuning: province-scale multipolygons (NNN 390 polygons against a
    # ~1300 km2 inclusion union) make GEOS overlays intractable at full source
    # resolution; simplify inputs deterministically (recorded per layer in the
    # engine provenance via properties.simplifiedM) before the zone algebra.
    if args.input_simplify_m and args.input_simplify_m > 0:
        layers, simplify_notes = engine.simplify_layers(layers, args.input_simplify_m)
        aoi = aoi.simplify(args.input_simplify_m, preserve_topology=True)
        for zone in manifest:
            manifest[zone]["inputSimplifyM"] = args.input_simplify_m
        dump_json(run_dir / "layers.json", manifest, indent=1)

    if "aoi" in needed_zones:
        # Seed after simplify so marker overlays match the algebra AOI.
        binding = geo_bindings.get("aoi") or {}
        layers["aoi"] = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": 0,
                "properties": {"fid": 0, "role": "aoi"},
                "geometry": mapping(aoi),
            }],
            "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
            "properties": {
                "sourceId": "request-aoi",
                "featureCount": 1,
                "title": "Area of Interest (request AOI; inclusion basis / marker scope, no GIO)",
                "role": "aoi",
                "authoritative": True,
                "lastChecked": request.get("requestedAt"),
            },
        }
        manifest["aoi"] = {
            "zoneId": "aoi",
            "aliasSourceId": "request-aoi",
            "title": "Area of Interest (request AOI)",
            "role": "aoi",
            "authoritative": True,
            "featureCount": 1,
            "aliasNote": (
                "Sentinel zone: the request AOI serves as inclusion basis "
                "(FR-AOI-01, run_summary.inclusionBasis=aoi) because every inclusion "
                "rule in this shard is zone-loos (V4); geometry is the use-case AOI, "
                "not an invented suitability or infrastructure layer."
            ),
            "geoBinding": {
                "geometrySource": binding.get("geometrySource") or "none",
                "gioJoinId": binding.get("gioJoinId"),
                "caveat": binding.get("caveat"),
            },
            "inputSimplifyM": args.input_simplify_m if args.input_simplify_m and args.input_simplify_m > 0 else None,
        }
        dump_json(run_dir / "layers.json", manifest, indent=1)
        source_of_zone["aoi"] = "request-aoi"

    engine_rules = []
    for r in formalized:
        missing = [z for z in rule_zones(r) if z not in layers]
        if missing:
            degradations.append(
                {"kind": "rule-dropped", "rule": r["id"], "zones": missing,
                 "error": "zone layer unavailable this run; rule excluded from deterministic execution "
                          "and flagged for human review"}
            )
        else:
            engine_rules.append(r)
    sources_prov = {
        zone: {
            "serviceUrl": (fc.get("properties") or {}).get("serviceUrl"),
            "layerId": (fc.get("properties") or {}).get("layerId"),
            "lastChecked": (fc.get("properties") or {}).get("lastChecked"),
        }
        for zone, fc in layers.items()
    }
    with log.stage("zone-engine", "Geo Analyst: deterministic FormalRule execution (shapely path)",
                   "zone-engine", used=["formalrules.json", "layers.json"], generated=["zones.json"]):
        attempts = 0
        while True:
            try:
                rich_zones = engine.execute_rules(engine_rules, layers, aoi=aoi, sources=sources_prov,
                                                  payload_round_dp=6)
                break
            except engine.RuleError as exc:
                attempts += 1
                if attempts > 6:
                    raise
                msg = str(exc)
                dropped = None
                for r in engine_rules:
                    if r["id"] in msg:
                        dropped = r
                        break
                if dropped is None:
                    raise
                degradations.append({"kind": "rule-dropped", "rule": dropped["id"], "error": msg})
                engine_rules.remove(dropped)
                print(f"[engine] dropped rule {dropped['id']} after RuleError: {msg[:140]}")
        final_rich = next(z for z in rich_zones if z.get("operation") == "final")
        # Defensive: the engine's final carries the core rule ids; with the
        # FR-AOI-01 inclusion basis it is never empty, but keep the poc
        # marker-only-track stamping as a fallback.
        if not final_rich.get("ruleIds"):
            final_rich["ruleIds"] = [r["id"] for r in engine_rules]
        inclusion_zone = next(
            (z for z in rich_zones if z.get("operation") == "intersection"),
            next((z for z in rich_zones if z.get("operation") == "inclusion_union"), None),
        )
        contract_zones = wrap_contract_zones(rich_zones, request["id"], jurisdictie=land)
        dump_json(run_dir / "zones.json", contract_zones, indent=1)
        rule_stats = per_rule_stats(engine_rules, layers, aoi)
        dump_json(run_dir / "rule-stats.json", rule_stats, indent=1)
        print(f"[engine] {len(rich_zones)} zones; inclusion\u2229AOI="
              f"{(inclusion_zone['areaKm2'] if inclusion_zone else float('nan')):.3f} km2; "
              f"final={final_rich['areaKm2']:.3f} km2")

    # Zone-semantiek taak 9: inclusionBasis documenteert of de inclusion-union
    # uit executabele zone-gebonden inclusion-regels bestaat of (fase 1: alle
    # tracks) de request-AOI is via de orchestrator-basisrule FR-AOI-01.
    inclusion_basis = (
        "formalized-inclusion-zones"
        if any(r.get("zoneSemantics") == "inclusion" and r.get("id") != "FR-AOI-01"
               for r in engine_rules)
        else "aoi"
    )

    # ---------------- 6. Cartographer --------------------------------------- #
    with log.stage("cartographer", "Cartographer: zones.geojson + GML + report input",
                   cartographer.CARTOGRAPHER_VERSION, used=["zones.json"],
                   generated=["zones.geojson", "zones.gml"]):
        gj = cartographer.write_geojson(rich_zones, run_dir / "zones.geojson")
        gml = cartographer.write_gml(gj)
        if not gml["ok"]:
            print(f"[cartographer] GML export degraded: {gml['error']}")
        report_input = cartographer.build_report_input(
            rich_zones, sources=sources_prov,
            outputs={"geojson": str(gj), "gml": gml["path"] if gml["ok"] else None, "gmlStatus": gml},
            title=track_cfg["report_title"],
        )
        dump_json(run_dir / "report_input.json", report_input, indent=1)

    # ---------------- 7. Critic ---------------------------------------------- #
    with log.stage("critic", "Critic/Validator: V0-V3 deterministic + V4 pending",
                   critic.Critic.agent_name,
                   used=["request.json", "normcards.json", "formalrules.json", "zones.json", "decision-table.json"],
                   generated=["validation.json"]):
        critic_obj = critic.Critic()
        reports_l = critic_obj.evaluate_run(
            request=request,
            normcards=cards,
            formalrules=rules,
            zones=contract_zones,
            decision_table=None,  # replaced below after the explainer runs
            layers=layers,
            aoi=aoi,
            engine_rules=engine_rules,
            final_zone=final_rich,
            inclusion_area_m2=inclusion_zone["areaM2"] if inclusion_zone else None,
            degradations=degradations,
            run_id=run_id,
            track=args.use_case,
        )
        verdict0 = reports_l[-1]["verdict"]
        print(f"[critic] pre-explainer pipeline verdict: {verdict0}")

    # ---------------- 8. Explainer ------------------------------------------- #
    with log.stage("explainer", "Explainer: decision table + PROV bundle",
                   explainer.Explainer.agent_name,
                   used=["normcards.json", "formalrules.json", "zones.json"],
                   generated=["decision-table.json", "decision-table.md", "prov.json"]):
        expl = explainer.Explainer()
        curator_stamps = sorted({c.get("extractedBy", "") for c in cards if c.get("extractedBy")})
        formalizer_stamps = sorted({r.get("formalizedBy", "") for r in rules if r.get("formalizedBy")})
        prov_narrative = (
            f"run {run_id} of {RUN_VERSION}; curated norm corpus poc-nspd/{track_cfg['normcards']} "
            f"(taak 6/7: {', '.join(curator_stamps) or agents.ANALYST_RUN}) with formal rules "
            f"poc-nspd/{shard_rel} ({', '.join(formalizer_stamps) or agents.FORMALIZER_RUN}); "
            f"instrument {INSTRUMENTS[land]}; zone geometry from pinned national open-data "
            f"aliases (ZONE_SOURCES), lastChecked stamps in layers.json; V2b jurisdictie-gate "
            f"{v2b['status']}; full PROV in prov.json"
        )
        dt = expl.build_decision_table(
            request=request, normcards=cards, formalrules=rules,
            generated_at=utcnow(), prov_narrative=prov_narrative,
            table_id=track_cfg["decision_table_id"], title=track_cfg["decision_table_title"],
        )
        # Review-fix (taak 9): FR-AOI-01 is een orchestrator-constructie en leent
        # géén citaat van de bijgaande normcard (cards[0] was anders zichtbaar
        # als criterium/norm/bron — foute juridische attributie). De kolommen die
        # naar de bron wijzen krijgen constructie-inhoud; "zone effect" blijft de
        # schema-enumwaarde "included" en draagt het aoi-basis-label in de noot
        # (het decision-table-schema staat geen andere waarde toe). normCardId
        # blijft gevuld — schema-verplicht (NC-patroon) én vereist door
        # v2-decision-table-linkage — maar er wordt geen kaartcitaat meer getoond.
        for row in dt.get("rows", []):
            if row.get("ruleId") == "FR-AOI-01":
                row["criterion"] = "orchestrator-basis: request-AOI (constructie, geen norm)"
                row["norm"] = (
                    "run.py orchestrator FR-AOI-01 \u2014 geen rechtsbron "
                    "[uitvoeringsconstructie]"
                )
                row["source"] = (
                    f"use-cases/{args.use_case}.json (bbox.py NSPD_BBOX_WGS84, "
                    "EPSG:28992); geen document"
                )
                row["note"] = (
                    # dedup (fase-2 docronde): de inclusionBasis=aoi-zin staat
                    # al in de rationale van de constructieregel (hieronder als
                    # bestaande note toegevoegd) — hier alleen de nieuwe info
                    "included (aoi-basis) \u2014 geen bijgaande kaart geciteerd: geen "
                    "inclusion-regel in deze shard is executabel (zone-loos, V4). "
                    + (row.get("note") or "")
                ).strip()
        dump_json(run_dir / "decision-table.json", dt, indent=1)
        (run_dir / "decision-table.md").write_text(expl.decision_table_markdown(dt), encoding="utf-8")

        # re-run the critic with the decision table included (V0+V2 over it)
        reports_l = critic_obj.evaluate_run(
            request=request,
            normcards=cards,
            formalrules=rules,
            zones=contract_zones,
            decision_table=dt,
            layers=layers,
            aoi=aoi,
            engine_rules=engine_rules,
            final_zone=final_rich,
            inclusion_area_m2=inclusion_zone["areaM2"] if inclusion_zone else None,
            degradations=degradations,
            run_id=run_id,
            track=args.use_case,
        )
        vdir = run_dir / "validation"
        for vr in reports_l:
            dump_json(vdir / f"{vr['artifactType']}.json", vr, indent=1)
        dump_json(run_dir / "validation.json", reports_l, indent=1)
        verdict = reports_l[-1]["verdict"]
        print(f"[critic] pipeline verdict: {verdict}")

        # PROV bundle (hashes over what is already on disk)
        ent = [
            explainer.entity_for(run_dir / "request.json", "OpportunityMapRequest"),
            explainer.entity_for(NSPD_ROOT / shard_rel, "evidence shard"),
            explainer.entity_for(NSPD_ROOT / "corpus" / "sources.json", "document source registry"),
            explainer.entity_for(NSPD_ROOT / "data" / "sources.json", "geo source registry"),
            explainer.entity_for(run_dir / "normcards.json", "NormCard[]"),
            explainer.entity_for(run_dir / "normcards-rejected.json", "cite-or-abstain ledger"),
            explainer.entity_for(run_dir / "formalrules.json", "FormalRule[]"),
            explainer.entity_for(run_dir / "layers.json", "layer manifest"),
            explainer.entity_for(run_dir / "zones.json", "ZoneResult[]"),
            explainer.entity_for(run_dir / "rule-stats.json", "per-rule footprint stats"),
            explainer.entity_for(gj, "zones GeoJSON (RFC 7946)"),
            explainer.entity_for(run_dir / "report_input.json", "cartographer report input"),
            explainer.entity_for(run_dir / "decision-table.json", "DecisionTable"),
            explainer.entity_for(run_dir / "decision-table.md", "DecisionTable (markdown)"),
            explainer.entity_for(run_dir / "v2b.json", "V2b jurisdictie-gate result"),
            explainer.entity_for(run_dir / "validation.json", "ValidationReport[]"),
        ]
        if gml["ok"]:
            ent.append(explainer.entity_for(Path(gml["path"]), "zones GML 3.2"))
        for zone, sid in sorted(source_of_zone.items()):
            cache = geodata.DEFAULT_CACHE_DIR / f"{sid}.28992.geojson"
            if cache.exists():
                ent.append(explainer.entity_for(cache, "layer cache (EPSG:28992)",
                                                {"zone": zone, "sourceId": sid}))
        prov = expl.build_prov(
            run_id=run_id,
            generated_at=utcnow(),
            request_id=str(request["id"]),
            namespace=track_cfg["prov_namespace"],
            agents=[
                ORCHESTRATOR_AGENT,
                {"id": "legal-recon-agent", "name": "NormAnalyst",
                 "version": ", ".join(curator_stamps) or agents.ANALYST_RUN,
                 "role": "curated NormCard corpus load (taak 6/7; agent #3 seam)"},
                {"id": "norm-formalizer", "name": "NormFormalizer",
                 "version": ", ".join(formalizer_stamps) or agents.FORMALIZER_RUN,
                 "role": "curated FormalRule shard load + orchestrator AOI-basisrule FR-AOI-01 (agent #4 seam)"},
                {"id": "jurisdictie-gate", "name": "V2b jurisdictie-gate",
                 "version": "jurisdictie-gate#poc-nspd-task8",
                 "role": f"V2b jurisdictie-match incl. V2B-BRON documentregister: {v2b['status']}"},
                {"id": "geo-connector", "name": "GeoData connector", "version": geodata.USER_AGENT.split(" ")[0],
                 "role": "registry fetch (ArcGIS REST / OGC API Features), cache-first (agent #5 tool)"},
                {"id": "zone-engine", "name": "FormalRule zone engine", "version": engine.ENGINE_VERSION,
                 "role": "deterministic execution + validation repair provenance (agent #5)"},
                {"id": "cartographer", "name": "Cartographer", "version": cartographer.CARTOGRAPHER_VERSION,
                 "role": "GeoJSON/GML serialization (agent #6)"},
                {"id": "critic-validator", "name": "Critic/Validator", "version": critic.CRITIC_VERSION,
                 "role": "V0-V3 deterministic checks, V4 pending (agent #7)"},
                {"id": "explainer", "name": "Explainer", "version": explainer.EXPLAINER_VERSION,
                 "role": "decision table + PROV (agent #8)"},
                {"id": "report", "name": "HTML report renderer", "version": report.REPORT_VERSION,
                 "role": "single-file report (agent #6 view tier)"},
            ],
            activities=log.activities,
            entities=ent,
            derivations=[
                {"generatedEntity": "formalrules.json", "usedEntity": Path(shard_rel).name,
                 "note": "curated FormalRule shard + orchestrator AOI-basisrule FR-AOI-01"},
                {"generatedEntity": "normcards.json", "usedEntity": Path(track_cfg["normcards"]).name,
                 "note": "curated NormCard corpus load (cite-or-abstain)"},
                {"generatedEntity": "v2b.json", "usedEntity": "normcards.json",
                 "note": "V2b jurisdictie-gate over normcards + formal rules"},
                {"generatedEntity": "zones.json", "usedEntity": "formalrules.json",
                 "note": "engine executed FormalRules over fetched layers"},
                {"generatedEntity": "decision-table.json", "usedEntity": "normcards.json",
                 "note": "every row links a normCardId"},
                {"generatedEntity": "validation.json", "usedEntity": "zones.json",
                 "note": "V0-V3 over the artifact tree"},
            ],
            sources=[
                {
                    "zone": zone,
                    "sourceId": sid,
                    "service": f"{(manifest.get(zone) or {}).get('serviceUrl')}/{(manifest.get(zone) or {}).get('layerId')}",
                    "lastChecked": (manifest.get(zone) or {}).get("lastChecked"),
                    "fetchedAt": (manifest.get(zone) or {}).get("fetchedAt"),
                    "features": (manifest.get(zone) or {}).get("featureCount"),
                    "aliasFor": (manifest.get(zone) or {}).get("geoBinding", {}).get("gioJoinId")
                    or (manifest.get(zone) or {}).get("geoBinding", {}).get("geometrySource"),
                    "authoritative": (manifest.get(zone) or {}).get("authoritative"),
                }
                for zone, sid in sorted(source_of_zone.items())
            ],
        )
        dump_json(run_dir / "prov.json", prov, indent=1)

    # ---------------- 9. HTML report ----------------------------------------- #
    with log.stage("report", "Report: single-file HTML with Leaflet map + tables",
                   report.REPORT_VERSION,
                   used=["zones.geojson", "decision-table.json", "validation.json", "normcards.json", "prov.json"],
                   generated=["report.html"]):
        total_repairs = count_repairs(final_rich.get("provSteps"))
        verdicts = {vr["artifactType"]: vr["verdict"] for vr in reports_l}
        badges = [{"label": f"verdict: {verdict}", "cls": verdict},
                  {"label": f"V2b: {v2b['status']}", "cls": v2b["status"]},
                  {"label": "V4 human: pending", "cls": "pending"},
                  {"label": f"cite-or-abstain: {len(cards)} cards / {len(rejected_ledger.get('abstentions', []))} abstentions", "cls": ""}]
        headline = [
            {"k": "AOI (jurisdictie)", "v": f"{aoi.area/1e6:,.1f} km\u00b2",
             "s": f"NSPD-{_LAND_LABEL[land]}-helft van de districtsbbox (EPSG:28992, snede 3.73\u00b0E)"},
            {"k": "Inclusion \u2229 AOI", "v": f"{inclusion_zone['areaKm2']:,.1f} km\u00b2" if inclusion_zone else "\u2014",
             "s": "inclusion basis: request-AOI (FR-AOI-01; inclusionBasis=aoi)"
                  if inclusion_basis == "aoi" else "union of the formalized inclusion zones"},
            {"k": "Final opportunity zone", "v": f"{final_rich['areaKm2']:,.1f} km\u00b2",
             "s": "na executie van de formele exclusions (NL: natura2000-nl via PDOK)" if land == "nl"
             else "geen gepinde BE-exclusions in fase 1: finale zone = BE-AOI"},
            {"k": "Rules executed", "v": f"{len(engine_rules)} of {len(rules)}",
             "s": f"{cov['formalized']} formalized; {cov['ambiguous']} ambiguous \u2192 V4; {cov['rejected']} rejected"},
            {"k": "Zones emitted", "v": str(len(rich_zones)), "s": "incl. markers (attention/conditional/compensation)"},
            {"k": "Geometry repairs", "v": str(total_repairs), "s": "invalid-as-served features, recorded in prov"},
        ]
        zones_table = [
            {
                "id": z.get("id"),
                "operation": z.get("operation"),
                "ruleIds": z.get("ruleIds", []),
                "areaKm2": f"{z.get('areaKm2', 0):,.3f}",
                "layers": z.get("layers", []),
                "provSteps": len(z.get("provSteps") or []),
                "repairs": count_repairs(z.get("provSteps")),
            }
            for z in rich_zones
        ]
        validation_view = [
            {
                "id": vr["id"],
                "artifactType": vr["artifactType"],
                "verdict": vr["verdict"],
                "levels": [
                    {"name": name, "status": lvl["status"], "checks": lvl.get("checks") or [],
                     "notes": lvl.get("notes")}
                    for name, lvl in vr["levels"].items()
                ],
            }
            for vr in reports_l
        ]
        normcards_view = [
            {
                "id": c["id"], "article": c["source"]["article"], "instrument": c["instrument"],
                "legalForce": c["legalForce"], "confidence": c["confidence"], "claim": c["claim"],
                "quote": c["source"]["quote"], "uri": c["source"]["uri"], "docId": c["source"]["docId"],
                "version": c["source"]["version"], "theme": c["theme"],
                "zoneIds": (c.get("geoBinding") or {}).get("zoneIds"),
                "gioJoinId": (c.get("geoBinding") or {}).get("gioJoinId"),
                "caveat": (c.get("geoBinding") or {}).get("caveat"),
            }
            for c in cards
        ]
        map_data = report.build_map_data(rich_zones, request["areaOfInterest"]["geometry"],
                                         tolerance_m=args.display_tolerance_m)
        prov_view = {
            "activities": [
                {"label": a["label"], "agent": a["agent"], "startedAt": a["startedAt"],
                 "endedAt": a["endedAt"], "used": a["used"], "generated": a["generated"]}
                for a in log.activities
            ],
            "agents": [a for a in prov["agent"]],
            "sources": [
                {
                    "zone": s["zone"], "sourceId": s["sourceId"], "service": s["service"],
                    "features": s["features"], "lastChecked": s["lastChecked"],
                    "aliasFor": s["aliasFor"] or "(national source)",
                }
                for s in prov["hadPrimarySource"]
            ],
        }
        limitations = list(_LIMITATIONS) + list(
            track_cfg["limitations"](cov, rejected_ledger.get("abstentions", []))
        )
        for d in degradations:
            limitations.append(f"Degradation this run: {json.dumps(d, ensure_ascii=False)}")
        report_data = {
            "run": {
                "title": track_cfg["report_title"],
                "run_id": run_id,
                "use_case": args.use_case,
                "generated_at": utcnow(),
                "policy_stage": request["policyStage"],
                "instrument": INSTRUMENTS[land],
                "badges": badges,
            },
            "headline": headline,
            "headline_note": track_cfg["headline_note"],
            "map": map_data,
            "zones_table": zones_table,
            "decision": {"columns": dt["columns"], "rows": dt["rows"]},
            "validation": validation_view,
            "normcards": normcards_view,
            "abstentions": rejected_ledger.get("abstentions", []),
            "prov": prov_view,
            "limitations": limitations,
            "tunings": tunings,
            "paths": {"listing": " / ".join(sorted(p.name for p in run_dir.iterdir() if p.is_file()))},
        }
        report.write_report(run_dir / "report.html", report_data)

    # ---------------- 9b. PROV completion for late artifacts ------------------ #
    # The PROV bundle (stage 8) hashes only what is on disk when it is built;
    # report.html, the per-artifact validation reports and zones.xsd are
    # written after it, and the explainer/report activities complete only when
    # their stage blocks exit. Complete the bundle here — before
    # run_summary.json hashes prov.json — so every artifact file in the run
    # directory is a PROV entity. prov.json and run_summary.json are recorded
    # without sha256 (a file cannot contain its own hash); their integrity is
    # carried by run_summary.json's artifact list and the bundle's own entity
    # hashes of every other file.
    prov["activity"] = list(log.activities)
    activity_ids = {a.get("id") for a in prov["activity"]}
    existing_ids = {e["id"] for e in prov["entity"]}

    def _late_entity(rel: str, etype: str, *, with_sha: bool = True,
                     note: str = "") -> Dict[str, Any]:
        p = run_dir / rel
        ent_late: Dict[str, Any] = {"id": rel, "type": etype, "path": str(p)}
        if with_sha and p.exists():
            ent_late["sha256"] = sha256_of(p)
        if note:
            ent_late["note"] = note
        return ent_late

    late_entities = [_late_entity(f"validation/{vr['artifactType']}.json", "ValidationReport")
                     for vr in reports_l]
    if (run_dir / "zones.xsd").exists() and "zones.xsd" not in existing_ids:
        late_entities.append(explainer.entity_for(run_dir / "zones.xsd",
                                                  "zones GML 3.2 XML schema"))
    late_entities.extend([
        _late_entity("report.html", "single-file HTML report"),
        _late_entity("prov.json", "PROV bundle (this file)", with_sha=False,
                     note="self-referential; integrity via run_summary.json artifact hashes"),
        _late_entity("run_summary.json",
                     "run summary (headline, tunings, artifact hashes)", with_sha=False,
                     note="written after prov.json; its sha256 lives in its own artifacts list"),
    ])
    prov["entity"].extend(e for e in late_entities if e["id"] not in existing_ids)
    ent_ids = {e["id"] for e in prov["entity"]}
    late_links = [(f"validation/{vr['artifactType']}.json", "critic") for vr in reports_l] + [
        ("zones.xsd", "cartographer"), ("report.html", "report"), ("prov.json", "explainer"),
    ]
    for rel, act in late_links:
        if rel in ent_ids and act in activity_ids and not any(
                w.get("entity") == rel for w in prov["wasGeneratedBy"]):
            prov["wasGeneratedBy"].append({"entity": rel, "activity": act,
                                           "time": utcnow()})
    dump_json(run_dir / "prov.json", prov, indent=1)

    # ---------------- 10. run summary ---------------------------------------- #
    artifacts = sorted(p for p in run_dir.iterdir() if p.is_file())
    summary = {
        "runId": run_id,
        "useCase": args.use_case,
        "generatedAt": utcnow(),
        "durationS": round(time.time() - started, 1),
        "orchestrator": RUN_VERSION,
        "instrument": INSTRUMENTS[land],
        "verdict": verdict,
        "verdicts": verdicts,
        "headline": {
            "aoiKm2": round(aoi.area / 1e6, 3),
            "inclusionIntersectAoiKm2": inclusion_zone["areaKm2"] if inclusion_zone else None,
            "finalOpportunityKm2": final_rich["areaKm2"],
            "rulesTotal": len(rules),
            "rulesExecuted": len(engine_rules),
            "zones": len(rich_zones),
            "geometryRepairs": total_repairs,
            "normCards": len(cards),
            "abstentions": len(rejected_ledger.get("abstentions", [])),
        },
        "perRule": rule_stats,
        "degradations": degradations,
        "tunings": tunings,
        "v2b": v2b,
        "inclusionBasis": inclusion_basis,
        "crossTrackCitations": sorted(cross_track_citations),
        "v3": next(
            (c["detail"] for vr in reports_l for lvl in vr["levels"].values()
             for c in lvl.get("checks", []) if c["id"] == "v3-reexecution-agreement"),
            None,
        ),
        "artifacts": [{"name": p.name, "path": str(p), "sha256": sha256_of(p),
                       "bytes": p.stat().st_size} for p in artifacts],
        "agents": prov["agent"],
    }
    dump_json(run_dir / "run_summary.json", summary, indent=1)

    # ---------------- console summary ---------------------------------------- #
    print()
    print("=" * 78)
    print(f"RUN {run_id} — verdict: {verdict.upper()}")
    print("=" * 78)
    rows = [
        ("AOI (jurisdictie)", f"{aoi.area/1e6:,.3f} km2"),
        ("Inclusion ∩ AOI", f"{inclusion_zone['areaKm2']:,.3f} km2" if inclusion_zone else "—"),
        ("Final opportunity zone", f"{final_rich['areaKm2']:,.3f} km2"),
        ("Rules executed / total", f"{len(engine_rules)} / {len(rules)} "
         f"({cov['formalized']} formalized, {cov['ambiguous']} ambiguous→V4, {cov['rejected']} rejected)"),
        ("Zones emitted", str(len(rich_zones))),
        ("Geometry repairs (recorded)", str(total_repairs)),
        ("V2b gate", f"{v2b['status']} ({len(v2b['checks'])} checks; inclusionBasis={inclusion_basis})"),
        ("Verdicts", ", ".join(f"{k}={v}" for k, v in verdicts.items())),
    ]
    for k, v in rows:
        print(f"  {k:<28} {v}")
    if summary["v3"]:
        print(f"  {'V3 re-execution':<28} {summary['v3']}")
    if degradations:
        print(f"  DEGRADATIONS ({len(degradations)}):")
        for d in degradations:
            print(f"    - {json.dumps(d, ensure_ascii=False)[:160]}")
    print(f"  Duration {summary['durationS']}s; artifacts:")
    for p in artifacts:
        print(f"    {run_dir / p.name}")
    print("=" * 78)
    print(f"[report] open {run_dir / 'report.html'} (works from file://)")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        traceback.print_exc()
        print(f"[run] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
