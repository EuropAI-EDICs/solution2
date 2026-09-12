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

__all__ = ["build_cell_steps", "render_hexmap_time",
           "render_hexmap_time_multi"]

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


def _p90(xs: Sequence[float]) -> float:
    # numpy-stijl lineaire interpolatie; voldoende voor een kleurschaal
    if not xs:
        return 0.0
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = 0.9 * (len(s) - 1)
    lo = int(pos)
    return s[lo] + (s[min(lo + 1, len(s) - 1)] - s[lo]) * (pos - lo)


def build_trend_series(
    values: Mapping[str, Sequence[Optional[float]]],
    months: Sequence[str],
    *,
    min_overlap: int = 2,
) -> Optional[Dict[str, Any]]:
    """Verandering per cel t.o.v. het eerste jaar (H3-cel als stabiele
    sleutel over de tijd).

    Per cel en eindjaar: mediaan over kalendermaanden van
    waarde(eindjaar, maand) − waarde(eerste jaar, maand); alleen
    maanden die in beide jaren gemeten zijn (≥ ``min_overlap``, anders
    geen uitspraak). ``months``: ISO "YYYY-MM" per stap. Kleurschaal
    ``q`` per jaar: P90 van |delta| over cellen, symmetrisch rond 0.
    """
    n_steps = max((len(s) for s in values.values()), default=0)
    if not values or not months or len(months) != n_steps:
        return None
    years = sorted({int(m[:4]) for m in months})
    end_years = [y for y in years if y > years[0]]
    if not end_years:
        return None
    per_cell: Dict[str, Dict[int, float]] = {}
    for cell, series in values.items():
        by_ym = {(int(months[t][:4]), int(months[t][5:7])): float(v)
                 for t, v in enumerate(series) if v is not None}
        deltas = {}
        for ey in end_years:
            diffs = [by_ym[(ey, m)] - by_ym[(years[0], m)]
                     for m in range(1, 13)
                     if (ey, m) in by_ym and (years[0], m) in by_ym]
            if len(diffs) >= min_overlap:
                deltas[ey] = round(statistics.median(diffs), 4)
        if deltas:
            per_cell[cell] = deltas
    q: Dict[str, float] = {}
    for ey in end_years:
        ds = [abs(d[ey]) for d in per_cell.values() if ey in d]
        q[str(ey)] = round(_p90(ds), 4) if len(ds) >= 4 else 0.0
    return {
        "baseYear": years[0],
        "years": end_years,
        "q": q,
        "cells": {c: {str(y): d for y, d in ds.items()}
                  for c, ds in per_cell.items()},
    }


def build_morans_series(
    values: Mapping[str, Sequence[Optional[float]]],
    *,
    call,
    permutations: int = 199,
) -> Optional[List[Any]]:
    """Global Moran's I per tijdstap, via het nldt-proces (H3-grid-
    buurschap). Stappen met minder dan 3 gevulde cellen krijgen null:
    dan is autocorrelatie niet gedefinieerd."""
    if call is None or not values:
        return None
    n_steps = max(len(s) for s in values.values())
    series: List[Any] = []
    for t in range(n_steps):
        vals = {c: s[t] for c, s in values.items()
                if t < len(s) and s[t] is not None}
        if len(vals) < 3:
            series.append(None)
            continue
        stats = call("h3-morans-i",
                     {"values": vals,
                      "permutations": permutations})["statistics"]
        series.append({"I": stats.get("moransI"),
                       "p": stats.get("pValue")})
    return series


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
    # de legenda is statisch voor de single-renderer; na de scripts
    # invoegen is dus veilig (geen JS leest deze elementen)
    html = html.replace("</body>", meta_html + "</body>")
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    return html


_MULTI_TEMPLATE = """<!doctype html>
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
  .panel select {{ font: inherit; max-width: 100%; margin: 2px 0 6px;
                   padding: 4px 6px; border-radius: 6px; border: 1px solid #c6cdd6; }}
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
  <select id="param" aria-label="Parameter"></select>
  <select id="mode" aria-label="Weergave">
    <option value="waarde">Waarde per maand</option>
    <option value="trend">Trend t.o.v. eerste jaar</option>
  </select>
  <div class="step" id="step-label"></div>
  <div class="row">
    <button id="play" title="Speel de tijdstappen af">&#9654; Afspelen</button>
    <input type="range" id="slider" min="0" max="{n_steps_1}" value="0" step="1">
  </div>
  <div id="spark-wrap" style="display:none">
    <svg id="spark" width="100%" height="38" preserveAspectRatio="none"
         role="img" aria-label="Moran's I per maand"></svg>
    <div style="font-size:11px;color:#5b6472;margin:0 0 2px">
      ruimtelijke clustering (Moran's I) per maand — stip = huidige stap</div>
  </div>
</div>
{legend_html}
<script type="application/json" id="anim-data">{payload}</script>
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
  var DATA = JSON.parse(document.getElementById('anim-data').textContent);
  var steps = DATA.steps;
  var sel = document.getElementById('param');
  Object.keys(DATA.params).forEach(function (key, i) {{
    var o = document.createElement('option');
    o.value = key;
    o.textContent = DATA.params[key].label + ' [' + DATA.params[key].unit + ']';
    sel.appendChild(o);
    if (key === DATA.default) sel.selectedIndex = i;
  }});
  var map = L.map('map', {{zoomSnap: 0.25}});
  L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);
  var layer = null, curKey = null, fitted = false;
  var slider = document.getElementById('slider');
  var label = document.getElementById('step-label');
  var modeSel = document.getElementById('mode');
  var trendOpt = modeSel.options[1];
  var MODE = 'waarde';

  function yearOf (i) {{ return +steps[i].split(' ').pop(); }}
  function fmt1 (v) {{
    return Math.abs(v) >= 10 ? String(Math.round(v)) : String(+v.toFixed(1));
  }}
  function rampFor (p) {{
    return function (v) {{
      if (v === null || v === undefined) return '#d8dde3';
      var span = (p.max - p.min) || 1;
      var t = Math.max(0, Math.min(1, (v - p.min) / span));
      if (p.invert) t = 1 - t;
      return 'hsl(' + Math.round(110 * (1 - t)) + ', 72%, 46%)';
    }};
  }}
  function trendYearFor (p, i) {{
    var ys = p.trend.years, y = yearOf(i);
    for (var k = 0; k < ys.length; k++) if (ys[k] >= y) return ys[k];
    return ys[ys.length - 1];
  }}
  function rampTrendFor (p, year) {{
    var q = p.trend.q[String(year)] || 0;
    return function (d) {{
      if (d === null || d === undefined) return '#d8dde3';
      var t = q > 0 ? Math.max(0, Math.min(1, (d + q) / (2 * q))) : 0.5;
      if (p.invert) t = 1 - t;  // t=0 = gunstig einde, als bij rampFor
      return 'hsl(' + Math.round(110 * (1 - t)) + ', 72%, 46%)';
    }};
  }}
  function legendRows (p, year) {{
    var rows = '';
    if (MODE === 'trend' && p.trend) {{
      var q = p.trend.q[String(year)] || 0;
      [[0, 'Gunstig veranderd', -q], [0.5, 'Onveranderd', 0],
       [1, 'Ongunstig veranderd', q]].forEach(function (r) {{
        var b = p.invert ? 1 - r[0] : r[0];
        rows += '<div class="row"><span class="swatch" style="background:' +
          'hsl(' + Math.round(110 * (1 - b)) + ', 72%, 46%)"></span><span>' +
          r[1] + ' — <b>' + fmt1(r[2]) + ' ' + p.unit + '</b></span></div>';
      }});
    }} else {{
      p.stops.forEach(function (s) {{
        var hue = Math.round(110 * (1 - s.b));
        rows += '<div class="row"><span class="swatch" style="background:' +
          'hsl(' + hue + ', 72%, 46%)"></span><span>' + s.label +
          ' — <b>' + s.value + ' ' + p.unit + '</b></span></div>';
      }});
    }}
    return rows;
  }}
  function updateLegend (p, year) {{
    var lr = document.getElementById('legend-rows');
    if (lr) lr.innerHTML = legendRows(p, year);
    var lt = document.getElementById('legend-title');
    if (lt) lt.textContent = p.label +
      (MODE === 'trend' && p.trend ? ' — trend' : '');
  }}
  var SPARK_W = 420, SPARK_H = 38, SPARK_LO = -0.25, SPARK_HI = 1.0;
  function sparkY (I) {{
    return SPARK_H - 3 - ((I - SPARK_LO) / (SPARK_HI - SPARK_LO)) * (SPARK_H - 8);
  }}
  function drawSpark (p) {{
    var wrap = document.getElementById('spark-wrap');
    var svg = document.getElementById('spark');
    if (!svg || !wrap) return;
    if (!p.morans || !p.morans.length) {{ wrap.style.display = 'none'; return; }}
    wrap.style.display = '';
    var n = p.morans.length, pts = [];
    p.morans.forEach(function (m, i) {{
      if (m && m.I !== null && m.I !== undefined)
        pts.push(((i / (n - 1)) * SPARK_W).toFixed(1) + ',' +
                 sparkY(m.I).toFixed(1));
    }});
    var base = sparkY(0).toFixed(1);
    svg.setAttribute('viewBox', '0 0 ' + SPARK_W + ' ' + SPARK_H);
    svg.innerHTML = '<line x1="0" y1="' + base + '" x2="' + SPARK_W +
      '" y2="' + base + '" stroke="#d8dde3" stroke-width="1"/>' +
      '<polyline points="' + pts.join(' ') +
      '" fill="none" stroke="#2563eb" stroke-width="1.5"/>' +
      '<circle id="spark-dot" r="3" fill="#2563eb" cx="0" cy="-10"/>';
  }}
  function moveSparkDot (p, i) {{
    var dot = document.getElementById('spark-dot');
    if (!dot || !p.morans) return;
    var n = p.morans.length, m = p.morans[i];
    dot.setAttribute('cx', ((i / (n - 1)) * SPARK_W).toFixed(1));
    if (m && m.I !== null && m.I !== undefined) {{
      dot.setAttribute('cy', sparkY(m.I).toFixed(1));
      dot.setAttribute('opacity', 1);
    }} else {{
      dot.setAttribute('cy', '-10');
      dot.setAttribute('opacity', 0.25);
    }}
  }}
  function buildLayer (key) {{
    curKey = key;
    var p = DATA.params[key];
    trendOpt.disabled = !p.trend;
    if (trendOpt.disabled && MODE === 'trend') {{
      MODE = 'waarde'; modeSel.value = 'waarde';
    }}
    trendOpt.textContent = p.trend
      ? 'Trend t.o.v. ' + p.trend.baseYear + ' (per kalendermaand)' : 'Trend';
    if (layer) map.removeLayer(layer);
    layer = L.geoJSON(p.fc, {{
      style: function () {{ return {{color: '#d8dde3', weight: 0, fillOpacity: 0.25}}; }},
      onEachFeature: function (f, lyr) {{
        lyr.bindPopup('<b>cel ' + f.properties.cell + '</b><br>' +
          '<span id="pv-' + f.properties.cell + '"></span>');
      }}
    }}).addTo(map);
    if (!fitted && p.fc.features && p.fc.features.length) {{
      map.fitBounds(layer.getBounds().pad(0.08)); fitted = true;
    }}
    drawSpark(p);
  }}
  function setStep (i) {{
    var p = DATA.params[curKey];
    var ramp = rampFor(p);
    var year = (MODE === 'trend' && p.trend) ? trendYearFor(p, i) : null;
    var tramp = year ? rampTrendFor(p, year) : null;
    layer.eachLayer(function (lyr) {{
      var cell = lyr.feature.properties.cell;
      var pv = document.getElementById('pv-' + cell);
      if (tramp) {{
        var d = (p.trend.cells[cell] || {{}})[String(year)];
        lyr.setStyle({{fillColor: tramp(d === undefined ? null : d),
                       fillOpacity: d === undefined ? 0.25 : 0.85}});
        if (pv) pv.textContent = 'trend ' + p.trend.baseYear + ' \u2192 ' + year + ': ' +
          (d === undefined ? 'te weinig jaren'
            : (d > 0 ? '+' : '') + d + ' ' + p.unit);
      }} else {{
        var v = p.cells[cell] ? p.cells[cell][i] : null;
        lyr.setStyle({{fillColor: ramp(v), fillOpacity: v === null ? 0.25 : 0.85}});
        if (pv) pv.textContent = steps[i] + ': ' +
          (v === null ? 'geen meting' : v + ' ' + p.unit);
      }}
    }});
    label.textContent = tramp
      ? ('trend ' + p.trend.baseYear + ' \u2192 ' + year) : steps[i];
    slider.value = i;
    moveSparkDot(p, i);
    updateLegend(p, year);
  }}
  function applyMode () {{
    MODE = modeSel.value;
    var p = DATA.params[curKey];
    var minI = 0;
    if (MODE === 'trend' && p.trend) {{
      for (var i = 0; i < steps.length; i++)
        if (yearOf(i) >= p.trend.years[0]) {{ minI = i; break; }}
    }}
    slider.min = minI;
    setStep(Math.max(minI, +slider.value));
  }}
  modeSel.addEventListener('change', function () {{ stop(); applyMode(); }});
  sel.addEventListener('change', function () {{
    stop(); buildLayer(sel.value); applyMode();
  }});
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
    var i = +slider.value, minI = +slider.min, span = steps.length - minI;
    timer = setInterval(function () {{
      i = minI + (i - minI + 1) % span;
      setStep(i);
    }}, {interval_ms});
  }});
  buildLayer(sel.value);
  applyMode();
}})();
</script>
{legend_html}
</body>
</html>
"""


def _default_stops_labels():
    return [(0.0, "Gunstig"), (0.5, "Mediaan"), (1.0, "Ongunstig")]


def render_hexmap_time_multi(
    bundles: Mapping[str, Mapping[str, Any]],
    *,
    steps: Sequence[str],
    metas: Mapping[str, Mapping[str, Any]],
    default: str,
    title: str,
    stops: Optional[Sequence[Tuple[float, str]]] = None,
    trend: Optional[Mapping[str, Mapping[str, Any]]] = None,
    morans: Optional[Mapping[str, Sequence[Any]]] = None,
    step_interval_ms: int = 700,
    out_path: Optional[Path] = None,
) -> str:
    """One animated hex map with a parameter switcher.

    ``bundles``: {param_key: build_cell_steps bundle}; ``metas``:
    {param_key: {label, unit, vmin, vmax, invert, [stops]}} — per-stof
    stops (b, label) met groen=gunstig; zonder eigen stops gelden
    Gunstig/Mediaan/Ongunstig. ``trend``: {param_key:
    build_trend_series}; ``morans``: {param_key: build_morans_series}
    — beiden optioneel per stof; de UI verbergt wat ontbreekt.
    Gedeelde stappenlijst.
    """
    stops = stops or _default_stops_labels()
    def _sw(t: float, invert: bool) -> str:
        tt = max(0.0, min(1.0, t))
        if invert:
            tt = 1 - tt
        return f"hsl({round(110 * (1 - tt))}, 72%, 46%)"

    def _fmt(v: float) -> str:
        return f"{v:.0f}" if abs(v) >= 10 else f"{v:g}"

    payload = {
        "default": default,
        "steps": list(steps),
        "params": {
            key: {
                "label": metas[key]["label"],
                "unit": metas[key]["unit"],
                "min": metas[key]["vmin"], "max": metas[key]["vmax"],
                "invert": bool(metas[key].get("invert")),
                "stops": [
                    {"b": b,
                     "label": lbl,
                     "value": _fmt(metas[key]["vmin"] +
                                   ((b if not metas[key].get("invert")
                                     else 1.0 - b)
                                    * (metas[key]["vmax"] - metas[key]["vmin"])))}
                    for b, lbl in metas[key].get("stops", stops)
                ],
                "fc": bundles[key]["cells_fc"],
                "cells": bundles[key]["values"],
                "trend": (trend or {}).get(key),
                "morans": (morans or {}).get(key),
            }
            for key in bundles
        },
    }
    legend_html = (
        '<div class="legend" style="position:absolute;z-index:1000;'
        'right:12px;bottom:20px;"><div class="title" id="legend-title"></div>'
        '<div id="legend-rows"></div>'
        '<div class="note" style="margin-top:6px">Groen = gunstig, rood = '
        'ongunstig binnen het eigen gemeten bereik (P10–P90); grijs = '
        'geen meting die stap.</div></div>')
    n_steps = max(b["nSteps"] for b in bundles.values())
    html = _MULTI_TEMPLATE.format(
        title=title,
        n_steps_1=max(0, n_steps - 1),
        payload=json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c"),
        interval_ms=step_interval_ms,
        legend_html=legend_html)
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    return html
