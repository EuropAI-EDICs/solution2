#!/usr/bin/env python3
"""Deterministic FormalRule executor (zone engine) for the opportunity-map PoC.

Track B, file 2 of 4. Executes the multi-agent plan's ``FormalRule[]``
contracts deterministically (no LLM at runtime — the neuro-symbolic split of
§2.4 of MULTI_AGENT_PLAN.md: LLMs propose, this engine executes and verifies).

Input model (tolerant to the exact key spellings the Formalizer emits):

* ``rules``: list of FormalRule dicts. Recognised per rule:
  - id: ``id`` | ``ruleId`` | ``normCardId`` (fallback ``rule@<i>``)
  - semantics: ``zoneSemantics`` = ``inclusion`` | ``exclusion`` | anything
    else (``compensation``, ``attention``, ...) — non-core semantics are
    reported as marker zones without altering the result
  - source layers: ``sourceLayerId`` | ``sourceLayer`` | ``layer`` |
    ``dataLayer`` | ``layerRef`` — a layer id or list of ids (keys into the
    ``layers`` dict); an inline ``geometry`` (GeoJSON dict) is also honoured
  - buffer distance: ``value``+``unit`` (m/km) | ``distance``+``distanceUnit``
    | ``bufferM`` — metres in EPSG:28992; absent/0 = use geometry as-is
* ``layers``: ``{layerId: FeatureCollection}`` as produced by
  ``geodata.fetch_layer`` (EPSG:28992). Plain paths to GeoJSON files and
  WGS84 collections (crs member inspected) are also accepted.
* ``aoi``: optional area of interest — GeoJSON geometry dict or shapely
  geometry in EPSG:28992. Inclusion output is intersected with it.

Execution: inclusion = union of inclusion layers (buffered when a distance
is stated) ∩ AOI; exclusion = per-rule buffer in EPSG:28992 metres via
shapely, then difference; every intermediate geometry is validity-checked
with ``shapely.is_valid`` and repaired with ``make_valid`` **with the repair
recorded in the provenance** (V1 evidence; recon found 8/44 invalid features
on the hosted wind layer). Output: ``ZoneResult[]`` per §5 of the plan —
``geometry.payload`` is a GeoJSON geometry reprojected to EPSG:4326 via
pyproj/shapely.ops.transform, ``areaKm2`` is computed in metric EPSG:28992,
and each result carries per-operation provenance strings naming the rule,
the source layer (+ lastChecked when known), the op and any repairs.

``reexecute_independent`` is the V3 second implementation path: the same
rule semantics executed through geopandas (``GeoSeries.buffer`` /
``gpd.overlay(how='difference')`` / ``union_all``) instead of raw shapely,
returning the resulting EPSG:28992 geometry so the Critic can compare
areas/IoU. Determinism: no timestamps, fixed buffer resolution (16
segments/quarter), rules applied in list order.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import shapely
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

try:
    from pyproj import Transformer
    from shapely.ops import transform as _shp_transform

    _RD_TO_WGS84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    _WGS84_TO_RD = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)

    def to_wgs84(geom):
        return _shp_transform(lambda x, y, z=None: _RD_TO_WGS84.transform(x, y), geom)

    def _to_rd(geom):
        return _shp_transform(lambda x, y, z=None: _WGS84_TO_RD.transform(x, y), geom)

except Exception:  # pragma: no cover
    raise ImportError("engine.py requires pyproj (toolchain guarantees it)")

__all__ = [
    "RuleError",
    "ENGINE_VERSION",
    "execute_rules",
    "reexecute_independent",
    "to_wgs84",
    "iou",
    "polygonal",
    "zone_prov_steps",
]

ENGINE_VERSION = "poc-zone-engine/0.1"
BUFFER_RESOLUTION = 16  # quad segments per quarter circle, fixed for determinism
CRS_RD = "EPSG:28992"
CRS_WGS84 = "EPSG:4326"

_LAYER_KEYS = ("sourceLayerId", "sourceLayer", "layer", "dataLayer", "layerRef")
_DISTANCE_KEYS = ("bufferM", "distanceMeters", "distance_m")
_UNIT_TO_M = {
    "m": 1.0, "meter": 1.0, "meters": 1.0, "metre": 1.0, "metres": 1.0,
    "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
    "kilometre": 1000.0, "kilometres": 1000.0, "cm": 0.01,
}


class RuleError(ValueError):
    """Raised for rules the engine refuses to guess about (cite-or-abstain)."""


# --------------------------------------------------------------------------- #
# Small tolerant accessors
# --------------------------------------------------------------------------- #

def _first(d, names, default=None):
    for n in names:
        if isinstance(d, dict) and n in d and d[n] is not None:
            return d[n]
    return default


def rule_id(rule, index):
    rid = _first(rule, ("id", "ruleId", "normCardId"))
    return str(rid) if rid is not None else f"rule@{index}"


def rule_semantics(rule):
    """zoneSemantics, normalized. Core semantics are ``inclusion`` and
    ``exclusion``; any other value (``compensation``, ``attention``, ...)
    is treated as a *marker*: its (buffered) zone is reported but never
    alters the opportunity zone. A missing value is refused (cite-or-abstain)."""
    sem = _first(rule, ("zoneSemantics", "semantics", "zone_semantics"))
    if sem is None:
        raise RuleError(f"rule {rule_id(rule, '?')} has no zoneSemantics; refusing to guess")
    return str(sem).strip().lower()


def rule_layer_ids(rule):
    """Candidate source-layer ids, in priority order, deduplicated.

    Reads the track-A FormalRule shape (``zoneSelector.zoneIds`` list and
    ``zoneSelector.geometrySource``) plus the flat spellings
    (``sourceLayerId`` | ``sourceLayer`` | ``layer`` | ``dataLayer`` |
    ``layerRef``). Resolution against the fetched ``layers`` dict happens at
    execution time so unknown candidates produce one clear error."""
    cands = []
    zs = rule.get("zoneSelector") if isinstance(rule, dict) else None
    if isinstance(zs, dict):
        zids = zs.get("zoneIds")
        if isinstance(zids, (list, tuple)):
            cands += [str(z) for z in zids]
        elif isinstance(zids, str):
            cands.append(zids)
        if zs.get("geometrySource"):
            cands.append(str(zs["geometrySource"]))
    val = _first(rule, _LAYER_KEYS)
    if isinstance(val, str):
        cands.append(val)
    elif isinstance(val, (list, tuple)):
        cands += [str(v) for v in val]
    elif val is not None:
        cands.append(str(val))
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def rule_distance_m(rule):
    """Distance in metres (EPSG:28992 units), or 0.0 when absent.

    Priority: ``zoneSelector.bufferDistanceM`` (track-A FormalRule shape)
    then flat keys (``bufferM``/``distanceMeters``/...) then
    ``value``+``unit`` / ``distance``+``distanceUnit`` / ``conditions[0]``.
    """
    zs = rule.get("zoneSelector") if isinstance(rule, dict) else None
    if isinstance(zs, dict) and zs.get("bufferDistanceM") is not None:
        return float(zs["bufferDistanceM"])
    direct = _first(rule, _DISTANCE_KEYS)
    if direct is not None:
        return float(direct)
    value = _first(rule, ("value", "distance", "buffer"))
    if value is None:
        conds = rule.get("conditions") if isinstance(rule, dict) else None
        if isinstance(conds, list) and conds:
            c0 = conds[0]
            if isinstance(c0, dict) and isinstance(c0.get("value"), (int, float)):
                unit = str(c0.get("unit") or "m").strip().lower()
                if unit in _UNIT_TO_M:
                    return float(c0["value"]) * _UNIT_TO_M[unit]
        return 0.0
    unit = str(_first(rule, ("unit", "distanceUnit", "units"), "m")).strip().lower()
    if unit and unit not in _UNIT_TO_M:
        raise RuleError(f"rule {rule_id(rule, '?')} has unsupported unit {unit!r}")
    return float(value) * _UNIT_TO_M.get(unit, 1.0)


# --------------------------------------------------------------------------- #
# Geometry plumbing
# --------------------------------------------------------------------------- #

def polygonal(geom):
    """Return (polygon-only geometry, count_of_dropped_non_polygonal_parts).

    ``make_valid`` can emit GeometryCollections mixed with lines/points;
    buffers/differences need (Multi)Polygons, so non-polygonal debris is
    dropped and *counted* for provenance.
    """
    if geom is None or geom.is_empty:
        return geom, 0

    def parts(g):
        t = g.geom_type
        if t == "Polygon":
            return [g], 0
        if t == "MultiPolygon":
            return list(g.geoms), 0
        if t == "GeometryCollection":
            out, dropped = [], 0
            for sub in g.geoms:
                p, d = parts(sub)
                out.extend(p)
                dropped += d + (0 if p or sub.geom_type in ("Polygon", "MultiPolygon") else 1)
            return out, dropped
        return [], 1  # LineString/Point dropped

    plist, dropped = parts(geom)
    if not plist:
        return shapely.geometry.Polygon(), dropped
    merged = plist[0] if len(plist) == 1 else unary_union(plist)
    return merged, dropped


def _ensure_valid(geom, prov, ctx):
    """Validity-check; repair with make_valid and RECORD it. Returns geometry."""
    if geom is None:
        return shapely.geometry.Polygon()
    repairs = 0
    if not geom.is_valid:
        geom = make_valid(geom)
        repairs = 1
    geom, dropped = polygonal(geom)
    note = f"op=validity_check; ctx={ctx}; make_valid_repairs={repairs}"
    if dropped:
        note += f"; dropped_non_polygonal={dropped}"
    prov.append(note + f"; engine={ENGINE_VERSION} shapely/{shapely.__version__}")
    return geom


def _fc_crs_is_wgs84(fc):
    crs = fc.get("crs") if isinstance(fc, dict) else None
    if not isinstance(crs, dict):
        return False
    name = str((crs.get("properties") or {}).get("name") or crs.get("name") or "")
    return "4326" in name or "CRS84" in name


def _load_fc(fc):
    if isinstance(fc, (str, Path)):
        with open(fc, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return fc


def layer_geometries(layer_id, layers, prov):
    """Shapely geometries of a fetched layer, in EPSG:28992 (reprojecting a
    WGS84 twin transparently, with provenance). Returns a list."""
    if layer_id not in layers:
        raise RuleError(
            f"rule references layer {layer_id!r} which was not fetched/passed "
            f"(known layers: {', '.join(sorted(layers)) or 'none'})"
        )
    fc = _load_fc(layers[layer_id])
    geoms = []
    reprojected = _fc_crs_is_wgs84(fc)
    for f in fc.get("features", []):
        g = f.get("geometry")
        if g is None:
            continue
        geoms.append(shape(g) if not reprojected else _to_rd(shape(g)))
    if reprojected:
        prov.append(
            f"op=reproject; layer={layer_id}; from={CRS_WGS84}; to={CRS_RD}; "
            f"engine={ENGINE_VERSION}"
        )
    return geoms


def _layer_prov_name(layer_id, layers, sources):
    """Canonical layer provenance label: id(serviceUrl/layerId; lastChecked=...)."""
    bits = [layer_id]
    src = (sources or {}).get(layer_id) or {}
    raw = layers.get(layer_id) if layers else None
    props = (raw.get("properties") or {}) if isinstance(raw, dict) else {}
    url = src.get("serviceUrl") or props.get("serviceUrl")
    lyr = src.get("layerId", props.get("layerId"))
    if url:
        bits.append(f"{url.rstrip('/')}/{lyr}" if lyr is not None else url)
    lc = src.get("lastChecked") or props.get("lastChecked")
    if lc:
        bits.append(f"lastChecked={lc}")
    sim = props.get("simplifiedM") or (src.get("simplifiedM"))
    if sim:
        bits.append(f"simplifiedM={sim}")
    if len(bits) == 1:
        return layer_id
    return f"{bits[0]}({'; '.join(bits[1:])})"


def simplify_layers(layers, tolerance_m):
    """Deterministically Douglas-Peucker-simplify every layer geometry (metres,
    EPSG:28992, topology preserved) so that overlay/buffer operations on
    province-scale multipolygons stay tractable.

    Returns ``(new_layers, notes)`` where each simplified FeatureCollection
    carries ``properties.simplifiedM`` — the engine then records
    ``simplifiedM=...`` in every per-layer provenance step, and the run
    summary records the tolerance as a tuned parameter. The original caches
    are never modified; ``tolerance_m <= 0`` returns the inputs unchanged.
    """
    if not tolerance_m or tolerance_m <= 0:
        return layers, []
    new_layers, notes = {}, []
    for lid, fc in layers.items():
        if isinstance(fc, (str, Path)):
            fc = _load_fc(fc)
        feats = []
        for f in fc.get("features", []):
            g = f.get("geometry")
            if g is None:
                feats.append(f)
                continue
            geom = shape(g).simplify(float(tolerance_m), preserve_topology=True)
            f2 = dict(f)
            f2["geometry"] = mapping(geom)
            feats.append(f2)
        props = dict(fc.get("properties") or {})
        props["simplifiedM"] = float(tolerance_m)
        new_layers[lid] = {**fc, "features": feats, "properties": props}
        notes.append(
            f"op=input_simplify; layer={lid}; tolerance_m={tolerance_m}; "
            f"method=douglas-peucker(preserve_topology); engine={ENGINE_VERSION}"
        )
    return new_layers, notes


def _union_layer(layer_id, layers, prov, sources):
    geoms = layer_geometries(layer_id, layers, prov)
    if not geoms:
        prov.append(
            f"op=union; layer={_layer_prov_name(layer_id, layers, sources)}; "
            f"features=0; result=empty; engine={ENGINE_VERSION}"
        )
        return shapely.geometry.Polygon()
    fixed, repairs, dropped = [], 0, 0
    for g in geoms:
        if not g.is_valid:
            g = make_valid(g)
            repairs += 1
        p, d = polygonal(g)
        dropped += d
        fixed.append(p)
    u = unary_union(fixed)
    u = _ensure_valid(u, prov, f"union layer={layer_id}")
    note = (
        f"op=union; layer={_layer_prov_name(layer_id, layers, sources)}; "
        f"features={len(geoms)}; make_valid_repairs={repairs}; "
        f"area_m2={u.area:.6f}; engine={ENGINE_VERSION}"
    )
    if dropped:
        note += f"; dropped_non_polygonal={dropped}"
    prov.append(note)
    return u


def _resolve_layers(rid, candidates, layers):
    """Keep only candidate layer ids that were actually fetched; raise a
    clear error naming all candidates when none resolve."""
    resolved = [l for l in candidates if l in layers]
    if not resolved:
        raise RuleError(
            f"rule {rid} references layers {candidates or '[]'} but none were "
            f"fetched/passed (known layers: {', '.join(sorted(layers)) or 'none'})"
        )
    return resolved


def _area_km2(geom):
    return geom.area / 1_000_000.0


def _round_coords(obj, dp=6):
    """Recursively round coordinate floats (default 6 dp ~ 0.11 m in WGS84)."""
    if isinstance(obj, dict):
        return {k: _round_coords(v, dp) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_coords(v, dp) for v in obj]
    if isinstance(obj, float):
        return round(obj, dp)
    return obj


def to_zone_geometry(geom, round_dp=None):
    """ZoneResult geometry member: GeoJSON payload in EPSG:4326.

    ``round_dp`` (optional) rounds coordinate floats to that many decimal
    places (6 dp ~ 0.11 m) purely to keep payload sizes sane; areas/ids are
    always computed on the unrounded geometry, so the default ``None``
    emits exact coordinates. When rounding is active the rounded geometry is
    validity-checked and micro-invalidities introduced by rounding are
    repaired (make_valid) so the emitted payload is always a VALID geometry
    (exactly what the V1 gate checks); the repair count is returned as the
    second tuple element for provenance.
    """
    def _maybe_round(obj):
        return _round_coords(obj, round_dp) if round_dp else obj

    def _to_json_lists(obj):
        # shapely mapping() yields tuples; JSON geometry coordinates are
        # arrays — convert so in-memory schema validation matches the
        # serialized form exactly (json.dumps would do the same)
        if isinstance(obj, dict):
            return {k: _to_json_lists(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_json_lists(v) for v in obj]
        return obj

    def _as_payload(m):
        if m.get("type") == "GeometryCollection":
            return {
                "type": "GeometryCollection",
                "geometries": [
                    _to_json_lists({"type": g["type"], "coordinates": g["coordinates"]})
                    if "coordinates" in g else g
                    for g in m["geometries"]
                ],
            }
        return _to_json_lists({"type": m["type"], "coordinates": m["coordinates"]})

    repairs = 0
    if geom is None or geom.is_empty:
        payload = {"type": "GeometryCollection", "geometries": []}
    else:
        m = mapping(to_wgs84(geom))
        if round_dp:
            m = _maybe_round(m)
            g = shape(m)
            if not g.is_valid:
                # rounding can create micro-invalidities; repair and keep the
                # repaired geometry EXACTLY as produced (its new intersection
                # vertices stay full precision so the payload stays valid —
                # never round a second time after repairing). GEOS linework
                # make_valid refuses some rounded-degenerate multipolygons
                # outright ("Overlay input is mixed-dimension"); buffer(0)
                # repairs those losslessly (fase-3 landbouw fixwave: 37-part
                # kassen-sliver multipolygon, area preserved, 0 dropped).
                try:
                    g = make_valid(g)
                except Exception:
                    g = g.buffer(0)
                g, dropped = polygonal(g)
                repairs = 1 + (dropped or 0)
                m = mapping(g)
        payload = _as_payload(m)
    return {"format": "GeoJSON", "payload": payload, "crs": CRS_WGS84}, repairs


def iou(a, b):
    """Intersection-over-Union of two geometries (for the Critic's V3 check)."""
    union_area = a.union(b).area
    if union_area == 0.0:
        return 1.0
    return a.intersection(b).area / union_area


def zone_prov_steps(zone):
    """Convenience accessor: the list of provenance step strings of a ZoneResult."""
    return zone.get("provSteps", [])


# --------------------------------------------------------------------------- #
# Main deterministic executor (shapely path)
# --------------------------------------------------------------------------- #

def execute_rules(rules, layers, aoi=None, sources=None, payload_round_dp=None):
    """Execute FormalRule[] over fetched layers -> list[ZoneResult].

    The returned list has one ZoneResult per inclusion step, one per applied
    exclusion rule (cumulative geometry), one per compensation marker, and a
    final entry with ``operation == 'final'`` and all rule ids + all prov.
    """
    rules = list(rules or [])
    if sources is None:
        sources = {}
    prov = []
    mark = 0

    def _snapshot():
        """Provenance steps generated since the last emitted ZoneResult."""
        nonlocal mark
        steps = prov[mark:]
        mark = len(prov)
        return steps

    aoi_geom = None
    if aoi is not None:
        aoi_geom = aoi if hasattr(aoi, "geom_type") else shape(aoi)
        aoi_geom = _ensure_valid(aoi_geom, prov, "aoi")

    # ---- partition rules: core semantics vs markers ------------------------
    inclusion, exclusion, markers = [], [], []
    for i, r in enumerate(rules):
        sem = rule_semantics(r)
        rid = rule_id(r, i)
        rr = dict(r)
        rr["_rid"] = rid
        rr["_sem"] = sem
        if sem == "inclusion":
            inclusion.append(rr)
        elif sem == "exclusion":
            exclusion.append(rr)
        else:  # compensation / attention / ... -> reported, never subtracted
            markers.append(rr)

    zone = None
    inclusion_ids, inclusion_layer_ids = [], []
    parts = []
    for r in inclusion:
        rid = r["_rid"]
        dist = rule_distance_m(r)
        lids = rule_layer_ids(r)
        if not lids and "geometry" not in r:
            raise RuleError(
                f"inclusion rule {rid} names no source layer and carries no inline geometry"
            )
        for lid in _resolve_layers(rid, lids, layers):
            g = _union_layer(lid, layers, prov, sources)
            if dist > 0:
                prov.append(
                    f"op=buffer; rule={rid}; layer={_layer_prov_name(lid, layers, sources)}; "
                    f"distance_m={dist}; crs={CRS_RD}; resolution={BUFFER_RESOLUTION}; "
                    f"engine={ENGINE_VERSION}"
                )
                g = g.buffer(dist, quad_segs=BUFFER_RESOLUTION)
                g = _ensure_valid(g, prov, f"buffer rule={rid} layer={lid}")
            parts.append(g)
            inclusion_layer_ids.append(lid)
        if "geometry" in r and r["geometry"] is not None:
            g = shape(r["geometry"])
            g = _ensure_valid(g, prov, f"inline geometry rule={rid}")
            parts.append(g)
        inclusion_ids.append(rid)

    zones = []
    if parts:
        zone = unary_union(parts)
        zone = _ensure_valid(zone, prov, "inclusion_union")
        prov.append(
            f"op=inclusion_union; rules={','.join(inclusion_ids)}; "
            f"layers={','.join(inclusion_layer_ids)}; area_m2={zone.area:.6f}; "
            f"engine={ENGINE_VERSION}"
        )
        zones.append(
            _zone(
                "inclusion_union",
                inclusion_ids,
                zone,
                layers_used=inclusion_layer_ids,
                prov_steps=_snapshot(),
                round_dp=payload_round_dp,
            )
        )
        if aoi_geom is not None:
            zone = zone.intersection(aoi_geom)
            zone = _ensure_valid(zone, prov, "clip_aoi")
            prov.append(
                f"op=intersection; rules={','.join(inclusion_ids)}; target=AOI; "
                f"area_m2={zone.area:.6f}; engine={ENGINE_VERSION}"
            )
            zones.append(
                _zone(
                    "intersection",
                    inclusion_ids,
                    zone,
                    layers_used=inclusion_layer_ids,
                    prov_steps=_snapshot(),
                    round_dp=payload_round_dp,
                )
            )
    elif aoi_geom is not None:
        zone = shapely.geometry.Polygon(aoi_geom) if aoi_geom.geom_type == "Polygon" else aoi_geom
        prov.append(f"op=aoi_seed; area_m2={zone.area:.6f}; engine={ENGINE_VERSION}")
    else:
        raise RuleError(
            "no inclusion rules and no AOI given — nothing to seed the zone from"
        )

    # ---- exclusion -------------------------------------------------------
    for r in exclusion:
        rid = r["_rid"]
        dist = rule_distance_m(r)
        lids = rule_layer_ids(r)
        if not lids and "geometry" not in r:
            raise RuleError(
                f"exclusion rule {rid} names no source layer and carries no inline geometry"
            )
        excl_parts = []
        for lid in _resolve_layers(rid, lids, layers):
            g = _union_layer(lid, layers, prov, sources)
            if dist > 0:
                prov.append(
                    f"op=buffer; rule={rid}; layer={_layer_prov_name(lid, layers, sources)}; "
                    f"distance_m={dist}; crs={CRS_RD}; resolution={BUFFER_RESOLUTION}; "
                    f"engine={ENGINE_VERSION}"
                )
                g = g.buffer(dist, quad_segs=BUFFER_RESOLUTION)
                g = _ensure_valid(g, prov, f"buffer rule={rid} layer={lid}")
            excl_parts.append(g)
        if "geometry" in r and r["geometry"] is not None:
            g = shape(r["geometry"])
            g = _ensure_valid(g, prov, f"inline geometry rule={rid}")
            excl_parts.append(g)
        excl = unary_union(excl_parts)
        before = zone.area
        zone = zone.difference(excl)
        zone = _ensure_valid(zone, prov, f"difference rule={rid}")
        prov.append(
            f"op=difference; rule={rid}; layers={','.join(lids) or 'inline-geometry'}; "
            f"buffer_m={dist}; area_before_m2={before:.6f}; area_after_m2={zone.area:.6f}; "
            f"engine={ENGINE_VERSION}"
        )
        zones.append(
            _zone("difference", [rid], zone, layers_used=lids, prov_steps=_snapshot(),
              round_dp=payload_round_dp)
        )

    # ---- markers (compensation / attention / ...): reported, never subtracted
    for r in markers:
        rid = r["_rid"]
        sem = r["_sem"]
        dist = rule_distance_m(r)
        lids = rule_layer_ids(r)
        prov.append(
            f"op=marker; rule={rid}; semantics={sem}; "
            f"note=non-core semantics reported as marker zone, does not alter "
            f"the opportunity zone; engine={ENGINE_VERSION}"
        )
        mark_geom = shapely.geometry.Polygon()
        for lid in _resolve_layers(rid, lids, layers):
            g = _union_layer(lid, layers, prov, sources)
            if dist > 0:
                prov.append(
                    f"op=buffer; rule={rid}; layer={_layer_prov_name(lid, layers, sources)}; "
                    f"distance_m={dist}; crs={CRS_RD}; resolution={BUFFER_RESOLUTION}; "
                    f"engine={ENGINE_VERSION}"
                )
                g = g.buffer(dist, quad_segs=BUFFER_RESOLUTION)
                g = _ensure_valid(g, prov, f"buffer rule={rid} layer={lid}")
            mark_geom = mark_geom.union(g)
        zones.append(
            _zone(
                f"{sem}_mark",
                [rid],
                mark_geom,
                layers_used=lids,
                prov_steps=_snapshot(),
                round_dp=payload_round_dp,
            )
        )

    final_ids = [r["_rid"] for r in inclusion + exclusion]
    final = _zone("final", final_ids, zone, round_dp=payload_round_dp, layers_used=sorted({
        lid for lid in inclusion_layer_ids
    } | {lid for r in exclusion for lid in rule_layer_ids(r)}))
    final["prov"] = " | ".join(prov)
    final["provSteps"] = prov
    zones.append(final)
    return zones


def _zone(operation, rule_ids, geom_rd, layers_used=(), prov_steps=(), round_dp=None):
    if not geom_rd.is_valid:  # defensive: inputs are validated upstream
        geom_rd = make_valid(geom_rd)
        geom_rd, _ = polygonal(geom_rd)
    digest = hashlib.md5(
        f"{operation}|{','.join(rule_ids)}|{geom_rd.area:.6f}".encode("utf-8")
    ).hexdigest()[:10]
    steps = list(prov_steps)
    geometry, payload_repairs = to_zone_geometry(geom_rd, round_dp=round_dp)
    if payload_repairs:
        steps.append(
            f"op=payload_validity_repair; rounding_dp={round_dp}; "
            f"make_valid_repairs={payload_repairs}; engine={ENGINE_VERSION}"
        )
    prov_str = " | ".join(steps)
    return {
        "id": f"zr-{operation}-{digest}",
        "ruleIds": list(rule_ids),
        "operation": operation,
        "geometry": geometry,
        "geometryValid": geom_rd.is_valid and not geom_rd.is_empty,
        "areaKm2": round(_area_km2(geom_rd), 9),
        "areaM2": round(geom_rd.area, 6),
        "layers": list(layers_used),
        "operands": list(layers_used),
        "status": "ok",
        "prov": prov_str,
        "provenance": prov_str,
        "provSteps": steps,
        # deterministic identity fields; the orchestrator/agents layer stamps
        # wall-clock metadata when wrapping this dict into the ZoneResult contract
        "computedBy": ENGINE_VERSION,
        "computedAt": "",
    }


# --------------------------------------------------------------------------- #
# V3 re-execution path (geopandas implementation)
# --------------------------------------------------------------------------- #

def reexecute_independent(rules, layers, aoi=None):
    """Second, independent implementation for the V3 semantic re-execution
    check: same FormalRule semantics executed with geopandas primitives
    (``GeoSeries.buffer`` / ``GeoDataFrame.overlay(how='difference')`` /
    ``union_all``) instead of raw shapely calls.

    Returns the final zone as a shapely geometry in EPSG:28992 so the Critic
    can compare areas / IoU against the pipeline's ZoneResult (whose
    ``areaM2`` is computed in the same CRS).
    """
    import geopandas as gpd
    import pandas as pd

    rules = list(rules or [])

    def _gdf_of(layer_id):
        if layer_id not in layers:
            raise RuleError(f"reexecute: layer {layer_id!r} not fetched/passed")
        fc = _load_fc(layers[layer_id])
        geoms, reprojected = [], _fc_crs_is_wgs84(fc)
        for f in fc.get("features", []):
            g = f.get("geometry")
            if g is None:
                continue
            g = shape(g)
            geoms.append(_to_rd(g) if reprojected else g)
        if not geoms:
            return gpd.GeoDataFrame(
                {"fid": pd.Series([], dtype="int64")},
                geometry=[],
                crs=CRS_RD,
            )
        fixed = []
        for g in geoms:
            if not g.is_valid:
                g = make_valid(g)
            p, _dropped = polygonal(g)
            fixed.append(p)
        return gpd.GeoDataFrame(
            {"fid": range(len(fixed))}, geometry=fixed, crs=CRS_RD
        )

    def _apply_distance(gdf, dist):
        if dist > 0:
            return gpd.GeoDataFrame(
                {"fid": gdf.get("fid", pd.Series(range(len(gdf))))},
                geometry=gdf.geometry.buffer(dist, resolution=BUFFER_RESOLUTION).tolist(),
                crs=CRS_RD,
            )
        return gdf

    zone = None

    def _inclusion_union(r, dist, lids):
        parts = []
        for lid in lids:
            parts.append(_apply_distance(_gdf_of(lid), dist))
        if "geometry" in r and r["geometry"] is not None:
            g = shape(r["geometry"])
            if not g.is_valid:
                g = make_valid(g)
            p, _ = polygonal(g)
            parts.append(gpd.GeoDataFrame({"fid": [0]}, geometry=[p], crs=CRS_RD))
        if not parts:
            return None
        gs = gpd.GeoSeries(
            pd.concat([p.geometry for p in parts], ignore_index=True), crs=CRS_RD
        )
        return gs.union_all() if hasattr(gs, "union_all") else gs.unary_union

    # Same rule semantics as execute_rules (which PARTITIONS rules before
    # executing): first the union of ALL inclusion zones (rule order), then
    # the per-rule exclusions. Processing rules in raw list order instead
    # would let a late inclusion re-add area that an earlier exclusion had
    # already removed — a different semantics, not an implementation delta.
    core = []
    for i, r in enumerate(rules):
        sem = rule_semantics(r)
        rid = rule_id(r, i)
        dist = rule_distance_m(r)
        # mirror execute_rules' _resolve_layers: keep only candidates that
        # were actually fetched (track-A rules also name geometrySource
        # values such as 'national_source' as candidates, which are layer
        # *roles*, not fetchable layer ids)
        lids = [l for l in rule_layer_ids(r) if l in layers]
        if not lids and "geometry" not in r and sem in ("inclusion", "exclusion"):
            raise RuleError(
                f"reexecute: rule {rid} references layers "
                f"{rule_layer_ids(r) or '[]'} but none were fetched/passed "
                f"(known layers: {', '.join(sorted(layers)) or 'none'})"
            )
        if sem in ("inclusion", "exclusion"):
            core.append((sem, rid, dist, lids, r))

    for sem, rid, dist, lids, r in [c for c in core if c[0] == "inclusion"]:
        u = _inclusion_union(r, dist, lids)
        if u is None:
            continue
        zone = u if zone is None else shapely.union(zone, u)

    # Seed the zone from the AOI BEFORE applying exclusions, mirroring
    # execute_rules' aoi_seed branch: a ruleset without inclusion rules still
    # starts from the AOI, so exclusions clip it (previously they were
    # skipped entirely — inclusion-less tracks verified nothing).
    if zone is None:
        if aoi is not None:
            zone = aoi if hasattr(aoi, "geom_type") else shape(aoi)
        else:
            raise RuleError("reexecute_independent: no inclusion rules and no AOI")

    for sem, rid, dist, lids, r in [c for c in core if c[0] == "exclusion"]:
        excl_parts = []
        for lid in lids:
            excl_parts.append(_apply_distance(_gdf_of(lid), dist))
        if "geometry" in r and r["geometry"] is not None:
            g = shape(r["geometry"])
            if not g.is_valid:
                g = make_valid(g)
            p, _ = polygonal(g)
            excl_parts.append(gpd.GeoDataFrame({"fid": [0]}, geometry=[p], crs=CRS_RD))
        if not excl_parts:
            continue
        excl = gpd.GeoDataFrame(pd.concat(excl_parts, ignore_index=True), crs=CRS_RD)
        zone_gdf = gpd.GeoDataFrame({"fid": [0]}, geometry=[zone], crs=CRS_RD)
        diff = gpd.overlay(zone_gdf, excl, how="difference", keep_geom_type=True)
        if diff.empty:
            zone = shapely.geometry.Polygon()
        else:
            gs = diff.geometry
            zone = gs.union_all() if hasattr(gs, "union_all") else gs.unary_union
        # compensation/attention/conditional rules are markers; the
        # independent path skips them, exactly like the markers the primary
        # engine reports without altering the zone
    if aoi is not None and any(rule_semantics(r) == "inclusion" for r in rules):
        aoi_geom = aoi if hasattr(aoi, "geom_type") else shape(aoi)
        zone = shapely.intersection(zone, aoi_geom)
    return zone
