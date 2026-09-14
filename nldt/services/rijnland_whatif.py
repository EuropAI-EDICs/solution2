"""Rijnland peilen what-if: scenario deltas → CDC lake batches → report."""

from __future__ import annotations

import copy
import importlib.util
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.cdc import bronze_cdc_dir, silver_peilen_path
from services.lake import DEFAULT_BUCKET, NLDT_ROOT

WORKSPACE = NLDT_ROOT.parent
POC_RIJNLAND = WORKSPACE / "poc-rijnland"
DEFAULT_ARCHIVE = POC_RIJNLAND / "data" / "peilen" / "peilen.json"


def load_archive(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_ARCHIVE
    return json.loads(p.read_text(encoding="utf-8"))


def apply_scenario_to_archive(
    archive: dict[str, Any],
    scenario: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (scenario_archive, cdc_change_rows) without mutating input."""
    delta = float(scenario["delta_m"])
    layer = (scenario.get("layer") or "all").lower()
    station_ids = set(scenario.get("stationIds") or [])
    limit = scenario.get("limit")

    out = copy.deepcopy(archive)
    stations = out.get("stations") or {}
    changes: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    touched = 0

    for sid, rec in stations.items():
        if station_ids and sid not in station_ids:
            continue
        rec_layer = (rec.get("layer") or "").lower()
        if layer != "all" and rec_layer != layer:
            continue
        latest = rec.get("latest") or {}
        if latest.get("value") is None:
            continue
        before = float(latest["value"])
        after = before + delta
        latest["value"] = after
        latest["fetchedAt"] = now
        latest["whatIf"] = {
            "before": before,
            "after": after,
            "delta_m": delta,
            "scenarioId": scenario.get("id"),
        }
        rec["latest"] = latest
        day = now[:10]
        days = rec.setdefault("days", {})
        days[day] = {
            "n": 1,
            "median": after,
            "min": after,
            "max": after,
            "whatIf": True,
        }
        touched += 1
        changes.append(
            {
                "cdc_lsn": touched,
                "op": "U",
                "peilgebied_id": sid,
                "waterstand_m": after,
                "measured_at": now,
                "source": f"whatif:{scenario.get('id') or 'scenario'}",
                "captured_at": now,
                "before_m": before,
                "delta_m": delta,
                "layer": rec_layer,
                "name": rec.get("name"),
            }
        )
        if limit is not None and touched >= int(limit):
            break

    out["whatIf"] = {
        "scenario": {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
            "description": scenario.get("description"),
            "delta_m": delta,
            "layer": layer,
            "stationIds": sorted(station_ids) if station_ids else None,
            "limit": limit,
        },
        "stationsTouched": touched,
        "appliedAt": now,
    }
    return out, changes


def stations_to_geojson(
    archive: dict[str, Any],
    changes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Point FeatureCollection for what-if map (WGS84 lon/lat = x/y)."""
    touched_ids = {c["peilgebied_id"] for c in changes}
    change_by_id = {c["peilgebied_id"]: c for c in changes}
    features: list[dict[str, Any]] = []
    for sid, rec in (archive.get("stations") or {}).items():
        x, y = rec.get("x"), rec.get("y")
        if x is None or y is None:
            continue
        latest = rec.get("latest") or {}
        wi = latest.get("whatIf") or {}
        ch = change_by_id.get(sid)
        if ch:
            before = float(ch["before_m"])
            after = float(ch["waterstand_m"])
            delta_m = float(ch["delta_m"])
        elif wi:
            before = float(wi["before"])
            after = float(wi["after"])
            delta_m = float(wi["delta_m"])
        else:
            val = latest.get("value")
            if val is None:
                continue
            before = after = float(val)
            delta_m = 0.0
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
                "properties": {
                    "id": sid,
                    "name": rec.get("name") or sid,
                    "layer": rec.get("layer") or "",
                    "before": before,
                    "after": after,
                    "delta_m": delta_m,
                    "touched": sid in touched_ids,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def write_cdc_batch(changes: list[dict[str, Any]], *, poc: str = "rijnland") -> Path | None:
    if not changes:
        return None
    rows = [
        {
            "cdc_lsn": c["cdc_lsn"],
            "op": c["op"],
            "peilgebied_id": c["peilgebied_id"],
            "waterstand_m": c["waterstand_m"],
            "measured_at": c["measured_at"],
            "source": c["source"],
            "captured_at": c["captured_at"],
        }
        for c in changes
    ]
    import duckdb

    out_dir = bronze_cdc_dir(poc)
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-whatif"
    dest = out_dir / f"{batch_id}.parquet"
    jl = out_dir / f"{batch_id}.jsonl"
    with jl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    con = duckdb.connect()
    con.execute(
        f"COPY (SELECT * FROM read_json_auto('{jl.as_posix()}')) "
        f"TO '{dest.as_posix()}' (FORMAT PARQUET)"
    )
    jl.unlink(missing_ok=True)
    return dest


def _load_apply_batches():
    path = NLDT_ROOT / "scripts" / "cdc_apply_peilen.py"
    spec = importlib.util.spec_from_file_location("cdc_apply_peilen", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cdc_apply_peilen"] = mod
    spec.loader.exec_module(mod)
    return mod.apply_batches


def write_diff_html(changes: list[dict[str, Any]], scenario: dict[str, Any], dest: Path) -> Path:
    rows = "".join(
        f"<tr><td>{c.get('name') or c['peilgebied_id']}</td>"
        f"<td>{c.get('layer')}</td>"
        f"<td>{c['before_m']:.3f}</td>"
        f"<td>{c['waterstand_m']:.3f}</td>"
        f"<td>{c['delta_m']:+.3f}</td></tr>"
        for c in changes[:200]
    )
    html = f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"/>
<title>Rijnland peilen what-if</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;background:#f6f7f9;color:#1a1a1a}}
table{{border-collapse:collapse;width:100%;background:#fff}}
th,td{{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}}
th{{background:#e8eef5}}
.meta{{margin-bottom:1.5rem}}
</style></head><body>
<h1>{scenario.get('title') or 'Rijnland peilen what-if'}</h1>
<div class="meta">
<p>{scenario.get('description') or ''}</p>
<p><strong>Δ</strong> {scenario.get('delta_m')} m ·
<strong>laag</strong> {scenario.get('layer') or 'all'} ·
<strong>stations</strong> {len(changes)}</p>
</div>
<table>
<thead><tr><th>Station</th><th>Laag</th><th>Voor</th><th>Na</th><th>Δ m</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p><em>AI proposes · pipeline disposes · human decides</em></p>
</body></html>
"""
    dest.write_text(html, encoding="utf-8")
    return dest


def build_whatif_map_html(
    archive: dict[str, Any],
    changes: list[dict[str, Any]],
    scenario: dict[str, Any],
    dest: Path,
) -> Path:
    """Breda-style Leaflet map: scenario panel + vóór/na/Δ recolor modes."""
    fc = stations_to_geojson(archive, changes)
    payload = {
        "scenarios": [
            {
                "id": scenario.get("id") or "scenario",
                "title": scenario.get("title") or "Rijnland peilen what-if",
                "description": scenario.get("description") or "",
                "delta_m": scenario.get("delta_m"),
                "layer": scenario.get("layer") or "all",
                "n": len(changes),
            }
        ],
        "geo": fc,
        "defaultMode": "after",
        "modes": ["after", "before", "delta"],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    html = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What if…? — Rijnland peilen</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
 body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,sans-serif;color:#111827;background:#f4f6f8}
 header{background:#0b3d5c;color:#fff;padding:16px 24px}
 header h1{margin:0;font-size:21px} header p{margin:4px 0 0;color:#9ec3d9;font-size:13.5px}
 #map{height:78vh;background:#eef2f5}
 .paneel{position:absolute;top:12px;right:12px;z-index:1000;background:#fff;
   border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.3);padding:14px 16px;
   font-size:14px;width:320px;max-height:86vh;overflow-y:auto}
 .paneel h3{margin:0 0 6px;font-size:14px;color:#6b7280;font-weight:600;
   text-transform:uppercase;letter-spacing:.04em}
 .scen-kaart{border:1px solid #e5e7eb;border-radius:8px;padding:8px 10px;margin:5px 0;
   cursor:pointer;display:block}
 .scen-kaart:hover{border-color:#0b7ea4}
 .scen-kaart.actief{border-color:#0b7ea4;background:#f0f9fc}
 .scen-kaart b{display:block;font-size:14px}
 .scen-kaart .wat{font-size:12.5px;color:#4b5563;margin-top:4px}
 .modus-rij label{display:inline-block;margin:2px 6px 2px 0;cursor:pointer;
   border:1px solid #e5e7eb;border-radius:6px;padding:2px 8px;font-size:13px}
 .modus-rij input{margin-right:3px}
 .modus-rij label.actief{border-color:#0b3d5c;background:#0b3d5c;color:#fff}
 .uitleg{margin-top:10px;border-top:1px solid #eef0f3;padding-top:8px;font-size:13px;color:#4b5563}
 .legend{background:#fff;padding:8px 10px;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.25);
   font-size:12px}
 .legend .bar{height:10px;border:1px solid #999;margin:4px 0;
   background:linear-gradient(90deg,#08306b,#2171b5,#6baed6,#c6dbef,#f7fbff)}
 .legend .bar.delta{background:linear-gradient(90deg,#b71c1c,#f2b8b5,#eeeeee,#a5d6a7,#1e7e34)}
 .leaflet-popup-content{font-size:13.5px;min-width:220px}
 .rij{display:flex;justify-content:space-between;border-bottom:1px solid #f0f2f5;padding:3px 0}
</style></head><body>
<header>
 <h1>What if…? — Rijnland peilen</h1>
 <p>Scenario deltas on measuring stations (mNAP). Map default = absolute peil
    <b>na</b> the scenario. <em>AI proposes · pipeline disposes · human decides</em></p>
</header>
<div id="map">
 <div class="paneel">
  <h3>Kies een scenario</h3><div id="scen"></div>
  <h3 style="margin-top:12px">Kaartmodus</h3>
  <div class="modus-rij" id="modus">
   <label class="actief"><input type="radio" name="modus" value="after" checked> Na</label>
   <label><input type="radio" name="modus" value="before"> Vóór</label>
   <label><input type="radio" name="modus" value="delta"> Δ</label>
  </div>
  <div class="uitleg" id="uitleg"></div>
 </div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        onerror="window.__noLeaflet=true"></script>
<script>
window.__DATA__ = __PAYLOAD__;
(function(){
 if(window.__noLeaflet||typeof L==='undefined'){
  document.getElementById('map').innerHTML='<div style="padding:40px">'+
   'Map (Leaflet, CDN) unreachable — open this file with an internet connection.</div>';return;}
 var D=window.__DATA__;
 var mode=D.defaultMode||'after';
 var map=L.map('map',{preferCanvas:true}).setView([52.15,4.65],10);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,
   attribution:'&copy; OpenStreetMap-bijdragers'}).addTo(map);
 function seqColor(t){
  var stops=['#08306b','#2171b5','#6baed6','#c6dbef','#f7fbff'];
  var i=Math.min(stops.length-2, Math.max(0, Math.floor(t*(stops.length-1))));
  return stops[i];
 }
 function deltaColor(d, maxAbs){
  if(maxAbs<=0) return '#eeeeee';
  var t=Math.max(-1, Math.min(1, d/maxAbs));
  if(t<0) return t<-0.5?'#b71c1c':'#f2b8b5';
  if(t>0) return t>0.5?'#1e7e34':'#a5d6a7';
  return '#eeeeee';
 }
 var vals=[];
 D.geo.features.forEach(function(f){
  var p=f.properties; vals.push(p.before, p.after);
 });
 var vmin=Math.min.apply(null, vals), vmax=Math.max.apply(null, vals);
 if(!(isFinite(vmin)&&isFinite(vmax))||vmin===vmax){vmin-=0.05;vmax+=0.05;}
 var maxAbs=0;
 D.geo.features.forEach(function(f){
  var a=Math.abs(f.properties.delta_m||0); if(a>maxAbs) maxAbs=a;
 });
 if(maxAbs<=0) maxAbs=0.05;
 function valueOf(p){
  if(mode==='before') return p.before;
  if(mode==='delta') return p.delta_m;
  return p.after;
 }
 function fillOf(p){
  if(mode==='delta') return deltaColor(p.delta_m||0, maxAbs);
  var v=valueOf(p);
  var t=(v-vmin)/(vmax-vmin);
  return seqColor(Math.max(0, Math.min(1, t)));
 }
 var markers=[];
 var group=L.featureGroup();
 D.geo.features.forEach(function(f){
  var p=f.properties, c=f.geometry.coordinates;
  var m=L.circleMarker([c[1], c[0]], {
    radius: p.touched?8:5,
    color: p.touched?'#0b3d5c':'#6b7280',
    weight: p.touched?2:1,
    fillColor: fillOf(p),
    fillOpacity: mode==='delta' && !p.touched ? 0.12 : (p.touched?0.9:0.35)
  });
  m.bindPopup(function(){
   return '<b>'+p.name+'</b><div class="rij"><span>Laag</span><span>'+p.layer+
    '</span></div><div class="rij"><span>Vóór</span><span>'+Number(p.before).toFixed(3)+
    ' m</span></div><div class="rij"><span>Na</span><span>'+Number(p.after).toFixed(3)+
    ' m</span></div><div class="rij"><span>Δ</span><span>'+
    (p.delta_m>=0?'+':'')+Number(p.delta_m).toFixed(3)+' m</span></div>';
  });
  markers.push({m:m,p:p});
  group.addLayer(m);
 });
 group.addTo(map);
 if(markers.length) map.fitBounds(group.getBounds().pad(0.08));
 var legend=L.control({position:'bottomleft'});
 legend.onAdd=function(){var d=L.DomUtil.create('div','legend'); this._d=d; this.upd(); return d;};
 legend.upd=function(){
  if(mode==='delta'){
   this._d.innerHTML='<b>Δ peil (m)</b><div class="bar delta"></div>'+
    'lager · 0 · hoger<br><span style="color:#6b7280">touched dikker omrand</span>';
  } else {
   this._d.innerHTML='<b>Peil mNAP ('+(mode==='before'?'vóór':'na')+')</b>'+
    '<div class="bar"></div>'+vmin.toFixed(2)+' · '+vmax.toFixed(2);
  }
 };
 legend.addTo(map);
 function ververs(){
  markers.forEach(function(x){
   x.m.setStyle({
     fillColor: fillOf(x.p),
     fillOpacity: mode==='delta' && !x.p.touched ? 0.12 : (x.p.touched?0.9:0.35),
     weight: x.p.touched?2:1
   });
  });
  legend.upd();
  var s=D.scenarios[0], u=document.getElementById('uitleg');
  if(!s){u.innerHTML='';return;}
  var label={after:'absolute peil na scenario', before:'absolute peil vóór scenario',
    delta:'delta t.o.v. vóór (uniforme Δ blijft één tint)'};
  u.innerHTML='<b>'+s.title+'</b><div>'+s.description+'</div>'+
   '<div style="margin-top:6px">Δ '+s.delta_m+' m · laag '+s.layer+' · '+s.n+
   ' stations · modus: '+label[mode]+'</div>';
 }
 var se=document.getElementById('scen');
 D.scenarios.forEach(function(s,i){
  var d=document.createElement('div');
  d.className='scen-kaart'+(i===0?' actief':'');
  d.innerHTML='<b>'+s.title+'</b><div class="wat">'+s.description+
   '<br>Δ '+s.delta_m+' m · '+s.layer+' · '+s.n+' stations</div>';
  d.onclick=function(){
   Array.prototype.forEach.call(se.children,function(c){c.classList.remove('actief');});
   d.classList.add('actief'); ververs();
  };
  se.appendChild(d);
 });
 Array.prototype.forEach.call(document.querySelectorAll('#modus input'), function(r){
  r.onchange=function(){
   mode=r.value;
   Array.prototype.forEach.call(document.querySelectorAll('#modus label'),
     function(c){c.classList.remove('actief');});
   r.parentElement.classList.add('actief');
   ververs();
  };
 });
 ververs();
})();
</script></body></html>""".replace("__PAYLOAD__", data)
    dest.write_text(html, encoding="utf-8")
    return dest


def build_whatif_report(
    *,
    scenario: dict[str, Any],
    changes: list[dict[str, Any]],
    cdc_batch: str | None,
    silver_uri: str | None,
    run_dir: str,
    conflict_summary: dict[str, Any] | None = None,
    map_html: str | None = None,
) -> dict[str, Any]:
    deltas = [c["delta_m"] for c in changes]
    layers: dict[str, int] = {}
    for c in changes:
        layers[c.get("layer") or "unknown"] = layers.get(c.get("layer") or "unknown", 0) + 1
    return {
        "id": f"whatif-{scenario.get('id') or 'scenario'}",
        "artifactType": "rijnland-peil-whatif-report",
        "scenario": scenario,
        "stationsTouched": len(changes),
        "layersTouched": layers,
        "delta_m": scenario.get("delta_m"),
        "deltaStats": {
            "min": min(deltas) if deltas else None,
            "max": max(deltas) if deltas else None,
            "median": statistics.median(deltas) if deltas else None,
        },
        "cdcBatch": cdc_batch,
        "silverUri": silver_uri,
        "runDir": run_dir,
        "mapHtml": map_html,
        "conflict": conflict_summary,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "doctrine": "AI proposes · pipeline disposes · human decides",
    }


def run_whatif(
    scenario: dict[str, Any],
    *,
    archive_path: Path | None = None,
    out_dir: Path | None = None,
    apply_to_lake: bool = True,
    attach_conflict_replay: bool = True,
) -> dict[str, Any]:
    archive = load_archive(archive_path)
    scenario_archive, changes = apply_scenario_to_archive(archive, scenario)
    if not changes:
        raise ValueError("scenario touched 0 stations — check layer/stationIds/limit")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir or (POC_RIJNLAND / "runs" / f"{ts}-peilen-whatif")
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "peilen-whatif.json").write_text(
        json.dumps(scenario_archive, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    (run_dir / "scenario.json").write_text(
        json.dumps(scenario, indent=2) + "\n", encoding="utf-8"
    )
    write_diff_html(changes, scenario, run_dir / "whatif-diff.html")
    map_html = build_whatif_map_html(
        scenario_archive, changes, scenario, run_dir / "whatif-map.html"
    )

    cdc_path = None
    silver_uri = None
    if apply_to_lake:
        cdc_path = write_cdc_batch(changes)
        if cdc_path:
            apply_batches = _load_apply_batches()
            applied = apply_batches([cdc_path], silver_peilen_path("rijnland"))
            silver_uri = (
                f"lake://{DEFAULT_BUCKET}/silver/rijnland/peilen_latest/peilen_latest.parquet"
            )
            (run_dir / "cdc-apply.json").write_text(
                json.dumps(applied, indent=2) + "\n", encoding="utf-8"
            )

    conflict_summary = None
    if attach_conflict_replay:
        conflict_summary = _conflict_replay_summary()

    report = build_whatif_report(
        scenario=scenario,
        changes=changes,
        cdc_batch=str(cdc_path) if cdc_path else None,
        silver_uri=silver_uri,
        run_dir=str(run_dir),
        conflict_summary=conflict_summary,
        map_html=str(map_html),
    )
    (run_dir / "whatif-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "changes.json").write_text(
        json.dumps(changes[:500], indent=2) + "\n", encoding="utf-8"
    )

    return {
        "summary": {
            "mode": "whatif",
            "runDir": str(run_dir),
            "stationsTouched": len(changes),
            "delta_m": scenario.get("delta_m"),
            "layer": scenario.get("layer") or "all",
            "scenarioId": scenario.get("id"),
            "cdcBatch": str(cdc_path) if cdc_path else None,
            "silverUri": silver_uri,
            "diffHtml": str(run_dir / "whatif-diff.html"),
            "mapHtml": str(map_html),
            "conflictVerdict": (conflict_summary or {}).get("verdict"),
            "reportPath": str(run_dir / "whatif-report.json"),
            "lakeUriHint": silver_uri,
        }
    }


def _conflict_replay_summary() -> dict[str, Any] | None:
    try:
        from services.process_adapter.poc_handlers import execute_rijnland_peil_conflict

        out = execute_rijnland_peil_conflict({"mode": "replay"})
        return out.get("summary")
    except Exception as exc:
        return {"error": str(exc), "mode": "replay_failed"}
