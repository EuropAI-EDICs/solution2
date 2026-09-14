# Rijnland peilen what-if map (Breda-stijl) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit a Breda-style Leaflet `whatif-map.html` from each Rijnland peilen what-if run so absolute peilen (vóór/na/Δ) are readable on a map, not only in a uniform-Δ table.

**Architecture:** Extend `nldt/services/rijnland_whatif.py` with `stations_to_geojson` + `build_whatif_map_html`; call them from `run_whatif` after the archive is written. Payload mirrors Breda’s `window.__DATA__` pattern (scenarios + GeoJSON + client recolor modes). No H3, no changes to `poc-breda/`.

**Tech Stack:** Python 3 (nldt `.venv`), pytest, Leaflet 1.9.4 CDN + OSM tiles (same as Breda `build_whatif_html`).

**Spec:** `docs/superpowers/specs/2026-09-14-rijnland-peilen-whatif-map-design.md`

## Global Constraints

- **Doctrine:** AI proposes · pipeline disposes · human decides — map is read-only; no OLTP writes from UI.
- **Interpreter:** prefer `/Users/marc/Projecten/ldttoolbox/nldt/.venv/bin/python` when present; else `PYTHONPATH=nldt python3`.
- **Offline tests:** do not require network; assert HTML structure/`__DATA__` only (Leaflet CDN failure path like Breda).
- **Coords:** peilen stations use WGS84 `x`=lon, `y`=lat (all 315 currently have coords); skip stations missing either.
- **Default map mode:** `"after"` (absolute mNAP after scenario). Modes: `"after"` | `"before"` | `"delta"`.
- **YAGNI:** v1 ships one scenario in the panel; payload still uses `scenarios: [...]` for later multi-variant.
- **Commit style:** short imperative English; commit only files touched by the task; do not push unless asked.
- **Do not edit** the design spec file or `poc-breda/`.

## File map

| File | Role |
|------|------|
| `nldt/services/rijnland_whatif.py` | GeoJSON builder + HTML map builder + wire into `run_whatif` |
| `nldt/tests/test_rijnland_whatif.py` | Failing-then-passing tests for map artefact |
| `nldt/15-cdc-data-lake-pipeline.md` | Smoke: open `whatif-map.html` |

---

### Task 1: GeoJSON payload + failing tests

**Files:**
- Modify: `nldt/services/rijnland_whatif.py`
- Modify: `nldt/tests/test_rijnland_whatif.py`

**Interfaces:**
- Consumes: `apply_scenario_to_archive` output `(scenario_archive, changes)`; station records with `x`, `y`, `name`, `layer`, `latest.whatIf|{value}`
- Produces:
  - `stations_to_geojson(archive: dict, changes: list[dict]) -> dict` — GeoJSON FeatureCollection
  - Feature props: `id`, `name`, `layer`, `before`, `after`, `delta_m`, `touched` (bool)
  - Geometry: `Point` with coordinates `[x, y]` (lon, lat)

- [ ] **Step 1: Write the failing tests**

Append to `nldt/tests/test_rijnland_whatif.py`:

```python
def test_stations_to_geojson_touched_points():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        apply_scenario_to_archive,
        load_archive,
        stations_to_geojson,
    )

    archive = load_archive(PEILEN)
    scenario = {"id": "t-map", "delta_m": 0.05, "layer": "boezem", "limit": 5}
    out, changes = apply_scenario_to_archive(archive, scenario)
    fc = stations_to_geojson(out, changes)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 5
    touched = [f for f in fc["features"] if f["properties"]["touched"]]
    assert len(touched) == 5
    for f in touched:
        lon, lat = f["geometry"]["coordinates"]
        assert isinstance(lon, (int, float)) and isinstance(lat, (int, float))
        assert f["properties"]["delta_m"] == 0.05
        assert f["properties"]["after"] == pytest.approx(
            f["properties"]["before"] + 0.05
        )


def test_build_whatif_map_html_has_data_and_modes(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        apply_scenario_to_archive,
        build_whatif_map_html,
        load_archive,
    )

    archive = load_archive(PEILEN)
    scenario = {
        "id": "boezem-plus5cm",
        "title": "Boezempeilen +5 cm",
        "description": "test",
        "delta_m": 0.05,
        "layer": "boezem",
        "limit": 5,
    }
    out, changes = apply_scenario_to_archive(archive, scenario)
    dest = tmp_path / "whatif-map.html"
    build_whatif_map_html(out, changes, scenario, dest)
    html = dest.read_text(encoding="utf-8")
    assert "window.__DATA__" in html
    assert "leaflet@1.9.4" in html
    assert '"defaultMode": "after"' in html or '"defaultMode":"after"' in html
    assert "before" in html and "after" in html and "delta" in html
    assert "Boezempeilen +5 cm" in html


def test_run_whatif_writes_map_html(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import run_whatif

    out_dir = tmp_path / "whatif-run-map"
    result = run_whatif(
        {
            "id": "map-test",
            "title": "map test",
            "delta_m": 0.05,
            "layer": "boezem",
            "limit": 5,
        },
        archive_path=PEILEN,
        out_dir=out_dir,
        apply_to_lake=False,
        attach_conflict_replay=False,
    )
    assert (out_dir / "whatif-map.html").is_file()
    assert result["summary"]["mapHtml"] == str(out_dir / "whatif-map.html")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rijnland_whatif.py::test_stations_to_geojson_touched_points \
  tests/test_rijnland_whatif.py::test_build_whatif_map_html_has_data_and_modes \
  tests/test_rijnland_whatif.py::test_run_whatif_writes_map_html -v
```

Expected: FAIL — `ImportError` / `AttributeError` for `stations_to_geojson` / `build_whatif_map_html`, or missing `mapHtml`.

- [ ] **Step 3: Implement `stations_to_geojson`**

Add to `nldt/services/rijnland_whatif.py` (after `apply_scenario_to_archive`):

```python
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
```

- [ ] **Step 4: Run GeoJSON test only — should pass**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rijnland_whatif.py::test_stations_to_geojson_touched_points -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/rijnland_whatif.py nldt/tests/test_rijnland_whatif.py
git commit -m "$(cat <<'EOF'
Add peilen what-if GeoJSON helper and failing map tests.

EOF
)"
```

---

### Task 2: `build_whatif_map_html` + wire `run_whatif`

**Files:**
- Modify: `nldt/services/rijnland_whatif.py` (`build_whatif_map_html`, `run_whatif` summary)
- Modify: `nldt/tests/test_rijnland_whatif.py` (already added in Task 1)

**Interfaces:**
- Consumes: `stations_to_geojson(archive, changes)`
- Produces:
  - `build_whatif_map_html(archive, changes, scenario, dest: Path) -> Path`
  - Writes HTML with `window.__DATA__ = {...}` where payload keys are:
    - `scenarios: list[{id, title, description, delta_m, layer, n}]`
    - `geo: FeatureCollection`
    - `defaultMode: "after"`
    - `modes: ["after","before","delta"]`
  - `run_whatif` summary gains `"mapHtml": str(run_dir / "whatif-map.html")`
  - Report optional key `"mapHtml"` on disk report is nice-to-have; summary key is required

- [ ] **Step 1: Implement `build_whatif_map_html`**

Add function that:
1. Builds `fc = stations_to_geojson(archive, changes)`.
2. Builds payload:

```python
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
```

3. Embeds HTML modeled on Breda (header + `#map` + `.paneel` + Leaflet CDN), with this JS behavior:
   - `L.map` fitBounds to feature latlngs (fallback center `[52.15, 4.65]`, zoom 10).
   - OSM tile layer.
   - One scenario card in `#scen` (active by default).
   - Mode radios: na / vóór / Δ (`after`/`before`/`delta`); default checked = after.
   - For each feature: `L.circleMarker([lat, lon], {radius, color, fillColor, weight, opacity, fillOpacity})`.
   - Color scale:
     - `after`/`before`: shared domain over all `before`∪`after` values → blue→cyan sequential (water); use simple 5-stop interpolate.
     - `delta`: diverging around 0 (e.g. `#b71c1c` negative, `#eeeeee` zero, `#1e7e34` positive); uniform +0.05 → one positive tint (expected).
   - Touched: `weight: 2`; untouched: `weight: 1`, lower `fillOpacity` (e.g. 0.35); in `delta` mode hide or fade untouched (`fillOpacity: 0.1` or skip).
   - Popup HTML: name, layer, before → after, Δ m (3 decimals).
   - CDN `onerror` → set `window.__noLeaflet=true` and show fallback message (copy Breda pattern).
   - Footer/header line: `AI proposes · pipeline disposes · human decides`.

Keep the HTML in a Python triple-quoted string with `__PAYLOAD__` placeholder replaced by `data` (same as Breda’s `__PAYLOAD__` replace). Do **not** import from `poc-breda`.

Minimal color helper in the same JS block:

```javascript
function seqColor(t){ // t in [0,1]
  var stops=['#08306b','#2171b5','#6baed6','#c6dbef','#f7fbff'];
  var i=Math.min(stops.length-2, Math.floor(t*(stops.length-1)));
  return stops[i];
}
function deltaColor(d, maxAbs){
  if(maxAbs<=0) return '#eeeeee';
  var t=Math.max(-1, Math.min(1, d/maxAbs));
  if(t<0) return t<-0.5?'#b71c1c':'#f2b8b5';
  if(t>0) return t>0.5?'#1e7e34':'#a5d6a7';
  return '#eeeeee';
}
```

- [ ] **Step 2: Wire `run_whatif`**

Immediately after `write_diff_html(...)`:

```python
map_path = write_diff_html  # NO — separate call:
build_whatif_map_html(
    scenario_archive, changes, scenario, run_dir / "whatif-map.html"
)
```

In returned `summary` dict add:

```python
"mapHtml": str(run_dir / "whatif-map.html"),
```

Optionally add `"mapHtml"` to `build_whatif_report` return dict (same string) so `whatif-report.json` documents it.

- [ ] **Step 3: Run map-related tests**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest tests/test_rijnland_whatif.py -v
```

Expected: all tests in the file PASS (including existing ones).

- [ ] **Step 4: Manual smoke (optional but preferred)**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python scripts/rijnland_whatif_peilen.py \
    --delta-m 0.05 --layer boezem --no-conflict && \
  open "$(ls -td ../poc-rijnland/runs/*-peilen-whatif | head -1)/whatif-map.html"
```

(Adjust CLI flags to match `rijnland_whatif_peilen.py` — if there is no `--no-conflict`, pass whatever disables conflict replay, or rely on default. Inspect argparse first.)

Verify visually: stations colored differently under **na**; toggle **vóór** recolors; **Δ** nearly uniform for +5 cm.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/rijnland_whatif.py nldt/tests/test_rijnland_whatif.py
git commit -m "$(cat <<'EOF'
Add Breda-style Leaflet map for Rijnland peilen what-if.

EOF
)"
```

---

### Task 3: Docs smoke path

**Files:**
- Modify: `nldt/15-cdc-data-lake-pipeline.md` (section “Rijnland what-if”)

**Interfaces:**
- Consumes: artefacts from Task 2 (`whatif-map.html`, `summary.mapHtml`)
- Produces: documented open path for humans/agents

- [ ] **Step 1: Update the what-if section**

In `nldt/15-cdc-data-lake-pipeline.md`, under `## Rijnland what-if (implemented)`, change the artefact sentence to include the map, e.g.:

```markdown
Scenario deltas on peilen archive → CDC bronze batch → DuckDB silver apply →
`whatif-report.json` + `whatif-diff.html` + **`whatif-map.html`** (Leaflet,
Breda-style scenario panel; modes na / vóór / Δ) + optional peil-conflict replay.

Smoke (map): after a run, open
`poc-rijnland/runs/<ts>-peilen-whatif/whatif-map.html` (needs network for
Leaflet/OSM CDN). Default colour = absolute peil **na** scenario so uniform
Δ still shows spatial variation.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/15-cdc-data-lake-pipeline.md
git commit -m "$(cat <<'EOF'
Document peilen what-if map smoke path.

EOF
)"
```

---

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| `whatif-map.html` artefact | Task 2 |
| `build_whatif_map_html` in `rijnland_whatif.py` | Task 2 |
| Wire `run_whatif` + `mapHtml` summary | Task 2 |
| GeoJSON from archive coords | Task 1 |
| Modes after/before/delta; default after | Task 2 |
| Scenario panel (multi-ready, one scenario v1) | Task 2 |
| Leaflet 1.9.4 + CDN fallback | Task 2 |
| Doctrine line | Task 2 |
| Tests | Task 1–2 |
| Docs smoke | Task 3 |
| Out of scope H3 / Breda edits / OLTP | — not planned |

No TBD/placeholder steps. Signatures consistent: `stations_to_geojson` → `build_whatif_map_html` → `summary["mapHtml"]`.
