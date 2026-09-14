# Rijnland peilen what-if map fase 2 (multi-scenario) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a multi-scenario Breda-style peilen map: fixed demo pack in the panel, only the CLI/process scenario disposed to CDC/lake.

**Architecture:** Load `examples/rijnland-whatif-demo-pack.json`, apply each scenario (demo + active) independently on a fresh baseline via `apply_scenario_to_archive`, merge into one Point GeoJSON with `properties.byScenario[id]`, render in `whatif-map.html`. Lake path stays single-scenario only.

**Tech Stack:** Python 3 (`nldt/.venv`), pytest, Leaflet 1.9.4 via jsDelivr, Carto basemap tiles.

**Spec:** `docs/superpowers/specs/2026-09-14-rijnland-peilen-whatif-map-fase2-design.md`

## Global Constraints

- **Doctrine:** AI proposes · pipeline disposes · human decides — demos never write OLTP/CDC/silver.
- **Interpreter:** `/Users/marc/Projecten/ldttoolbox/nldt/.venv/bin/python` with `PYTHONPATH=.` from `nldt/`.
- **Tiles/CDN:** keep `cdn.jsdelivr.net/npm/leaflet@1.9.4` and `{s}.basemaps.cartocdn.com/light_all/...` (no `tile.openstreetmap.org`).
- **Coords:** WGS84 `x`=lon, `y`=lat; skip stations missing either.
- **Default map mode:** `"after"`; default scenario = active CLI/process id.
- **Dedupe:** if active `id` equals a demo id, one panel card with `lakeApplied: true`.
- **Escape hatch:** `include_demo_pack=False` / `--no-demo-pack` → v1 single-scenario map payload.
- **Do not edit** `poc-breda/` or mutate the fase-2 design spec during implementation.
- **Commit style:** short imperative English; commit only task files; do not push unless asked.

## File map

| File | Role |
|------|------|
| `nldt/examples/rijnland-whatif-demo-pack.json` | Fixed 3-scenario demopakket |
| `nldt/services/rijnland_whatif.py` | `load_demo_pack`, `build_multi_scenario_map_payload`, HTML/JS + `run_whatif` wiring |
| `nldt/scripts/rijnland_whatif_peilen.py` | `--demo-pack` / `--no-demo-pack` |
| `nldt/tests/test_rijnland_whatif.py` | Pack / multi-payload / lake-isolation / HTML tests |
| `nldt/15-cdc-data-lake-pipeline.md` | Smoke note for multi-map |

Also commit the already-written design spec if still untracked:
`docs/superpowers/specs/2026-09-14-rijnland-peilen-whatif-map-fase2-design.md` (fold into Task 1 commit or a docs-only commit at end of Task 4).

---

### Task 1: Demo pack JSON + `load_demo_pack`

**Files:**
- Create: `nldt/examples/rijnland-whatif-demo-pack.json`
- Modify: `nldt/services/rijnland_whatif.py`
- Modify: `nldt/tests/test_rijnland_whatif.py`
- Optionally stage: `docs/superpowers/specs/2026-09-14-rijnland-peilen-whatif-map-fase2-design.md`

**Interfaces:**
- Consumes: JSON file with top-level `{"scenarios": [ ... ]}`
- Produces:
  - `DEFAULT_DEMO_PACK: Path` = `NLDT_ROOT / "examples" / "rijnland-whatif-demo-pack.json"`
  - `load_demo_pack(path: Path | None = None) -> list[dict[str, Any]]`
  - Each scenario dict has at least `id`, `title`, `delta_m`, `layer` (and optional `description`)

- [ ] **Step 1: Write the failing test**

Append to `nldt/tests/test_rijnland_whatif.py`:

```python
def test_load_demo_pack_has_three_scenarios():
    from services.rijnland_whatif import DEFAULT_DEMO_PACK, load_demo_pack

    assert DEFAULT_DEMO_PACK.is_file()
    pack = load_demo_pack()
    assert len(pack) == 3
    ids = {s["id"] for s in pack}
    assert ids == {"boezem-plus5cm", "boezem-minus5cm", "polders-plus10cm"}
    for s in pack:
        assert "delta_m" in s and "layer" in s and "title" in s
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rijnland_whatif.py::test_load_demo_pack_has_three_scenarios -v
```

Expected: FAIL (`ImportError` / missing `DEFAULT_DEMO_PACK` or file).

- [ ] **Step 3: Create demo pack file**

Create `nldt/examples/rijnland-whatif-demo-pack.json`:

```json
{
  "scenarios": [
    {
      "id": "boezem-plus5cm",
      "title": "Boezempeilen +5 cm",
      "description": "Demo: alle boezemstations 0.05 m hoger (mNAP).",
      "delta_m": 0.05,
      "layer": "boezem"
    },
    {
      "id": "boezem-minus5cm",
      "title": "Boezempeilen −5 cm",
      "description": "Demo: alle boezemstations 0.05 m lager (mNAP).",
      "delta_m": -0.05,
      "layer": "boezem"
    },
    {
      "id": "polders-plus10cm",
      "title": "Polderpeilen +10 cm",
      "description": "Demo: alle polderstations 0.10 m hoger (mNAP).",
      "delta_m": 0.10,
      "layer": "polders"
    }
  ]
}
```

- [ ] **Step 4: Implement loader**

In `nldt/services/rijnland_whatif.py` near `DEFAULT_ARCHIVE`:

```python
DEFAULT_DEMO_PACK = NLDT_ROOT / "examples" / "rijnland-whatif-demo-pack.json"


def load_demo_pack(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or DEFAULT_DEMO_PACK
    raw = json.loads(p.read_text(encoding="utf-8"))
    scenarios = raw.get("scenarios") if isinstance(raw, dict) else raw
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(f"demo pack has no scenarios: {p}")
    for s in scenarios:
        if not s.get("id") or s.get("delta_m") is None:
            raise ValueError(f"demo scenario missing id/delta_m in {p}")
    return scenarios
```

- [ ] **Step 5: Run test — expect PASS**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rijnland_whatif.py::test_load_demo_pack_has_three_scenarios -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/examples/rijnland-whatif-demo-pack.json \
  nldt/services/rijnland_whatif.py \
  nldt/tests/test_rijnland_whatif.py \
  docs/superpowers/specs/2026-09-14-rijnland-peilen-whatif-map-fase2-design.md
git commit -m "$(cat <<'EOF'
Add Rijnland peilen what-if demo pack and loader.

EOF
)"
```

(If the design spec is already committed, omit it from `git add`.)

---

### Task 2: `build_multi_scenario_map_payload`

**Files:**
- Modify: `nldt/services/rijnland_whatif.py`
- Modify: `nldt/tests/test_rijnland_whatif.py`

**Interfaces:**
- Consumes: `load_archive` / baseline `archive`; `apply_scenario_to_archive`; `load_demo_pack`
- Produces:
  - `build_multi_scenario_map_payload(baseline: dict, active: dict, demo_scenarios: list[dict] | None) -> dict`
  - Return shape matches spec contract: `scenarios`, `geo`, `defaultMode`, `defaultScenarioId`, `modes`
  - Each feature `properties.byScenario[id] = {before, after, delta_m, touched}`
  - Scenario meta includes `lakeApplied: bool` (true only for active id after dedupe)

- [ ] **Step 1: Write failing tests**

```python
def test_multi_scenario_payload_by_scenario_and_dedupe():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        build_multi_scenario_map_payload,
        load_archive,
        load_demo_pack,
    )

    baseline = load_archive(PEILEN)
    active = {
        "id": "boezem-plus5cm",
        "title": "CLI active",
        "delta_m": 0.05,
        "layer": "boezem",
        "limit": 20,
    }
    demos = load_demo_pack()
    # Force demos to same limit for speed in test by copying with limit
    demos = [{**d, "limit": 20} for d in demos]
    payload = build_multi_scenario_map_payload(baseline, active, demos)
    assert payload["defaultMode"] == "after"
    assert payload["defaultScenarioId"] == "boezem-plus5cm"
    assert payload["modes"] == ["after", "before", "delta"]
    ids = [s["id"] for s in payload["scenarios"]]
    assert ids.count("boezem-plus5cm") == 1
    assert len(payload["scenarios"]) == 3  # 3 demos, active deduped into plus5cm
    lake = [s for s in payload["scenarios"] if s["id"] == "boezem-plus5cm"][0]
    assert lake["lakeApplied"] is True
    assert any(not s["lakeApplied"] for s in payload["scenarios"] if s["id"] != "boezem-plus5cm")
    feats = payload["geo"]["features"]
    assert feats
    touched_plus = [
        f for f in feats
        if (f["properties"].get("byScenario") or {}).get("boezem-plus5cm", {}).get("touched")
    ]
    assert len(touched_plus) == 20
    sample = touched_plus[0]["properties"]["byScenario"]["boezem-plus5cm"]
    assert sample["after"] == pytest.approx(sample["before"] + 0.05)


def test_multi_payload_without_demos_is_single():
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import (
        build_multi_scenario_map_payload,
        load_archive,
    )

    baseline = load_archive(PEILEN)
    active = {"id": "only", "title": "only", "delta_m": 0.02, "layer": "boezem", "limit": 5}
    payload = build_multi_scenario_map_payload(baseline, active, demo_scenarios=[])
    assert len(payload["scenarios"]) == 1
    assert payload["scenarios"][0]["lakeApplied"] is True
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rijnland_whatif.py::test_multi_scenario_payload_by_scenario_and_dedupe \
  tests/test_rijnland_whatif.py::test_multi_payload_without_demos_is_single -v
```

Expected: FAIL — missing `build_multi_scenario_map_payload`.

- [ ] **Step 3: Implement payload builder**

Add to `nldt/services/rijnland_whatif.py`:

```python
def build_multi_scenario_map_payload(
    baseline: dict[str, Any],
    active: dict[str, Any],
    demo_scenarios: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Merge demo + active scenarios into one map payload (lake only for active)."""
    demos = list(demo_scenarios or [])
    active_id = active.get("id") or "scenario"
    # Order: demos first, then active if new; replace demo entry when same id
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for s in demos:
        sid = s.get("id") or "demo"
        if sid not in by_id:
            order.append(sid)
        by_id[sid] = {**s, "lakeApplied": False}
    if active_id in by_id:
        by_id[active_id] = {**active, "lakeApplied": True}
    else:
        order.append(active_id)
        by_id[active_id] = {**active, "lakeApplied": True}

    # Per-scenario apply on fresh baseline
    changes_by_id: dict[str, list[dict[str, Any]]] = {}
    for sid in order:
        _arch, ch = apply_scenario_to_archive(baseline, by_id[sid])
        changes_by_id[sid] = ch
        by_id[sid]["n"] = len(ch)

    # Build points from baseline coords; attach byScenario
    features: list[dict[str, Any]] = []
    for sid_station, rec in (baseline.get("stations") or {}).items():
        x, y = rec.get("x"), rec.get("y")
        if x is None or y is None:
            continue
        by_scen: dict[str, Any] = {}
        for scen_id, ch_list in changes_by_id.items():
            # index changes once outside loop in real impl for O(n)
            pass
        features.append(...)  # see full impl below

    # Prefer this complete implementation:
```

**Use this complete function body (replace the sketch above):**

```python
def build_multi_scenario_map_payload(
    baseline: dict[str, Any],
    active: dict[str, Any],
    demo_scenarios: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    demos = list(demo_scenarios or [])
    active_id = str(active.get("id") or "scenario")
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for s in demos:
        sid = str(s.get("id") or "demo")
        if sid not in by_id:
            order.append(sid)
        by_id[sid] = {**s, "lakeApplied": False}
    if active_id in by_id:
        by_id[active_id] = {**active, "lakeApplied": True}
    else:
        order.append(active_id)
        by_id[active_id] = {**active, "lakeApplied": True}

    change_index: dict[str, dict[str, dict[str, Any]]] = {}
    for sid in order:
        _arch, ch_list = apply_scenario_to_archive(baseline, by_id[sid])
        change_index[sid] = {c["peilgebied_id"]: c for c in ch_list}
        by_id[sid]["n"] = len(ch_list)

    features: list[dict[str, Any]] = []
    for st_id, rec in (baseline.get("stations") or {}).items():
        x, y = rec.get("x"), rec.get("y")
        if x is None or y is None:
            continue
        by_scen: dict[str, Any] = {}
        for sid in order:
            ch = change_index[sid].get(st_id)
            if ch:
                by_scen[sid] = {
                    "before": float(ch["before_m"]),
                    "after": float(ch["waterstand_m"]),
                    "delta_m": float(ch["delta_m"]),
                    "touched": True,
                }
            else:
                latest = rec.get("latest") or {}
                val = latest.get("value")
                if val is None:
                    continue
                v = float(val)
                by_scen[sid] = {
                    "before": v,
                    "after": v,
                    "delta_m": 0.0,
                    "touched": False,
                }
        if not by_scen:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
                "properties": {
                    "id": st_id,
                    "name": rec.get("name") or st_id,
                    "layer": rec.get("layer") or "",
                    "byScenario": by_scen,
                },
            }
        )

    scenarios_meta = []
    for sid in order:
        s = by_id[sid]
        scenarios_meta.append(
            {
                "id": sid,
                "title": s.get("title") or sid,
                "description": s.get("description") or "",
                "delta_m": s.get("delta_m"),
                "layer": s.get("layer") or "all",
                "n": int(s.get("n") or 0),
                "lakeApplied": bool(s.get("lakeApplied")),
            }
        )

    return {
        "scenarios": scenarios_meta,
        "geo": {"type": "FeatureCollection", "features": features},
        "defaultMode": "after",
        "defaultScenarioId": active_id,
        "modes": ["after", "before", "delta"],
    }
```

Note on untouched branches: the `else` branch that fills `touched: False` for every station×scenario can make the FC huge and slow. **Prefer:** only add `byScenario[sid]` when `ch` exists **or** when you need baseline for colour domain. Spec allows greying untouched. Simpler/faster variant accepted by tests above:

Only attach `byScenario[sid]` when the station appears in `change_index[sid]` **or** always attach baseline `touched: False` for stations that have coords — tests only assert touched count for plus5cm. Implementing full baseline for all scenarios is OK if tests stay under a few seconds; if slow, only include stations that are touched by **any** scenario plus enough untouched for context — **minimum for tests:** all stations that are touched by at least one scenario, with `byScenario` entries for every `sid` in `order` (missing → baseline value `touched: False`).

Recommended lean rule used by implementer:

```python
# Collect station ids touched by any scenario
touched_any = set()
for idx in change_index.values():
    touched_any.update(idx.keys())
# Emit features for all stations with coords that are in touched_any
# OR all with coords (simpler). Prefer all with coords for map completeness.
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rijnland_whatif.py::test_multi_scenario_payload_by_scenario_and_dedupe \
  tests/test_rijnland_whatif.py::test_multi_payload_without_demos_is_single -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/rijnland_whatif.py nldt/tests/test_rijnland_whatif.py
git commit -m "$(cat <<'EOF'
Add multi-scenario peilen what-if map payload builder.

EOF
)"
```

---

### Task 3: HTML/JS + `run_whatif` + CLI

**Files:**
- Modify: `nldt/services/rijnland_whatif.py` (`build_whatif_map_html`, `run_whatif`)
- Modify: `nldt/scripts/rijnland_whatif_peilen.py`
- Modify: `nldt/tests/test_rijnland_whatif.py`

**Interfaces:**
- Consumes: `build_multi_scenario_map_payload`, `load_demo_pack`
- Produces:
  - `build_whatif_map_html` accepts either legacy `(archive, changes, scenario, dest)` **or** prefer new signature:
    - `build_whatif_map_html(dest: Path, *, payload: dict) -> Path`  
    - Keep a thin wrapper: if called with old args, build single-scenario payload via `build_multi_scenario_map_payload(archive_as_baseline_from_changes...)` — simplest path:
    - Change to: `build_whatif_map_html(payload: dict, dest: Path) -> Path` and update all call sites/tests.
  - JS reads `byScenario[actScen]` for colours/popups; scenario cards show lake badge when `lakeApplied`.
  - `run_whatif(..., include_demo_pack: bool = True, demo_pack_path: Path | None = None)`
  - Summary keys: `demoPack`, `scenariosOnMap` (list of ids)
  - Lake apply still only from active `changes`

- [ ] **Step 1: Write / update failing tests**

Update `test_build_whatif_map_html_has_data_and_modes` to build a multi payload and assert multiple scenario ids in HTML.

Add:

```python
def test_run_whatif_multi_map_lake_only_active(tmp_path, monkeypatch):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services import rijnland_whatif as rw

    calls = {"cdc": 0}

    def fake_write_cdc(changes, **kwargs):
        calls["cdc"] += 1
        p = tmp_path / "fake.parquet"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(rw, "write_cdc_batch", fake_write_cdc)
    monkeypatch.setattr(rw, "_load_apply_batches", lambda: (lambda batches, dest: {"ok": True}))

    active = {
        "id": "cli-active-unique",
        "title": "CLI unique",
        "delta_m": 0.05,
        "layer": "boezem",
        "limit": 5,
    }
    out = rw.run_whatif(
        active,
        archive_path=PEILEN,
        out_dir=tmp_path / "run",
        apply_to_lake=True,
        attach_conflict_replay=False,
        include_demo_pack=True,
    )
    html = Path(out["summary"]["mapHtml"]).read_text(encoding="utf-8")
    assert "cli-active-unique" in html
    assert "boezem-minus5cm" in html
    assert "polders-plus10cm" in html
    assert out["summary"]["scenariosOnMap"]
    assert calls["cdc"] == 1  # only active batch
    assert len(out["summary"]["scenariosOnMap"]) >= 3


def test_run_whatif_no_demo_pack_single(tmp_path):
    if not PEILEN.is_file():
        pytest.skip("peilen.json missing")
    from services.rijnland_whatif import run_whatif

    out = run_whatif(
        {"id": "solo", "title": "solo", "delta_m": 0.05, "layer": "boezem", "limit": 3},
        archive_path=PEILEN,
        out_dir=tmp_path / "solo",
        apply_to_lake=False,
        attach_conflict_replay=False,
        include_demo_pack=False,
    )
    html = Path(out["summary"]["mapHtml"]).read_text(encoding="utf-8")
    assert "solo" in html
    assert "boezem-minus5cm" not in html
```

Also update existing `test_build_whatif_map_html_has_data_and_modes` to use the new `build_whatif_map_html(payload, dest)` API (build payload via `build_multi_scenario_map_payload` with empty demos or one scenario).

- [ ] **Step 2: Run new tests — expect FAIL**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest \
  tests/test_rijnland_whatif.py::test_run_whatif_multi_map_lake_only_active \
  tests/test_rijnland_whatif.py::test_run_whatif_no_demo_pack_single -v
```

Expected: FAIL on unexpected kwargs / missing summary keys.

- [ ] **Step 3: Refactor `build_whatif_map_html(payload, dest)`**

Replace the payload construction at the top of `build_whatif_map_html` so it takes `payload: dict` already built. Update JS:

1. `var actScen = D.defaultScenarioId || (D.scenarios[0] && D.scenarios[0].id);`
2. Domain for absolute colours: iterate all features × all `byScenario` values' before/after.
3. `function blob(p){ return (p.byScenario||{})[actScen] || null; }`
4. Markers: skip or grey if `!blob(p)`; colour from `blob(p).after|before|delta_m`.
5. Scenario cards: on click set `actScen=s.id`, toggle `.actief`, `ververs()`.
6. Badge: if `s.lakeApplied` show `<span class="soort">lake</span>` (reuse/add CSS `.soort` like Breda).
7. Popup uses `blob(p)`.
8. Keep Carto + jsDelivr.

Minimal CSS add:

```css
.scen-kaart .soort{font-size:11px;padding:1px 7px;border-radius:9px;background:#e8f4fa;
  color:#0b3d5c;display:inline-block;margin:3px 4px 3px 0}
```

- [ ] **Step 4: Wire `run_whatif`**

```python
def run_whatif(
    scenario: dict[str, Any],
    *,
    archive_path: Path | None = None,
    out_dir: Path | None = None,
    apply_to_lake: bool = True,
    attach_conflict_replay: bool = True,
    include_demo_pack: bool = True,
    demo_pack_path: Path | None = None,
) -> dict[str, Any]:
    archive = load_archive(archive_path)
    scenario_archive, changes = apply_scenario_to_archive(archive, scenario)
    if not changes:
        raise ValueError("scenario touched 0 stations — check layer/stationIds/limit")
    # ... write peilen-whatif / scenario / diff as today ...
    demos = load_demo_pack(demo_pack_path) if include_demo_pack else []
    payload = build_multi_scenario_map_payload(archive, scenario, demos)
    map_html = build_whatif_map_html(payload, run_dir / "whatif-map.html")
    # lake apply ONLY `changes` from active — unchanged
    # summary extras:
    #   "demoPack": str(demo_pack_path or DEFAULT_DEMO_PACK) if include_demo_pack else None,
    #   "scenariosOnMap": [s["id"] for s in payload["scenarios"]],
```

Important: `build_multi_scenario_map_payload` must use the **baseline** `archive` (pre-active), not `scenario_archive`.

- [ ] **Step 5: CLI flags**

In `nldt/scripts/rijnland_whatif_peilen.py`:

```python
ap.add_argument("--demo-pack", type=Path, default=None,
                help="Demo pack JSON (default: examples/rijnland-whatif-demo-pack.json)")
ap.add_argument("--no-demo-pack", action="store_true",
                help="Map shows only the active scenario (v1 behaviour)")
# ...
result = run_whatif(
    scenario,
    archive_path=args.archive,
    out_dir=args.out,
    apply_to_lake=not args.no_lake,
    attach_conflict_replay=not args.no_conflict,
    include_demo_pack=not args.no_demo_pack,
    demo_pack_path=args.demo_pack,
)
```

- [ ] **Step 6: Fix callers / old tests**

Update `test_build_whatif_map_html_has_data_and_modes` and any direct `build_whatif_map_html(archive, changes, scenario, dest)` calls to the new signature.

- [ ] **Step 7: Run full what-if suite**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python -m pytest tests/test_rijnland_whatif.py -v
```

Expected: all PASS.

- [ ] **Step 8: Manual smoke**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && \
  PYTHONPATH=. .venv/bin/python scripts/rijnland_whatif_peilen.py \
    --delta-m 0.05 --layer boezem --no-conflict --no-lake && \
  open "$(ls -td ../poc-rijnland/runs/*-peilen-whatif | head -1)/whatif-map.html"
```

Verify ≥3 scenario cards; clicking minus5cm / polders recolors; lake badge on active.

- [ ] **Step 9: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/rijnland_whatif.py \
  nldt/scripts/rijnland_whatif_peilen.py \
  nldt/tests/test_rijnland_whatif.py
git commit -m "$(cat <<'EOF'
Wire multi-scenario peilen what-if map with demo pack.

EOF
)"
```

---

### Task 4: Docs

**Files:**
- Modify: `nldt/15-cdc-data-lake-pipeline.md` (Rijnland what-if section)
- Ensure design spec is committed if still untracked

**Interfaces:**
- Consumes: Task 3 artefacts (`scenariosOnMap`, `--demo-pack`, `--no-demo-pack`)
- Produces: documented smoke for multi-map

- [ ] **Step 1: Update docs**

Add under the what-if section:

```markdown
### Multi-scenario map (fase 2)

Default map loads `examples/rijnland-whatif-demo-pack.json` (boezem ±5 cm,
polders +10 cm) plus the CLI/process scenario. Click scenario cards to recolour.
Only the active scenario is written to CDC/silver.

```bash
PYTHONPATH=. python scripts/rijnland_whatif_peilen.py --delta-m 0.05 --layer boezem --no-conflict --no-lake
open ../poc-rijnland/runs/<ts>-peilen-whatif/whatif-map.html
# v1 single-scenario map:
PYTHONPATH=. python scripts/rijnland_whatif_peilen.py --delta-m 0.05 --layer boezem --no-demo-pack --no-lake --no-conflict
```
```

- [ ] **Step 2: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/15-cdc-data-lake-pipeline.md \
  docs/superpowers/specs/2026-09-14-rijnland-peilen-whatif-map-fase2-design.md \
  docs/superpowers/plans/2026-09-14-rijnland-peilen-whatif-map-fase2.md
git commit -m "$(cat <<'EOF'
Document peilen what-if multi-scenario map (fase 2).

EOF
)"
```

---

## Spec coverage (self-review)

| Spec item | Task |
|-----------|------|
| Demo pack JSON (3 scenarios) | Task 1 |
| `load_demo_pack` | Task 1 |
| Multi payload + `byScenario` + dedupe + `lakeApplied` | Task 2 |
| HTML multi panel + modes | Task 3 |
| `run_whatif` lake-only-active + summary keys | Task 3 |
| CLI `--demo-pack` / `--no-demo-pack` | Task 3 |
| Tests (pack, multi, lake isolation, escape hatch) | Tasks 1–3 |
| Docs smoke | Task 4 |
| Out of scope hex/MCP/Breda edits | — not planned |

No TBD placeholders. Signatures: `load_demo_pack` → `build_multi_scenario_map_payload` → `build_whatif_map_html(payload, dest)` → `run_whatif(..., include_demo_pack=)`.
