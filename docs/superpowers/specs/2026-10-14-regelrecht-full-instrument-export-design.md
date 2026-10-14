# Ontwerp — Volledige RegelRecht-export Omgevingsverordening Utrecht & Omgevingsplan Eindhoven

| | |
|---|---|
| **Datum** | 14 oktober 2026 |
| **Status** | goedgekeurd in brainstorm (§1–§3); klaar voor implementatieplan |
| **Scope** | `nldt/simulation/regelrecht/full_export/`, uitbreiding `regelrecht-demo.html`, artefacten onder `full_export/out/` |
| **Bronnen** | [POC_REGELRECHT_INTEGRATION.md](../../POC_REGELRECHT_INTEGRATION.md) · [2026-09-29-simulation-regelrecht-design.md](2026-09-29-simulation-regelrecht-design.md) · vastgepinde CVDR-HTML · PoC-corpora (`poc/`, `poc-bp2op/`) |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Scope artikelen | **B** — volledige instrument-export uit lokale CVDR/DSO-HTML (niet alleen geoogste NormCards) |
| Formalisering | **2** — actieve FormalizerPass per artikel (deterministische templates + onthouding) |
| Deliverable | **C** — architectuur + werkende exporter + demo-uitbreiding |
| Architectuur | **1** — instrument-first: één YAML per instrument-versie |

Buiten scope: live DSO Omgevingsdocumenten API (401 zonder key); LLM-formalizer; upstream PR naar MinBZK/regelrecht-corpus (wel voorbereidende YAML-vorm); Breda/Rijnland.

## Context

De bestaande RegelRecht-demo dekt één Utrecht-artikel (5.3) en één Eindhoven-paar (22.1 / 10.2). De PoC's hebben al veel meer geoogst (~84 NormCards over 13 Utrecht-tracks; Eindhoven 311 bron- + 762 doelregels), en lokaal liggen volledige HTML-dumps:

- Utrecht: `docs/research/sources/cvdr704250-omgevingsverordening-geldend-2025-10-13.html` (CVDR704250)
- Eindhoven: `poc-bp2op/corpus/eindhoven/omgevingsplan-eindhoven-cvdr696400-geldend-2026-06-29.html` (CVDR696400)

Doel: die instrumenten als RegelRecht v0.7.1-YAML exporteren, elk artikel actief formaliseren waar templates dat toelaten, en de demo laten browsen over het hele instrument met coverage en live executie waar `machine_readable` bestaat.

## Architectuur

```text
CVDR-HTML (vastgepind)
  Utrecht:  docs/research/sources/cvdr704250-….html
  Eindhoven: poc-bp2op/corpus/eindhoven/omgevingsplan-….html
        │
        ▼
┌───────────────────┐
│  ArticleSplitter  │  HTML → articles[{number, text, url, containers}]
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     PoC-artefacten (alleen-lezen)
│  EvidenceAligner  │◄──── NormCards / FormalRules / bron·doel·omzet
│                   │      match op artikelnummer + verbatim overlap
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  FormalizerPass   │  hit FormalRule/template → machine_readable
│                   │  open norm / geen template → text-only + abstention
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  RegelRechtWriter │  1 YAML/instrument (v0.7.1) + formalization-report.json
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  DemoBuilder      │  instrument-browser, coverage, live engine indien MR
└───────────────────┘
```

### Contractregels

1. Eén YAML per instrument-versie (RegelRecht-padconventie); niet één bestand per artikel.
2. `machine_readable` alleen bij geslaagde formalisering; anders weglaten (“carried as text only”).
3. Geo/zone blijft externe booleaanse `input` zonder `source.regulation` — dezelfde naad als art. 5.3.
4. Eindhoven: bron- en doelartikelen in hetzelfde plan-YAML; conversierelaties in het formalization-report (niet in BWBR-only `references`).
5. Critic V2 (verbatim grounding) + schema v0.7.1 zijn hard gates; `humanOnTheButtons` blijft `v4_pending`.
6. Geen netwerk in de default-build; bronnen zijn de vastgepinde HTML-bestanden.

## FormalizerPass

Elk splitter-artikel krijgt precies één status:

| Status | Wanneer | In YAML |
|---|---|---|
| `formalized` | Bestaande FormalRule `status=formalized` óf template-hit met deterministische predicates | `machine_readable` aanwezig |
| `ambiguous` | FormalRule/template: open norm of procedureel | geen `machine_readable`; regel in abstention-ledger |
| `rejected` | Geen uitvoerbare claim (scope / toelichting / visie) | tekst-only |
| `unmatched` | Artikel in HTML zonder NormCard; kale FormalizerPass → template of `ambiguous` | zoals boven |

### Mapping FormalRule → RegelRecht `execution`

| PoC | RegelRecht |
|---|---|
| `conditions[].operator` `<=` / `==` / `>=` / `!=` | `LESS_THAN_OR_EQUAL` / `EQUALS` / `GREATER_THAN_OR_EQUAL` / `NOT_EQUALS` |
| meerdere conditions | `AND` over die operaties |
| `zoneSelector` | booleaanse `input` `in_<zoneId>`, source buiten regulation |
| `zoneSemantics: inclusion` + conditions | output = AND(zone-input, conditions) |
| `zoneSemantics: exclusion` | AND met zone-input `EQUALS false` (of equivalent `NOT`) |
| procedural / open norm | geen actions → abstention |
| Eindhoven bron↔doel equivalentie | twee MR-blokken + gedeelde demoCases; link in report |

### Hard rules

1. Geen LLM in de default-pass — alleen deterministische templates (lijn `norm-formalizer#deterministic-templates-v1`).
2. Cite-or-abstain: zonder template → `ambiguous`, nooit predicates verzinnen.
3. EvidenceAligner-hit (bestaande FormalRule) wint van kale template-match op hetzelfde artikel.
4. Pass schrijft `formalization-report.json`: tellingen + per-artikel `{number, status, reason, normCardId?, formalRuleId?}` — diffbaar en golden-testbaar.

## Bestanden en I/O

Nieuwe module: `nldt/simulation/regelrecht/full_export/`

| Pad | Rol |
|---|---|
| `split_cvdr_html.py` | ArticleSplitter |
| `align_evidence.py` | EvidenceAligner |
| `formalize_to_rr.py` | FormalizerPass + mapping |
| `write_instrument_yaml.py` | YAML-writer + schema-validatie v0.7.1 |
| `build_full_demo.py` | demo + coverage + golden subset |
| `build_all.py` | orkestratie CLI (`--stamp`) |
| `out/utrecht-cvdr704250.yaml` | volledige verordening |
| `out/eindhoven-cvdr696400.yaml` | volledig omgevingsplan |
| `out/*-formalization-report.json` | status per artikel |
| `out/*-articles.json` | splitter-artefact (QA) |

Bestaande voorbeelden onder `docs/examples/regelrecht/` blijven **smoke-fixtures** (art. 5.3 / 22.1+10.2). De full-export-YAML's zijn de canonieke corpusvorm.

**Build-commando:**

```bash
nldt/.venv/bin/python -m nldt.simulation.regelrecht.full_export.build_all --stamp <ISO-timestamp>
```

Idempotent met dezelfde `--stamp`; HTML-bron-sha256 in het report.

Eindhoven hergebruikt waar mogelijk `poc-bp2op/pipeline/parsers.parse_doelregeling` (en bronextractie uit dezelfde HTML) als splitter-basis, zodat artikelgrenzen niet opnieuw worden uitgevonden. Utrecht: nieuwe splitter op de CVDR704250-HTML, met regressie tegen bekende NormCard-artikelnummers.

## Demo

Uitbreiding van `regelrecht-demo.html` (gegenereerd vanuit template):

1. PoC-keuze + **artikelkiezer** (zoek/filter; coverage-chips: formalized / ambiguous / text-only / rejected).
2. Ketenbalk per artikel: citaat → YAML-fragment → schema → engine/trace **of** “text-only” + abstention-reason.
3. Interactielab alleen als `machine_readable` bestaat; anders lab uitgeschakeld met uitleg.
4. Selftest: bestaande **16** golden cases blijven verplicht. Aanvullend: deterministische subset van formalized artikelen (cap **20 per PoC**), gegenereerd uit het report — badge toont `16 + K` geslaagd.
5. Hub-links in `poc-utrecht.html` / `poc-eindhoven.html` / `index.html` wijzen naar de uitgebreide demo; teasertekst noemt coverage i.p.v. enkel art. 5.3 / 10.2.

## Foutafhandeling

| Fase | Conditie | Gedrag |
|---|---|---|
| Split | HTML ontbreekt of 0 artikelen | exit ≠ 0 |
| Align | FormalRule zonder matching artikelnummer | warning in report; rule niet silently dropped — `orphanedFormalRules[]` |
| Formalize | template zonder required fields | behandel als `ambiguous` |
| Write | YAML faalt schema v0.7.1 | exit ≠ 0, geen demo-write |
| Demo | selftest < 16 basiscases | rode banner, controls uit (bestaand gedrag) |

## Tests

Uitbreiding van `nldt/tests/test_simulation_regelrecht.py` (of sibling `test_simulation_regelrecht_full.py`):

1. Beide instrument-YAML's schema-valide tegen vastgepind `regelrecht-v0.7.1.schema.json`.
2. Elk artikel met status `formalized` in het report heeft `machine_readable` in de YAML; `ambiguous`/`rejected` niet.
3. Coverage-totalen in report = aantal splitter-artikelen.
4. Verbatim: voor formalized artikelen met NormCard-quote is de genormaliseerde quote ⊆ artikeltekst.
5. Idempotente rebuild met dezelfde `--stamp` (byte-identiek YAML + report, modulo afgesproken stamp-veld).
6. Smoke: art. 5.3 (Utrecht) en art. 10.2 (Eindhoven) blijven formalized en engine-compatibel met de bestaande 16 golden cases.
7. Mini-engine evalueert alle gegenereerde demoCases in de cap-subset zonder divergentie t.o.v. Python-referentie.

## Bouwvolgorde (voor het implementatieplan)

1. ArticleSplitter Utrecht + Eindhoven + `*-articles.json` fixtures/tests.
2. EvidenceAligner + orphan-rapportage.
3. FormalizerPass + mapping + report-schema.
4. RegelRechtWriter + schema-gate.
5. DemoBuilder + template/UI (kiezer, coverage, lab-gate).
6. `build_all` orkestratie + testsuite + README-update in `nldt/simulation/README.md`.
7. Korte architectuurparagraaf in `docs/POC_REGELRECHT_INTEGRATION.md` die naar deze spec wijst.

## Niet doen

- Geen live DSO-fetch in CI/demo.
- Geen LLM-voorstellen in de default-pass.
- Geen opsplitsing in per-artikel YAML-bestanden.
- Geen wijziging van het RegelRecht-schema zelf (upstream-issues blijven in POC_REGELRECHT_INTEGRATION).
