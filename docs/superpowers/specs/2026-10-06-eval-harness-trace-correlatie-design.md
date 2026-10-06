# Ontwerp — Eval-harness en trace-correlatie: GS-1/GS-3-regressie in CI + run-id over journal, prov en spans

| | |
|---|---|
| **Datum** | 6 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | pytest-marker-harness met golden-regressie over de 13 canonieke Utrecht-runs (cache-only her-uitvoering, diff tegen gecommitte goldens), seam-comparators als lokaal-only tests, run/job-id-correlatie over journal + prov + spans met JSONL-spanexporter. Afdwinging lokaal via markers; CI bewust gedescoped |
| **Buiten scope** | GS-2 (BNK-cases — het operationele vlak, agents #9–12, is niet gebouwd), Langfuse/Jaeger-server (OTLP-exporter wél env-gated voorbereid), expert-zones als aparte GS-1-dataset (de gecommitte canonieke runs zijn de frozen goldens), **GitHub Actions-workflow** — bewust gedescoped; later toevoegbaar als één YAML die dezelfde pytest-aanroep herhaalt |
| **Bronnen** | [`MULTI_AGENT_PLAN.md`](../../../MULTI_AGENT_PLAN.md) §4 (evaluation plan: golden sets GS-1..3, metrics, "eval-harness runs GS-1..3 in CI on every prompt/model/graph change; traces diffed") · [`docs/GENAI_SEAMS.md`](../../GENAI_SEAMS.md) (S1/S2/S7-comparator-invarianten) · [`nldt/08-roadmap.md`](../../../nldt/08-roadmap.md) ("OTLP exporter (Langfuse/Jaeger) instead of console-only spans") · [`nldt/services/common/telemetry.py`](../../../nldt/services/common/telemetry.py) (bestaande `span()` + console-exporter) · [harness-unificatie-spec](2026-10-06-utrecht-harness-unificatie-design.md) (M3: gedeeld journal-format) |
| **Keuzes uit de sessie** | prioriteit: **beide minimaal** (eval-regressie + trace-correlatie, geen observability-server) · afdwingingslaag: **lokaal via markers, CI gedescoped** — de harness is machine-onafhankelijk en CI is alleen afdwinging; her-openen door later één workflow-YAML toe te voegen · architectuur: **pytest-marker-harness** (aanpak 1) boven een standalone eval-runner of alles-in-standaardsuites |

## Context en doel

`MULTI_AGENT_PLAN.md` §4 schrijft een evaluatieplan voor: golden sets die per DSR-iteratie groeien, met de invariante dat de eval-harness "GS-1..3 in CI on every prompt/model/graph change" draait en traces diffed. Wat er vandaag is:

- **Goldens bestaan de facto**: alle 15 canonieke run-directories (incl. 2 oudere wind-varianten) zijn gecommit met volledige artefactsets (`run_summary.json`, `validation/*`, `zones.json`, `layers.json`, `decision-table.json`, `zones.gml`, `prov.json`). Er is alleen geen geautomatiseerde vergelijking tegen die goldens.
- **Comparators bestaan ad hoc**: `poc/llm/compare_norm_llm.py` (S1/S2: nul-drift op citaties/rechtskracht/geo-bindingen) en `poc/scenarios/compare_authors.py` (S7: `floorIntact`) schrijven `comparison.json`, maar zijn losse scripts zonder CI-koppeling of pytest-integratie.
- **Observability is halverwege**: `nldt/services/common/telemetry.py` heeft een OpenTelemetry TracerProvider met console-only exporter en een `span()`-contextmanager (gebruikt in de process-adapter); de roadmap noemt de OTLP-exporter als open punt. Sinds de harness-unificatie (M3) landen process-executies in het gedeelde journal — maar journal, prov en spans zijn niet op één run-id gecorreleerd.
- **Er is geen CI**: geen `.github/workflows/`, dus geen automatische regie-guard bij model-, prompt- of pipeline-wijzigingen.

Dit ontwerp levert de minimale, self-contained versie van het plan-artikel: **een golden-regressie die bij elke push de 13 canonieke Utrecht-tracks op cache her-uitvoert en diff't tegen de goldens**, plus **run-id-correlatie over journal, prov en spans** met een bestandsbased spanexporter. Geen server, geen GS-2.

## 1. Golden-regressie (GS-1 + GS-3)

### Normalisatie en diff — `poc/pipeline/golden.py` (nieuw, puur)

Per track: vergelijk een verse cache-only run tegen de canonieke golden.

- **Exact gelijk** (na normalisatie): `verdict`; de zes `verdicts`-verdicts op artefactniveau (`opportunity-map-request`, `norm-card-set`, `formal-rule-set`, `zone-result-set`, `decision-table`, `pipeline-run`); `perRule` als lijst `(ruleId, verdict)`.
- **IoU-check**: zone-geometrie niet byte-gewijs maar via IoU(new, golden) ≥ 0,9999 per track én gelijk feature-aantal — robuust tegen floating-point drift, gevoelig genoeg voor inhoudelijke drift.
- **GML-structuurcheck** (GS-3-kern): `zones.gml` geparseerd als XML; vergelijkt feature-aantal, de verzameling `gml:id`s en de property-sets per feature — niet de byte-volgorde.
- **Gestripte velden** (mogen verschillen): `runId`, `requestId`, `generatedAt`, `durationS`, `startedAtTime`/`endedAtTime`, en overige tijdstempels.
- **Uitvoer**: `golden-diff.json` (per track: track, golden-id, exact-match booleans, IoU, gml-samenvatting, lijst afwijkingen) — console-samenvatting bij pytest-falen, artefact in CI.

Canonieke mapping (13 tracks): wind → `20260830T113234Z-wind`, zon → `20260830T142439Z-zon`, bos → `20260830T142446Z-bos`, water → `20261004T185116Z-water`, bodem → `20261004T185509Z-bodem`, mobiliteit → `20261005T072839Z-mobiliteit`, landschap → `20261005T070621Z-landschap`, landbouw → `20261005T094244Z-landbouw`, wonen → `20261005T100258Z-wonen`, werken → `20261006T121921Z-werken`, recreatie → `20261006T114934Z-recreatie`, biomassa → `20261006T120133Z-biomassa`, energietoets → `20261006T171730Z-energietoets`. De mapping staat als dict in `golden.py`; de twee oudere wind-runs zijn bewust geen goldens.

### Regressiesuite — `poc/tests/test_golden_regression.py` (nieuw)

`@pytest.mark.golden`, geparametriseerd over de 13 tracks. Elke case: roep de bestaande pipeline aan via het use-case-pad dat `run.py` ook gebruikt (cache-first, geen live-fetch), normaliseer, diff tegen golden, assert. Lokaal dagelijks werken blijft snel met `pytest -m "not golden"`; `pytest -m golden` draait de regressie expliciet. De suite genereert géén nieuwe goldens — bij een intentionele wijziging commit de ontwikkelaar een verse canonieke run (bestaand repo-patroon) en verschuift eventueel de mapping.

### Seam-comparators als tests — `poc/tests/test_seam_comparators.py` (nieuw)

`@pytest.mark.llm`, skipped wanneer de betreffende endpoint-env ontbreekt (`LDT_NORM_LLM_ENDPOINT` / `LDT_SCENARIO_LLM_ENDPOINT`): roept de bestaande comparator-modules aan (deterministische leg offline, LLM-leg alleen met endpoint) en assert op de bestaande invariants (`nul drift op citaties/rechtskracht/geo-bindingen`, `floorIntact`). Deze marker draait bewust **niet** in GitHub Actions (geen Ollama in hosted runners); de CI-taak voor deze tests bestaat niet, de tests documenteren het lokale gebruik.

## 2. Trace-correlatie (run-id over journal, prov, spans)

- **Journal**: `execute_local(process_id, inputs, job_id=None)` — de router roept de wrapper aan mét `job_id` (die bestaat daar al vóór de call, `new_job_id()`); `journal_process_event` neemt `jobId` op in de entry. Bestaande journal-tests blijven groen; één nieuwe assert op `jobId`.
- **Spans**: `route_execute` zet een run/job-context (contextvar) die `span()`-attributen verrijkt met `job.id`; nieuwe **JSONL-spanexporter** in `telemetry.py` schrijft gesloten spans weg naar `nldt/data/traces/<datum>-spans.jsonl` (map overridable via `NLDT_TRACES_DIR`, analoog aan `NLDT_JOURNAL_PATH`; `nldt/data/` is al gitignored) (één JSON-object per regel: name, timestamps, attributes incl. job-id) naast de bestaande console-exporter; `NLDT_OTLP_ENDPOINT` geefd een OTLP-exporter (BatchSpanProcessor) als er wél een collector draait — zonder env geen netwerk.
- **prov.json** bevat per proces al `startedAtTime`/`endedAtTime` + job-id in de job-store; correlatie = zelfde `jobId` in journal-entry, span-attributen en job-record. Geen nieuw formaat, alleen het id doorgesleep.

## 3. CI — `.github/workflows/ci.yml` (nieuw)

- **Trigger**: push en PR op `main`.
- **Marker-registratie**: nieuw `poc/pytest.ini` registreert de markers `golden` en `llm` en stelt `addopts = -m "not golden and not llm"` — de standaard `pytest`-run (lokaal én in CI) blijft daarmee de snelle suite, en een expliciete `-m golden` op de CLI overschrijft de default (addopts gaat vóór de CLI-args).
- **Job `golden`** (`needs: tests`): `pytest poc/tests -m golden -q`; cache-first runs zijn licht (elke track enkele seconden; de geo-caches liggen in git). Bij falen wordt `golden-diff.json` als workflow-artifact geüpload. Geen secrets, geen matrix; één ubuntu-runner.
- **Eerste run**: de workflow is pas na push waarneembaar; de implementatie verifieert lokaal dat beide jobs-commando's exact dezelfde pytest-aanroepen zijn, en controleert de eerste GitHub-run in de afronding.

## 4. Foutgedrag en testing

- Diff-falen is nooit silent: pytest-toelichting toont per track de afwijkingen (welke velden, IoU-waarde, gml-omvang) en CI uploadt het diff-rapport.
- `golden.py` is puur en gedekt door unit-tests op mini-fixture-artefacten (normalisatie stript de juiste velden; IoU-tolerantie werkt op kleine geometrieën; gml-samenvatting telt features/ids/properties).
- Exporter-test met tmp-path (spans landen als JSONL, attributen bevatten job-id); journal-`jobId`-test; de rest van de suites blijft ongemoeid (nldt 362, poc 295+1).

## Risico's

- **Caches in git**: de her-uitvoering vertrouwt op gecommitte geo-caches; als een track bij uitvoering toch live-fetch triggert, faalt de test zichtbaar (geen stille netwerkafhankelijkheid) — de implementatie verifieert per track een volledig offline her-uitvoering.
- **Breekbare normalisatie**: te streng = vals alarm bij elke run, te los = blind; daarom verdicts/perRule exact, geometrie IoU-gelimiteerd, gml structureel — en de normalisatie zelf goed unit-gedekt.
- **Omgevingsverschillen** (OS/PROJ-versies tussen machines kunnen projecties micro-latijn): IoU-tolerantie vangt dat op; bij blijkbare omgevingsdrift is de tolerantie één regel aanpassen.
