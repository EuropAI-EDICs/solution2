# Ontwerp — Decision-trail memory: de semantic memory-laag (leerstaat B10, automatische observaties)

| | |
|---|---|
| **Datum** | 7 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | deterministische consolidatie-laag die automatische observaties uit bestaande artefacten (journal-errors, HITL-verdicts, rejection ledgers, golden-drift) omzet in durabele, schema-gedwongen decision-trail-records met de drie leerniveaus uit het AGENTIC_STATE_PLAN, plus idempotente CLI (consolidate/handle/promote) en een leerrapport |
| **Buiten scope** | menselijke observatie-invoer (override, klacht, correctieverzoek — fase-D-materiaal), MCP read-tool `list_decision_trails` (volgende stap), automatische promotie tussen leerniveaus, lake-publicatie, LLM-reflectie in de consolidatie |
| **Bronnen** | het harness-artikel (Tkachuk, okt 2026 — component 3: memory-architectuur; doctrine "consolidation async, outside the hot path", "vector similarity alone is not a memory architecture") · [`AGENTIC_STATE_PLAN.md`](../../AGENTIC_STATE_PLAN.md) B10 (leerstaat: decision trail per materieel signaal, vijf velden, drie leerniveaus) en fase E · ecosystem-taxonomie agent memory (LangMem/Zep/mem0/MemGPT: episodic/procedural/semantic) · bestaan: `deep-agents/journal.py` + jobId-correlatie (harness-unificatie M3), `nldt/data/traces/` (eval-harness), rejection ledgers, golden-regressie |
| **Keuzes uit de sessie** | eerste gebruik: **leerstaat/decision-trail** (niet taakpatronen of gebruikerscontinuïteit) · alleen **automatische observaties** · architectuur: **gescheiden consolidator + store + rapport** (aanpak A) · terminologie: **observation** i.p.v. het planwoord "signaal", record blijft **decision trail** |

## Context en doel

De agent-memory-taxonomie die de ecosystem-frameworks (LangMem, Zep, mem0, MemGPT) delen kent drie lagen. Twee van de drie bestaat in dit repo al:

| Laag | Betekenis | Status in dit repo |
|---|---|---|
| **Episodic memory** | specifieke gebeurtenissen/trajecten | ✅ `poc/runs/` + `prov.json`, `deep-agents/runs/live/steps.jsonl` (journal), `nldt/data/runs/` (job-records), `nldt/data/traces/` (spans sinds de eval-harness) |
| **Procedural memory** | vaardigheden: hoe taken worden gedaan | ✅ `nldt/skills/poc/` (`skill://`-resources, SEP-2640) |
| **Semantic memory** | gegeneraliseerde lessen die over episodes heen blijven | ❌ ontbreekt — dit ontwerp |

Het AGENTIC_STATE_PLAN (B10, leerstaat) beschrijft precies deze laag in governance-vorm: per materieel signaal — in dit ontwerp **observation** geheten — een decision-trail-record met vijf velden (wat gebeurde, waarom, wat moet veranderen, wie beslist, hielp het) en drie leerniveaus (operationeel → organisatie → institutioneel). Dat stond gepland in fase E (maand 10–18); dit mijlpaal trekt het vooruit als eerste memory-bouwsteen. De doctrine uit het harness-artikel wordt gevolgd: consolidatie is **async en buiten het hot path** (writers veranderen niet), selectie is **deterministisch, niet gegenereerd** (geen LLM in de kring), en het geheugen is **scoped met provenance** (elke trail draagt jobId/runId — de correlatie uit de harness-unificatie).

## 1. Componenten — `nldt/services/memory/` (nieuw pakket)

| Onderdeel | Verantwoordelijkheid |
|---|---|
| `observations.py` | pure extractors; elk retourneert een lijst observation-dicts met `type`, `source`, `provenance` (jobId/runId waar beschikbaar) en observatie-specifieke payload. Lenient: afwezige bronnen leveren een lege lijst, nooit een fout |
| `store.py` | durabele trail-store: append-only JSONL onder `${NLDT_MEMORY_DIR:-nldt/data/memory/trails}/YYYYMMDD-trails.jsonl` (`nldt/data/` is gitignored); elke regel één record, gevalideerd tegen het schema bij schrijven; lezen = alle regels over alle bestanden, gesorteerd op trailId/tijdstempel |
| `consolidate.py` | CLI: `python -m services.memory.consolidate` — draait alle extractors, dedupliceert op trailId, schrijft nieuwe records; idempotent (tweede run → nul nieuwe records). Tevens de afhandel-acties: `--handle <trailId> --note "…"` (status → `handled`, `didItHelp` → note-waarde) en `--promote <trailId> --level organisatie|institutioneel` |
| `report.py` | leerrapport (retrieval, v1): aggregatie per `learningLevel`/observationType/`status`; open items bovenaan; promotie-kandidaten gemarkeerd (observatietype ≥ 3 keer open op operationeel niveau) |
| schema | `nldt/schemas/decision-trail.schema.json`, geladen en gevalideerd via de bestaande `services.common.schema.load_schema`/`validate_instance`-functies |

## 2. Observatiebronnen (v1, alle automatisch)

| ObservationType | Bron | Extractie |
|---|---|---|
| `journal_error` | journal (`NLDT_JOURNAL_PATH`, default `deep-agents/runs/live/steps.jsonl`) | regels met `kind=process_result` en `status=error`; provenance = `jobId`/`agent` uit de regel |
| `hitl_needs_human` | orchestrator run-records onder `nldt/data/runs/*/` | lenient scan van JSON-bestanden op validation-verdict `needs_human`; provenance = runId uit de mapnaam. Exacte persistentievorm wordt in het implementatieplan met een verificatie-stap gepind; de extractor is tolerant op dict-vormen |
| `ledger_reject` | `poc/scenario-runs/*/proposals-rejected.json` + `norm-llm-ledger.json` waar aanwezig (glob) | lenient dict- én lijstvorm; elke afgewezen proposal is één observation met bestandspad als source |
| `golden_drift` | `poc/eval/golden-diff.json` (bestaat pas als de rapport-runner is gedraaid) | tracks met `pass=false`; nieuw rapport-bestand `poc/eval/golden-diff.json` wordt door een kleine runner geschreven die `pytest -m golden` uitvoert en per-track resultaten vastlegt — **op verzoek, nooit onderdeel van de standaard consolidatie** |

Geen van de vier bronnen is een nieuwe schrijver in het hot path; de journal, run-records en ledgers zijn er al (episodic layer), de consolidator leest ze alleen.

## 3. Trail-record (B10-vijfstappen + memory-doctrine)

```jsonc
{
  "trailId": "dt-<hash8 van observation-type + source + identificatie>",   // dedup-sleutel
  "observation": {
    "type": "journal_error | hitl_needs_human | ledger_reject | golden_drift",
    "source": "steps.jsonl | nldt/data/runs/<id> | poc/scenario-runs/<id>/proposals-rejected.json | poc/eval/golden-diff.json",
    "provenance": { "jobId": "…", "runId": "…" },       // correlatie harness-unificatie
    "detail": "…"                                        // observatie-specifiek (bv. proces-id, fout, track)
  },
  "what": "…",                     // automatisch uit de observation volgens type-regel
  "why": "…",                      // vooringevuld volgens type-regel (bv. golden_drift → 'pipeline- of modelwijziging drifte de golden-output'), overschrijfbaar via --handle
  "whatShouldChange": "…",         // vooringevuld volgens type-regel
  "whoDecides": "operator",        // default operationeel; promotie is expliciet
  "didItHelp": null,               // leeg tot afhandeling; --handle vult
  "learningLevel": "operationeel | organisatie | institutioneel",   // scope; default operationeel
  "status": "open | handled",
  "createdAt": "<ISO-UTC>"
}
```

De standaardwaarden van `what`/`why`/`whatShouldChange` per observationType zijn een vaste tabel in `observations.py` (deterministisch, citeerbaar) — geen LLM-tekstgeneratie.

## 4. Data flow

1. Bestaand: journal/run-records/ledgers vullen zich tijdens runs (episodic layer — onveranderd).
2. Periodiek of voor beslispunten: operator draait `python -m services.memory.consolidate` → nieuwe observaties worden trail-records met `status: open`; bestaande trailIds worden overgeslagen.
3. Operator leest het leerrapport (`python -m services.memory.report`), handelt open items af (`consolidate --handle <trailId> --note "…"` — vult `didItHelp`), promoveert terugkerende lessen (`consolidate --promote … --level organisatie`).
4. Promotie is nooit automatisch; het rapport markeert kandidaten (zelfde observationType ≥ 3× open op operationeel).

## 5. Testing

- `observations.py`: unit-tests op mini-fixture-bestanden per type — inclusief de afwezigheidscase (bron ontbreekt → lege lijst) en dict- én lijstvormen voor ledgers; golden-drift alleen met aanwezig diff-bestand.
- `store.py`: append-idempotentie (tweede consolidate → zelfde aantal), schema-validatie van elk geschreven record, NLDT_MEMORY_DIR-override, lezen over meerdere dagbestanden.
- `consolidate.py`/`report.py`: CLI-tests op tmp-path — dedup, `--handle` (status + didItHelp), `--promote` (level), rapport-sorteervolgorde en promotie-kandidaat-markering.
- Golden-diff-runner: aparte test dat het JSON-formaat klopt (geen volledige golden-run in de suite — die is al gedekt door de `golden`-marker).
- Bestaande suites ongewijzigd groen (poc 302/1, nldt 365).

## 6. Koppelingen

- **AGENTIC_STATE_PLAN**: de fase-E-deliverable "decision trail bovenop journal + PROV" trekt met dit ontwerp vooruit. Landingsplaats wijkt bewust af van de daar genoemde "uitbreiding `deep-agents/journal.py`" — de journal blijft episodic writer, de semantic laag leest er van. Bij dezelfde commit krijgt dat plan een kleine fase-E-notitie (decision trail vervroegd, landingsplaats `nldt/services/memory/`).
- **Harness-artikel**: dit is component 3 in minimale vorm — durabele, scoped, provenance-gedragen memory met async consolidatie buiten het hot path en deterministische selectie. Retrieval v1 = het leerrapport; `list_decision_trails` als read-only MCP-tool is de volgende stap (dan krijgt ook het planningvlak `search_memory`-achtige toegang).
