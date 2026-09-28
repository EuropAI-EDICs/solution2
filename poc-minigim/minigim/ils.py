"""ILS (Input Grex) draft-gebiedsindeling: deterministisch afgeleid uit open data.

Volgens de MiniGIM-ILS v0.8 worden gebiedsdelen geclassificeerd in een
Niveau 0-3-hiërarchie (uitgeefbaar/mandelig/openbaar → verhard/groen/water →
…). Niveau 0 is een ONTWERPKEUZE: de runner classificeert de *huidige*
situatie (openbare ruimte blijft openbaar; percelen zijn kandidaat-uitgeefbaar)
en laat de definitieve indening aan de ontwerper (v4 pending, draft=true).
Elk feature krijgt ilsNodeId, nodePath, ifcExportAs en de EPset_minigim-
eigenschappen voor zover openbaar afleidbaar ("van wie was je?" = eigendom is
wettelijk geen open data → expliciet null met toelichting).
"""

from __future__ import annotations

import json
from pathlib import Path

import shapely.geometry as sg

from .checklist import _clip, _current_only, _geom

# (bron, laag, BGT-functie-prefix of None) → ILS-node
BGT_MAPPING = [
    ("pdok-bgt-ogc-api", "wegdeel", None, "n2.wegen"),          # onder n1.verhard/n0.openbaar
    ("pdok-bgt-ogc-api", "waterdeel", None, "n2.water"),        # onder n1.water/n0.openbaar
    ("pdok-bgt-ogc-api", "begroeidterreindeel", None, "n1.groen"),
    ("pdok-bgt-ogc-api", "onbegroeidterreindeel", "verhard", "n1.verhard"),
    ("pdok-bgt-ogc-api", "overbruggingsdeel", None, "n2.brug-overbruggingsdeel"),
]


class IlsDraftBuilder:
    def __init__(self, registry, runner):
        """runner: ChecklistRunner (hergebruikt de geclipte lagen uit de cache)."""
        self.reg = registry
        self.runner = runner

    def build(self) -> tuple[dict, list]:
        """Geeft (draft-artifact, per-feature geometrieën) — run.py schrijft beide."""
        features = []          # per ILS-node geaggregeerde summary
        unassigned = {}        # bronclass → {count, areaM2} zonder ILS-node
        out_geometries = []    # per-feature classificatie (output-laag)

        for sid, coll, functie_prefix, node_id in BGT_MAPPING:
            layer = self.runner._layer(sid, coll)
            if not self.runner._ok(layer):
                unassigned[f"{coll}"] = {"count": 0, "areaM2": 0.0, "reason": "bronlaag niet beschikbaar"}
                continue
            fc, _hist = _current_only(layer["fc"], sid)
            clipped, _src = _clip(fc, self.runner.aoi_geom)
            kept, dropped = [], []
            for f in clipped:
                if functie_prefix is None:
                    kept.append(f)
                    continue
                # token-match op functie òf fysiek_voorkomen (live-BGT laat
                # 'functie' bij onbegroeid terrein veelal leeg); prefix-regel:
                # "verharding" telt als verhard, "onverhard" níet
                props = f.get("properties") or {}
                tokens = set()
                for fld in ("functie", "fysiek_voorkomen"):
                    tokens.update(
                        str(props.get(fld) or "").lower().replace(",", " ").replace(";", " ").split()
                    )
                hit = any(t == functie_prefix or t.startswith(functie_prefix) for t in tokens)
                (kept if hit else dropped).append(f)
            if kept:
                self._append(features, out_geometries, node_id, coll, kept)
            if dropped:
                area = 0.0
                for f in dropped:
                    g = _geom(f)
                    if g.geom_type in ("Polygon", "MultiPolygon"):
                        area += g.area
                key = f"{coll}:{functie_prefix}!=match"
                unassigned[key] = {
                    "count": len(dropped), "areaM2": round(area, 1),
                    "reason": "geen passende ILS-node (bijv. onverhard onbegroeid terrein)",
                }

        # kadastrale percelen → n2.percelen (kandidaat uitgeefbaar)
        layer = self.runner._layer("pdok-brk-kadastrale-kaart", "perceel")
        if self.runner._ok(layer):
            clipped, _src = _clip(layer["fc"], self.runner.aoi_geom)
            self._append(features, out_geometries, "n2.percelen", "kadastralekaart:perceel", clipped)
        else:
            unassigned["percelen"] = {"count": 0, "areaM2": 0.0, "reason": "bronlaag niet beschikbaar"}

        # BAG-panden → n3.bebouwd (op percelen)
        layer = self.runner._layer("pdok-bag-wfs", "bag:pand")
        if self.runner._ok(layer):
            clipped, _src = _clip(layer["fc"], self.runner.aoi_geom)
            self._append(features, out_geometries, "n3.bebouwd", "bag:pand", clipped)
        else:
            unassigned["panden"] = {"count": 0, "areaM2": 0.0, "reason": "bronlaag niet beschikbaar"}

        # EPset-minigim: wat is open afleidbaar
        epset_note = (
            "EPset_minigim: 'Wat ben je?' = ILS-label (IfcName); 'Van wie was je?' = "
            "eigendom — wettelijk geen open data (kadastrale percelen geven perceelnummer/"
            "sectie, geen eigenaar) → null; 'Van wie wordt je?' = ontwerpkeuze → null."
        )

        return {
            "ilsVersion": self.reg.ils["sourceVersion"],
            "draft": True,
            "v4": "pending",
            "niveau0Note": (
                "niveau-0 classificatie (uitgeefbaar/mandelig/openbaar) beschrijft de HUIDIGE "
                "situatie (openbare infrastructuur openbaar; percelen kandidaat-uitgeefbaar); "
                "de definitieve gebiedsindeling is een ontwerpbeslissing (v4 pending)"
            ),
            "features": features,
            "unassigned": unassigned,
            "epsetNote": epset_note,
            "geometryFile": "ils-draft.features.28992.geojson",
        }, out_geometries

    def _append(self, features, out_geoms, node_id: str, source_layer: str, feats: list) -> None:
        node = self.reg.ils_nodes.get(node_id)
        if node is None:
            return
        path = " > ".join(self.reg.ils_path_labels(node_id))
        area = 0.0
        for f in feats:
            g = _geom(f)
            if g.geom_type in ("Polygon", "MultiPolygon"):
                area += g.area
            props = dict(f.get("properties") or {})
            props["ilsNodeId"] = node_id
            props["ilsNodePath"] = path
            props["ifcExportAs"] = self.reg.ils_ifc(node_id)
            props["epsetMinigim"] = {
                "watBenJe": node["label"],
                "vanWieWasJe": None,
                "vanWieWordtJe": None,
            }
            out_geoms.append({"type": "Feature", "properties": props, "geometry": f["geometry"]})
        features.append({
            "ilsNodeId": node_id,
            "nodePath": path,
            "level": node["level"],
            "label": node["label"],
            "ifcExportAs": self.reg.ils_ifc(node_id),
            "sourceLayer": source_layer,
            "count": len(feats),
            "areaM2": round(area, 1),
        })

    @staticmethod
    def write(draft: dict, geometries: list, runs_dir: Path) -> None:
        path = runs_dir / "ils-draft.features.28992.geojson"
        fc = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
            "features": geometries,
        }
        path.write_text(json.dumps(fc, ensure_ascii=False) + "\n", encoding="utf-8")
