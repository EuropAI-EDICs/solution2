# Ontwerp — DSO-kennisgraaf als vijfde stap in Tab 7

| | |
|---|---|
| **Datum** | 2026-11-08 |
| **Status** | goedgekeurd ontwerp (gecombineerde graaf, in Tab 7) |
| **Scope** | een kennisgraaf-paneel als extra tijdlijnstap in de bestaande Tab 7 "DSO ↔ RegelRecht" van `simulation/simulation.html`, build-time gevoed uit de kennisbank-artefacten |
| **Aansluiting** | [Tab 7-spec](2026-11-08-dso-kb-simulatie-tab-design.md) · [DSO-KB MCP-spec](2026-11-07-dso-kb-mcp-design.md) · PoC-1-idioom `build_kg1` en PoC-2-idioom `build_kg` in `simulation/build_simulation.py` |
| **Doctrine** | bouwtijd-replay; deterministische layout in de build (geen physics); géén LLM, géén runtime-diensten |

---

## 1. Doel en niet-doelen

**Doel.** De officiële IMOW-annotatiestructuur als graaf zichtbaar maken — artikel → regeltekst (wId) → juridische regel → activiteit/locatie → GIO-bestand — met de RegelRecht-status als knoopkleur eroverheen, in het PoC-1-idioom (vaste kolommen, staged lighting, vooraf gerenderde tooltips).

**Niet-doelen.** Geen graaf-database of query-taal (geen RDF/SPARQL); geen live-bevraging; geen weergave van álle 811 Eindhovense artikelen tegelijk (selectie + subgraph); géén wijziging aan de vier bestaande stappen van Tab 7 behalve de stap-aantallen in verify.

## 2. Genomen besluiten

1. **Vijfde tijdlijnstap** `["kennisgraaf", "kg7.json"]` in `VSTAGES7`; `makeSim7` krijgt een S(4)-stap die de kolommen achtereenvolgens aanlicht (artikel → regelteksten → regels → activiteiten/locaties → GIO's). Verify schuift mee: 4 → **5 stappen**.
2. **Join via `identificatie`, niet via wId**: `regelteksten[].identificatie` ↔ `regels[].regeltekstRef` (IMOW-URI's); artikelnummer komt uit de wId (`__art_([\d.]+)`). *(Gemeten 08-11: de wId-join vindt nul koppelingen — de identificatie-join is de juiste.)*
3. **Selectie**: standaard **top-12 artikelen naar aantal juridische regels** (overzichtsgraaf), plus dropdowns: instrument (Eindhoven/Utrecht) en artikel (alle graadwaardige artikelen, cap 500 — Eindhoven 811 → de dropdown toont de top-500, het subgraph-menu bevat dezelfde cap). Artikelkeuze tekent het volledige subgraph van dat artikel.
4. **Begrenzing**: per artikel max **6 regelteksten en 12 regels** in de payload (overschot als getelde stippellijn-"…+N"-knoop); alléén artikelen met ≥1 regel (Eindhoven 811/811, Utrecht 107/107 — alle DSO-hit-artikelen blijken regels te hebben).
5. **Locatie-knopen** zijn alles wat in `locatieRefs` van regels voorkomt, verrijkt met noemer/type uit `locaties` ∪ `gebiedsaanwijzingen`; waar `pakket-index.json` een `gml`-bestand koppelt volgt een GIO-knoop (volgende kolom), anders een stippellijn-eindknoop "geen koppelbaar gml" (Utrecht-patroon).

## 3. Componenten

### 3.1 `simulation/build_simulation.py` — `build_kg7()`

Leest per instrument: `annotaties.json` (regelteksten wId+identificatie; regelsVoorIedereen/instructieregels met regeltekstRef + activiteitLocatieaanduidingen(activiteitRef, activiteitregelkwalificatie, locatieRefs); locaties; gebiedsaanwijzingen), `pakket-index.json` (gio: locatieIdentificatie → bestand) en `overlap.json` (rrStatus per artikelnummer).

Payload per instrument (compact, arrays):

```json
{"top": ["1.8","3.37","10.186","22.61","10.254"],
 "artikelen": {"1.8": {"status": "formalized", "nRegels": 12, "nRT": 12,
                        "rts": ["gm0772_…__art_1.8__para_1"],
                        "regels": [{"id": "nl.imow-gm0772.jr.…", "rt": 0,
                                    "act": "Bouwen", "kw": "vergunningplicht",
                                    "locs": [0, 1]}]},
               "…": {}},
 "locaties": [{"id": "nl.imow-gm0772.ambtsgebied.9999999999",
               "noemer": "Ambtsgebied", "type": "locatie", "gml": null}],
 "keuze": ["1.8","3.37", "…"]}
```

(`rts`/`regels` afgekapt per besluit 4; `keuze` = artikelnummers voor de dropdown, cap 500, gesorteerd op regels-aantal.) De **layout** (kolom-x, knoop-y, groepsbanden) berekent de build deterministisch — het template tekent alleen paden (PoC-1/PoC-2-idioom).

### 3.2 `simulation/template.html` — paneel + stap

- Nieuwe kaart in view7 onder de driftkaart: SVG-paneel (viewBox naar PoC-1-kg-formaat), **zes kolommen** met koppen `artikel · regeltekst · juridische regel · activiteit · locatie · GIO`, twee dropdowns (instrument, artikel; sweep6-select-patroon).
- **Knoopkleur**: artikel- en regeltekst-knopen groen bij `status=="formalized"`, amber bij onthouding (statusCounts-palet); activiteit-knoopkleur op kwalificatie (vergunningplicht amber, meldingplicht cyaan, anders geduid grijs); GIO-knoop groen bij koppelbaar gml.
- **Tooltips** vooraf gerenderd in de build (artikelnummer+titelindien aanwezig, wId, regel-identificatie-kort, activiteit+kwalificatie, locatie-noemer+gml-bestandsnaam-kort).
- **Staged lighting** in S(4): per kolom een `setTimeout`-golf; knopen dragen `st`-veld (5.x) zoals PoC-1.
- Herrenderen bij dropdown-wissel is puur lokaal (data zit al in `DATA.dsokb.kg`), geen rebuild.

### 3.3 `simulation/verify_static.mjs`

- Bestaand blok: `s7.steps.length !== 4` → `!== 5`.
- Nieuwe asserts: `ds.kg7Data()` bestaat voor beide instrumenten; Eindhoven `top[0] === "1.8"` en `artikelen["1.8"].nRegels === 12`; `status`-kleur aanwezig (groen voor 1.8 — formalized); na artikel-dropdown-wissel (`ds.kg7Kies("eindhoven","3.37")`) tekent het paneel subgraph-knopen (`kg7-n > 0`); GIO-knoop aanwezig voor Eindhoven locatie met gml.
- Slotlog: `sim7 5 stappen`.

### 3.4 `simulation/README.md`

Tab 7-paragraaf uitbreiden met de graaf-stap (kolommen, selectie, begrenzingen, waar het gml-bestand vandaan komt).

## 4. Foutafhandeling en begrenzing

- Ontbrekend artefact → build stopt hard (bestaand gedrag van `build_dso_kb` geldt ook voor de graaf-lezingen).
- `--gent-only`: heel het graaf-paneel hangt onder de bestaande `if(DKB)`-guard en in het gent-only bestand verborgen (tab7 is al verborgen); geen nieuwe patch-ankers nodig behalve de S(4)-toevoeging binnen bestaande blokken.
- Overschrijding van de caps (6 rt / 12 regels / 500 keuze) → getelde restknoop, nooit truncatie-zonder-melding.

## 5. Gouden getallen (gemeten 08-11-2026, cache van 08-11)

| Instrument | top-artikel | regels | graadwaardige artikelen | totaal regels |
|---|---|---|---|---|
| Eindhoven | **1.8** | 12 | 811 | 1407 |
| Utrecht | **10.4** | 9 | 107 | 218 |

Top-5 Eindhoven: 1.8 (12, **formalized**) · 3.37 (10, **unmatched**) · 10.186 (7) · 22.61 (7, formalized) · 10.254 (6). Top-5 Utrecht: 10.4 (9, **unmatched** — het best verbonden Utrecht-artikel is dus een onthouding, op zich al een verhaal) · 6.44 (6) · 3.79 (5) · 3.66 (5) · 9.19 (5).

## 6. Bouwvolgorde (globaal; plan verfijnt)

1. `build_kg7()` + data-aansluiting (`DATA.dsokb.kg`) + begrenzingen
2. template: paneel + dropdowns + layout-render + S(4)-stap + VSTAGES7-uitbreiding
3. verify: 5 stappen + graaf-asserts + slotlog; README
4. eindcontrole: volledige cyclus + gent-only + pytest-regressie

---

## Errata / versmallingen na uitvoering (2026-11-08)

1. **§5 top-5-lijstjes zijn níét tie-broken weergegeven**: de deterministische nummerieke tie-break maakt Eindhoven nr. 5 tot **10.195** (niet 10.254; beide 6 regels) en Utrecht nr. 3 tot **3.66** (niet 3.79; beide 5 regels). De build/print/verify volgen de tie-break.
2. **§2.5 "stippellijn-eindknoop bij niet-koppelbaar gml" is versmald**: de GIO-knoop blijft weg wanneer geen gml koppelbaar is; de locatie-tooltip vermeldt "gml: niet koppelbaar" (README beschrijft het gedrag zoals geïmplementeerd).
3. **§3.1/§4 overzichts-sampling**: het top-overzicht toont per artikel max 3 regelteksten en 3 regels (subgraph-caps blijven 6/12 mét restknoop); de tooltip vermeldt de totale aantallen.
