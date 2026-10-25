# Ontwerp — NormCards & Norm Formalizer herijken op RegelRecht (NDD v0.8.11)

| | |
|---|---|
| **Datum** | 25 oktober 2026 |
| **Status** | goedgekeurd in brainstorm (§1–§4); klaar voor implementatieplan |
| **Scope** | `poc/schemas` + corpus/templates/Formalizer, `zone_projector`, deep-agents roles/tools, `nldt/simulation/regelrecht` (schema-pin, full_export, demo), docs-links |
| **Upstream** | [NederlandseDigitaleDienst/regelrecht](https://github.com/NederlandseDigitaleDienst/regelrecht) (`schema/latest` → **v0.8.11**; `MinBZK/regelrecht` redirect) |
| **Bronnen** | [POC_REGELRECHT_INTEGRATION.md](../../POC_REGELRECHT_INTEGRATION.md) · [2026-10-14-regelrecht-full-instrument-export-design.md](2026-10-14-regelrecht-full-instrument-export-design.md) · lokale pin `nldt/simulation/regelrecht/schema/` |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Doel | **A** — schemas & Formalizer dichter bij RegelRecht; zone-engine via booleaanse externe inputs |
| Migratie | **3** — dual-write: beide vormen in FormalRule-artefact |
| Source of truth | **A** — RegelRecht-`execution` is SoT; `zoneSelector`/`conditions`/… worden afgeleid |
| Breedte | **4** — Utrecht-PoC (13 tracks) + deep-agents + full_export/demo |
| NormCard | **C** — bijna 1:1 RegelRecht-artikelfragment (`number`/`text`/`url` + PoC-provenance) |
| Architectuur | **1** — in-place herijken; RR-operatie-enums vastpinnen uit v0.8.11 (geen live `latest` in runtime) |
| Sync | Canonieke org **NDD**; pin **v0.8.11** + sha256; sync-script + drift-gate |

Buiten scope: upstream PR naar NDD-corpus; live Rust-engine in de PoC-pipeline; forceren van poc-nspd schema-breuk buiten dual-write; Breda/Rijnland.

## Context

PoC-NormCards/FormalRules zijn zone-georiënteerd (`zoneSelector`, `conditions`, status formalized/ambiguous/rejected). RegelRecht modelleert artikelen met optioneel `machine_readable.execution` (`parameters`/`input`/`output`/`actions`). De full_export mapte FormalRule → MR; die richting keert om: Formalizer author’t `execution`, export leest die rechtstreeks.

Upstream is verhuisd van MinBZK naar NDD; schema is doorgegroeid van de vastgepinde **v0.7.1** naar **v0.8.11**. Herijken omvat inhoudelijke contracten én sync met die repo.

## Architectuur

```text
NDD regelrecht schema/v0.8.11
        │ sync_regelrecht_schema.py (pin + sha256)
        ▼
┌───────────────────────┐
│  gepinde schema.json  │  nldt/simulation/regelrecht/schema/
└───────────┬───────────┘
            │ enums/defs voor execution-subset
            ▼
NormCard (RR-artikelvorm + PoC-velden)
        │
        ▼
┌─────────────────────┐
│  NormFormalizer     │  templates: execution + zoneBinding
│  (poc + deep-agents)│  status formalized|ambiguous|rejected
└─────────┬───────────┘
          │ FormalRule met execution (SoT)
          ▼
┌─────────────────────┐
│  zone_projector     │  → zoneSelector / conditions / zoneSemantics / ruleType
└─────────┬───────────┘
          │ dual-write artefact
          ├──────────────────────────────┐
          ▼                              ▼
   zone-engine / viewer          full_export → articles[].machine_readable
   (bestaande zone-velden)       + demo (v0.8.11 validatie)
```

## §1 — Sync + schemas/contracts

### Sync-contract

- Canonieke bron: `https://github.com/NederlandseDigitaleDienst/regelrecht`, pad `schema/v0.8.11/schema.json` (niet `schema/latest` in runtime).
- Lokaal artefact: `nldt/simulation/regelrecht/schema/regelrecht-v0.8.11.schema.json` + README (bron-URL, pin-datum, sha256).
- Script `sync_regelrecht_schema.py`: download → byte-compare → update pin en `$schema`-URL’s in exports/examples; test/CI faalt bij sha-drift t.o.v. vastgelegde pin.
- Actieve docs/links: MinBZK → NDD. v0.7.1 blijft alleen historisch tot migratie compleet is.

### NormCard (≈ RR-artikel)

Verplicht RR-kern:

- `number` (artikelnummer zoals in de wet)
- `text` (verbatim; markdown/quote)
- `url` (artikel- of instrument-URI)

PoC-velden blijven: `id` (`NC-*`), `legalForce`, `theme`, `appliesTo`, `verified`, provenance (`extractedBy`/`extractedAt`; optioneel `evidenceId`, `instrument`, CVDR als annotatie). `cvdr_id` bestaat niet in v0.8.x — niet als RR-kernveld eisen.

`machine_readable` hoort niet op de NormCard; executie leeft op de FormalRule.

### FormalRule (dual-write)

- Bij `status=formalized`: verplicht `execution` als subset van RR `machineReadableSection.execution` (`produces`, `parameters`, `input`, `output`, `actions`), operaties/enums uit de gepinde v0.8.11-definitions.
- `zoneSelector` + `conditions` (+ afgeleide `zoneSemantics`/`ruleType` waar van toepassing) blijven in het JSON-artefact als **projectie**; niet handmatig authoren.
- Equivalentie-gate: `zone_projector(execution, zoneBinding) ≡` opgeslagen zone-velden (canon-JSON).
- Ambiguous/rejected: geen uitvoerbare `execution` (of weggelaten) + verplichte `reason`; in instrument-YAML text-only artikel.

## §2 — Formalizer + projector

Templates en Formalizer schrijven alleen `execution` (+ status/metadata) en optioneel **`zoneBinding`** (PoC-extensie, niet in upstream-YAML): koppelt booleaanse `execution.input`-namen aan `zoneIds`, `geometrySource`, optioneel `gioJoinId` / buffer.

Projector-regels (vast):

1. RR-vergelijkingen → `conditions[]`.
2. Geo-`input` + binding → `zoneSelector`; polariteit via conventie/template (`in_` / `buiten_`) of expliciete tag → inclusion/exclusion.
3. Geen giswerk: ontbrekende binding waar geo vereist is, of onbekende operatie → hard fail of `ambiguous`, nooit raden.

Migratie: per Utrecht-track templates herschrijven naar `execution`; regeneratie schrijft dual-write formalrules + herbouwde normcards. Golden: art. 5.3 (FR-W-03) gedrag stabiel t.o.v. huidige voorbeeld-YAML na schema-URL-bump naar v0.8.11.

LLM-formalizer (deep-agents) mag alleen `execution` + `zoneBinding` voorstellen; projector vult zone; submit weigert zonder projectie-pass.

## §3 — Export, demo, deep-agents

**full_export:** omgekeerde FormalRule→MR-mapper verdwijnt als SoT-pad. Bij formalized: `articles[].machine_readable` = `endpoint`/`competent_authority` (template/metadata) + `execution`. Instrument-YAML `$schema` → NDD v0.8.11; Utrecht herbouwen; Eindhoven blijft zolang templates `execution` leveren.

**regelrecht-demo:** golden art. 5.3 / 10.2 her-valideren tegen v0.8.11; UI/docs “v0.7.1” → “v0.8.11”; MinBZK-links → NDD.

**deep-agents:** `prompts/roles/normspecialist.md` + `formalizer.md` op RR-artikelvorm / execution+zoneBinding; `tools/norms.py` + `formalize.py` op nieuwe schemas; harnessregister-sha’s bijwerken waar prompts actief gepind zijn.

## §4 — Tests, fouten, acceptatie

Gates:

1. NormCard/FormalRule tegen herijkte PoC-schemas.
2. Formalized: `execution` valide als RR-execution-subset tegen pin v0.8.11.
3. Dual-write equivalentie (projector ≡ opgeslagen zone-velden).
4. Geëxporteerde instrument-YAML tegen `regelrecht-v0.8.11.schema.json`.
5. Schema-sync sha256 ≡ NDD `schema/v0.8.11` (lokale `--allow-drift` alleen expliciet).

Suites: projector-unit (5.3 + missing binding / unknown op); corpus regeneratie 13 tracks + bestaande contract/replay-tests; `nldt.tests.test_simulation_regelrecht*`; deep-agents offline validate/submit + register-conformance.

Acceptatie:

- Golden art. 5.3: zelfde machine_readable-gedrag; schema-URL/versie gebumpt.
- Canonieke wind-run zone-algebra binnen bestaande V3-tolerantie.
- Geen MinBZK-URLs in actieve paden (docs, `$schema`, README-pin).

Foutgedrag: harde fail bij schema/projectie/sync-gate; geen stille fallback naar de oude FormalRule→MR-mapper na cutover.

## Niet-doelen (herhaling)

- Geen corpus-PR naar NDD in deze iteratie.
- Geen verplichte Rust-engine in de PoC-run (Python reference + zone-engine blijven).
- poc-nspd niet forceren buiten wat dual-write al dekt.

## Volgende stap

Implementatieplan via writing-plans skill → `docs/superpowers/plans/2026-10-25-normcard-formalizer-regelrecht.md`.
