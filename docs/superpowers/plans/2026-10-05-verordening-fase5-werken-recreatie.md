# Verordening-regeluitbreiding fase 5 (werken + recreatie) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tracks `werken` (H9-afdelingen 9.1.1/9.1.2/9.2, objectType `business_development`) en `recreatie` (H9-afdeling 9.3, objectType `recreation_development`) volgens het bewezen fase-1/2/3-patroon; eindstand elf tracks. Dit zijn de H9-heroverwegingskandidaten AWN-04/07 uit fase 3.

**Architecture:** Vast vierstappenpatroon (recon-shard+leger → zones registry+cache+aliases → templates+TRACKS+use-case+canonieke pass-run → docs). Beide tracks delen hoofdstuk 9 met wonen (gate-eis: 40/40-dekking per track). Bindende spiegels: `poc/corpus/evidence-{landbouw,wonen}.json`, `poc/tests/test_{landbouw,wonen}_{zones,run}.py`, SDD-ledger `.superpowers/sdd/verordening-fase3/progress.md`.

**Tech Stack:** stdlib + jsonschema via `nldt/.venv`; snapshot `docs/research/sources/cvdr704250-tekst-extract.txt` als SoT; `poc/data/agrest-namen.json` als zoneselectie-bewijs.

## Global Constraints

- Cite-or-abstain: elke `quote_nl` letterlijk (whitespace-genormaliseerd) in de snapshot-BODY; elk H9-artikel per track in shard ∨ `ledger.articlesConsidered`; geen verzonnen zones/getallen.
- Bestaande tracks/runs byte-identiek; engine/critic/explainer frozen (geen nieuwe hardening verwacht); suites groen (poc 274+1skip, nldt 337); `set -o pipefail` in commit-chains; expliciete `git add`-lijsten; run.py-samenvoegingen met volledige nieuwline-correcte anchors (fase-3-seams-les).
- Dedup-regel: `landelijk_gebied` (9.9/9.11) en `stedelijk_gebied` (9.18) hergebruikt bijzelfde service+laag; acht nieuwe entries (6 werken + 2 recreatie), 104→112.
- Adjudicatiekader (fase-2/3-consolidatie): exclusie alléén als de geweigerde activiteitsklasse binnen het objecttype valt én de zone niet het eigen ontwikkelingskader van het objecttype is; object-gescoped/systematisch-gekwalificeerde verboden → marker; verordeningeigen uitzonderingen op art. 9.3 → inclusion (W-05/WN-idioom).

---

### Task 1: Enums + theme-pattern
- [ ] objectType-enum +`business_development`,`recreation_development`; ambitions +`economic_vitality`,`recreation`; theme-pattern +`werken|recreatie`; positieve enum-tests.
- [ ] Suite groen; commit `feat(poc): enums +business_development/recreation_development; ambitions +economic_vitality/recreation; theme +werken|recreatie`.

### Task 2: werken-recon
- [ ] Shard 6 records WE-01..06 (9.9, 9.11, 9.16, 9.18, 9.19, 9.20; citaten programmatisch verifiëren); leger 34 considered + abstenties (wonen-/stilte-artikelen buiten objecttype, 9.16a beoordelingsregel, 9.21 [Gereserveerd], 9.22/9.23 → recreatie-track); manifest + gate-parametrize `+"werken"`.
- [ ] Commit `feat(poc): werken-recon — evidence-shard H9 met cite-or-abstain-dekking`.

### Task 3: werken-zones
- [ ] Live probes 6 nieuwe zones (Gebied uitbreiding bedrijventerrein onder voorwaarden mogelijk, Kantoor op knooppunt Utrecht Centraal, Kantoor op knooppunt Leidsche Rijn Centrum, Reductielocaties, Gebiedstransformatie of herstructurering, Gebied detailhandel buiten bestaand winkelgebied); registry + fetch + aliases; test `test_werken_zones.py` (begrensde parse, hergebruik-verankering landelijk_gebied/stedelijk_gebied); gaps expliciet.
- [ ] Commit `feat(poc): werken-zones — registry, cache-twins en ZONE_SOURCES-aliases`.

### Task 4: werken formalisering + run
- [ ] Templates WE-01..06 (WE-03/WE-04 inclusions, WE-06 exclusion met tenzij a-g in tags, WE-01/02/05 markers), TRACKS, `use-cases/werken.json` (business_development, economic_vitality, wind-AoI), canonieke run + `test_werken_run.py`.
- [ ] Run pass; commit `feat(poc): werken-track live — templates, TRACKS, use-case, canonieke pass-run`.

### Task 5: recreatie-recon
- [ ] Shard 2 records RC-01/02 (9.22, 9.23; beide expliciete "In afwijking van Artikel 9.3"-openingen); leger 38 considered; manifest + gate `+"recreatie"`.
- [ ] Commit `feat(poc): recreatie-recon — evidence-shard H9 met cite-or-abstain-dekking`.

### Task 6: recreatie-zones
- [ ] Probes + registry (Gebied bovenlokaal dagrecreatieterrein, Recreatiezone) + aliases + `test_recreatie_zones.py`.
- [ ] Commit `feat(poc): recreatie-zones — registry, cache-twins en ZONE_SOURCES-aliases`.

### Task 7: recreatie formalisering + run
- [ ] Templates RC-01/02 (beide inclusions — verordeningeigen uitzonderingen op art. 9.3), TRACKS, `use-cases/recreatie.json` (recreation_development, recreation), run + `test_recreatie_run.py`.
- [ ] Run pass; commit `feat(poc): recreatie-track live — templates, TRACKS, use-case, canonieke pass-run`.

### Task 8: afsluiting
- [ ] Regressie poc+nldt; docs (header "elf tracks", 79 records, 112 entries, §2-tabel + twee rijen, §8l/8m, §7 ×11); SDD-ledger.
- [ ] Commit `docs(poc): fase 4 verordening-uitbreiding — werken+recreatie geactualiseerd`; eindreview + fixwave + her-review + merge volgens het fase-1/2/3-recept.
