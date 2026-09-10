"""Single-file offline Leaflet hex map for H3 overlay artifacts.

Same idiom as pipeline/report_template.html (Leaflet via CDN with a text
fallback when offline): choropleth over one numeric property per cell,
popup with the cell id and value. No build step, no jinja — the geojson
is embedded as a JSON script block.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<style>
  body {{ margin: 0; font: 14px/1.4 system-ui, sans-serif; }}
  #map {{ height: 100vh; }}
  .legend {{ background: #fff; padding: 8px 10px; border-radius: 6px;
             box-shadow: 0 1px 4px rgba(0,0,0,.3); }}
  .legend .swatch {{ display: inline-block; width: 14px; height: 14px;
                     margin-right: 6px; border-radius: 3px; vertical-align: -2px; }}
</style>
</head>
<body>
<div id="map"></div>
<script type="application/json" id="cells-data">{payload}</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
(function () {{
  var mapEl = document.getElementById('map');
  if (typeof L === 'undefined') {{
    mapEl.innerHTML = '<div style="padding:24px;color:#5b6472;font-size:14px">' +
      'Leaflet could not be loaded (CDN unreachable). The per-cell table in ' +
      'h3-crosstrack.json carries the same information.</div>';
    mapEl.style.height = 'auto';
    return;
  }}
  var cells = JSON.parse(document.getElementById('cells-data').textContent);
  var prop = {value_property_json};
  function ramp(v) {{
    v = Math.max(0, Math.min(1, v));
    return 'hsl(' + Math.round(110 * (1 - v)) + ', 72%, 48%)';
  }}
  var layer = L.geoJSON(cells, {{
    style: function (f) {{
      var v = Number(f.properties[prop] || 0);
      return {{color: '#37474f', weight: 0.8, fillColor: ramp(v),
              fillOpacity: 0.75}};
    }},
    onEachFeature: function (f, lyr) {{
      var p = f.properties;
      lyr.bindPopup('<b>' + p.cell + '</b><br>' +
        prop + ': ' + (p[prop] !== undefined ? p[prop] : 'n/a') +
        (p.inZoneFraction !== undefined
          ? '<br>in zone: ' + p.inZoneFraction : ''));
    }}
  }}).addTo(map);
  map.fitBounds(layer.getBounds().pad(0.06));
  var legend = L.control({{position: 'bottomright'}});
  legend.onAdd = function () {{
    var d = L.DomUtil.create('div', 'legend');
    var html = '<b>{value_label}</b><br>';
    for (var i = 0; i <= 4; i++) {{
      var v = i / 4;
      html += '<span class="swatch" style="background:' + ramp(v) + '"></span>' +
              (v).toFixed(2) + (i < 4 ? '<br>' : '');
    }}
    d.innerHTML = html;
    return d;
  }};
  legend.addTo(map);
}})();
</script>
</body>
</html>
"""


def render_hex_map(
    cells_fc: Dict[str, Any],
    *,
    title: str,
    value_property: str = "conflictFraction",
    value_label: Optional[str] = None,
    out_path: Optional[Path] = None,
) -> str:
    """Render a cell FeatureCollection to a standalone hex-choropleth map."""
    html = _TEMPLATE.format(
        title=title,
        payload=json.dumps(cells_fc, ensure_ascii=False),
        value_property_json=json.dumps(value_property),
        value_label=value_label or value_property,
    )
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    return html
