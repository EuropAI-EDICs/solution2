# Design — Tab 7: "STTR toepast" als derde status (vierde laag)

| | |
|---|---|
| **Datum** | 8 november 2026 |
| **Zuster** | [2026-11-08-dso-kb-simulatie-tab-design.md](2026-11-08-dso-kb-simulatie-tab.md) (tab 7 zelf), [2026-11-08-dso-kb-kennisgraaf-design.md](2026-11-08-dso-kb-kennisgraaf-design.md) (kg7) |
| **Kader** | [POC_STTR_IMTR_KANSEN.md](../../../POC_STTR_IMTR_KANSEN.md) — kans 1: de doctrine wordt drieledig in de beslisladen (annoteert/toetst/toepast) en Tab 7 toont drie statussen per instrument in plaats van twee |
| **Data** | `dso_overlap/out/<instrument>.rtr.json` (contract `rtr/v1`) + `<instrument>.sttr.json` (contract `sttr-index/v1`), gebouwd door `dso_overlap.rtr` en `regelrecht.sttr` |

## Doel

Tab 7 vertelt de doctrine "DSO annoteert · RegelRecht toetst · STTR toepast · AI verkent" (vier
lagen, geen LLM in de beslislijn) met dezelfde Discipline als de rest: elk getal uit een
cache-artefact, elke afwezigheid een expliciete status. De STTR-laag krijgt (a) een eigen
stap in de stappenrail, (b) een derde statuslijn per instrumentkaart, (c) een eigen kaart
tussen de instrumentkaarten en de drift-kaart.

## UI-wijzigingen (simulation/template.html)

1. **kop7** (NL+EN): "Drie lagen" → "Vier lagen, niet door elkaar: **DSO annoteert** ·
   **RegelRecht toetst** · **STTR toepast** (de officiële DMN-vragen die in het
   Omgevingsloket draaien — RTR-artefacten `rtr.json`/`sttr.json`) · **AI verkent**".
   `kb7-titel` idem.
2. **VSTAGES7**: nieuwe stap 4 `["STTR toepast","rtr.json · sttr.json"]` tussen
   "RegelRecht toetst" en "verversen & drift" (kennisgraaf schuift naar 6). Rail, logs en
   `stageCls7` volgen automatisch uit de lijst.
3. **Instrumentkaart** (`kb7InstCard`): derde statuslijn onder de toets-regel —
   Eindhoven: `STTR: 162 RTR-bestanden · 2.322/3.465 decisions uitvoerbaar op de engine`
   (uit `inst.sttr`); Utrecht: `STTR: geen aanlevering gekoppeld (OIN onbekend)` — een
   absent-status, geen nul.
4. **Nieuwe kaart `kb7-sttrcard`** (na `kb7-utrecht`): "STTR toepast — officiële
   toepasbare regels (DMN) uit de RTR" met per instrument OIN, aantal geldige
   bestanden + begindatum-bereik, de projecteerbaar-verdeling (groen projecteerbaar /
   amber niet, met top-redenen als tooltip/legenda), en de doctrine-noot dat STTR
   per **activiteit** concludeert (enum) waar RegelRecht per **artikel** toetst
   (boolean) — aanvullende lagen, geen dekking.
5. **makeSim7**: nieuwe stage-log op stap 4 met de gouden getallen (zie hieronder) en
   de doctrine-regel aangevuld naar vier lagen; de kennisgraaf-stage-log ongewijzigd.
6. **Footer**: één regel "Tab 7 … zie [POC_STTR_IMTR_KANSEN.md]" naast de bestaande
   tab-verwijzingen.

## Data (simulation/build_simulation.py · `build_dso_kb`)

Per instrument léést (optioneel) `<iid>.rtr.json` + `<iid>.sttr.json` en emit:

```jsonc
"sttr": {                       // null als beide ontbreken
  "oin": "00000001001902763000",
  "geldig": 162, "bestanden": 162,
  "begindatumMin": "07-07-2022", "begindatumMax": "28-10-2026",
  "decisions": 3465, "projecteerbaar": 2322, "scenario": 2044,
  "dmnVersies": {"1.1": 118, "1.2": 44},
  "redenenTop": [["not(null)-wachters", 546], ["COLLECT multi-hit", 88]],
  "gegenereerdOp": "…" }
```

Alleen `rtr.json` aanwezig → `"sttr": {"onvolledig": "draai regelrecht.sttr …"}` zodat de
UI een herstelpad toont in plaats van een nul. `DSO_INSTRUMENTEN`-volgorde en de rest van
het displayblok ongewijzigd; gent-only build onaangetast (view7 blijft achter `if(DKB)`).

## Gouden getallen (PRE-cache 8-11-2026)

- Eindhoven (OIN `00000001001902763000`): **162** geldige STTR-bestanden,
  **3.465** decisions, **2.322** projecteerbaar (67 %), **2.044** scenario-uitgevoerd,
  0 engine-fouten; dmnVersies 118×1.1 + 44×1.2; top-redenen `not(null)` 546× en
  COLLECT 88×; begindata 07-07-2022 → 28-10-2026.
- Utrecht: **geen OIN gekoppeld** in `instruments.py` — absent-status (kans 3 van de
  notitie: lokaliseren via gm-code is de route, geen aanname).

## Grenzen

- STTR-conclusies zijn per **activiteit** (enum: Vergunningplicht/Toestemmingsvrij/…);
  de tab toont de uitvoerbaarheid van de tabellen op ónze engine, niet een
  loket-conclusie voor een concreet voorstel — dat is geen UI-claim maar doctrine.
- PRE, niet prod; PRE-RTR-data kan leveranciersruis bevatten (zie de
  correctie-notitie in de kansen-notitie: bevoegd gezag altijd via de gm-code).
- De kaart toont géén inhoud van de DMN's zelf — daarvoor blijft
  `dso_kb.lees_sttr()`/`docs/research/sttr-imtr/` de bron.

## Verificatie

- `nldt/.venv/bin/python simulation/build_simulation.py` print per instrument de
  STTR-regel naast de bestaande dekkingsregel.
- Gerenderde `simulation.html` bevat `kb7-sttrcard`, "Vier lagen", "STTR toepast";
  `python -m unittest nldt.tests.test_simulation_sttr` blijft groen (datazijde).
