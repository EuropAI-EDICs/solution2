# toolbox-sim/app/play_visualise.py
"""EU LDT Play & Visualise-sim: dataSources + dataLayers (SCENARIO)."""
from __future__ import annotations

import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class SourceConfiguration(BaseModel):
    type: str
    url: str
    headers: list = []


class SecurityConfiguration(BaseModel):
    type: str
    headers: list = []


class DataSourceIn(BaseModel):
    name: str
    sourceConfiguration: SourceConfiguration
    securityConfiguration: SecurityConfiguration


class DataLayerIn(BaseModel):
    name: str
    dataSource: str
    type: str
    configuration: dict = {}


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim play-visualise", docs_url=None, openapi_url=None)
    add_provenance(app, "play-visualise")
    data_sources: dict[str, dict] = {}
    data_layers: dict[str, dict] = {}
    counter = {"n": 0}

    def _next(prefix: str) -> str:
        counter["n"] += 1
        return f"{prefix}-{counter['n']}"

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/dataSources")
    def create_data_source(payload: DataSourceIn, _: dict = Depends(require_bearer)):
        ds_id = _next("ds")
        data_sources[ds_id] = payload.model_dump()
        data_sources[ds_id]["id"] = ds_id
        return data_sources[ds_id]

    @app.post("/api/dataLayers")
    def create_data_layer(payload: DataLayerIn, _: dict = Depends(require_bearer)):
        if payload.dataSource not in data_sources:
            raise HTTPException(status_code=404, detail={"error": "dataSourceNotFound", "description": payload.dataSource})
        dl_id = _next("dl")
        data_layers[dl_id] = payload.model_dump()
        data_layers[dl_id]["id"] = dl_id
        return data_layers[dl_id]

    @app.get("/api/dataLayers/{dl_id}")
    def get_data_layer(dl_id: str, _: dict = Depends(require_bearer)):
        if dl_id not in data_layers:
            raise HTTPException(status_code=404, detail={"error": "dataLayerNotFound", "description": dl_id})
        return data_layers[dl_id]

    @app.get("/ui/map", response_class=HTMLResponse)
    def ui_map():
        """Leesbare kaartviewer over de geregistreerde layers (browser-target, zonder auth)."""
        layers = [
            {
                "id": dl["id"],
                "name": dl["name"],
                "dataSource": dl["dataSource"],
                "url": data_sources.get(dl["dataSource"], {}).get("sourceConfiguration", {}).get("url", ""),
            }
            for dl in data_layers.values()
        ]
        layers_js = json.dumps(layers)
        layers_js = layers_js.replace("</", "<\\/")  # voorkom </script>-uitbraak in inline JSON
        html = """<!doctype html>
<html><head><meta charset="utf-8"><title>toolbox-sim Play &amp; Visualise kaart</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>#map{height:100vh} .layerbox{position:absolute;top:8px;right:8px;z-index:1000;background:#fff;padding:8px;border-radius:6px;font:13px sans-serif}</style>
</head><body><div id="map"></div><div class="layerbox" id="layers"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const LAYERS = __LAYERS__;
const map = L.map('map').setView([52.09, 5.12], 8);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: 'Leaflet | OSM'}).addTo(map);
const box = document.getElementById('layers');
for (const layer of LAYERS) {
  const label = document.createElement('label');
  label.style.display = 'block';
  const cb = document.createElement('input');
  cb.type = 'checkbox'; cb.checked = true;
  fetch(layer.url).then(r => r.json()).then(fc => {
    const g = L.geoJSON(fc, {onEachFeature: (f, popup) => popup.bindPopup(document.createTextNode(JSON.stringify(f.properties || {}, null, 1)))});
    g.addTo(map); cb.addEventListener('change', () => cb.checked ? map.addLayer(g) : map.removeLayer(g));
    label.textContent = ' ' + layer.name;
  }).catch(() => { label.textContent = ' ' + layer.name + ' (bron onbereikbaar)'; });
  label.prepend(cb); box.appendChild(label);
}
</script></body></html>"""
        return HTMLResponse(content=html.replace("__LAYERS__", layers_js))

    return app
