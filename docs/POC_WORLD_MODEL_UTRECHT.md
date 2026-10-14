# World model — PoC Utrecht scenario-copilot

Integratie van een **world model**-laag voor Plane B (scenario sweep) in de Utrecht
PoC, geselecteerd en gepositioneerd volgens de Stanford HAI issue brief
[*The World Model and Spatial Intelligence Era*](https://hai.stanford.edu/assets/files/hai-issue-brief-the-world-model-and-spatial-intelligence-era.pdf)
(juli 2026).

## Taxonomie (HAI / Fei-Fei Li)

| Categorie | Functie | Rol in PoC Utrecht |
|-----------|---------|-------------------|
| **Simulator** | Toestand, geometrie, dynamica | [`poc/pipeline/engine.py`](../poc/pipeline/engine.py) + scenario-sweep — **bron van waarheid** voor km², IoU, zones |
| **Renderer** | Observaties / verkenbare scènes | **World Labs Marble** (exploratief) + **HY-World WorldMirror** (3D reconstructie-context) + Leaflet/Cesium **engine view** |
| **Planner** | Acties in de fysieke wereld | Buiten scope scenario-copilot |

De brief waarschuwt voor de *visual plausibility trap*: een Renderer mag er overtuigend
uitzien zonder juridisch of geometrisch correct te zijn. Daarom geldt:

> **AI proposeert (Marble-prompt / HY-recon) · engine disposeert (zones) · mens beslist (HITL).**

Zie [`docs/GENAI_SEAMS.md`](GENAI_SEAMS.md) S7/S8 en REQ-05 in
[`nldt/edic/requirements-backlog.md`](../nldt/edic/requirements-backlog.md).

## Gekozen world model: Marble (Renderer) + engine-grounded scene graph

**Primair:** deterministische GeoJSON uit `poc/scenario-runs/` (control + per-scenario
`geometryFile`) in [`nldt/simulation/utrecht-whatif-demo.html`](../nldt/simulation/utrecht-whatif-demo.html).

**Secundair (exploratie):** [World Labs Marble](https://worldlabs.ai/) — categorie
Renderer in de brief. Alleen via [`world-scene-spec`](../poc/schemas/world-scene-spec.schema.json):
gestructureerde `marblePrompt` afgeleid van `scenario-report.json`, nooit vrije
LLM-geometrie.

Marble-output gaat **niet** door Critic V2/V3 en vervangt geen `zones.geojson`.

### Disclaimer (brief)

De HAI-brief vermeldt financiering door o.a. Nvidia/Google en dat mede-auteur
Fei-Fei Li CEO is van World Labs. De keuze hier is **functioneel** (Renderer voor
copilot); WM-0 (engine-only demo) blijft volwaardig zonder Marble-API.

## Architectuur

```
scenario-report.json  ──►  world_scene.build_specs()  ──►  world-scene-specs.json
        │                              │
        └──────────────────────────────┼──► Leaflet demo (engine-only metrics)
                                       ├──► Marble explore URL (hypothetical + HITL)
                                       └──► HY WorldMirror recon assets (context + HITL/fixture)
```

Mapping naar [`docs/SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md) §3.4
(scenario plane) en dual-audience
[`nldt/22-dual-audience-spatial-planning.md`](../nldt/22-dual-audience-spatial-planning.md):
publiek ziet engine view; Marble / HY-recon achter planner-gate.

## Processen & demo

| Artefact | Pad |
|----------|-----|
| Schema | `poc/schemas/world-scene-spec.schema.json` |
| Builder | `poc/pipeline/world_scene.py` |
| HY recon adapter | `poc/pipeline/hyworld_recon.py` |
| OGC process | `world-scene-build` in `nldt/services/process_adapter/poc_handlers.py` |
| Demo (Leaflet / Marble) | `nldt/simulation/utrecht-whatif-demo.html` |
| Demo (Cesium / HY recon) | `nldt/simulation/utrecht-hyworld-recon-demo.html` |
| Fixture-run (geo + recon) | `poc/scenario-runs/_fixture-zon-scen/` (+ `recon/`) |
| Canonical LLM sweep (cijfers) | `poc/scenario-runs/20260831T175842Z-zon-scen/scenario-report.json` |

### Marble-gates (WM-1 spike)

- `allowGenerativeRenderer` alleen `true` bij `provenanceBasis.type === hypothetical`
- Live URL: `MARBLE_API_BASE` + `marble_client.build_explore_url` (geen zones naar Marble zonder expliciete operator-goedkeuring: `MARBLE_HITL_APPROVED=1` of process-input `hitlApproved`)

### HY World / WorldMirror (reconstructie)

[HY-World 2.0](https://hyworld.dev/) (Tencent HunyuanWorld) is een **open-source** world model.
Voor Utrecht gebruiken we eerst **WorldMirror 2.0** (multi-view / video → point cloud /
3DGS / cameras), niet de full text→wereld generatiepipeline.

| Aspect | Marble | HY WorldMirror |
|--------|--------|----------------|
| Rol | generative explore URL | 3D reconstructie-context |
| Output in PoC | explore link | `points.cesium.json` (+ optioneel mesh/cameras) |
| Contract | `marble` / `marblePrompt` | `hyworldRecon` |
| Stamp | `marble-explore-not-legal` | `hyworld-recon-context-not-legal` |
| CI | geen API-key nodig voor fixture | **geen GPU/weights in CI** — fixture-first |

Adapter:

```bash
# PLY → Cesium JSON (stdlib)
cd poc && python3 -m pipeline.hyworld_recon export-points \
  --ply path/to/points.ply --out recon/points.cesium.json --lon-lat

# Refs op world-scene-specs zetten (live vereist HITL; --fixture voor demodata)
python3 -m pipeline.hyworld_recon register \
  --run-dir scenario-runs/_fixture-zon-scen \
  --asset-dir scenario-runs/_fixture-zon-scen/recon --fixture

# Optioneel live (GPU + clone): export HYWORLD_ROOT=/path/to/HY-World-2.0
python3 -m pipeline.hyworld_recon worldmirror --input photos/ --out-dir recon/
```

Hardware (upstream): CUDA 12.x, Python 3.11+, typisch 24–40+ GB VRAM. Product-preview
op hyworld.dev kan waitlist/China-signup vereisen; PoC vertrouwt op
[GitHub open source](https://github.com/Tencent-Hunyuan/HY-World-2.0) + fixtures.

Native 3DGS in Cesium zit **niet** in v0 — browser toont downsampled punten (of later mesh).

## Evaluatie (beleid, niet VBench)

- **km² / IoU / artikelen:** uitsluitend uit engine-artefacten
- **Marble / HY-recon:** documenteer coherenceduur en sim-to-real in run-notities; geen safety-critical deploy
- **PROV:** `world-scene-specs.json` als entity naast sweep `prov.json`

## Verificatie

```bash
cd poc && ../nldt/.venv/bin/python -m pytest tests/test_world_scene.py tests/test_hyworld_recon.py -q
cd ../nldt && .venv/bin/python -m pytest tests/test_world_scene.py tests/test_world_scene_process.py -q
```

Checklist: `poc/pipeline/engine.py` en `critic.py` importeren geen `marble_client` en geen
`hyworld_recon`.
