"""Voert de lijst-bindings uit: per checklist-item een deterministische levering.

Doctrine: een item is auto/partial (runner levert, met prov), manual
(gedocumenteerde mens-route) of out-of-scope (structureel). Een falende bron
is nooit fataal voor de run: het item krijgt deliveredStatus=not-delivered
plus risicovlag — zichtbaar, nooit stilletjes geskipt.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

import shapely.geometry as sg

from .fetch import OGC_FILTER_BREDA, fetch_layer


class _FetchLayerError(RuntimeError):
    """Bronlaag kon niet worden opgehaald (faal-isolatie per item)."""


def _geom(feature) -> sg.base.BaseGeometry:
    return sg.shape(feature["geometry"])


def _clip(fc: dict, aoi_geom) -> tuple[list, int]:
    """Clip features op de plangrens; geeft (geclipte features, bron-aantal).

    Reparatie uitsluitend voor vlakken: buffer(0) op punten/lijnen geeft
    lege geometrieën (shapely-semantiek).
    """
    out = []
    src = fc.get("features", [])
    for f in src:
        if f.get("geometry") is None:
            continue
        g = _geom(f)
        if g.geom_type in ("Polygon", "MultiPolygon") and not g.is_valid:
            g = g.buffer(0)
        inter = g.intersection(aoi_geom)
        if inter.is_empty:
            continue
        out.append({**f, "geometry": json.loads(json.dumps(inter.__geo_interface__))})
    return out, len(src)


def _current_only(fc: dict, sid: str) -> tuple[dict, int]:
    """BGT levert ook historische objecten (eind_registratie gevuld); alleen
    de actuele stand tellen. Andere bronnen onaangetast."""
    if sid != "pdok-bgt-ogc-api":
        return fc, 0
    kept, dropped = [], 0
    for f in fc.get("features", []):
        if (f.get("properties") or {}).get("eind_registratie"):
            dropped += 1
        else:
            kept.append(f)
    return {**fc, "features": kept}, dropped


def _area_m2(features) -> float:
    tot = 0.0
    for f in features:
        g = _geom(f)
        if g.geom_type in ("Polygon", "MultiPolygon"):
            tot += g.area
    return tot


def _length_km(features) -> float:
    tot = 0.0
    for f in features:
        g = _geom(f)
        if g.geom_type in ("LineString", "MultiLineString"):
            tot += g.length
    return tot / 1000.0


def _breakdown(features, field: str, top: int = 12) -> dict:
    counts: dict[str, int] = {}
    for f in features:
        v = (f.get("properties") or {}).get(field)
        v = "(onbekend)" if v in (None, "") else str(v)
        counts[v] = counts.get(v, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1])[:top])


def _histogram(features, field: str) -> dict:
    bins = {}
    for f in features:
        v = (f.get("properties") or {}).get(field)
        if isinstance(v, (int, float)) and 1500 < float(v) < 2100:
            bins[f"{int(v) // 10 * 10}s"] = bins.get(f"{int(v) // 10 * 10}s", 0) + 1
    return dict(sorted(bins.items()))


def _entropy_norm(features, field: str) -> float:
    counts = _breakdown(features, field, top=10_000)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for c in counts.values():
        p = c / total
        ent -= p * math.log(p)
    max_ent = math.log(len(counts)) if len(counts) > 1 else 1.0
    return round(ent / max_ent, 4) if max_ent > 0 else 0.0


CBS_SENTINELS = (-99995, -99997, -99998, -99999)


class ChecklistRunner:
    """Voert alle bindings uit tegen één plangrens (cache-first)."""

    def __init__(self, registry, aoi_fc: dict, runs_dir: Path, refresh: bool = False):
        self.reg = registry
        self.aoi_fc = aoi_fc
        self.refresh = refresh
        self.layers_dir = runs_dir / "layers"
        self.layers_dir.mkdir(parents=True, exist_ok=True)

        polys = [g for f in aoi_fc["features"] for g in self._polys(_geom(f))]
        self.aoi_geom = sg.MultiPolygon(polys) if polys else sg.Polygon()
        self.bto_m2 = round(self.aoi_geom.area, 1)
        self.bbox = self.aoi_geom.bounds
        self.layer_results: dict[str, dict] = {}

    @staticmethod
    def _polys(g):
        if g.geom_type == "Polygon":
            return [g]
        if g.geom_type == "MultiPolygon":
            return list(g.geoms)
        return []

    # ------------------------------------------------------------------ #
    def _layer(self, service_id: str, collection: str | None = None,
               cbs: bool = False, use_bbox: bool = True) -> dict:
        """Bronlaag cache-first ophalen; memoized per (bron, laag, filter, bbox-modus)."""
        key = f"{service_id}::{collection or ''}::{'cbs' if cbs else ''}::{'' if use_bbox else 'nb'}"
        if key in self.layer_results:
            return self.layer_results[key]

        source = dict(self.reg.sources_by_id[service_id])
        if collection:
            if source["protocol"] == "ogc-api-features":
                source["collections"] = [collection]
            elif source["protocol"] == "wfs2":
                source["typeNames"] = [collection]
        bbox = self.bbox if use_bbox else None
        try:
            fc, manifest = fetch_layer(
                source, bbox=bbox, refresh=self.refresh,
                cbs_filter=OGC_FILTER_BREDA if cbs else None,
            )
            res = {"key": key, "fc": fc, "manifest": manifest, "error": None}
        except Exception as exc:  # noqa: BLE001 — faal-isolatie per laag
            res = {"key": key, "fc": None, "manifest": None,
                   "error": f"{type(exc).__name__}: {exc}"}
        self.layer_results[key] = res
        return res

    @staticmethod
    def _ok(layer: dict) -> bool:
        return layer.get("fc") is not None and layer.get("error") is None

    def _write_layer(self, slug: str, features) -> str:
        fc = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
            "features": features,
        }
        path = self.layers_dir / f"{slug}.28992.geojson"
        path.write_text(json.dumps(fc, ensure_ascii=False) + "\n", encoding="utf-8")
        return f"layers/{path.name}"

    def _set_prov(self, rec, binding, layer: dict, derived: bool = False) -> None:
        item = self.reg.item(binding["lijstItemId"])
        if derived:
            rec["prov"] = {
                "bronRegistratie": "afgeleid van run-input (plangrens)",
                "bronLeverancier": None, "fetchedAt": None, "sha256": None,
                "protocol": "derived", "urls": [],
            }
            return
        m = layer["manifest"]
        rec["prov"] = {
            "bronRegistratie": item.get("bronRegistratie"),
            "bronLeverancier": item.get("bronLeverancier"),
            "fetchedAt": m.get("fetchedAt"),
            "sha256": m.get("sha256"),
            "protocol": m.get("protocol"),
            "urls": m.get("urls"),
        }

    # ------------------------------------------------------------------ #
    def run(self) -> list[dict]:
        return [self._execute(i, self.reg.binding(i["id"])) for i in self.reg.lijst["items"]]

    def _execute(self, item: dict, binding: dict) -> dict:
        rec = {
            "lijstItemId": item["id"],
            "thema": item["thema"],
            "onderdeel": item.get("onderdeel"),
            "item": item.get("item"),
            "prioriteit": item.get("prioriteit"),
            "bindingStatus": binding["status"],
            "deliveredStatus": "nvt",
            "values": {},
            "layerRef": None,
            "prov": None,
            "proxyNote": binding.get("proxyNote"),
            "manualPointer": binding.get("manualPointer"),
            "riskFlags": [],
            "notes": list(binding.get("notes", [])),
        }

        if binding["status"] in ("manual", "out-of-scope"):
            rec["deliveredStatus"] = "manual-action" if binding["status"] == "manual" else "nvt"
            if binding["status"] == "manual":
                rec["values"] = {"route": binding.get("manualPointer")}
            self._flag_risks(rec)
            return rec

        op = (binding.get("derivation") or {}).get("op", "none")
        params = (binding.get("derivation") or {}).get("params", {})
        handler = getattr(self, f"_op_{op}", None)
        if handler is None:
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"runner-fout: onbekende derivation-op {op}")
        else:
            try:
                handler(rec, binding, item, params)
            except Exception as exc:  # noqa: BLE001 — faal-isolatie per item
                rec["deliveredStatus"] = "not-delivered"
                rec["notes"].append(f"runner-fout: {type(exc).__name__}: {exc}")
        self._flag_risks(rec)
        return rec

    def _flag_risks(self, rec) -> None:
        if rec.get("prioriteit") == "hoog" and rec["deliveredStatus"] != "delivered":
            rec["riskFlags"].append("hoog-prioriteit niet automatisch geleverd")

    # ----------------------------- derivation-ops ----------------------------- #
    def _op_echo_input(self, rec, binding, item, params):
        rec["values"] = {
            "btoM2": self.bto_m2,
            "btoHa": round(self.bto_m2 / 10000, 2),
            "bbox28992": [round(v, 1) for v in self.bbox],
            "perimeterM": round(self.aoi_geom.length, 1),
        }
        rec["layerRef"] = self._write_layer("plangrens", self.aoi_fc["features"])
        rec["deliveredStatus"] = "delivered"
        self._set_prov(rec, binding, None, derived=True)

    def _op_representative_point(self, rec, binding, item, params):
        from pyproj import Transformer

        p = self.aoi_geom.representative_point()
        lon, lat = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True).transform(p.x, p.y)
        rec["values"] = {"rdX": round(p.x, 2), "rdY": round(p.y, 2),
                         "lon": round(lon, 6), "lat": round(lat, 6)}
        rec["deliveredStatus"] = "delivered"
        self._set_prov(rec, binding, None, derived=True)

    def _clip_based(self, rec, binding, item, params):
        sid = binding["serviceRefs"][0]
        colls = params.get("collections") or [params.get("collection") or params.get("typeName")]
        all_feats, src_n, hist = [], 0, 0
        layer = None
        for coll in colls:
            layer = self._layer(sid, coll)
            if not self._ok(layer):
                rec["deliveredStatus"] = "not-delivered"
                rec["notes"].append(f"bronlaag {coll} niet beschikbaar: {layer['error']}")
                return
            fc, dropped = _current_only(layer["fc"], sid)
            hist += dropped
            feats, n = _clip(fc, self.aoi_geom)
            all_feats.extend(feats)
            src_n += n
        feats = all_feats
        values = {"featureCount": len(feats), "sourceFeatureCount": src_n}
        if hist:
            values["historicalObjectsFiltered"] = hist
        cap = (self.reg.sources_by_id.get(sid) or {}).get("maxFeaturesWithoutPagination")
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
        rec["layerRef"] = self._write_layer(_slugify(item["id"]), feats)
        rec["deliveredStatus"] = "delivered"
        self._set_prov(rec, binding, layer)

    _op_clip_layer = _clip_based
    _op_clip_stats = _clip_based
    _op_count_in_aoi = _clip_based

    def _op_list_in_aoi(self, rec, binding, item, params):
        sid = binding["serviceRefs"][0]
        coll = params.get("collection") or params.get("typeName")
        layer = self._layer(sid, coll)
        if not self._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"bronlaag niet beschikbaar: {layer['error']}")
            return
        fc, _dropped = _current_only(layer["fc"], sid)
        feats, src_n = _clip(fc, self.aoi_geom)
        fields = params.get("fields") or ["ci_citation"]
        rows = [{k: (f.get("properties") or {}).get(k) for k in fields
                 if k in (f.get("properties") or {})} for f in feats[:250]]
        rec["values"] = {"count": len(feats), "sourceFeatureCount": src_n,
                         "list": rows, "listCap": 250}
        rec["layerRef"] = self._write_layer(_slugify(item["id"]), feats)
        rec["deliveredStatus"] = "delivered"
        self._set_prov(rec, binding, layer)

    def _op_presence(self, rec, binding, item, params):
        sid = binding["serviceRefs"][0]
        # bij afstandsbepaling de laag landelijk ophalen (geen bbox-beperking)
        layer = self._layer(sid, None, use_bbox=not params.get("maxDistanceKm"))
        if not self._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"bronlaag niet beschikbaar: {layer['error']}")
            return
        feats, _src = _clip(layer["fc"], self.aoi_geom)
        values = {"overlapFeatureCount": len(feats)}
        if feats and feats[0].get("geometry", {}).get("type") in ("Polygon", "MultiPolygon"):
            values["overlapM2"] = round(_area_m2(feats), 1)
        if params.get("maxDistanceKm"):
            best = None
            for f in layer["fc"].get("features", []):
                if f.get("geometry") is None:
                    continue
                d = _geom(f).distance(self.aoi_geom) / 1000.0
                if best is None or d < best:
                    best = d
            values["distanceToNearestKm"] = round(best, 2) if best is not None else None
            values["presence"] = bool(feats)
        rec["values"].update(values)
        if feats:
            rec["layerRef"] = self._write_layer(_slugify(item["id"]), feats)
        rec["deliveredStatus"] = "delivered"
        self._set_prov(rec, binding, layer)

    def _op_proxy_ratio(self, rec, binding, item, params):
        stat_field = params.get("statField")
        if stat_field:  # CBS-buurtstatistiek, oppervlaktegewogen
            layer = self._layer("pdok-cbs-wijkenbuurten-2024", None, cbs=True)
            if not self._ok(layer):
                rec["deliveredStatus"] = "not-delivered"
                rec["notes"].append(f"CBS niet beschikbaar: {layer['error']}")
                return
            tot_w, tot_a = 0.0, 0.0
            for f in layer["fc"].get("features", []):
                inter = _geom(f).buffer(0).intersection(self.aoi_geom)
                if inter.is_empty:
                    continue
                v = (f.get("properties") or {}).get(stat_field)
                if isinstance(v, (int, float)) and v not in CBS_SENTINELS:
                    tot_w += float(v) * inter.area
                    tot_a += inter.area
            rec["values"] = {
                "statField": stat_field,
                "estimate": round(tot_w / tot_a, 1) if tot_a else None,
                "method": "oppervlaktegewogen CBS 2024 buurtstatistiek binnen plangrens",
            }
            rec["deliveredStatus"] = "delivered"
            self._set_prov(rec, binding, layer)
            return

        num = params.get("numerator")
        if num == "vbo_oppervlakte_sum":
            layer = self._layer("pdok-bag-wfs", "bag:verblijfsobject")
            if not self._ok(layer):
                rec["deliveredStatus"] = "not-delivered"
                rec["notes"].append(f"BAG niet beschikbaar: {layer['error']}")
                return
            feats, _ = _clip(layer["fc"], self.aoi_geom)
            area_sum = sum(float((f.get("properties") or {}).get("oppervlakte") or 0) for f in feats)
            rec["values"] = {"fsiProxy": round(area_sum / self.bto_m2, 4) if self.bto_m2 else None,
                             "vboOppervlakteM2": round(area_sum, 1)}
        elif num == "begroeid_terreindeel_m2":
            layer = self._layer("pdok-bgt-ogc-api", "begroeidterreindeel")
            if not self._ok(layer):
                rec["deliveredStatus"] = "not-delivered"
                rec["notes"].append(f"BGT niet beschikbaar: {layer['error']}")
                return
            fc, _hist = _current_only(layer["fc"], "pdok-bgt-ogc-api")
            feats, _ = _clip(fc, self.aoi_geom)
            groen = _area_m2(feats)
            rec["values"] = {"gsiProxy": round(groen / self.bto_m2, 4) if self.bto_m2 else None,
                             "begroeidTerreindeelM2": round(groen, 1)}
        else:
            raise _FetchLayerError(f"onbekende proxy_ratio {num}")
        rec["deliveredStatus"] = "delivered"
        self._set_prov(rec, binding, layer)

    def _op_proxy_entropy(self, rec, binding, item, params):
        layer = self._layer("pdok-bag-wfs", "bag:verblijfsobject")
        if not self._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"BAG niet beschikbaar: {layer['error']}")
            return
        feats, _ = _clip(layer["fc"], self.aoi_geom)
        rec["values"] = {"mxiProxy": _entropy_norm(feats, params.get("field", "gebruiksdoel")),
                         "method": "genormaliseerde Shannon-entropy van gebruiksdoelen"}
        rec["deliveredStatus"] = "delivered"
        self._set_prov(rec, binding, layer)


def summarize(records: list[dict]) -> dict:
    by_status = Counter(r["bindingStatus"] for r in records)
    by_delivered = Counter(r["deliveredStatus"] for r in records)
    hoog = [r for r in records if r.get("prioriteit") == "hoog"]
    d = sum(1 for r in hoog if r["deliveredStatus"] == "delivered")
    return {
        "itemCount": len(records),
        "bindingStatus": dict(by_status),
        "deliveredStatus": dict(by_delivered),
        "autoCoverageOfHoog": {"hoog": len(hoog), "delivered": d,
                               "pct": round(100 * d / len(hoog), 1) if hoog else None},
        "hoogPrioriteitNotDelivered": [r["lijstItemId"] for r in hoog
                                       if r["deliveredStatus"] != "delivered"],
    }


def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")
