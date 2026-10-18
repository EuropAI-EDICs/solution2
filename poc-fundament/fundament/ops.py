"""Generieke derivatie-ops voor de BindingExecutor (retrieval-familie).

Verplaatst uit poc-minigim/minigim/checklist.py (methodes → functies met de
executor als eerste argument). PoC-specifieke ops (bv. proxy_ratio/proxy_entropy
met vaste bron-ids) registreren PoC's zelf naast DEFAULT_OPS.
"""

from __future__ import annotations

from pyproj import Transformer

from .derivations import (_area_m2, _breakdown, _clip, _current_only, _geom,
                          _histogram, _length_km, _slugify)


def op_echo_input(ex, rec, binding, item, params):
    rec["values"] = {
        "btoM2": ex.bto_m2,
        "btoHa": round(ex.bto_m2 / 10000, 2),
        "bbox28992": [round(v, 1) for v in ex.bbox],
        "perimeterM": round(ex.aoi_geom.length, 1),
    }
    rec["layerRef"] = ex._write_layer("plangrens", ex.aoi_fc["features"])
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, None, derived=True)


def op_representative_point(ex, rec, binding, item, params):
    p = ex.aoi_geom.representative_point()
    lon, lat = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True).transform(p.x, p.y)
    rec["values"] = {"rdX": round(p.x, 2), "rdY": round(p.y, 2),
                     "lon": round(lon, 6), "lat": round(lat, 6)}
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, None, derived=True)


def _clip_based(ex, rec, binding, item, params):
    sid = binding["serviceRefs"][0]
    colls = params.get("collections") or [params.get("collection") or params.get("typeName")]
    all_feats, src_n, hist = [], 0, 0
    layer = None
    for coll in colls:
        layer = ex._layer(sid, coll)
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"bronlaag {coll} niet beschikbaar: {layer['error']}")
            return
        fc, dropped = _current_only(layer["fc"], sid)
        hist += dropped
        feats, n = _clip(fc, ex.aoi_geom)
        all_feats.extend(feats)
        src_n += n
    feats = all_feats
    values = {"featureCount": len(feats), "sourceFeatureCount": src_n}
    if hist:
        values["historicalObjectsFiltered"] = hist
    cap = (ex.reg.sources_by_id.get(sid) or {}).get("maxFeaturesWithoutPagination")
    if cap is not None and src_n >= cap:
        values["layerCapped"] = True
        rec["notes"].append(
            f"bronlaag server-afgekapt op {cap} features (geen paginering) — dekking kan incompleet zijn"
        )
    if feats:
        g0 = feats[0]["geometry"]["type"]
        if g0 in ("Polygon", "MultiPolygon"):
            values["areaM2"] = round(_area_m2(feats), 1)
            values["areaHa"] = round(values["areaM2"] / 10000, 2)
        elif g0 in ("LineString", "MultiLineString"):
            values["lengthKm"] = round(_length_km(feats), 2)
    field = params.get("field")
    if field == "bouwjaar":
        values["bouwjaarHistogram"] = _histogram(feats, "bouwjaar")
    elif field == "gebruiksdoel":
        values["gebruiksdoelBreakdown"] = _breakdown(feats, "gebruiksdoel")
    elif field == "functie" or "wegdeel" in colls:
        values["functieBreakdown"] = _breakdown(feats, "functie")
    rec["values"].update(values)
    rec["layerRef"] = ex._write_layer(_slugify(item["id"]), feats)
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


op_clip_layer = op_clip_stats = op_count_in_aoi = _clip_based


def op_list_in_aoi(ex, rec, binding, item, params):
    sid = binding["serviceRefs"][0]
    coll = params.get("collection") or params.get("typeName")
    layer = ex._layer(sid, coll)
    if not ex._ok(layer):
        rec["deliveredStatus"] = "not-delivered"
        rec["notes"].append(f"bronlaag niet beschikbaar: {layer['error']}")
        return
    fc, _dropped = _current_only(layer["fc"], sid)
    feats, src_n = _clip(fc, ex.aoi_geom)
    fields = params.get("fields") or ["ci_citation"]
    rows = [{k: (f.get("properties") or {}).get(k) for k in fields
             if k in (f.get("properties") or {})} for f in feats[:250]]
    rec["values"] = {"count": len(feats), "sourceFeatureCount": src_n,
                     "list": rows, "listCap": 250}
    rec["layerRef"] = ex._write_layer(_slugify(item["id"]), feats)
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


def op_presence(ex, rec, binding, item, params):
    sid = binding["serviceRefs"][0]
    # bij afstandsbepaling de laag landelijk ophalen (geen bbox-beperking)
    layer = ex._layer(sid, None, use_bbox=not params.get("maxDistanceKm"))
    if not ex._ok(layer):
        rec["deliveredStatus"] = "not-delivered"
        rec["notes"].append(f"bronlaag niet beschikbaar: {layer['error']}")
        return
    feats, _src = _clip(layer["fc"], ex.aoi_geom)
    values = {"overlapFeatureCount": len(feats)}
    if feats and feats[0].get("geometry", {}).get("type") in ("Polygon", "MultiPolygon"):
        values["overlapM2"] = round(_area_m2(feats), 1)
    if params.get("maxDistanceKm"):
        best = None
        for f in layer["fc"].get("features", []):
            if f.get("geometry") is None:
                continue
            d = _geom(f).distance(ex.aoi_geom) / 1000.0
            if best is None or d < best:
                best = d
        values["distanceToNearestKm"] = round(best, 2) if best is not None else None
        values["presence"] = bool(feats)
    rec["values"].update(values)
    if feats:
        rec["layerRef"] = ex._write_layer(_slugify(item["id"]), feats)
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


DEFAULT_OPS = {
    "echo_input": op_echo_input,
    "representative_point": op_representative_point,
    "clip_layer": op_clip_layer,
    "clip_stats": op_clip_stats,
    "count_in_aoi": op_count_in_aoi,
    "list_in_aoi": op_list_in_aoi,
    "presence": op_presence,
}
