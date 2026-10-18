"""BindingExecutor: voert taak-bindingen deterministisch uit (faal-isolerend).

Generalisatie van poc-minigim ChecklistRunner (PoC-5). Doctrine:
- binding auto/partial → executor levert, met prov; manual → gedocumenteerde
  mens-route; falen degradeert de taak (not-delivered + risicovlag), breekt
  nooit de run en wordt nooit gefaked;
- alle getallen komen uit derivatie-ops; er zit geen LLM in deze laag.

Injectiepunten:
  fetch_fn   : callable(source, bbox=..., refresh=..., cbs_filter=...) -> (fc, manifest)
  cbs_filter : optioneel protocol-filter dat bij cbs=True wordt doorgegeven
  ops        : dict op-naam -> handler(ex, rec, binding, item, params)
"""

from __future__ import annotations

import json
from pathlib import Path

import shapely.geometry as sg

from .derivations import _geom


class BindingExecutor:
    def __init__(self, registry, aoi_fc: dict, runs_dir: Path, refresh: bool = False, *,
                 fetch_fn, cbs_filter: str | None = None, ops: dict):
        self.reg = registry
        self.aoi_fc = aoi_fc
        self.refresh = refresh
        self._fetch_fn = fetch_fn
        self.cbs_filter = cbs_filter
        self.ops = dict(ops)
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
            fc, manifest = self._fetch_fn(
                source, bbox=bbox, refresh=self.refresh,
                cbs_filter=self.cbs_filter if cbs else None,
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
        return [self._execute(i, self.reg.binding(i["id"])) for i in self.reg.tasks()]

    def _execute(self, item: dict, binding: dict) -> dict:
        rec = {
            "lijstItemId": item["id"],
            "thema": item.get("thema"),
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
        handler = self.ops.get(op)
        if handler is None:
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"runner-fout: onbekende derivation-op {op}")
        else:
            try:
                handler(self, rec, binding, item, params)
            except Exception as exc:  # noqa: BLE001 — faal-isolatie per item
                rec["deliveredStatus"] = "not-delivered"
                rec["notes"].append(f"runner-fout: {type(exc).__name__}: {exc}")
        self._flag_risks(rec)
        return rec

    def _flag_risks(self, rec) -> None:
        if rec.get("prioriteit") == "hoog" and rec["deliveredStatus"] != "delivered":
            rec["riskFlags"].append("hoog-prioriteit niet automatisch geleverd")
