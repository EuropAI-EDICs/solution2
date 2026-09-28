"""HTML-rapport voor de MiniGIM-gebiedscheck (single-file, tabellen-first).

Offline-leesbaar: alle tabellen zijn platte HTML; de kaart laadt Leaflet van
CDN en valt terug op de tabellen als er geen internet is (zelfde patroon als
poc-breda report.html).
"""

from __future__ import annotations

import html
import json
from pathlib import Path

STATUS_LABEL = {
    "auto": "auto",
    "partial": "proxy",
    "manual": "handmatig",
    "out-of-scope": "n.v.t.",
    "delivered": "✓ geleverd",
    "not-delivered": "✗ niet geleverd",
    "manual-action": "→ handmatige actie",
    "nvt": "—",
}


def _esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def _values_cell(values: dict) -> str:
    if not values:
        return "—"
    parts = []
    for k, v in values.items():
        if k in ("list",):
            parts.append(f"<b>{_esc(k)}</b>: {len(v)} regels (in artifact)")
        elif isinstance(v, dict):
            sub = ", ".join(f"{_esc(kk)}={_esc(vv)}" for kk, vv in list(v.items())[:6])
            parts.append(f"<b>{_esc(k)}</b>: {sub}")
        elif isinstance(v, list):
            parts.append(f"<b>{_esc(k)}</b>: {_esc(v)}")
        else:
            parts.append(f"<b>{_esc(k)}</b>: {_esc(v)}")
    return "; ".join(parts)[:600]


def build_report(run: dict, checklist: dict, ils_draft: dict, validation: dict,
                 layers_geojson: dict[str, dict]) -> str:
    items = checklist["items"]
    themas = {}
    for it in items:
        themas.setdefault(it["thema"], []).append(it)

    rows_html = []
    for thema, its in themas.items():
        rows_html.append(
            f'<tr class="thema"><td colspan="7">{_esc(thema)}</td></tr>'
        )
        for it in its:
            flags = " ".join(f'<span class="flag">{_esc(f)}</span>' for f in it["riskFlags"])
            prov = it.get("prov") or {}
            bron = prov.get("bronRegistratie") or ""
            leverancier = prov.get("bronLeverancier") or ""
            manual = f'<div class="muted">{_esc(it["manualPointer"] or "")}</div>' if it.get("manualPointer") else ""
            proxy = f'<div class="muted">proxy: {_esc(it["proxyNote"])}</div>' if it.get("proxyNote") else ""
            naam = " / ".join(filter(None, [it.get("onderdeel"), it.get("item")])) or "(groepsrij)"
            rows_html.append(
                "<tr>"
                f'<td>{_esc(naam)}<div class="muted">{_esc(it["lijstItemId"])}</div></td>'
                f'<td class="center">{_esc(it.get("prioriteit") or "—")}</td>'
                f'<td class="center">{STATUS_LABEL.get(it["bindingStatus"], it["bindingStatus"])}</td>'
                f'<td class="center">{STATUS_LABEL.get(it["deliveredStatus"], it["deliveredStatus"])}</td>'
                f"<td>" + _values_cell(it["values"]) + proxy + manual + "</td>"
                f"<td>{_esc(bron)}<div class='muted'>{_esc(leverancier)}</div></td>"
                f"<td>{flags}</td>"
                "</tr>"
            )
    checklist_table = "\n".join(rows_html)

    ils_rows = "\n".join(
        "<tr>"
        f'<td>{_esc(f["nodePath"])}</td>'
        f'<td class="center">{f["level"]}</td>'
        f'<td class="center">{_esc(f["ifcExportAs"] or "—")}</td>'
        f'<td class="center">{f["count"]}</td>'
        f'<td class="right">{f["areaM2"]:,.1f}</td>'
        f'<td class="muted">{_esc(f["sourceLayer"])}</td>'
        "</tr>"
        for f in ils_draft.get("features", [])
    )
    unassigned = "\n".join(
        f"<li><b>{_esc(k)}</b>: {_esc(v.get('reason', ''))} (n={v.get('count', 0)})</li>"
        for k, v in ils_draft.get("unassigned", {}).items()
    ) or "<li>geen</li>"

    v_rows = "\n".join(
        f'<tr class="{"ok" if c["ok"] else "fail"}"><td>{_esc(c["level"])}</td>'
        f'<td>{_esc(c["artifact"])}</td><td>{("PASS" if c["ok"] else "FAIL")}</td>'
        f'<td>{_esc(c["detail"])}</td></tr>'
        for c in validation["levels"]
    )

    s = checklist["summary"]
    hoog = s["autoCoverageOfHoog"]
    layers_json = json.dumps(layers_geojson, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MiniGIM gebiedscheck — {_esc(run["runId"])}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
:root {{ --ink:#1a1a1a; --muted:#666; --line:#e3e3e3; --yellow:#ffd84d; }}
body {{ font-family: -apple-system, "Segoe UI", sans-serif; color: var(--ink); margin: 0; background:#fafafa; }}
header {{ background:#111; color:#fff; padding:1.4rem 2rem; }}
header h1 {{ margin:0 0 .3rem; font-size:1.4rem; }} header .sub {{ color:#bbb; font-size:.85rem; }}
main {{ padding: 1.5rem 2rem 4rem; max-width: 1400px; margin: 0 auto; }}
h2 {{ margin-top: 2.2rem; font-size:1.15rem; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; font-size: .82rem; }}
th, td {{ border:1px solid var(--line); padding:.42rem .55rem; vertical-align: top; text-align:left; }}
th {{ background:#f3f3f3; position: sticky; top:0; }}
tr.thema td {{ background:#111; color:#fff; font-weight:600; letter-spacing:.06em; text-transform:uppercase; font-size:.75rem; }}
.center {{ text-align:center; }} .right {{ text-align:right; }}
.muted {{ color: var(--muted); font-size:.75rem; }}
.flag {{ background:var(--yellow); padding:.05rem .4rem; border-radius:.3rem; font-size:.7rem; font-weight:600; display:inline-block; margin-top:.2rem; }}
.kpis {{ display:flex; gap:1rem; flex-wrap:wrap; margin:1.2rem 0; }}
.kpi {{ background:#fff; border:1px solid var(--line); border-bottom:3px solid var(--yellow); border-radius:.4rem; padding:.7rem 1.1rem; min-width:9rem; }}
.kpi .n {{ font-size:1.5rem; font-weight:700; }} .kpi .l {{ font-size:.72rem; color:var(--muted); }}
#map {{ height: 460px; border:1px solid var(--line); border-radius:.4rem; margin-top:.8rem; }}
tr.ok td:nth-child(3) {{ color:#0a7d24; font-weight:700; }}
tr.fail td:nth-child(3) {{ color:#b00020; font-weight:700; }}
footer {{ color:var(--muted); font-size:.75rem; margin-top:3rem; border-top:1px solid var(--line); padding-top:1rem; }}
</style></head><body>
<header>
  <h1>MiniGIM gebiedscheck — {_esc(run["label"])}</h1>
  <div class="sub">Omgevingsanalyse Lijst {_esc(run["miniGimVersions"]["lijst"])} · ILS {_esc(run["miniGimVersions"]["ils"])} ·
  run {_esc(run["runId"])} · BTO {_esc(f"{run['aoi']['btoM2']:,.0f}")} m² · verdict {_esc(validation["verdict"]).upper()}</div>
</header>
<main>
<section class="kpis">
  <div class="kpi"><div class="n">{s["itemCount"]}</div><div class="l">checklist-items</div></div>
  <div class="kpi"><div class="n">{s["deliveredStatus"].get("delivered", 0)}</div><div class="l">automatisch geleverd</div></div>
  <div class="kpi"><div class="n">{s["deliveredStatus"].get("manual-action", 0)}</div><div class="l">handmatige actie</div></div>
  <div class="kpi"><div class="n">{hoog["pct"] if hoog["pct"] is not None else "—"}%</div><div class="l">hoog-prioriteit auto ({hoog["delivered"]}/{hoog["hoog"]})</div></div>
</section>
<p>Legenda: <b>auto</b> = runner levert uit sleutelloze open bron · <b>proxy</b> = geleverd als expliciet gelabelde proxy/dekking ·
<b>handmatig</b> = gedocumenteerde mens-route. Elk geleverd item draagt prov (bronregister, URL, fetchedAt, sha256) in
<code>omgevingsanalyse.json</code>.</p>

<h2>Kaart</h2>
<div id="map"><noscript><p class="muted">Kaart vereist JavaScript — zie de tabellen en GeoJSON-lagen in de run-map.</p></noscript></div>

<h2>Omgevingsanalyse — checklist ({_esc(run["miniGimVersions"]["lijst"])})</h2>
<table>
<tr><th>item</th><th>prioriteit</th><th>binding</th><th>levering</th><th>waarden</th><th>bron</th><th>risico</th></tr>
{checklist_table}
</table>

<h2>ILS draft-gebiedsindeling ({_esc(run["miniGimVersions"]["ils"])})</h2>
<p class="muted">{_esc(ils_draft["niveau0Note"])}</p>
<table>
<tr><th>node-pad (Niveau 0 → …)</th><th>niveau</th><th>IfcExportAs</th><th>objecten</th><th>oppervlak m²</th><th>bronlaag</th></tr>
{ils_rows}
</table>
<h3>Buiten de ILS-hiërarchie</h3>
<ul>{unassigned}</ul>
<p class="muted">{_esc(ils_draft["epsetNote"])}</p>

<h2>Validatie (V0–V3; V4 = pending by design)</h2>
<table>
<tr><th>level</th><th>artifact</th><th>resultaat</th><th>detail</th></tr>
{v_rows}
</table>

<footer>
MiniGIM-methodiek: minigim.nl (Lijst v0.91 + ILS v0.8, DMI-ecosysteem/NEPROM).
Tooling: poc-minigim (PoC-5 LDT-toolbox) — deterministisch, cache-first, 0 API-sleutels, geen LLM in de beslislijn.
Dit is een gebiedscheck-ontwerpoutput (draft); besluiten blijven mensenwerk (V4).
</footer>
</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const LAYERS = {layers_json};
if (typeof L !== "undefined") {{
  const map = L.map("map").setView([51.59, 4.78], 14);
  L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
    maxZoom: 19, attribution: "© OpenStreetMap"}}).addTo(map);
  const names = Object.keys(LAYERS);
  const palette = ["#e6194b","#3cb44b","#4363d8","#f58231","#911eb4","#008080","#9a6324","#800000","#808000","#000075"];
  let first = true;
  const overlays = {{}};
  names.forEach((name, i) => {{
    const gj = L.geoJSON(LAYERS[name], {{ style: {{color: palette[i % palette.length], weight:1.5, fillOpacity:.25}},
      pointToLayer: (f,latlng)=>L.circleMarker(latlng, {{radius:4, color:palette[i % palette.length]}}) }});
    overlays[name] = gj; gj.addTo(map);
    if (first) {{ try {{ map.fitBounds(gj.getBounds().pad(0.05)); first=false; }} catch(e) {{}} }}
  }});
  L.control.layers(null, overlays).addTo(map);
}}
</script>
</body></html>"""
