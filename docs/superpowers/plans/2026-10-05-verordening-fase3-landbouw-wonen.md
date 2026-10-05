# Verordening-regeluitbreiding fase 3 (landbouw + wonen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tracks `landbouw` (H8, objectType `agricultural_expansion`) en `wonen` (H9, objectType `housing_development`) volgens het bewezen fase-1/2-patroon; eindstand negen tracks op één instrument.

**Architecture:** Elke track doorloopt het vastgelegde vierstappenpatroon (recon-shard+leger → zones registry+cache+aliases → templates+TRACKS+use-case+canonieke pass-run → docs). Bindende spiegels (gecommit): `poc/corpus/evidence-{mobiliteit,landschap}.json`, `poc/corpus/normcards-rejected-{mobiliteit,landschap}.json`, `poc/tests/test_{mobiliteit,landschap}_{zones,run}.py`, `poc/run.py::TRACKS/ZONE_SOURCES`, `poc/pipeline/agents.py::TEMPLATE_SPECS/EVIDENCE_ENRICHMENT`, SDD-ledger `.superpowers/sdd/verordening-fase2/progress.md` (lessen per taak).

**Tech Stack:** stdlib + jsonschema via `nldt/.venv`; snapshot `docs/research/sources/cvdr704250-tekst-extract.txt` als SoT; `poc/data/agrest-namen.json` (122 namen) als zoneselectie-bewijs.

## Global Constraints

- Cite-or-abstain: elke `quote_nl` letterlijk (whitespace-genormaliseerd) in de snapshot-BODY (titel-grep; de body splitst `Hoofdstuk`/nummer en `Artikel`/titel over eigen regels — TOC-grep pakt verkeerde instanties); elk artikel van het hoofdstuk in shard ∨ `ledger.articlesConsidered`; geen verzonnen zones/join-ids/getallen.
- Bestaande tracks/runs byte-identiek; gedeelde pipeline-modulen (engine, critic, explainer) onaangeroerd; suites groen (huidige stand: poc 260 passed + 1 skipped, nldt 337 passed).
- Gitignored `poc/data/*`: nieuwe registry-entries + cache-twins met `git add -f` + expliciete paden; worktree-patroon zoals fase 1/2 (branch `verordening-fase3`, worktree `ldttoolbox-vf3`, venv-symlink, poc/data kopiëren, SDD-ledger in de worktree, na merge archiveren naar hoofdwerkmap).
- Extractie-lessen (fase 1/2, geborgd): UUID's; `returnCountOnly` negeert `where` (tel via paging); umbrella-supersets geometrisch verifiëren (symdiff ~0); live paged counts per entry; begrensde `_alias_source_ids`-parse (ZONE_SOURCES-blok) is nu standaard; world-scene-fixture is timestamp-stil gemaakt — werkmap hoort schoon te blijven na suite-runs.
- Dedup-regel: bestaande registry-entries (o.a. `agrest-ov-landelijk-gebied`, `agrest-ov-stiltegebied`) hergebruikt alléén bijzelfde service+laag; de registry-rol is een regelfamilie-uitspraak, de per-rule binding (exclusion vs conditional vs inclusion) gebeurt in de track-templates (grondwater-precedent). `Landelijk gebied` is voor wind inclusion-scope (art. 9.2) en voor wonen verstedelijkingsverbod-zone (art. 9.3) — zelfde laag, per-rule binding.
- Reeds in de schema's: objectTypes `agricultural_expansion`/`housing_development` bestaan; ambitions-enum mist een landbouwwaarde (taak 1); norm-card theme-pattern mist `landbouw|wonen` (taak 1).

---

### Task 1: Enums + theme-pattern

**Files:** Modify `poc/schemas/opportunity-map-request.schema.json` (ambitions + `agriculture`), `poc/schemas/norm-card.schema.json` (theme-pattern + `landbouw|wonen`); Test: uitbreiding `poc/tests/test_objecttype_enum.py`.
- [ ] Ambitions-enum + `"agriculture"` (positieve test; negatieve tests bestaan al).
- [ ] Theme-pattern uitgebreid met `landbouw|wonen`.
- [ ] Suite groen; commit `feat(poc): enums +agriculture; theme +landbouw|wonen`.

### Task 2: landbouw-recon

**Files:** Create `poc/corpus/evidence-landbouw.json`, `poc/corpus/normcards-rejected-landbouw.json`; Modify `poc/corpus/track-manifest.json` + gate-parametrize.
**Interfaces:** ids `LB-01…`, objectType `agricultural_expansion`, chapters `["8"]`; H8 = 7 artikelen, álle met titel "Instructieregel" (8.1 agrarisch bedrijf, 8.2 landbouwontwikkelingsgebied, 8.3 landbouwstabiliseringsgebied, 8.4 geitenhouderij, 8.5 concentratiegebied glastuinbouw, 8.6 glastuinbouw niet toegestaan, 8.7 beperken bodembewerking). Verwachte shard ≥5; zones-kandidaten staan letterlijk in `agrest-namen.json` (Gebied agrarische bedrijven, Landbouwontwikkelingsgebied, Landbouwstabiliseringsgebied, Concentratiegebied glastuinbouw, Gebied glastuinbouw niet toegestaan, Gebied beperken bodembewerking); 8.4-geitenhouderij feitelijk bepalen (gebiedsaanwijzing of niet).
- [ ] Recon H8 (body direct na H7-body-einde ~regel 9400; citaten programmatisch verifiëren), shard + ledger + manifestentry + gate-parametrize `+"landbouw"`.
- [ ] Gate groen; commit `feat(poc): landbouw-recon — evidence-shard H8 met cite-or-abstain-dekking`.

### Task 3: landbouw-zones

**Files:** Modify `poc/data/sources.json`, `poc/run.py::ZONE_SOURCES`; Test `poc/tests/test_landbouw_zones.py` (spiegel landschap-zones: begrensde parse, match-verankering, cache-twins).
- [ ] Selectie `agrarisch|landbouw|glastuinbouw|bodembewerking` (case-insensitive) over `agrest-namen.json`; live paged counts + union/extents per zone; registry-entries volgens agrest-OV-patroon (rol per letterlijke regelformulering); fetch+cache-twins (`git add -f`); gaps expliciet (geen surrogaat).
- [ ] Test groen; commit `feat(poc): landbouw-zones — registry, cache-twins en ZONE_SOURCES-aliases`.

### Task 4: landbouw formalisering + run

**Files:** Modify `poc/pipeline/agents.py` (LB-enrichment + TEMPLATE_SPECS), `poc/run.py::TRACKS`; Create `poc/use-cases/landbouw.json` (AoI letterlijk wind-AoI, `agricultural_expansion`, ambitions `["agriculture"]`, UUID), run-map; Test `poc/tests/test_landbouw_run.py` (spiegel verharde run-tests).
- [ ] TRACKS-entry (eigen report_title, `DT-landbouw-utrecht-poc1`, `ldttoolbox:poc:landbouw:`, headline_note feitelijke regels+artikelen, limitations-lambda).
- [ ] Run verdict `pass`; commit `feat(poc): landbouw-track live — templates, TRACKS, use-case, canonieke pass-run`.

### Task 5: wonen-recon

**Files:** Create `poc/corpus/evidence-wonen.json`, `poc/corpus/normcards-rejected-wonen.json`; Modify manifest + gate-parametrize.
**Interfaces:** ids `WN-01…`, objectType `housing_development`, chapters `["9"]`; H9 = 41 artikelen (9.1–9.37 + 9.14a/9.16a/9.48a; 9.38–9.47 bestaan niet). Kernregel 9.3 verstedelijkingsverbod Landelijk gebied (exclusion-kandidaat op bestaande laag); wonen-instructieregels 9.6–9.16 (o.a. 9.8 recreatiewoning, 9.10 kernrandzone, 9.15 uitbreiding woningbouw); werken 9.17–9.21 en recreatie 9.22–9.23: zone-gebonden instructieregels — beslis per regel in-objectType of abstain-met-heroverwegingsnotitie (werken/recreatie kunnen eigen fase-4-tracks worden); stiltegebied 9.24–9.37 deels al wind-track (hergebruik-afweging, geen dubbelformalisering van dezelfde regel-semantiek binnen dit objecttype zonder eigen citaat).
- [ ] Recon H9 (body na H8; 41/41 dekking), shard + ledger + manifestentry + gate-parametrize `+"wonen"`.
- [ ] Gate groen; commit `feat(poc): wonen-recon — evidence-shard H9 met cite-or-abstain-dekking`.

### Task 6: wonen-zones

**Files:** Modify `poc/data/sources.json`, `poc/run.py::ZONE_SOURCES`; Test `poc/tests/test_wonen_zones.py`.
- [ ] Hergebruik `agrest-ov-landelijk-gebied` (9.3) en evt. stiltegebied-aliases bijzelfde service+laag; nieuwe entries feitelijk uit treffers (kandidaten: Stedelijk gebied, Kernrandzone, Gebied recreatiewoning, Gebied uitbreiding woningbouw onder voorwaarden mogelijk, Gebiedstransformatie of herstructurering, Recreatiezone, Gebied bovenlokaal dagrecreatieterrein, Reductielocaties, Kantoor op knooppunt ×2, Gebied detailhandel buiten bestaand winkelgebied, Gebied uitbreiding bedrijventerrein onder voorwaarden mogelijk); live probes; gaps expliciet.
- [ ] Test groen; commit `feat(poc): wonen-zones — registry, cache-twins en ZONE_SOURCES-aliases`.

### Task 7: wonen formalisering + run

**Files:** Modify `poc/pipeline/agents.py` (WN-templates), `poc/run.py::TRACKS`; Create `poc/use-cases/wonen.json` (AoI letterlijk wind-AoI, `housing_development`, ambitions `["housing"]`, UUID), run-map; Test `poc/tests/test_wonen_run.py`.
- [ ] TRACKS-entry (eigen report_title, `DT-wonen-utrecht-poc1`, `ldttoolbox:poc:wonen:`).
- [ ] Run verdict `pass`; commit `feat(poc): wonen-track live — templates, TRACKS, use-case, canonieke pass-run`.

### Task 8: afsluiting

- [ ] Volledige regressie poc (+nldt); docs: README-trackregels + architectuurdoc (header "negen tracks", recordtelling feitelijk, §2-tabel + twee rijen, §4-rijen 8j/8k, §7 ×9); commit `docs(poc): fase 3 verordening-uitbreiding — landbouw+wonen geactualiseerd`.
- [ ] SDD-ledger bijwerken; eindreview + fixwave + merge volgens het fase-1/2-recept (reviewer-subagent; else controller-inline precedent; her-review na fixwave; merge --no-ff; ledger archiveren; worktree+branch opruimen).
