# World model — PoC Utrecht scenario-copilot

Integratie van een **world model**-laag voor Plane B (scenario sweep) in de Utrecht
PoC, geselecteerd en gepositioneerd volgens de Stanford HAI issue brief
[*The World Model and Spatial Intelligence Era*](https://hai.stanford.edu/assets/files/hai-issue-brief-the-world-model-and-spatial-intelligence-era.pdf)
(juli 2026).

## Taxonomie (HAI / Fei-Fei Li)

| Categorie | Functie | Rol in PoC Utrecht |
|-----------|---------|-------------------|
| **Simulator** | Toestand, geometrie, dynamica | [`poc/pipeline/engine.py`](../poc/pipeline/engine.py) + scenario-sweep — **bron van waarheid** voor km², IoU, zones |
| **Renderer** | Observaties / verkenbare scènes | **World Labs Marble** (exploratief) + Leaflet/Cesium **engine view** |
| **Planner** | Acties in de fysieke wereld | Buiten scope scenario-copilot |

De brief waarschuwt voor de *visual plausibility trap*: een Renderer mag er overtuigend
uitzien zonder juridisch of geometrisch correct te zijn. Daarom geldt:

> **AI proposeert (Marble-prompt) · engine disposeert (zones) · mens beslist (HITL).**

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
                                       └──► Marble explore URL (hypothetical + HITL)
```

Mapping naar [`docs/SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md) §3.4
(scenario plane) en dual-audience
[`nldt/22-dual-audience-spatial-planning.md`](../nldt/22-dual-audience-spatial-planning.md):
publiek ziet engine view; Marble achter planner-gate.

## Processen & demo

| Artefact | Pad |
|----------|-----|
| Schema | `poc/schemas/world-scene-spec.schema.json` |
| Builder | `poc/pipeline/world_scene.py` |
| OGC process | `world-scene-build` in `nldt/services/process_adapter/poc_handlers.py` |
| Demo | `nldt/simulation/utrecht-whatif-demo.html` |
| Fixture-run (geo) | `poc/scenario-runs/_fixture-zon-scen/` |
| Canonical LLM sweep (cijfers) | `poc/scenario-runs/20260831T175842Z-zon-scen/scenario-report.json` |

### Marble-gates (WM-1 spike)

- `allowGenerativeRenderer` alleen `true` bij `provenanceBasis.type === hypothetical`
- Live URL: `MARBLE_API_BASE` + `marble_client.build_explore_url` (geen zones naar Marble zonder expliciete operator-goedkeuring: `MARBLE_HITL_APPROVED=1` of process-input `hitlApproved`)

## Evaluatie (beleid, niet VBench)

- **km² / IoU / artikelen:** uitsluitend uit engine-artefacten
- **Marble:** documenteer coherenceduur en sim-to-real in run-notities; geen safety-critical deploy
- **PROV:** `world-scene-specs.json` als entity naast sweep `prov.json`

## Verificatie

```bash
cd nldt && .venv/bin/python -m pytest tests/test_world_scene.py tests/test_world_scene_process.py -q
```

Checklist: `poc/pipeline/engine.py` en `critic.py` importeren geen `marble_client`.
