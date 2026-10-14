# toolbox-sim/app/algorithms.py
"""EU LDT algoritmmodel-stubs: echte grondslag waar die bestaat, anders expliciet seeded."""
from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from pathlib import Path

MODEL_IDS = [
    "neighbourhood-energy-demand",
    "building-environmental-footprint",
    "renovation-strategies",
    "urban-planning-vulnerability",
    "urban-mobility",
    "pollution-propagation",
    "police-routing",
]
SYNTHETIC = {"urban-mobility", "pollution-propagation", "police-routing"}
KNMI_ID = "urn:ngsi-ld:WeatherObserved:knmi-260"
PEILEN_ID = "urn:ngsi-ld:WaterObserved:rijnland-peilen-latest"
ZONES = ["utrecht-wind", "utrecht-zon", "utrecht-bos", "eindhoven-bp2op"]


class MissingGround(RuntimeError):
    def __init__(self, need: str):
        super().__init__(need)
        self.need = need


class UnknownModel(KeyError):
    pass


class BadInput(ValueError):
    pass


@dataclass
class Ground:
    knmi: list[dict] | None = None
    peilen: list[dict] | None = None
    eubd: list[dict] | None = None

    def require(self, what: str) -> None:
        if {"knmi": self.knmi, "peilen": self.peilen, "eubd": self.eubd}[what] is None:
            raise MissingGround(what)


def load_ground(fixtures_dir: Path) -> Ground:
    def _read(relpath: str):
        path = fixtures_dir / relpath
        return json.loads(path.read_text()) if path.exists() else None

    temporal = _read("dp-temporal.jsonld") or {}
    return Ground(
        knmi=(temporal.get(KNMI_ID) or {}).get("instances"),
        peilen=(temporal.get(PEILEN_ID) or {}).get("instances"),
        eubd=_read("ngsi-ld/eubd-buildings.jsonld"),
    )


def _seed(*parts) -> float:
    return (zlib.crc32("|".join(str(p) for p in parts).encode()) % 10000) / 10000.0


def _entity_area_m2(entity: dict) -> float:
    """Planar oppervlak in EPSG:28992 (PoC-conventie: rekenen in RD)."""
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform

    geom = shape(entity["location"]["value"])
    to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True).transform
    return transform(to_rd, geom).area


def _eubd_totals(ground: Ground) -> dict:
    ground.require("eubd")
    tiles = {}
    total = 0.0
    for entity in ground.eubd or []:
        area = _entity_area_m2(entity)
        quadkey = entity.get("quadkey", {}).get("value", "?")
        tiles[quadkey] = tiles.get(quadkey, 0.0) + area
        total += area
    return {"tiles": dict(sorted(tiles.items(), key=lambda kv: -kv[1])), "total": total, "count": len(ground.eubd or [])}


def _energy_demand(inputs: dict, ground: Ground) -> dict:
    totals = _eubd_totals(ground)
    intensity = inputs.get("intensity_kwh_per_m2_year")
    if not isinstance(intensity, (int, float)) or intensity <= 0:
        raise BadInput("intensity_kwh_per_m2_year (float > 0) is vereist; de stub verzint geen intensiteit")
    top = {q: round(area * intensity, 1) for q, area in list(totals["tiles"].items())[:10]}
    return {
        "outputs": {
            "kwh_total": round(totals["total"] * intensity, 1),
            "kwh_top10_tiles": top,
            "area_m2_total": round(totals["total"], 1),
            "tile_count": totals["count"],
        },
        "provenance": {
            "areas": "fixtures/ngsi-ld/eubd-buildings.jsonld (bron: exposure.entities, EPSG:28992-planar)",
            "parameter": "intensity_kwh_per_m2_year van aanvrager",
        },
    }


def _footprint(inputs: dict, ground: Ground) -> dict:
    totals = _eubd_totals(ground)
    carbon = inputs.get("carbon_kg_per_m2")
    if not isinstance(carbon, (int, float)) or carbon <= 0:
        raise BadInput("carbon_kg_per_m2 (float > 0) is vereist; de stub verzint geen intensiteit")
    return {
        "outputs": {
            "carbon_kg_total": round(totals["total"] * carbon, 1),
            "area_m2_total": round(totals["total"], 1),
            "tile_count": totals["count"],
        },
        "provenance": {
            "areas": "fixtures/ngsi-ld/eubd-buildings.jsonld (bron: exposure.entities)",
            "parameter": "carbon_kg_per_m2 van aanvrager",
        },
    }


def _renovation(inputs: dict, ground: Ground) -> dict:
    totals = _eubd_totals(ground)
    priority = [{"quadkey": q, "area_m2": round(a, 1)} for q, a in list(totals["tiles"].items())[:10]]
    return {
        "outputs": {
            "priority_by_tile": priority,
            "note": "prioritering op echte tegeloppervlak; pakketkosten zijn bewust niet gesimuleerd",
        },
        "provenance": {"areas": "fixtures/ngsi-ld/eubd-buildings.jsonld (bron: exposure.entities)"},
    }


def _vulnerability(inputs: dict, ground: Ground) -> dict:
    ground.require("peilen")
    values = sorted(float(i["value"]) for i in ground.peilen or [])
    rows = []
    for i in sorted(ground.peilen or [], key=lambda x: x["datasetId"]):
        v = float(i["value"])
        rank = sum(1 for x in values if x <= v) / len(values)
        rows.append({"peilgebied": i["datasetId"], "waterstand_m": v, "index": round(rank, 3)})
    return {
        "outputs": {"peilgebieden": rows},
        "provenance": {
            "source": "fixtures/dp-temporal.jsonld#peilen_latest",
            "method": "percentielrang van waterstand per peilgebied (hoe ondieper/hoger, hoe hoger de index)",
        },
    }


def _mobility(inputs: dict, ground: Ground) -> dict:
    matrix = {a: {b: round(_seed(a, b, "od") * 1000, 1) for b in ZONES} for a in ZONES}
    modal = {z: {"car": round(0.4 + 0.2 * _seed(z, "car"), 2), "bike": round(0.3 + 0.1 * _seed(z, "bike"), 2)} for z in ZONES}
    return {
        "outputs": {"od_matrix_trips_day": matrix, "modal_split_share": modal},
        "provenance": {"syntheticSeed": True, "seed_basis": "crc32(zone|zone|tag)"},
        "synthetic": True,
    }


def _pollution(inputs: dict, ground: Ground) -> dict:
    raster = [[round(_seed("poll", r, c) * 50, 2) for c in range(16)] for r in range(16)]
    return {
        "outputs": {"grid_pm10_ug_m3": raster, "grid": "16x16 placeholder"},
        "provenance": {"syntheticSeed": True, "note": "placeholder voor het GPU-model (Pollution-Propagation-klasse)"},
        "synthetic": True,
    }


def _police(inputs: dict, ground: Ground) -> dict:
    response = {z: round(4 + 8 * _seed(z, "police"), 1) for z in ZONES}
    return {
        "outputs": {"response_minutes_by_zone": response},
        "provenance": {"syntheticSeed": True, "seed_basis": "crc32(zone|police)"},
        "synthetic": True,
    }


_HANDLERS = {
    "neighbourhood-energy-demand": _energy_demand,
    "building-environmental-footprint": _footprint,
    "renovation-strategies": _renovation,
    "urban-planning-vulnerability": _vulnerability,
    "urban-mobility": _mobility,
    "pollution-propagation": _pollution,
    "police-routing": _police,
}


def run_model(name: str, inputs: dict, ground: Ground) -> dict:
    handler = _HANDLERS.get(name)
    if handler is None:
        raise UnknownModel(name)
    result = handler(inputs or {}, ground)
    return {"model": name, "deterministic": True, **result}


def create_app(ground: Ground) -> "FastAPI":
    from fastapi import Depends, FastAPI
    from fastapi.responses import JSONResponse

    from app.guards import add_provenance, require_bearer

    app = FastAPI(title="toolbox-sim algorithms", docs_url=None, openapi_url=None)
    add_provenance(app, "algorithms")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/models")
    def list_models(_: dict = Depends(require_bearer)):
        return {"data": [{"id": m, "synthetic": m in SYNTHETIC} for m in MODEL_IDS]}

    @app.get("/models/{name}")
    def model_meta(name: str, _: dict = Depends(require_bearer)):
        if name not in _HANDLERS:
            return JSONResponse(status_code=404, content={"error": "model-not-found", "description": name})
        return {"id": name, "synthetic": name in SYNTHETIC, "deterministic": True}

    @app.post("/models/{name}/run")
    def run(name: str, inputs: dict, _: dict = Depends(require_bearer)):
        try:
            return run_model(name, inputs, ground)
        except UnknownModel:
            return JSONResponse(status_code=404, content={"error": "model-not-found", "description": name})
        except MissingGround as exc:
            return JSONResponse(status_code=503, content={"error": "missing-ground", "description": exc.need})
        except BadInput as exc:
            return JSONResponse(status_code=422, content={"error": "bad-input", "description": str(exc)})

    return app
