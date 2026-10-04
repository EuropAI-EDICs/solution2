# Plane D — Breda integrale gebiedsafweging (design)

**Vraag.** Wat gebeurt er met de vijf congreswaarden (democratisch, ruimtelijk,
economisch, sociaal, autonoom) als we in geselecteerde Breda-buurten een
**ruimtelijke claim** neerleggen — woningverdichting of dak-PV-maximalisatie —
en hoe maken we die trade-offs bestuurlijk vergelijkbaar zonder een
geautomatiseerde winnaar?

Dit is **Plane D** van de LDT-toolbox: compositie boven PoC-4
([`poc-breda/`](../../../poc-breda/)), geen nieuwe multi-objective optimizer.
Het beantwoordt de ZoN-behoefte aan *integrale gebiedsafweging* (meerjarenvisie
Zicht op Nederland) met één pilootstad.

| | |
|---|---|
| Status | Design 2026-10-04 · v1 scope locked |
| Related | [poc4-breda design](2026-09-13-poc4-breda-five-value-scan-design.md) · [nldt/11](../../../nldt/11-poc-patterns-scenarios-qa.md) · [nldt/24](../../../nldt/24-zichtopnl-alignment.md) |
| Non-goals v1 | Fysische effectmodellen; Utrecht-juridische sporen; cross-city optelbaarheid (ZN-2); LLM in de cijferlijn |

---

## Principes

1. **AI/LLM stelt voor, engines rekenen, mens beslist (V4).** Geen single
   winner-score als besluit.
2. **Claim = contract** (`spatial-claim.schema.json`), geen prompt.
3. **Control-first:** ongemuteerde herberekening van de baseline-scan moet
   scores bit-identiek reproduceren vóór claims worden geloofd (zelfde V3-idee
   als de what-if-naad).
4. **Cite-or-abstain:** elke Δ noemt regel-id + inputs; `hypothetical` eist
   rationale; geen stille imputatie.

---

## Architectuur

```text
value-scan (Plane A) ──► control recompute ──► SpatialClaimSpec[]
                                                    │
                                                    ▼
                                          deterministic claims.py
                                                    │
                                                    ▼
                                   gebiedsafweging-report + HTML
                                                    │
                                                    ▼
                                              V4 pending (human)
```

### Claim kinds (v1)

| kind | Economisch | Ruimtelijk | Sociaal | Democratisch | Autonoom |
|---|---|---|---|---|---|
| `dak_pv_maximalisatie` | ↑ (waarde van realiseren dakpotentieel) | ↓ licht bij hoge groendekking | — | — | ongewijzigd (manifest) |
| `woningverdichting` | ↑ licht (capaciteit) | ↓ (druk op groen) | ↑ (meer hitte-aandacht) | — | ongewijzigd |

`magnitude` ∈ {1…5} schaalt Δ’s lineair. Doelbuurten via `buurtcodes[]`
(CBS `BU…`).

### Capaciteitsdruk

`woningverdichting` voegt per geraakte buurt `capacityPressure`
(`magnitude × 10`) toe — herleidbaar, geen zesde waarde in de
congresindex.

---

## Artefacten

| Pad | Rol |
|---|---|
| `poc-breda/schemas/spatial-claim.schema.json` | Claim-contract |
| `poc-breda/schemas/gebiedsafweging-report.schema.json` | Rapport |
| `poc-breda/breda/claims.py` | Impactregels + runner |
| `poc-breda/afweging_run.py` | CLI |
| `poc-breda/claims/demo-breda.json` | 2 demo-claims |
| Recipe `breda-gebiedsafweging` | nLDT process facade |

---

## Done when (v1)

- Offline tests: control stabiel; schema’s groen; Δ’s voor beide kinds.
- HTML toont ≥1 buurt: baseline vs claim, Δ per waarde, regels + rationale.
- V4 = `pending`; geen geautomatiseerde “beste claim”.
