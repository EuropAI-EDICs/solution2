# Ontwerp — Breda Laya System-1 + System-2 handoff

| | |
|---|---|
| **Datum** | 25 oktober 2026 |
| **Status** | goedgekeurd in brainstorm; implementatie |
| **Scope** | `simulation/laya_breda/`, tab 4 S1 UI, deep-agents S2-handoff |
| **Niet in scope** | Browser-WebLLM; S2 die cijfers verzint; what-if; hertrain Utrecht/Eindhoven |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| System-1 | Nieuw Breda-Laya-model (spiegel Utrecht) |
| System-2 runtime | Hybrid: offline sim = S1 + handoff; deep-agents/Ollama = LLM; live lab `?s2=1` |
| Triggers | Onder confidence-gate **of** ungrounded chat |
| Aanpak | `simulation/laya_breda/` + deep-agents S2-contract |

## System-1

Canonieke run: `poc-breda/runs/20260913T192628Z-breda-scan`. Eén case per buurt.

**State:** buurtnaam, wijkcode, inwoners, scores (4), missing[].

**Heads (gold uit scan):**

| Head | Type | Gold |
|---|---|---|
| `primary_value` | choice | argmin van democratic/spatial/economic/social |
| `attention_band` | score | tertielen laag/midden/hoog op primary score |
| `needs_human` | noul | true bij missing≠∅ of bottom-5 op primary |
| `autonomous_ok` | choice | ok als alle manifest-criteria `met`, anders review |

Hold-out: hele wijken. Gate: 0.55.

## System-2 handoff

**Payload:** question, buurtcode/buurtnaam, primary_value, scores, missing, attention_band, needs_human, confidence, gate_reason, runId, sourceIds.

S2 narrateert op S1-hint + ask_scan/engine; badge `System-2 · op basis van Laya System-1 (Breda)`. Geen nieuwe cijfers.

Offline sim: handoff-UI. `?s2=1`: POST lokaal endpoint; bij falen offline-fallback.

## Relatie tot tab-4-spec

Addendum op `2026-10-25-simulation-breda-five-value-tab-design.md`: golden Q&A blijft; daarnaast embedded Breda-Laya S1 + S2-handoff.

## Data lake (medallion)

Gebruikte open data + afgeleide dataset worden vastgelegd via
`simulation/laya_breda/lake_publish.py` en `nldt/services/lake/sync.py`:

| Zone | Key-prefix | Inhoud |
|---|---|---|
| bronze | `bronze/breda/cbs-buurten-2024/{gemeente}/{retrievedAt}/` | CBS/PDOK GeoJSON + `source.meta.json` (Breda, Eindhoven, Tilburg) |
| bronze | `bronze/breda/open-data/{layer}/{retrievedAt}/` | Breda open-data lagen (wijkdeals, groen, bomen, …) + meta |
| silver | `silver/breda/geo/` | alle gebruikte geo-lagen (CBS + Breda open data, incl. proxy-gemeenten) |
| silver | `silver/breda/laya/system1/{datasetId}/` | `train/eval/meta.jsonl`, `manifest.json` |
| gold | `gold/breda/laya/system1/{datasetId}/` | `predictions.json`, `finetune-summary.json` |
| gold | `gold/breda/runs/{canonicalRunId}/` | canonieke `value-scan` run (`20260913T192628Z-breda-scan`) |

`datasetId` = `20261025-breda-laya-s1`.
