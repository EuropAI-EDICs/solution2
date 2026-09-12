"""Animated hex map: cells that change colour over time (PoC-3 fase 2e).

One offline Leaflet page per time-stepped phenomenon (waterkwaliteit per
month, waterpeilen per day): slider + play cursor, per-cell per-step
values recolour live. All H3 work goes through the nldt bridge
(``h3-spatial-join-points`` for the location→cell mapping,
``h3-cells-to-geojson`` for boundaries) — no direct h3 import, same
convention as ``h3report``.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from shapely.geometry import mapping, shape
from shapely.ops import transform as sh_transform, unary_union

try:
    from pyproj import Transformer
except ImportError:  # pragma: no cover
    Transformer = None  # type: ignore

__all__ = ["build_cell_steps", "render_hexmap_time"]

_TO_WGS84 = None


def _transformer():
    global _TO_WGS84
    if _TO_WGS84 is None:
        if Transformer is None:
            raise RuntimeError("pyproj is required for hexmap_time")
        _TO_WGS84 = Transformer.from_crs("EPSG:28992", "EPSG:4326",
                                         always_xy=True)
    return _TO_WGS84


def _to_wgs(x: float, y: float):
    """RD → WGS84, with a pass-through for coordinates that already are
    degrees (the AGOL peil archive stores WGS84, WKP data RD)."""
    if abs(float(x)) <= 360 and abs(float(y)) <= 90:
        return float(x), float(y)
    return _transformer().transform(float(x), float(y))


def build_cell_steps(
    *,
    locations: Sequence[Mapping[str, Any]],
    resolution: int = 8,
    call=None,
) -> Optional[Dict[str, Any]]:
    """Locations with aligned per-step values → per-cell per-step medians.

    ``locations``: ``[{"x": rd_x, "y": rd_y, "values": [v|null, ...]}]``
    (all aligned to one step list, RD coordinates). The location→cell map
    is computed once via the bridge (convex hull of the points as the
    join polygon); per cell per step the median over present location
    values. Returns ``{"cells_fc", "values", "nSteps"}`` or None without
    a bridge.
    """
    if call is None or not locations:
        return None
    pts_wgs = [_to_wgs(l["x"], l["y"]) for l in locations]
    points_fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"i": i},
         "geometry": {"type": "Point", "coordinates": [round(x, 6), round(y, 6)]}}
        for i, (x, y) in enumerate(pts_wgs)]}
    hull = unary_union([shape(f["geometry"]) for f in points_fc["features"]]
                       ).convex_hull
    hull_fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": mapping(hull)}]}
    join = call("h3-spatial-join-points",
                {"points": points_fc, "polygon": hull_fc,
                 "resolution": resolution})["join"]
    loc_cell = {r["index"]: r["cell"] for r in join.get("perPoint", [])
                if r.get("inCells")}
    if not loc_cell:
        raise ValueError("geen locaties vielen in een cel "
                         "(coördinaten of polygon controleren)")

    n_steps = max(len(l["values"]) for l in locations)
    per_cell: Dict[str, List[List[float]]] = {}
    for i, loc in enumerate(locations):
        cell = loc_cell.get(i)
        if cell is None:
            continue
        slots = per_cell.setdefault(cell, [[] for _ in range(n_steps)])
        for t, v in enumerate(loc["values"]):
            if v is not None:
                slots[t].append(float(v))
    if not per_cell:
        return None

    values = {}
    for cell, slots in per_cell.items():
        values[cell] = [round(statistics.median(s), 4) if s else None
                        for s in slots]
    cells_fc = call("h3-cells-to-geojson",
                    {"cells": sorted(per_cell)})["features"]
    return {"cells_fc": cells_fc, "values": values, "nSteps": n_steps}


_TEMPLATE = """<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<style>
  body {{ margin: 0; font: 14px/1.45 "Segoe UI", system-ui, sans-serif; color: #1a2330; }}
  #map {{ height: 100vh; }}
  .panel {{ position: absolute; z-index: 1000; left: 12px; right: 12px; top: 12px;
            max-width: 460px; background: rgba(255,255,255,.95); padding: 10px 12px;
            border-radius: 8px; box-shadow: 0 1px 6px rgba(0,0,0,.22); }}
  .panel h1 {{ margin: 0 0 4px; font-size: 15px; font-weight: 650; }}
  .panel .step {{ font-size: 17px; font-weight: 700; color: #2563eb; margin: 2px 0 6px; }}
  .panel input[type=range] {{ width: 100%; accent-color: #2563eb; }}
  .panel .row {{ display: flex; gap: 10px; align-items: center; }}
  .panel button {{ font: inherit; font-weight: 600; color: #2563eb; background: #fff;
                   border: 1px solid #c6cdd6; border-radius: 6px; padding: 4px 10px;
                   cursor: pointer; }}
  .legend {{ background: rgba(255,255,255,.96); padding: 10px 12px; border-radius: 8px;
             box-shadow: 0 1px 6px rgba(0,0,0,.22); min-width: 220px; }}
  .legend .title {{ font-weight: 650; margin-bottom: 4px; }}
  .legend .row {{ display: flex; align-items: flex-start; gap: 8px; margin: 3px 0; font-size: 12px; }}
  .legend .swatch {{ flex: 0 0 16px; width: 16px; height: 16px; border-radius: 3px;
                     box-shadow: inset 0 0 0 1px rgba(0,0,0,.12); }}
  .legend .note {{ margin-top: 6px; font-size: 11px; color: #5b6472; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <h1>{title}</h1>
  <div class="step" id="step-label"></div>
  <div class="row">
    <button id="play" title="Speel de tijdstappen af">&#9654; Afspelen</button>
    <input type="range" id="slider" min="0" max="{n_steps_1}" value="0" step="1">
  </div>
</div>
<script type="application/json" id="cells-data">{payload}</script>
<script type="application/json" id="anim-meta">{meta}</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
(function () {{
  var mapEl = document.getElementById('map');
  if (typeof L === 'undefined') {{
    mapEl.innerHTML = '<div style="padding:24px;color:#5b6472;font-size:14px">' +
      'Leaflet kon niet geladen worden (CDN onbereikbaar); de per-cel waarden '
      'staan in het JSON-artefact.</div>';
    mapEl.style.height = 'auto'; return;
  }}
  var fc = JSON.parse(document.getElementById('cells-data').textContent);
  var meta = JSON.parse(document.getElementById('anim-meta').textContent);
  var steps = meta.steps;
  var cells = meta.cells;
  var span = (meta.max - meta.min) || 1;
  function ramp (v) {{
    if (v === null || v === undefined) return '#d8dde3';
    var t = Math.max(0, Math.min(1, (v - meta.min) / span));
    if (meta.invert) t = 1 - t;
    return 'hsl(' + Math.round(110 * (1 - t)) + ', 72%, 46%)';
  }}
  var map = L.map('map', {{zoomSnap: 0.25}});
  L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);
  var layer = L.geoJSON(fc, {{
    style: function (f) {{ return {{color: ramp(null), weight: 0, fillOpacity: 0.85}}; }},
    onEachFeature: function (f, lyr) {{
      lyr.bindPopup('<b>cel ' + f.properties.cell + '</b><br>' +
        '<span id="pv-' + f.properties.cell + '"></span>');
    }}
  }}).addTo(map);
  if (fc.features && fc.features.length) map.fitBounds(layer.getBounds().pad(0.08));

  var slider = document.getElementById('slider');
  var label = document.getElementById('step-label');
  function setStep (i) {{
    layer.eachLayer(function (lyr) {{
      var cell = lyr.feature.properties.cell;
      var v = cells[cell] ? cells[cell][i] : null;
      lyr.setStyle({{fillColor: ramp(v), fillOpacity: v === null ? 0.25 : 0.85}});
      var pv = document.getElementById('pv-' + cell);
      if (pv) pv.textContent = steps[i] + ': ' +
        (v === null ? 'geen meting' : v + ' ' + meta.unit);
    }});
    label.textContent = steps[i];
    slider.value = i;
  }}
  slider.addEventListener('input', function () {{ stop(); setStep(+slider.value); }});

  var playBtn = document.getElementById('play');
  var timer = null;
  function stop () {{
    if (timer) {{ clearInterval(timer); timer = null; }}
    playBtn.innerHTML = '&#9654; Afspelen';
  }}
  playBtn.addEventListener('click', function () {{
    if (timer) {{ stop(); return; }}
    playBtn.innerHTML = '&#9632; Stoppen';
    var i = +slider.value;
    timer = setInterval(function () {{
      i = (i + 1) % steps.length;
      setStep(i);
    }}, {interval_ms});
  }});

  setStep(0);
}})();
</script>
</body>
</html>
"""


def render_hexmap_time(
    bundle: Mapping[str, Any],
    *,
    steps: Sequence[str],
    title: str,
    value_label: str,
    unit: str,
    vmin: float,
    vmax: float,
    invert: bool = False,
    stops: Optional[Sequence[Tuple[float, str]]] = None,
    step_interval_ms: int = 700,
    out_path: Optional[Path] = None,
) -> str:
    """Render the ``build_cell_steps`` bundle as an animated hex map."""
    stops = stops or [(0.0, "Laag"), (0.5, "Midden"), (1.0, "Hoog")]

    def _sw(t: float) -> str:
        # mirror the JS ramp for the legend swatches
        tt = max(0.0, min(1.0, t))
        if invert:
            tt = 1 - tt
        return f"hsl({round(110 * (1 - tt))}, 72%, 46%)"

    meta = {
        "steps": list(steps),
        "cells": bundle["values"],
        "min": vmin, "max": vmax, "invert": invert, "unit": unit,
    }
    legend_rows = "".join(
        f'<div class="row"><span class="swatch" style="background:{_sw(t)}">'
        f'</span><span>{label}</span></div>' for t, label in stops)
    meta_html = (
        f'<div class="legend" style="position:absolute;z-index:1000;'
        f'right:12px;bottom:20px;"><div class="title">{value_label}</div>'
        f'{legend_rows}'
        f'<div class="note">Kleur = waarde per cel per tijdstap '
        f'(mediaan over meetlocaties in de cel); grijze cellen hebben '
        f'die stap geen meting.</div></div>')
    html = _TEMPLATE.format(
        title=title,
        n_steps_1=max(0, bundle["nSteps"] - 1),
        payload=json.dumps(bundle["cells_fc"], ensure_ascii=False)
        .replace("<", "\\u003c"),
        meta=json.dumps(meta, ensure_ascii=False).replace("<", "\\u003c"),
        interval_ms=step_interval_ms,
    )
    # insert the legend before the closing body tag (kept out of .format
    # because the legend contains braces-free html but simpler to append)
    html = html.replace("</body>", meta_html + "</body>")
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    return html
