# Verordening-regeluitbreiding fase 2 (mobiliteit + landschap) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tracks `mobiliteit` (H4, objectType `roadside_development`) en `landschap` (H7, `landscape_intervention`) volgens het bewezen fase-1-patroon, met de gate-uitbreiding voor multi-hoofdstuktracks als verplichte eerste taak.

**Architecture:** Elke track doorloopt het vastgelegde vierstappenpatroon (recon-shard+leger → zones registry+cache+aliases → templates+TRACKS+use-case+canonieke pass-run → docs). De canonieke voorbeelden zijn gecommit en dienen als bindende spiegel: `poc/corpus/evidence-{water,bodem}.json`, `poc/corpus/normcards-rejected-{water,bodem}.json`, `poc/corpus/track-manifest.json`, `poc/tests/test_track_conformance.py`, `poc/tests/test_{water,bodem}_{zones,run}.py`, `poc/run.py::TRACKS/ZONE_SOURCES`, `poc/pipeline/agents.py::TEMPLATE_SPECS/EVIDENCE_ENRICHMENT`, SDD-ledger `.superpowers/sdd/verordening-fase1/progress.md` (lessen per taak).

**Tech Stack:** stdlib + jsonschema via `nldt/.venv`; snapshot `docs/research/sources/cvdr704250-tekst-extract.txt` als SoT; `poc/data/agrest-namen.json` (122 namen) als zoneselectie-bewijs.

## Global Constraints

- Cite-or-abstain: elke `quote_nl` letterlijk (whitespace-genormaliseerd) in de snapshot-BODY (titel-grep + `tail`-instantie — het `^Artikel X `-idiom pakt de TOC!); elk artikel van het hoofdstuk in shard ∨ `ledger.articlesConsidered`; geen verzonnen zones/join-ids/getallen.
- Bestaande tracks/runs byte-identiek; gedeelde pipeline-modulen (engine, critic, explainer) onaangeroerd; suites groen (`cd poc && ../nldt/.venv/bin/python -m pytest tests -q`, na fase 1: 244 passed + 1 skip).
- Gitignored `poc/data/*`: nieuwe registry-entries + cache-twins met `git add -f` + expliciete paden; worktree-patroon zoals fase 1 (branch `verordening-fase2`, venv-symlink, poc/data kopiëren uit hoofdwerkmap, SDD-ledger).
- Extractie-lessen (fase 1): UUID's i.p.v. UC-namen; `returnCountOnly` negeert `where` (tel via paging); umbrella-supersets geometrisch verifiëren; `provincial_gio_unverified` + eigen CAVEAT zonder gioJoinId; inclusieloze tracks = exclusie-gedreven (V3-seedbug is gefixed — exclusies werken).

---

### Task 1: Gate multi-hoofdstuk + ambitions-enum

**Files:** Modify `poc/tests/test_track_conformance.py` (dekkingslUS over alle `chapters`), `poc/schemas/opportunity-map-request.schema.json` (ambitions-enum + `mobility_safety`); Test: uitbreiding van de conformatietest zelf.
**Interfaces:** Produces: gate accepteert `chapters: ["…","…"]` (verplichte carry-forward uit fase-1-review); ambitions-enum `[…, "mobility_safety"]`.
- [ ] Falende test: voeg aan de module een test toe met een inline mini-manifestentry `chapters: ["2","3"]` die dekt over beide hoofdstuk-artikellijsten (gebruik bestaande water+bodem-bestanden als fixture via tijdelijke manifest-injectie met `monkeypatch` op `load_manifest`); huidige `entry["chapters"][0]`-code dekt alleen H2 → faalt op H3-artikelen.
- [ ] Fix: `expected = set().union(*(chapter_articles(c) for c in entry["chapters"]))`.
- [ ] Ambitions: voeg `"mobility_safety"` toe aan de enum (test: `poc/tests/test_objecttype_enum.py`-stijl assert dat een request met `ambitions: ["mobility_safety"]` valideert).
- [ ] Suite groen; commit `feat(poc): gate dekt alle hoofdstukken; ambitions-enum +mobility_safety`.

### Task 2: mobiliteit-recon

**Files:** Create `poc/corpus/evidence-mobiliteit.json`, `poc/corpus/normcards-rejected-mobiliteit.json`; Modify `poc/corpus/track-manifest.json`.
**Interfaces:** ids `MO-01…`, objectType `roadside_development`, chapters `["4"]`; spiegel recordvorm exact op `evidence-bodem.json`.
- [ ] Recon H4 (afdelingen: 4.1 Bereikbaarheid → beleidskader/abstain; **4.2 provinciale weg** en **4.7 geluid provinciale weg** → verwacht formaliseerbaar (instructieregels met gebiedsaanwijzing, bijv. geluidszones); 4.3 lokale spoorweg, 4.4 vaarweg → zonegebonden waar letterlijk; 4.5 luchthavens, 4.6 externe veiligheid basisnet → letterlijke tekst beslist; 4.8 ontgrondingen → procedureel/abstain). Verwachte shard ≥2 records; rest `articlesConsidered` + gemotiveerde abstenties.
- [ ] Manifestentry `"mobiliteit"` (useCase `use-cases/mobiliteit.json`, formalizableArticles = feitelijke lijst).
- [ ] Gate groen (`4 passed`-niveau: water/bodem/mobiliteit + sanity); commit `feat(poc): mobiliteit-recon — evidence-shard H4 met cite-or-abstain-dekking`.

### Task 3: mobiliteit-zones

**Files:** Modify `poc/data/sources.json`, `poc/run.py::ZONE_SOURCES`; Test `poc/tests/test_mobiliteit_zones.py` (spiegel `test_bodem_zones.py`: `_alias_source_ids`-helper, cache-eis op alias-bronnen).
- [ ] Selectie uit `agrest-namen.json` op `geluid|basisnet|provinciale weg|spoor|vaarweg|luchthaven|ontoereikend` (case-insensitive); registry volgens agrest-OV-patroon; rollen conform letterlijke regelsemantiek; fetch+cache-twins (`git add -f`); aliaskeys bijv. `geluidszone_provinciale_weg`, `basisnet_ev` — feitelijk bepaald door de treffers; gaps expliciet rapporteren (nooit surrogaat).
- [ ] Test groen; commit `feat(poc): mobiliteit-zones — registry, cache-twins en ZONE_SOURCES-aliases`.

### Task 4: mobiliteit formalisering + TRACKS + use-case + canonieke run

**Files:** Modify `poc/pipeline/agents.py` (MO-templates), `poc/run.py::TRACKS`; Create `poc/use-cases/mobiliteit.json` (AoI letterlijk wind-AoI, `roadside_development`, ambitions `["mobility_safety"]`, UUID), `poc/runs/<ts>-mobiliteit/`; Test `poc/tests/test_mobiliteit_run.py` (spiegel verharde `test_water_run.py`: verdict pass + IoU ≥ 0,999 + rel-delta ≤ 1e-3 + replay volledige-artefactvergelijking).
- [ ] TRACKS-entry: spiegel de vorm van `TRACKS["water"]` (eigen report_title `Where is roadside development bounded by mobility rules…`, `DT-mobiliteit-utrecht-poc1`, `ldttoolbox:poc:mobiliteit:`, headline_note met de FEITELijke uitgevoerde regels+artikelen, limitations-lambda cov-vorm, vermelding onthouden families).
- [ ] Run: verdict `pass` vereist; commit run-map + code + test: `feat(poc): mobiliteit-track live — templates, TRACKS, use-case, canonieke pass-run`.

### Task 5–7: landschap — identieke driestappen

Task 5 recon: `LS-01…`, objectType `landscape_intervention`, chapters `["7"]`; afdelingen 7.1 cultuurhistorie + 7.2 kwaliteit landschap; veel open normen verwacht (grote abstentie-aandelen zijn eerlijk — spiegel AWH-12-stijl heroverwegingsnotities). Task 6 zones: selectie op `waterlinie|landgoed|aardkundig|cultuurhistorie|archeolog|kasteel|havezate`; hergebruik bestaande registry-entries `Hollandse_Waterlinie*` en `ow_bwp_aardkundig` alléén bijzelfde service+laag (fase-1-dedup-regel), anders nieuwe agrest-entries. Task 7 run: ambitions `["landscape","heritage"]`. Commits gespiegeeld aan taken 2–4.

### Task 8: afsluiting

- [ ] Volledige regressie poc (+nldt in hoofdwerkmap); docs: README-trackregels + architectuurdoc (§2-tabel, §4 8h/8i, header "zeven tracks / 42+…records" — feitelijke aantallen); commit `docs(poc): fase 2 verordening-uitbreiding — mobiliteit+landschap geactualiseerd`.
- [ ] SDD-ledger bijwerken; eindreview + fixwave + finishing volgens het fase-1-recept.
