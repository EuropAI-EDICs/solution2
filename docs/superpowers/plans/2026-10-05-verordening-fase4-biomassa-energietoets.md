# Verordening-regeluitbreiding fase 4 (biomassa + energietoets) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track `biomassa` (H5.6/5.7, objectType `biomass_installation`) afronden — de uitgestelde H5-rest uit het ontwerp — plus track `energietoets` (H5.10/5.11 als conditionele markers; 5.8/5.9 procedureel onthouden) zodat het instrument thuis-dekking heeft op álle H5-artikelen zonder een verzonnen netmodel.

**Architecture:** Zelfde vierstappenpatroon als fase 1–3 (recon-shard+leger → zones registry+cache+aliases → templates+TRACKS+use-case+canonieke pass-run → docs). Bindende spiegels: `poc/corpus/evidence-{landbouw,wonen}.json`, `poc/tests/test_{landbouw,wonen}_{zones,run}.py`, `poc/run.py::TRACKS/ZONE_SOURCES`, `poc/pipeline/agents.py::TEMPLATE_SPECS/EVIDENCE_ENRICHMENT`, design [`docs/superpowers/specs/2026-10-04-verordening-regeluitbreiding-design.md`](../specs/2026-10-04-verordening-regeluitbreiding-design.md) §Dekkingsstaat H5.

**Tech Stack:** stdlib + jsonschema via `nldt/.venv`; snapshot `docs/research/sources/cvdr704250-tekst-extract.txt` als SoT; `poc/data/agrest-namen.json` (122 namen) — biomassa-zones letterlijk aanwezig (`Gebied energie uit biomassa landelijk gebied`, `Gebied energie uit biomassa stedelijk gebied`); energietoets heeft **geen** GIO → markers/onthoudingen, geen surrogaat. EnergyCast/grid-capaciteit blijft een **seam** (SOLUTIONS_ARCHITECTURE §4 B congestion / MULTI_AGENT_PLAN EnergyCast), niet een fake engine in deze fase.

## Global Constraints

- Cite-or-abstain: elke `quote_nl` letterlijk (whitespace-genormaliseerd) in de snapshot-BODY (niet TOC); elk H5-artikel in wind/zon-shards **óf** biomassa/energietoets-shard **óf** ledger met reden (geen dubbele formalisering van 5.3–5.5).
- Bestaande tracks/runs byte-identiek; gedeelde pipeline-modulen onaangeroerd; suites groen.
- Gitignored `poc/data/*`: nieuwe registry-entries + cache-twins met `git add -f`; worktree `verordening-fase4` / `ldttoolbox-vf4` (venv-symlink, poc/data kopiëren, SDD-ledger).
- Enums: `biomass_installation` + ambitions `"energy"` bestaan al; theme-pattern heeft `energy:` — geen enum-taak nodig tenzij tests dat eisen.
- Dedup: Landelijk/Stedelijk-gebied-GIO's hergebruiken alléén bijzelfde service+laag (wonen-precedent); biomassa-specifieke GIO's krijgen eigen registry-rollen.
- Energietoets (5.11): "wordt rekening gehouden met de aansluitbaarheid" + inventariserend overleg → **conditional marker** (of abstain met EnergyCast-heroverweging), nooit spatial exclusion zonder netdata.

---

### Task 1: Worktree + SDD-ledger + H5-eigenaarschapskaart

**Files:** Create `.superpowers/sdd/verordening-fase4/progress.md`; Modify (alleen ledger-notities) — geen productiecode.
- [ ] Worktree/branch `verordening-fase4` volgens fase-3-recept.
- [ ] Tabel in progress.md: per artikel 5.1–5.11 → thuis (`wind`/`zon`/`biomassa`/`energietoets`/context) met bewijs uit bestaande shards.
- [ ] Commit `docs(plans): fase 4 verordening — biomassa + energietoets (H5-rest)`.

### Task 2: biomassa-recon

**Files:** Create `poc/corpus/evidence-biomassa.json`, `poc/corpus/normcards-rejected-biomassa.json`; Modify `poc/corpus/track-manifest.json` + gate-parametrize.
**Interfaces:** ids `BM-01…`, objectType `biomass_installation`, chapters `["5"]` met formalizableArticles feitelijk `["5.6","5.7"]` (+ eventueel 5.2 als context-citaat, niet dubbel-formaliseren); 5.1/5.3–5.5 blijven wind/zon; 5.8–5.11 naar energietoets-ledger of gedeeld H5-rest-ledger.
- [ ] Recon body-citaten 5.6/5.7 (programmatisch containment); shard + ledger + manifestentry `biomassa` + gate `+"biomassa"`.
- [ ] Gate groen; commit `feat(poc): biomassa-recon — evidence-shard H5.6/5.7 met cite-or-abstain-dekking`.

### Task 3: biomassa-zones

**Files:** Modify `poc/data/sources.json`, `poc/run.py::ZONE_SOURCES`; Test `poc/tests/test_biomassa_zones.py` (spiegel wonen/landbouw: begrensde `_alias_source_ids`).
- [ ] Selectie letterlijk op biomassa-namen in `agrest-namen.json`; live paged counts + extents; registry + cache-twins (`git add -f`); aliases bijv. `gebied_energie_biomassa_landelijk`, `gebied_energie_biomassa_stedelijk`.
- [ ] Test groen; commit `feat(poc): biomassa-zones — registry, cache-twins en ZONE_SOURCES-aliases`.

### Task 4: biomassa formalisering + run

**Files:** Modify `poc/pipeline/agents.py` (BM-enrichment + TEMPLATE_SPECS), `poc/run.py::TRACKS`; Create `poc/use-cases/biomassa.json` (AoI = wind-AoI, `biomass_installation`, ambitions `["energy"]`, UUID), canonieke run-map; Test `poc/tests/test_biomassa_run.py`.
- [ ] TRACKS-entry (`DT-biomassa-utrecht-poc1`, `ldttoolbox:poc:biomassa:`, headline_note feitelijk).
- [ ] Run verdict `pass`; commit `feat(poc): biomassa-track live — templates, TRACKS, use-case, canonieke pass-run`.

### Task 5: energietoets-recon

**Files:** Create `poc/corpus/evidence-energietoets.json`, `poc/corpus/normcards-rejected-energietoets.json`; Modify manifest + gate.
**Interfaces:** ids `ET-01…`, objectType kies **`energy_storage`** (bestaande enum; vraagt naar netbelasting bij nieuwe energie-functies) **óf** documenteer een bewuste keuze voor hergebruik `housing_development` als toetscontext — default in dit plan: **`energy_storage`** + ambitions `["energy"]`; chapters `["5"]`; formalizableArticles waarschijnlijk leeg of alleen conditionele 5.10/5.11-markers; 5.8/5.9 vergunningsketen → ledger.
- [ ] Recon 5.8–5.11 (body na Afdeling 5.3); ledger met EnergyCast/grid-heroverwegingsnotitie op 5.11 lid 2.
- [ ] Gate groen; commit `feat(poc): energietoets-recon — H5.8–5.11 cite-or-abstain + EnergyCast-seamnotitie`.

### Task 6: energietoets formalisering + run (marker-only)

**Files:** Modify `agents.py` + `TRACKS`; Create `poc/use-cases/energietoets.json`; Test `poc/tests/test_energietoets_run.py`.
- [ ] Geen nieuwe spatial zones (geen GIO) — final zone = AOI of inclusion-composition alleen als letterlijke tekst dat dwingt; 5.11 als conditional marker (mobiliteit-precedent).
- [ ] Run verdict `pass`; commit `feat(poc): energietoets-track live — conditionele markers, geen netmodel-surrogaat`.

### Task 7: afsluiting

- [x] Regressie poc (+nldt); docs: README-trackregels + `docs/SOLUTIONS_ARCHITECTURE.md` (tien/elf tracks feitelijk; §2-tabel; §4-rijen biomassa + energietoets; B congestion = seam blijft Open tot EnergyCast-MCP); optioneel UCS-process ids in `build_fixtures.py` recept-omschrijving.
- [x] Commit `docs(poc): fase 4 verordening-uitbreiding — biomassa + energietoets geactualiseerd`.
- [ ] Eindreview + fixwave + merge `--no-ff`; ledger archiveren; worktree opruimen.

## Out of scope (expliciet)

- Live netbeheerder-API / EnergyCast MCP-server-implementatie (aparte fase; hier alleen ledger-seam + architectuurverwijzing).
- Herformaliseren van wind/zon (5.3–5.5) of crosstrack-overlays over alle nieuwe tracks (optioneel tranche B).
