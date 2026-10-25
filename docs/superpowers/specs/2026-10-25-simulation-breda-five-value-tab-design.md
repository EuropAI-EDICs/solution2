# Ontwerp — Breda vijf-waardenscan in `simulation/simulation.html`

| | |
|---|---|
| **Datum** | 25 oktober 2026 |
| **Status** | goedgekeurd in brainstorm (§1–§3); klaar voor implementatieplan |
| **Scope** | Nieuwe tab 4 in `simulation/` (build + template + verify); offline embed van canonieke PoC-4-run |
| **Niet in scope** | Live `poc-breda/run.py` in de browser; volledige `report.html` (~4 MB); derde Laya-dataset; what-if / `breda_scenario`; MCP/`ask_scan` runtime |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Plaats | **A** — nieuwe tab 4 «Breda · vijf-waarden» (niet in Laya-switcher) |
| Chat | **A** — precomputed golden Q&A (~8–12), offline |
| Unlock | **A** — na korte PoC-4-timeline in tab 4 |
| Bouwwijze | **1** — native embed via `build_simulation.py` + `template.html` |

Laya-**karakteristieken** die we spiegelen: offline DATA-embed, unlock-na-run, chat met confidence/match-gate, probe-chips, geen live model. Breda blijft een **value-scan**-contract, geen System-1 heads.

## Context

- PoC-4: `poc-breda/` — 56 CBS-buurten × vijf congreswaarden (*AI in the City 2026*).
- Canonieke artefacten o.a. `value-scan.json`, `geo-buurten.wgs84.geojson`, `validation.json`, `run_summary.json`.
- `simulation/simulation.html` heeft nu PoC-1, PoC-2, Laya tab 3; Breda ontbreekt (bestaande demos zitten in `nldt/simulation/breda-*.html`).

## Architectuur

```text
poc-breda/runs/<canonical>-breda-scan/
  value-scan.json · geo-buurten · validation · run_summary
  (+ gecureerde golden Q&A bronnen)
        │
        ▼
simulation/build_simulation.py  →  build_breda()
        │  simplify geo · compact scan · embed qa[]
        ▼
DATA.poc4  ──►  template.html tab 4  ──►  simulation.html
                 timeline → unlock → chat
```

Pin de canonieke run-id expliciet in `build_simulation.py` (zoals `POC1_TRACKS` / `POC2_RUN`). Voorkeur: vastgelegde run die in PoC-4-docs/nLDT als referentie geldt; bij twijfel de nieuwste complete run met `value-scan.json` + geo + validation (bijv. `20260913T192628Z-breda-scan`), gedocumenteerd in de builder-constante.

---

## §1 — Tab-UX + data-payload

### Tab 4 «Breda · vijf-waarden»

- Layout analoog aan PoC-1: stagepane (kaart + waardenpanelen) + telemetry (timeline, bronnen, chat).
- Waarden-switcher: `democratisch | ruimtelijk | economisch | sociaal` → choropleth op buurtvlakken.
- **Autonoom**: geen choropleth; toon soevereiniteitsmanifest + bronlijst (`values.autonomous` / `sources`).
- Hover/klik buurt → scores (0–100) + `missing` (cite-or-abstain op indicatorniveau).
- Chat onderaan: locked tot timeline klaar; daarna golden Q&A.

### DATA-payload (`DATA.poc4`)

| Veld | Inhoud |
|---|---|
| `runId`, `summary` | uit `run_summary.json` |
| `scan` / `values` / `sources` | samenvatting uit `value-scan.json` |
| `buurten[]` | 56 × code, naam, scores (4), missing, basis meta (inwoners, wijk) |
| `rollup` | top/bottom per waarde |
| `geo` | display-gesimplificeerde polygonen per `buurtcode` (TOL-patroon als PoC-1) |
| `validation` | compacte level/check-status voor timeline-chips |
| `qa[]` | ~8–12 golden {question, answer, buurtnaam?, waarde?, mode?, probe?} |
| `nn` (optioneel) | lichte vocab/idf voor match — of substring/exact eerst |

Geen live fetch; geen in-browser port van `breda.qa`; geen volledige Leaflet-`report.html`.

---

## §2 — Timeline + unlock

Replay van artefacten (geen live execution):

| Stap | Label | UI |
|---|---|---|
| 0 | intake | AOI Breda + 56 buurten |
| 1 | fetch | bronchips (CBS PDOK, data.breda.nl, geo.breda.nl) |
| 2 | indicators | 4 ruimtelijke waarden + autonome-manifest teller |
| 3 | validate | checks uit `validation.json` |
| 4 | report | choropleth aan (default ruimtelijk) + rollup |
| 5 | unlock | `bredaUnlocked = true` + welkomstchat |

- Unlock is **lokaal** aan tab 4 (onafhankelijk van `layaOn.utrecht` / `eindhoven`).
- Deep-link: `?tab=4`; optioneel `?waarde=spatial|democratic|economic|social|autonomous`.

---

## §3 — Chat-contract

- Offline `qa[]`; match via genormaliseerde exact/substring of lichte NN over golden questions (Laya-probes-patroon).
- Onder drempel → abstain: geen grounded antwoord in de scan; verwijs naar herformuleren of probe-chip (System-2 = echte `ask_scan` buiten deze pagina).
- Na unlock: welkomstbericht + 4–6 probe-chips.
- Build-gate: elke golden row met `buurtnaam`/`buurtcode` moet bestaan in de ingebedde scan.

---

## Acceptatie

1. `python3 simulation/build_simulation.py` schrijft tab-4-DATA zonder netwerk.
2. `node simulation/verify_static.mjs` dekt tab 4: timeline tot unlock + ≥1 chat-probe.
3. Choropleth wisselt per waarde; autonomous toont manifest i.p.v. kleuren.
4. Chat locked vóór stap 5; daarna golden antwoord of abstain.
5. Pagina blijft single-file / `file://`-bruikbaar.

## Open (implementatieplan)

- Exacte canonieke run-id vastpinnen + sha/size-notitie in builder.
- Keuze Leaflet (CDN verboden voor file://) vs SVG/path-choropleth zoals PoC-1 map — **voorkeur: bestaande map-stack van simulation (geen CDN)**.
- Of golden Q&A als apart JSON onder `simulation/breda_qa.json` of gegenereerd uit run-`qa/`.
