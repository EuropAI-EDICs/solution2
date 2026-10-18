"""PoC-5-checklist: MiniGIM-bindingen op de fundament-executor (M2).

De generieke executie (bindingen, faal-isolatie, lagen, prov) staat in
fundament.executor; hier staan alleen de PoC-specifieke derivaties
(proxy_ratio/proxy_entropy met vaste bron-ids en het Breda-CBS-filter) en de
re-exports die ils.py/tests/run.py gebruiken. Doctrine onveranderd: falen
degradeert, breekt nooit, faket nooit.
"""

from __future__ import annotations

import math

from fundament.derivations import (CBS_SENTINELS, _area_m2, _breakdown, _clip,
                                   _current_only, _entropy_norm, _geom,
                                   _histogram, _length_km, summarize)
from fundament.executor import BindingExecutor
from fundament.ops import DEFAULT_OPS

from .fetch import OGC_FILTER_BREDA, fetch_layer

__all__ = ["ChecklistRunner", "summarize", "_clip", "_current_only", "_geom",
           "OGC_FILTER_BREDA", "fetch_layer"]


def _patchable_fetch(source, bbox=None, refresh=False, cbs_filter=None):
    """Module-global `fetch_layer` blijft de test-seam (mock.patch.object)."""
    return fetch_layer(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter)


class _FetchLayerError(RuntimeError):
    """Bronlaag kon niet worden opgehaald (faal-isolatie per item)."""


def _op_proxy_ratio(ex, rec, binding, item, params):
    stat_field = params.get("statField")
    if stat_field:  # CBS-buurtstatistiek, oppervlaktegewogen
        layer = ex._layer("pdok-cbs-wijkenbuurten-2024", None, cbs=True)
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"CBS niet beschikbaar: {layer['error']}")
            return
        tot_w, tot_a = 0.0, 0.0
        for f in layer["fc"].get("features", []):
            inter = _geom(f).buffer(0).intersection(ex.aoi_geom)
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
        ex._set_prov(rec, binding, layer)
        return

    num = params.get("numerator")
    if num == "vbo_oppervlakte_sum":
        layer = ex._layer("pdok-bag-wfs", "bag:verblijfsobject")
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"BAG niet beschikbaar: {layer['error']}")
            return
        feats, _ = _clip(layer["fc"], ex.aoi_geom)
        area_sum = sum(float((f.get("properties") or {}).get("oppervlakte") or 0) for f in feats)
        rec["values"] = {"fsiProxy": round(area_sum / ex.bto_m2, 4) if ex.bto_m2 else None,
                         "vboOppervlakteM2": round(area_sum, 1)}
    elif num == "begroeid_terreindeel_m2":
        layer = ex._layer("pdok-bgt-ogc-api", "begroeidterreindeel")
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"BGT niet beschikbaar: {layer['error']}")
            return
        fc, _hist = _current_only(layer["fc"], "pdok-bgt-ogc-api")
        feats, _ = _clip(fc, ex.aoi_geom)
        groen = _area_m2(feats)
        rec["values"] = {"gsiProxy": round(groen / ex.bto_m2, 4) if ex.bto_m2 else None,
                         "begroeidTerreindeelM2": round(groen, 1)}
    else:
        raise _FetchLayerError(f"onbekende proxy_ratio {num}")
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


def _op_proxy_entropy(ex, rec, binding, item, params):
    layer = ex._layer("pdok-bag-wfs", "bag:verblijfsobject")
    if not ex._ok(layer):
        rec["deliveredStatus"] = "not-delivered"
        rec["notes"].append(f"BAG niet beschikbaar: {layer['error']}")
        return
    feats, _ = _clip(layer["fc"], ex.aoi_geom)
    rec["values"] = {"mxiProxy": _entropy_norm(feats, params.get("field", "gebruiksdoel")),
                     "method": "genormaliseerde Shannon-entropy van gebruiksdoelen"}
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


MINIGIM_OPS = {**DEFAULT_OPS,
               "proxy_ratio": _op_proxy_ratio,
               "proxy_entropy": _op_proxy_entropy}


class ChecklistRunner(BindingExecutor):
    """PoC-5-bindingen: zelfde constructor-signatuur als vóór de refactor."""

    def __init__(self, registry, aoi_fc, runs_dir, refresh: bool = False):
        super().__init__(registry, aoi_fc, runs_dir, refresh=refresh,
                         fetch_fn=_patchable_fetch, cbs_filter=OGC_FILTER_BREDA,
                         ops=MINIGIM_OPS)
