# nLDT simulations

Static visualisations for **every** governed PoC — not only Utrecht.
Open via `file://` or `python3 -m http.server` from this directory.

## Hub

[`index.html`](index.html) — per-PoC sections with story, agent flow, and related demos.

## Rondleiding (alle demo's & architecturen)

[`toolbox-tour.html`](toolbox-tour.html) — begeleide tour in **7 rondes en 29 stops**:
fundament & architectuur, de vier PoC's, de RegelRecht/TPOD/DSO-keten (incl.
artefacten en voorstel-sweep), HCS/EDIC, bestuur & agentic state, platform &
dataspace en governance & roadmap. Werkt offline vanaf schijf; voortgang in
localStorage; dieplinks via `?stop=N`; pijltjestoetsen navigeren.

## Agentic State — executive demo

[`agentic-state-demo-en.html`](agentic-state-demo-en.html) (EN) ·
[`agentic-state-demo.html`](agentic-state-demo.html) (NL) — ten scenes: the Sitra diagnosis
(organisation-first vs function-first), the function as the shared level, a **simulated run through
the reference chain** (intake → norm specialist → formaliser → world-scene → geo → critic →
explainer; replay of the canonical Utrecht wind run `20260830T113234Z-wind`), the six PoCs as
concrete instances, the five gates, reuse, the learning loop, the phasing, and the ask to the board.
Design: [`docs/AGENTIC_STATE_PLAN.md`](../../docs/AGENTIC_STATE_PLAN.md).

## Human-Centred Services — EDIC recipe PoC's (fase 1 + 2)

[`hcs-key-demo.html`](hcs-key-demo.html) (NL) ·
[`hcs-key-demo-en.html`](hcs-key-demo-en.html) (EN) — The Key als recipe-PoC: vijf
blueprint-stappen als deterministische replay (`hcs-life-event-run`), persona-switcher
met edge cases, GenAI-testbank, KPI-baseline en leerstaat. Ontwerp:
[`docs/superpowers/specs/2026-10-09-hcs-recipes-pocs-design.md`](../../docs/superpowers/specs/2026-10-09-hcs-recipes-pocs-design.md).
Herbouwen:

```bash
nldt/.venv/bin/python nldt/simulation/hcs/build_runs.py --stamp <ISO-stamp>
```

[`hcs-uam-demo.html`](hcs-uam-demo.html) · [`hcs-grn-demo.html`](hcs-grn-demo.html) ·
[`hcs-cir-demo.html`](hcs-cir-demo.html) · [`hcs-min-demo.html`](hcs-min-demo.html)
(NL, met EN-switch; fase 3) — de vier city-dishes: UAM-01/09, GRN-01/03, CIR-04/01,
MIN-01/04 als deterministische replays via `hcs-recipe-run`, met scenario-switcher,
offline SVG-visualisaties (kaartschema, bladerdakraster, tijdreeks, hubladder),
testbank en KPI-panelen. De fixtures zijn tweetalig — elke demo heeft een
[`-en.html`](hcs-uam-demo-en.html)-tweeling.

[`hcs-menu-demo.html`](hcs-menu-demo.html) — het menu: alle 53 recipes over vijf
dishes als kaarten (elf met PoC-markering en doorklik), vijf stappen × G1–G5,
roll-up naar KVI's, recipe-cyclus en scale path.

## Per PoC

| PoC | Story | Agent flow | Extra demos |
|-----|-------|------------|-------------|
| **Breda** | [`poc-breda.html`](poc-breda.html) | [`breda-flow-demo.html`](breda-flow-demo.html) | [`breda-report-demo.html`](breda-report-demo.html) (Leaflet scan) · [`breda-whatif-demo.html`](breda-whatif-demo.html) · tour `?poc=breda` |
| **Utrecht** | [`poc-utrecht.html`](poc-utrecht.html) | [`utrecht-flow-demo.html`](utrecht-flow-demo.html) | [`utrecht-whatif-demo.html`](utrecht-whatif-demo.html) (Plane B copilot) · [`utrecht-hyworld-recon-demo.html`](utrecht-hyworld-recon-demo.html) (HY WorldMirror 3D context) · Building/3D/GIS overlay/mock/web3d + `?poc=utrecht` |
| **Rijnland** | [`poc-rijnland.html`](poc-rijnland.html) | [`rijnland-flow-demo.html`](rijnland-flow-demo.html) | [`rijnland-whatif-demo.html`](rijnland-whatif-demo.html) (Leaflet) + `?poc=rijnland` |
| **Eindhoven** | [`poc-eindhoven.html`](poc-eindhoven.html) | [`eindhoven-flow-demo.html`](eindhoven-flow-demo.html) | [`eindhoven-report-demo.html`](eindhoven-report-demo.html) · tour `?poc=eindhoven` |

## RegelRecht-demo (Utrecht & Eindhoven)

[`regelrecht-demo.html`](regelrecht-demo.html) — de keten artikel → YAML → schema →
executie → trace over het **volledige instrument** (artikelkiezer + coverage),
live rekenend waar `machine_readable` bestaat, met engine-selftest (16+K),
onthoudingen-paneel en de altijd openstaande jurittoets.

### Volle-instrument export

```bash
nldt/.venv/bin/python nldt/simulation/regelrecht/full_export/build_all.py --stamp <ISO-timestamp>
```

Schrijft `regelrecht/full_export/out/{utrecht,eindhoven}-cvdr*.yaml`,
`*-formalization-report.json`, `*-articles.json` en herbouwt de demo.
Schema: NDD RegelRecht **v0.8.11** (vastgepind, `regelrecht/schema/pin.json`); `full_export`
leest `FormalRule.execution` als bron van waarheid (NormCard herijking:
`docs/superpowers/specs/2026-10-25-normcard-formalizer-regelrecht-design.md`).
Ontwerp: `docs/superpowers/specs/2026-10-14-regelrecht-full-instrument-export-design.md`.

Smoke-runs (art. 5.3 / 10.2) blijven herbouwbaar via:

```bash
nldt/.venv/bin/python nldt/simulation/regelrecht/build_runs.py --stamp <ISO-timestamp>
```

(roept de volle demo aan zodra formalization-reports aanwezig zijn).
Contract: `regelrecht/simulation-run.schema.json`;
fase-1-ontwerp: `docs/superpowers/specs/2026-09-29-simulation-regelrecht-design.md`.

### TpOD/IMOW-index (annotatielaag)

```bash
nldt/.venv/bin/python -m nldt.simulation.regelrecht.tpod --instruments eindhoven,utrecht --toets --geo [--voorstel <fixture>]
```

Bouwt (offline, op de gecachte Presenteren-antwoorden van `dso_overlap`) per
instrument een `tpod-index`: wId-anchoring per artikel+lid, geo-feiten
(geselecteerde locaties + GIO-geometrierefs), documentstructuur,
activiteitstructuur en een expliciete pons-status. Met `--toets` worden de
formalized artikelen uit de DSO-hit geëxecuteerd op die geo-feiten (feit /
scenario / onthouding; met `--voorstel` volledig getoetst met scorecard).
Met `--geo` wordt de DSO-puntselectie punt-in-polygoon gekruisvalideerd
tegen de GIO-GML's uit het OW-uitwisselpakket (sweep + naam-afstemming).
Kansenkaart, gemeten cijfers en de punt-toets-resultaten:
[`docs/POC_TPOD_IMOW_KANSEN.md`](../../docs/POC_TPOD_IMOW_KANSEN.md).

### RTR/STTR — "STTR toepast" als derde status

```bash
# 1. RTR-cache verversen (PRE; DSO_API_KEY in .env, 162 Eindhovense DMN's):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.dso_overlap.rtr --instruments eindhoven --bestanden
# 2. STTR-import-index (offline, uit de cache; contract sttr-index/v1):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.sttr --instruments eindhoven
# 3. corpus-staging voor beide PoC's (offline; fase 1 migratietraject):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.corpus_export
```

De STTR-import ontleedt de DMN's (1.1 én 1.2) tot engine-projecties:
Eindhoven 162 bestanden · 3.465 decisions · 2.322 projecteerbaar · 2.044
scenario-uitgevoerd; niet-projecteerbare decisions dragen een expliciete reden
(top: `not(null)`-wachters en COLLECT multi-hit). De hub (Tab 7) toont per
instrument de derde status "STTR toepast", met absent-status waar geen OIN
gekoppeld is. Notitie: [`docs/POC_STTR_IMTR_KANSEN.md`](../../docs/POC_STTR_IMTR_KANSEN.md);
migratietraject: [`docs/MAPPING_DSO_NAAR_REGELRECHT.md`](../../docs/MAPPING_DSO_NAAR_REGELRECHT.md).

### Laya-formalisatie-poortwachter (Inzet A)

```bash
# 1. dataset (offline, deterministisch; holdout + kruisinstrument):
nldt/.venv/bin/python simulation/laya_formalizer/build_dataset.py
nldt/.venv/bin/python simulation/laya_formalizer/build_dataset.py --mode cross \
  --out-dir simulation/laya_formalizer/data-cross
# 2. fine-tune (trainings-venv, ~15–25 min per run op M3 Max):
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/finetune.py
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/finetune.py \
  --data-dir data-cross --output-dir checkpoints/formalizer-laya-cross
# 3. hints-artefacten + eval (laya-hints/v1 naast het formalization-report):
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/predict_export.py
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/predict_export.py --cross-eval
# 3b. ronde 3 — bijscholing voor een nieuw instrument (leercurve: ±⅓ van de
#     artikelen labels → 89% acc / 70% formalized-precisie; <50 labels niet doen):
nldt/.venv/bin/python simulation/laya_formalizer/build_dataset.py --mode bijscholing \
  --sample 150 --out-dir simulation/laya_formalizer/data-bijscholing-150
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/finetune.py \
  --data-dir simulation/laya_formalizer/data-bijscholing-150 \
  --output-dir simulation/laya_formalizer/checkpoints/formalizer-laya-bijscholing-150
deep-agents/laya_train/.venv/bin/python simulation/laya_formalizer/predict_export.py --bijscholing 150
# 4. werklijst template-gaps / LLM-kandidaten (nldt/.venv, artefact-only):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.full_export.laya_werklijst
```

System-1-triage per artikel (`voorspelde_status`, `heeft_evidence`, gate 0,55):
hints zijn adviserend, raken het formalization-report-contract niet en failen
zacht. Checkpoints blijven lokaal (sha256 in de artefacten). Plan:
[`docs/PLAN_LAYA_INZET.md`](../../docs/PLAN_LAYA_INZET.md); implementatieplan:
[`docs/superpowers/plans/2026-11-08-laya-formalisatie-poortwachter.md`](../../docs/superpowers/plans/2026-11-08-laya-formalisatie-poortwachter.md).

## Architecture tour

[`poc-mcp-skills.html`](poc-mcp-skills.html) — layers, Play tours (lifecycle, router, all four PoCs), Recipes catalogue.  
Deep-link: `?poc=breda|utrecht|rijnland|eindhoven|lifecycle|router`.

## Utrecht platform demos (also linked from Utrecht section)

| Demo | File |
|------|------|
| Building + zoning plan | `building-agent-demo.html` |
| Agent + 3D BAG | `agent-3d-demo.html` |
| GIS overlay agent flow | `agent-flow-demo.html` |
| Overlay mock | `mock-overlay-demo.html` |
| 3D BAG viewer | `web3d-viewer.html` |

## Opening

```bash
cd nldt/simulation
python3 -m http.server 8090
# → http://127.0.0.1:8090/
# → http://127.0.0.1:8090/rijnland-whatif-demo.html
```

Design: [`docs/superpowers/specs/2026-09-20-nldt-simulations-all-pocs-design.md`](../../docs/superpowers/specs/2026-09-20-nldt-simulations-all-pocs-design.md).
