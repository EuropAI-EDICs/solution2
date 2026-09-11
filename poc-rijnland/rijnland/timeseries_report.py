"""Time-series page for measured water quality (PoC-3 fase 2c).

Renders the monthly WKP fixture (``data/wkp/waterkwaliteit-monthly-
<from>-<to>.json``) as one self-contained offline HTML page: parameter
selector, monthly beheergebied-wide median with P25–P75 band, a 12-month
trend line, a seasonality panel (median per month-of-year) and a play
cursor that sweeps the period. Vanilla SVG + JS only — no CDN, no build
step, same single-file convention as the hex maps.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from rijnland.water_quality import NORMS

TS_VERSION = "poc-rijnland-timeseries/0.1"

__all__ = ["TS_VERSION", "climatology", "rolling_median", "render_timeseries"]

_MONTH_LABELS = ["jan", "feb", "mrt", "apr", "mei", "jun",
                 "jul", "aug", "sep", "okt", "nov", "dec"]


def climatology(rows: List[Mapping[str, Any]]) -> List[Optional[float]]:
    """Median per month-of-year across all years (None for empty months)."""
    by_month: Dict[int, List[float]] = {m: [] for m in range(1, 13)}
    for r in rows:
        by_month[int(r["ym"][5:7])].append(float(r["median"]))
    return [round(statistics.median(v), 4) if v else None
            for _m, v in sorted(by_month.items())]


def rolling_median(rows: List[Mapping[str, Any]], window: int = 12
                   ) -> List[Optional[float]]:
    """Centered rolling median of the monthly medians (None until full)."""
    vals = [float(r["median"]) for r in rows]
    out: List[Optional[float]] = []
    half = window // 2
    for i in range(len(vals)):
        lo, hi = i - half, i + half + 1
        if lo < 0 or hi > len(vals):
            out.append(None)
        else:
            out.append(round(statistics.median(vals[lo:hi]), 4))
    return out


def _unit_of(key: str) -> str:
    parts = key.split("|")
    return parts[2] if len(parts) > 2 else ""


_TEMPLATE = """<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ margin: 0; font: 14px/1.45 "Segoe UI", system-ui, sans-serif;
         color: #1a2330; background: #f4f6f8; }}
  .wrap {{ max-width: 1060px; margin: 0 auto; padding: 18px 16px 40px; }}
  header {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 12px;
            margin-bottom: 10px; }}
  h1 {{ margin: 0; font-size: 19px; font-weight: 650; }}
  .sub {{ color: #5b6472; font-size: 12.5px; }}
  .controls {{ display: flex; gap: 10px; align-items: center; margin: 8px 0 14px; }}
  select, button {{ font: inherit; padding: 6px 10px; border-radius: 6px;
                    border: 1px solid #c6cdd6; background: #fff; }}
  button {{ cursor: pointer; font-weight: 600; color: #2563eb; }}
  button.playing {{ color: #dc2626; }}
  .card {{ background: #fff; border-radius: 10px; padding: 12px 14px 8px;
           box-shadow: 0 1px 6px rgba(0,0,0,.10); margin-bottom: 14px; }}
  .card h2 {{ margin: 2px 0 6px; font-size: 13px; font-weight: 650;
              color: #3d4a5c; }}
  .legend {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px;
             color: #3d4a5c; padding: 2px 6px 8px; }}
  .legend .sw {{ display: inline-block; width: 14px; height: 3px;
                 vertical-align: 3px; margin-right: 5px; border-radius: 2px; }}
  .legend .band {{ width: 14px; height: 10px; vertical-align: -1px; }}
  svg text {{ font-family: inherit; }}
  .note {{ color: #5b6472; font-size: 11.5px; margin: 4px 6px 8px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{title}</h1>
    <span class="sub">{subtitle}</span>
  </header>
  <div class="controls">
    <label class="sub">Parameter
      <select id="param"></select></label>
    <button id="play" title="Beweeg een tijdcursor over de reeks">&#9654; Afspelen</button>
    <span class="sub" id="stats"></span>
  </div>
  <div class="card">
    <h2>Maandmediaan over het beheergebied (P25–P75-band) met 12-maands trendlijn</h2>
    <div class="legend">
      <span><span class="sw" style="background:#1a7f37"></span>maandmediaan</span>
      <span><span class="band" style="background:#9ec9a8; opacity:.45"></span>P25–P75 (spreiding locaties)</span>
      <span><span class="sw" style="background:#1a2330; height:4px"></span>12-maands trend</span>
    </div>
    <svg id="chart" width="100%" height="380" viewBox="0 0 1020 380"
         preserveAspectRatio="none"></svg>
    <div class="note" id="chartnote"></div>
  </div>
  <div class="card">
    <h2>Seizoenscyclus — mediaan per maand van het jaar (alle jaren)</h2>
    <svg id="season" width="100%" height="220" viewBox="0 0 1020 220"></svg>
    <div class="note" id="seasonnote"></div>
  </div>
  <p class="note">{provenance}</p>
</div>
<script type="application/json" id="ts-data">{payload}</script>
<script>
(function () {{
  var DATA = JSON.parse(document.getElementById('ts-data').textContent);
  var LBL = {month_labels_json};
  var chart = document.getElementById('chart');
  var season = document.getElementById('season');
  var sel = document.getElementById('param');
  var stats = document.getElementById('stats');
  var note = document.getElementById('chartnote');
  var snote = document.getElementById('seasonnote');

  DATA.parameters.forEach(function (p, i) {{
    var o = document.createElement('option');
    o.value = p.key; o.textContent = p.label + (p.unit ? ' [' + p.unit + ']' : '');
    if (p.key === DATA.default) sel.selectedIndex = i;
    sel.appendChild(o);
  }});
  sel.addEventListener('change', draw);

  var W = 1020, H = 380, PADL = 64, PADR = 16, PADT = 14, PADB = 30;
  var monthsAll = [];
  Object.keys(DATA.series).forEach(function (k) {{
    DATA.series[k].forEach(function (r) {{
      if (monthsAll.indexOf(r.ym) < 0) monthsAll.push(r.ym);
    }});
  }});
  monthsAll.sort();
  var mIdx = {{}}; monthsAll.forEach(function (m, i) {{ mIdx[m] = i; }});
  var X = function (i) {{ return PADL + i * (W - PADL - PADR) / Math.max(1, monthsAll.length - 1); }};
  var Y = function (v, y0, y1) {{
    var t = (v - y0) / ((y1 - y0) || 1);
    return PADT + (1 - Math.max(0, Math.min(1, t))) * (H - PADT - PADB);
  }};

  function esc (s) {{
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  }}

  function draw () {{
    var key = sel.value;
    var rows = DATA.series[key] || [];
    var meta = DATA.parameters.filter(function (p) {{ return p.key === key; }})[0];
    var xs = rows.map(function (r) {{ return mIdx[r.ym]; }});
    var lo = Math.min.apply(null, rows.map(function (r) {{ return r.p25; }}));
    var hi = Math.max.apply(null, rows.map(function (r) {{ return r.p75; }}));
    var span = (hi - lo) || 1;
    var y0 = lo - span * 0.08, y1 = hi + span * 0.08;

    var parts = [];
    parts.push('<rect x="' + PADL + '" y="' + PADT + '" width="' +
               (W - PADL - PADR) + '" height="' + (H - PADT - PADB) +
               '" fill="#fafbfc" stroke="#e3e7ec"/>');
    // y grid + labels
    for (var g = 0; g <= 4; g++) {{
      var v = y0 + (y1 - y0) * g / 4, yy = Y(v, y0, y1);
      parts.push('<line x1="' + PADL + '" x2="' + (W - PADR) + '" y1="' + yy +
                 '" y2="' + yy + '" stroke="#eef1f4"/>');
      parts.push('<text x="' + (PADL - 8) + '" y="' + (yy + 4) +
                 '" text-anchor="end" font-size="11" fill="#5b6472">' +
                 (Math.round(v * 100) / 100) + '</text>');
    }}
    // year ticks
    var lastYear = null;
    monthsAll.forEach(function (m, i) {{
      var yr = m.slice(0, 4);
      if (yr !== lastYear) {{
        lastYear = yr;
        var xx = X(i);
        parts.push('<line x1="' + xx + '" x2="' + xx + '" y1="' + PADT +
                   '" y2="' + (H - PADB) + '" stroke="#e3e7ec"/>');
        parts.push('<text x="' + xx + '" y="' + (H - 12) +
                   '" text-anchor="middle" font-size="11" fill="#5b6472">' +
                   yr + '</text>');
      }}
    }});
    // P25-P75 band
    var up = [], dn = [];
    rows.forEach(function (r) {{
      var x = X(mIdx[r.ym]);
      up.push(x + ',' + Y(r.p75, y0, y1));
      dn.unshift(x + ',' + Y(r.p25, y0, y1));
    }});
    if (up.length > 1) {{
      parts.push('<polygon points="' + up.concat(dn).join(' ') +
                 '" fill="#9ec9a8" opacity="0.35" stroke="none"/>');
    }}
    // monthly median line
    var med = rows.map(function (r) {{
      return X(mIdx[r.ym]) + ',' + Y(r.median, y0, y1);
    }});
    if (med.length > 1) {{
      parts.push('<polyline points="' + med.join(' ') +
                 '" fill="none" stroke="#1a7f37" stroke-width="1.6"/>');
    }}
    // 12-month trend
    var tr = DATA.trend[key] || [];
    var trPts = [];
    rows.forEach(function (r, i) {{
      if (tr[i] === null || tr[i] === undefined) return;
      trPts.push(X(mIdx[r.ym]) + ',' + Y(tr[i], y0, y1));
    }});
    if (trPts.length > 1) {{
      parts.push('<polyline points="' + trPts.join(' ') +
                 '" fill="none" stroke="#1a2330" stroke-width="2.6" opacity="0.85"/>');
    }}
    parts.push('<line id="cursor" x1="-10" x2="-10" y1="' + PADT + '" y2="' +
               (H - PADB) + '" stroke="#2563eb" stroke-width="1.4" opacity="0"/>');
    chart.innerHTML = parts.join('');

    var first = rows[0], last = rows[rows.length - 1];
    var trendFirst = null, trendLast = null;
    tr.forEach(function (v) {{ if (v !== null) {{
      if (trendFirst === null) trendFirst = v; trendLast = v;
    }}}});
    var pct = (trendFirst && trendLast)
      ? ' · trend ' + (trendLast > trendFirst ? '+' : '') +
        (Math.round((trendLast - trendFirst) / trendFirst * 1000) / 10) + '%'
      : '';
    stats.textContent = first.ym + ' … ' + last.ym + ' · ' +
      rows.length + ' maanden' + pct;
    note.textContent = meta.note;

    // ---- season panel ----
    var clim = DATA.climate[key] || [];
    var cl = clim.filter(function (v) {{ return v !== null; }});
    if (!cl.length) {{ season.innerHTML = ''; snote.textContent = 'geen data'; return; }}
    var SW = 1020, SH = 220, SPL = 64, SPR = 16, SPT = 14, SPB = 30;
    var s0 = Math.min.apply(null, cl) , s1 = Math.max.apply(null, cl);
    var sspan = (s1 - s0) || 1; s0 -= sspan * 0.1; s1 += sspan * 0.1;
    var SX = function (i) {{ return SPL + i * (SW - SPL - SPR) / 11; }};
    var SY = function (v) {{
      return SPT + (1 - Math.max(0, Math.min(1, (v - s0) / (s1 - s0)))) *
             (SH - SPT - SPB);
    }};
    var sp = [];
    sp.push('<rect x="' + SPL + '" y="' + SPT + '" width="' + (SW - SPL - SPR) +
            '" height="' + (SH - SPT - SPB) + '" fill="#fafbfc" stroke="#e3e7ec"/>');
    var spts = [];
    clim.forEach(function (v, i) {{
      sp.push('<text x="' + SX(i) + '" y="' + (SH - 12) +
              '" text-anchor="middle" font-size="11" fill="#5b6472">' +
              LBL[i] + '</text>');
      if (v !== null) spts.push(SX(i) + ',' + SY(v));
    }});
    if (spts.length > 1) {{
      sp.push('<polyline points="' + spts.join(' ') +
              '" fill="none" stroke="#2563eb" stroke-width="2"/>');
      clim.forEach(function (v, i) {{
        if (v !== null) sp.push('<circle cx="' + SX(i) + '" cy="' + SY(v) +
                                '" r="3.2" fill="#2563eb"/>');
      }});
    }}
    sp.push('<text x="' + (SPL - 8) + '" y="' + SY(s1) + '" text-anchor="end" font-size="11" fill="#5b6472">' +
            (Math.round(s1 * 100) / 100) + '</text>');
    sp.push('<text x="' + (SPL - 8) + '" y="' + SY(s0) + '" text-anchor="end" font-size="11" fill="#5b6472">' +
            (Math.round(s0 * 100) / 100) + '</text>');
    season.innerHTML = sp.join('');
    var peak = null, low = null;
    clim.forEach(function (v, i) {{
      if (v === null) return;
      if (peak === null || v > clim[peak]) peak = i;
      if (low === null || v < clim[low]) low = i;
    }});
    snote.textContent = 'Hoogste mediaan in ' + LBL[peak] +
      ' (' + clim[peak] + '), laagste in ' + LBL[low] + ' (' + clim[low] + ').';
  }}

  // ---- play cursor (the "simulation" sweep) ----
  var playBtn = document.getElementById('play');
  var raf = null, t0 = null;
  function step (ts) {{
    var cursor = document.getElementById('cursor');
    if (!cursor) {{ stop(); return; }}
    if (t0 === null) t0 = ts;
    var t = ((ts - t0) / 9000) % 1.0000001;
    var x = 64 + t * (1020 - 64 - 16);
    cursor.setAttribute('x1', x); cursor.setAttribute('x2', x);
    cursor.setAttribute('opacity', '0.85');
    raf = requestAnimationFrame(step);
  }}
  function stop () {{
    if (raf) cancelAnimationFrame(raf); raf = null; t0 = null;
    playBtn.classList.remove('playing');
    playBtn.innerHTML = '&#9654; Afspelen';
    var cursor = document.getElementById('cursor');
    if (cursor) cursor.setAttribute('opacity', '0');
  }}
  playBtn.addEventListener('click', function () {{
    if (raf) {{ stop(); return; }}
    playBtn.classList.add('playing');
    playBtn.innerHTML = '&#9632; Stoppen';
    raf = requestAnimationFrame(step);
  }});

  draw();
}})();
</script>
</body>
</html>
"""


def render_timeseries(
    fixture: Mapping[str, Any],
    *,
    title: str = "Waterkwaliteit Rijnland 2020–2026",
    default_parameter: str = "CONCTTE|chloride|mg/l",
    out_path: Optional[Path] = None,
) -> str:
    """Render the monthly fixture to a standalone interactive page."""
    series = fixture.get("series") or {}
    if not series:
        raise ValueError("fixture has no monthly series")
    params = []
    for key in sorted(series):
        norm = NORMS.get(key, {})
        unit = _unit_of(key)
        label = norm.get("label") or key.replace("|", " · ")
        worse = norm.get("worse") == "low" and "Lagere waarden zijn ongunstiger." \
            or ("Hogere waarden zijn ongunstiger." if norm else "")
        params.append({
            "key": key, "label": label, "unit": unit,
            "note": (f"Mediaan over alle meetlocaties per maand, "
                     f"P25–P75 over locaties; {worse}".strip()),
        })
    if default_parameter not in series:
        default_parameter = sorted(series)[0]
    payload = {
        "default": default_parameter,
        "parameters": params,
        "series": series,
        "trend": {k: rolling_median(v) for k, v in series.items()},
        "climate": {k: climatology(v) for k, v in series.items()},
    }
    raw = fixture.get("rawRowsPerYear") or {}
    years = sorted(int(y) for y in raw) or [0]
    subtitle = (f"{years[0]}–{years[-1]} · "
                f"{sum(raw.values()):,} metingen · "
                f"{len(series)} parameters".replace(",", "."))
    provenance = (
        f"Bron: {fixture.get('source')} (subject “{fixture.get('subject')}”, "
        f"{fixture.get('areaName')}), opgehaald {fixture.get('fetchedAt')} via "
        f"scripts/fetch_wkp.py --monthly. Maandbuckets met <2 metingen zijn "
        f"weggelaten; 2026 is een deels jaar. Geen wettelijke norm — "
        f"spreiding en trend zijn relatief aan de eigen metingen."
    )
    html = _TEMPLATE.format(
        title=title,
        subtitle=subtitle + (" · 2026 deels" if raw.get("2026", 0) < 1000 else ""),
        payload=json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c"),
        month_labels_json=json.dumps(_MONTH_LABELS),
        provenance=provenance,
    )
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    return html
