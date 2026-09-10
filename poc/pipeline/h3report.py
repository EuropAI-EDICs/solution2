"""Single-file offline Leaflet hex map for H3 overlay artifacts.

Same idiom as pipeline/report_template.html (Leaflet via CDN with a text
fallback when offline): choropleth over one numeric property per cell,
popup with the cell id and value. No build step, no jinja — the geojson
is embedded as a JSON script block.

Sparse H3 selections (e.g. a thin Groene contour at res 8) are *stitched*
for display: each measured cell's ``grid_disk`` neighbours are filled in
so adjacent hexes read as one continuous heatmap surface. Stitched cells
are marked ``interpolated`` and never pretend to be measured values. The
H3 work goes through the nldt bridge (``h3-grid-disk`` +
``h3-cells-to-geojson``) — this module never imports h3 itself; without
a bridge ``call`` the map simply renders un-stitched.

Domain copy (legend stops, zone label) is always passed explicitly by the
caller — either a named ``preset`` from ``_LEGEND_PRESETS`` or per-call
``stops``/``zone_label`` — so one PoC's wording can never leak onto
another's map.
"""

from __future__ import annotations

import html as _html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: Plain-language legend presets, keyed by preset NAME (never by property
#: name — several PoCs share ``conflictFraction`` with different domains).
_LEGEND_PRESETS: Dict[str, Dict[str, Any]] = {
    "groene-contour": {
        "title": "Conflict zon × bos",
        "zone_label": "Aandeel in Groene contour",
        "intro": (
            "Elke hexagon dekt een stukje van de Groene contour. De kleur "
            "laat zien welk deel van die hex tegelijk openstaat voor "
            "zonnevelden én voor nieuw natuurzoekgebied — hoe roder, hoe "
            "meer de twee claims elkaar raken. Losse hexen zijn voor de "
            "kaart aangevuld met buurcellen zodat het als aaneengesloten "
            "heatmap leest."
        ),
        "stops": [
            (0.0, "Geen conflict — alleen natuurzoekgebied"),
            (0.25, "Licht conflict"),
            (0.5, "Gedeeld gebied"),
            (0.75, "Sterk conflict"),
            (1.0, "Volledig conflict — ook open voor zon"),
        ],
    },
}

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
  .banner {{
    position: absolute; z-index: 1000; left: 12px; right: 12px; top: 12px;
    max-width: 440px; background: rgba(255,255,255,.94); padding: 10px 12px;
    border-radius: 8px; box-shadow: 0 1px 6px rgba(0,0,0,.22);
  }}
  .banner h1 {{ margin: 0 0 4px; font-size: 15px; font-weight: 650; }}
  .banner p {{ margin: 0; font-size: 12.5px; color: #3d4a5c; }}
  .legend {{
    background: rgba(255,255,255,.96); padding: 10px 12px; border-radius: 8px;
    box-shadow: 0 1px 6px rgba(0,0,0,.22); min-width: 220px; line-height: 1.35;
  }}
  .legend .title {{ font-weight: 650; margin-bottom: 4px; }}
  .legend .intro {{ font-size: 11.5px; color: #3d4a5c; margin: 0 0 8px; max-width: 250px; }}
  .legend .row {{ display: flex; align-items: flex-start; gap: 8px; margin: 3px 0; font-size: 12px; }}
  .legend .swatch {{
    flex: 0 0 16px; width: 16px; height: 16px; border-radius: 3px;
    margin-top: 1px; box-shadow: inset 0 0 0 1px rgba(0,0,0,.12);
  }}
  .legend .label {{ color: #1a2330; }}
  .legend .note {{ margin-top: 8px; font-size: 11px; color: #5b6472; }}
</style>
</head>
<body>
<div id="map"></div>
<script type="application/json" id="cells-data">{payload}</script>
<script type="application/json" id="map-meta">{meta}</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
(function () {{
  var mapEl = document.getElementById('map');
  if (typeof L === 'undefined') {{
    mapEl.innerHTML = '<div style="padding:24px;color:#5b6472;font-size:14px">' +
      'Leaflet kon niet geladen worden (CDN onbereikbaar). De per-cel tabel in ' +
      'het JSON-artefact bevat dezelfde informatie.</div>';
    mapEl.style.height = 'auto';
    return;
  }}
  var cells = JSON.parse(document.getElementById('cells-data').textContent);
  var meta = JSON.parse(document.getElementById('map-meta').textContent);
  var prop = meta.valueProperty;
  var stops = meta.stops || [];

  function ramp(v) {{
    v = Math.max(0, Math.min(1, Number(v) || 0));
    return 'hsl(' + Math.round(110 * (1 - v)) + ', 72%, 46%)';
  }}

  function plainLabel(v) {{
    if (!stops.length) return (Math.round(v * 100)) + '%';
    var best = stops[0], bestD = Math.abs(v - stops[0][0]);
    for (var i = 1; i < stops.length; i++) {{
      var d = Math.abs(v - stops[i][0]);
      if (d < bestD) {{ best = stops[i]; bestD = d; }}
    }}
    return best[1] + ' (' + Math.round(v * 100) + '%)';
  }}

  var banner = L.control({{position: 'topleft'}});
  banner.onAdd = function () {{
    var d = L.DomUtil.create('div', 'banner');
    d.innerHTML = '<h1>' + meta.title + '</h1><p>' + meta.intro + '</p>';
    L.DomEvent.disableClickPropagation(d);
    return d;
  }};

  var map = L.map('map', {{zoomSnap: 0.25}});
  L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);

  // No stroke between neighbours → contiguous heatmap surface.
  var layer = L.geoJSON(cells, {{
    style: function (f) {{
      var v = Number(f.properties[prop] || 0);
      var c = ramp(v);
      var opacity = f.properties.interpolated ? 0.55 : 0.82;
      return {{color: c, weight: 0, fillColor: c, fillOpacity: opacity}};
    }},
    onEachFeature: function (f, lyr) {{
      var p = f.properties;
      var v = Number(p[prop] || 0);
      var zone = (p.inZoneFraction !== undefined && !p.interpolated)
        ? '<br>' + meta.zoneLabel + ': ' + Math.round(p.inZoneFraction * 100) + '%'
        : '';
      var note = p.interpolated
        ? '<br><em style="color:#5b6472">Buurcel (alleen weergave, geen meting)</em>'
        : '';
      lyr.bindPopup(
        '<b>' + plainLabel(v) + '</b>' +
        '<br><span style="color:#5b6472">cel ' + p.cell + '</span>' + zone + note
      );
    }}
  }}).addTo(map);
  if (cells.features && cells.features.length) {{
    map.fitBounds(layer.getBounds().pad(0.08));
  }}
  banner.addTo(map);

  var legend = L.control({{position: 'bottomright'}});
  legend.onAdd = function () {{
    var d = L.DomUtil.create('div', 'legend');
    var html = '<div class="title">' + meta.legendTitle + '</div>';
    html += '<p class="intro">' + meta.legendIntro + '</p>';
    for (var i = 0; i < stops.length; i++) {{
      html += '<div class="row"><span class="swatch" style="background:' +
              ramp(stops[i][0]) + '"></span><span class="label">' +
              stops[i][1] + '</span></div>';
    }}
    html += '<div class="note">Polygoncijfers blijven leidend. Lichtere ' +
            'hexen zijn buurcellen om het vlak aaneen te rijgen — geen ' +
            'extra meting.</div>';
    d.innerHTML = html;
    L.DomEvent.disableClickPropagation(d);
    return d;
  }};
  legend.addTo(map);
}})();
</script>
</body>
</html>
"""


def _stops_for(preset_name: Optional[str],
               stops: Optional[Sequence[Tuple[float, str]]]
               ) -> List[List[Any]]:
    if stops is not None:
        return [[float(v), str(label)] for v, label in stops]
    preset = _LEGEND_PRESETS.get(preset_name or "")
    if preset:
        return [[float(v), str(label)] for v, label in preset["stops"]]
    return [[i / 4, f"{i / 4:.0%}"] for i in range(5)]


def stitch_for_heatmap(
    cells_fc: Dict[str, Any],
    *,
    value_property: str = "conflictFraction",
    ring: int = 1,
    call=None,
) -> Dict[str, Any]:
    """Fill ``grid_disk`` neighbours so sparse cells form contiguous blobs.

    Measured cells keep their values (and their existing geometries).
    Neighbours inherit the max value of adjacent measured cells and are
    flagged ``interpolated=True`` (display only); only the filled cells'
    boundaries are fetched. All H3 work goes through ``call(process_id,
    inputs) -> outputs`` — the nldt bridge (``h3-grid-disk`` +
    ``h3-cells-to-geojson``); this module has no direct h3 dependency.
    Returns the input unchanged when ``call`` is None (offline without
    bridge) or there is nothing to fill.
    """
    if call is None:
        return cells_fc
    feats = list(cells_fc.get("features") or [])
    if not feats:
        return cells_fc

    measured: Dict[str, Dict[str, Any]] = {}
    for feat in feats:
        props = dict(feat.get("properties") or {})
        cell = props.get("cell")
        if cell:
            measured[str(cell)] = props
    if not measured:
        return cells_fc

    disks = call("h3-grid-disk",
                 {"cells": sorted(measured), "ring": ring})["disk"]["disks"]
    filled: Dict[str, Dict[str, Any]] = {}
    for cell, props in measured.items():
        value = float(props.get(value_property) or 0.0)
        for nbr in disks.get(cell, []):
            if nbr in measured:
                continue
            prev = filled.get(nbr)
            if prev is None or value > float(prev.get(value_property) or 0.0):
                filled[nbr] = {
                    value_property: value,
                    "interpolated": True,
                    "inZoneFraction": props.get("inZoneFraction"),
                }

    out_feats = []
    for feat in feats:
        props = dict(feat.get("properties") or {})
        props["interpolated"] = False
        out_feats.append({**feat, "properties": props})
    if filled:
        boundary_fc = call("h3-cells-to-geojson",
                           {"cells": sorted(filled)})["features"]
        by_cell = {f["properties"]["cell"]: f
                   for f in boundary_fc.get("features") or []}
        for cell in sorted(filled):
            feat = by_cell[cell]
            feat["properties"].update(filled[cell])
            out_feats.append(feat)

    result = dict(cells_fc)
    result["features"] = out_feats
    return result


def render_hex_map(
    cells_fc: Dict[str, Any],
    *,
    title: str,
    value_property: str = "conflictFraction",
    value_label: Optional[str] = None,
    preset: Optional[str] = None,
    zone_label: Optional[str] = None,
    intro: Optional[str] = None,
    legend_intro: Optional[str] = None,
    stops: Optional[Sequence[Tuple[float, str]]] = None,
    stitch: bool = True,
    stitch_ring: int = 1,
    call=None,
    out_path: Optional[Path] = None,
) -> str:
    """Render a cell FeatureCollection as a contiguous hex heatmap.

    ``preset`` names a ``_LEGEND_PRESETS`` entry (domain copy: stops,
    intro, zone label); explicit arguments always win over the preset.
    ``call`` is the nldt h3step bridge used for display stitching.
    """
    display_fc = (
        stitch_for_heatmap(cells_fc, value_property=value_property,
                           ring=stitch_ring, call=call)
        if stitch else cells_fc
    )
    preset_doc = _LEGEND_PRESETS.get(preset or "", {})
    meta = {
        "title": title,
        "valueProperty": value_property,
        "legendTitle": value_label or preset_doc.get("title") or value_property,
        "zoneLabel": zone_label or preset_doc.get("zone_label") or "in zone",
        "intro": intro or preset_doc.get("intro") or (
            f"Kleur toont de waarde van «{value_property}» per H3-cel."
        ),
        "legendIntro": legend_intro or (
            "Van groen (laag) naar rood (hoog):"
        ),
        "stops": _stops_for(preset, stops),
    }
    # escape for embedding: "<" as \u003c keeps both JSON blocks valid
    # inside <script> and kills any </script> breakout
    html = _TEMPLATE.format(
        title=_html.escape(title),
        payload=json.dumps(display_fc, ensure_ascii=False).replace("<", "\u003c"),
        meta=json.dumps(meta, ensure_ascii=False).replace("<", "\u003c"),
    )
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    return html
