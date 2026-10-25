# poc-fundament — het MiniGIM-harnas voor PoC's

Het gedeelde fundament onder de nLDT-PoC's, gebaseerd op de MiniGIM-aanpak
(checklist-gedreven, expliciete bindingen `auto`/`partial`/`manual`,
faal-isolatie, PROV, deterministisch — zie
[`docs/MINIGIM.md`](../docs/MINIGIM.md) en de spec
`docs/superpowers/specs/2026-10-18-poc-fundament-minigim-harnas-design.md`).

## Wat hier ligt

| module | doet |
|---|---|
| `fundament/manifest.py` | laadt/valideert `fase-manifest.json` (de agent–fase–tool matrix) tegen `schemas/fase-manifest.schema.json` |
| `fundament/registers.py` | `TaskRegistry`: taken + bindings + bronnen met dekkingscheck |
| `fundament/fetch.py` | cache-first fetchers (OGC API Features, WFS 2.0, ArcGIS REST) met geïnjecteerde `cache_dir`/`user_agent` |
| `fundament/derivations.py` | pure derivatie-helpers (clip, historiefilter, statistiek, entropy) |
| `fundament/ops.py` + `executor.py` | `BindingExecutor` + generieke ops: per taak deterministisch leveren, falen degradeert (nooit fake, nooit fataal) |
| `fundament/matrix.py` | matrix → markdown (declaratief + per-run uitkomst) |
| `fundament/models.py` | modelregister-loader (BB13-patroon): computation-modellen + transports, schema-gevalideerd; conformance bewijst transport-bestaan |
| `fundament/harnesslab.py` | harness-lab motor: harness-varianten, probe-evidence en adoptie (harness2-methode, eigen deterministische rechter) |
| `tools/harness_lab.py` | CLI: `scaffold` / `probe` / `adopt` — zie de harness-lab-sectie hieronder |

## Matrix van de eerste pilot (minigim)

| fase | agent | tools | taken | bindingen | gate |
|---|---|---|---|---|---|
| F0-intake — Intake/scoping | intake (LLM) | validation | 1 | 1 auto | V0 |
| F1-omgevingsanalyse — Omgevingsanalyse (informatie ophalen) | minigim-specialist | retrieval | 69 | 14 auto, 10 partial, 45 manual | V0, V2 |
| F2-gebiedsindeling — ILS-draft gebiedsindeling | geospecialist | computation | 1 | 1 auto | V1 HITL: draft-keuze (v4 pending by design) |
| F3-doorrekening — Doorrekening (rekenmodel aanroepen) | minigim-specialist | computation | 5 | 5 partial | V3 |
| F4-synthese — Synthese & rapport | critic + explainer | validation, report | 2 | 2 auto | V0, V1, V2, V3 HITL: v4 (mens) pending |

## Hoe een PoC het gebruikt

1. **Registries**: taken (checklist), bindings en bronnen in eigen `registry/`/`data/` (gepinde JSON).
2. **Manifest**: genereer `fase-manifest.json` uit de bindings (zie `poc-minigim/tools/gen_fase_manifest.py` als voorbeeld) — per fase agent, tools (retrieval/computation), bindingen en gates.
3. **Executor**: subclass `BindingExecutor`, bind `fetch_fn`/`cache_dir`/`cbs_filter`, registreer PoC-specifieke ops naast `DEFAULT_OPS` (zie `poc-minigim/minigim/checklist.py`).
4. **Bewijs**: golden-artefacten vóór refactors (`poc-minigim/tools/capture_golden.py`-patroon), `test_golden` erna.

## Regels

- `fundament` importeert nooit `deep-agents`, `nldt` of een poc-package (getest in `tests/test_deps.py`).
- Getallen komen uit ops, nooit uit een LLM; een falende bron is `not-delivered` + risicovlag.
- Cache-first: her-runs zijn offline reproduceerbaar; cache-bestanden zijn uitwisselbaar tussen PoC's die dezelfde bron pinnen.
- **Import-brug:** consumenten zonder package-bootstrap voegen het fundament toe met
  `sys.path.append(str(REPO_ROOT / "poc-fundament"))` — append, nooit insert(0)
  (insert schaduwt lokale `tests`-packages onder unittest-discovery; M2-les).
  Zie `poc-nspd/tools/gen_fase_manifest.py` als voorbeeld.

Eerste consument: `poc-minigim` (PoC-5) — canonisch identiek bewezen in M2 (golden-test + live-vergelijker; volatile run-meta uitgezonderd, lagen byte-gelijkg).
Vervolg (eigen plannen): M3 slotgates in deep-agents, M4 transport-bruggen
(nldt-processes / A2A Agent Cards), M5 golden-per-fase.

## Harness-lab: varianten, probes, adoptie

De lab behandelt de agent-harness (prompts, slotgate-toolgrants, model-pinnen)
als versie-bare varianten — de propose–probe–compose-methode uit
[google-research/harness2](https://github.com/google-research/harness2), maar
gericht op onze eigen harness en geoordeeld door onze eigen deterministische
rechter (geen LLM-jury). Zie
`docs/superpowers/specs/2026-10-25-harness-lab-design.md`.

- **Register**: `harnessregister.json` (per poc, patroon van het
  modelregister): component (`prompt`/`toolGrants`/`modelPin`), target,
  status `actief`/`kandidaat`/`verworpen`, sha256-gepingd artifact; precies
  één `actief` per target (loader faalt daar luid op).
- **Variant**: JSON tegen `schemas/harness-variant.schema.json`; paden van
  prompt-bestanden zijn t.o.v. de map van het variantbestand.
- **Taskset**: taken (`static`/`route`/`standalone`) met deterministische
  checks (`delegatesTo`, `toolTraceIncludes`, `answer(Not)Contains`,
  `slotgate(Allows|Forbids)`) tegen `schemas/probe-taskset.schema.json`.

```bash
# 1. baselijn pinnen (register + identiteits-variant)
nldt/.venv/bin/python poc-fundament/tools/harness_lab.py scaffold \
  --adapter deepagents --register deep-agents/harnessregister.json \
  --out deep-agents/harness-lab/variants/baseline.json
# 2. proberen — fake = offline montuurbewijs; llm = echt model (check_ollama)
nldt/.venv/bin/python poc-fundament/tools/harness_lab.py probe --mode fake \
  --taskset deep-agents/harness-lab/tasksets/routing-kern.json \
  --variant deep-agents/harness-lab/variants/*.json --out harness-lab-runs/<ts>
# 3. menselijke knop: alleen met voldoend llm-bewijs (of --allow-fake)
nldt/.venv/bin/python poc-fundament/tools/harness_lab.py adopt \
  --register deep-agents/harnessregister.json \
  --variant .../variants/<id>.json --evidence .../runs/<ts>/<id>
```

Adoptie van een prompt-variant schrijft de varianttekst door naar het live
promptbestand (de verworpen voorganger houdt zijn eigen sha256, dus de oude
inhoud is reconstrueerbaar); `toolGrants`-adoptie is bewust geweigerd tot de
manifest-generatoren dat dragen. De lab-motor importeert géén agent-laag —
adapters worden door de CLI geïnjecteerd (eerste: `deep-agents/
harness_lab_adapter.py`).
