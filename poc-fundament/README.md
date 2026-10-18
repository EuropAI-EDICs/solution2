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

## Hoe een PoC het gebruikt

1. **Registries**: taken (checklist), bindings en bronnen in eigen `registry/`/`data/` (gepinde JSON).
2. **Manifest**: genereer `fase-manifest.json` uit de bindings (zie `poc-minigim/tools/gen_fase_manifest.py` als voorbeeld) — per fase agent, tools (retrieval/computation), bindingen en gates.
3. **Executor**: subclass `BindingExecutor`, bind `fetch_fn`/`cache_dir`/`cbs_filter`, registreer PoC-specifieke ops naast `DEFAULT_OPS` (zie `poc-minigim/minigim/checklist.py`).
4. **Bewijs**: golden-artefacten vóór refactors (`poc-minigim/tools/capture_golden.py`-patroon), `test_golden` erna.

## Regels

- `fundament` importeert nooit `deep-agents`, `nldt` of een poc-package (getest in `tests/test_deps.py`).
- Getallen komen uit ops, nooit uit een LLM; een falende bron is `not-delivered` + risicovlag.
- Cache-first: her-runs zijn offline reproduceerbaar; cache-bestanden zijn uitwisselbaar tussen PoC's die dezelfde bron pinnen.

Eerste consument: `poc-minigim` (PoC-5) — canonisch identiek bewezen in M2 (golden-test + live-vergelijker; volatile run-meta uitgezonderd, lagen byte-gelijkg).
Vervolg (eigen plannen): M3 slotgates in deep-agents, M4 transport-bruggen
(nldt-processes / A2A Agent Cards), M5 golden-per-fase.
