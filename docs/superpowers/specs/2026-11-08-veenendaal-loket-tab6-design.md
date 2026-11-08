# Design — Tab 6: "het loket"-stap + scenario-kruising (Veenendaal)

| | |
|---|---|
| **Datum** | 8 november 2026 |
| **Zuster** | [2026-11-08-sttr-toepast-tab7-design.md](2026-11-08-sttr-toepast-tab7-design.md) (Tab 7) · [USE_CASE_VEENENDAAL_SPOORZONE.md](../../../USE_CASE_VEENENDAAL_SPOORZONE.md) |
| **Kader** | [POC_STTR_IMTR_KANSEN.md](../../../POC_STTR_IMTR_KANSEN.md) — doorwerking in de PoC |
| **Data** | `poc-veenendaal/sttr-runs/<ts>-loketvragen/loketvragen.json` + nieuwe `<ts>-kruising/kruising.json` (engine: `sttr_kruising.py`) |

## Doel

Tab 6 vertelt de gebiedscheck als agentenverhaal (intake → bronnen → deduplice →
clip → doelen → critic → report). Het loket wordt de achtste stap: ná de
nulmeting en vóór het rapport staat de officiële vraagkant — en de
scenario-kruising maakt die stap gespreksstof: *welke officiële lagen raakt
welke programmavariant?*

## Nieuwe engine: `poc-veenendaal/sttr_kruising.py`

Kruist per sweep-scenario de **genomen BGT-vlakken** (`scenarios.json →
allocatie.genomen_ids`, geometrie uit `data/cache`) met de **GIO-lagen die de
werkgrens snijden** (uit de loketvragen-run; geometrie uit het
uitwisselpakket). Per GIO-laag: overlap-m² (drempel ≥ 1 m²) en aantal
geraakte GIO-objecten; union eerst geclipt op de werkgrens; ongeldige
geometrie gerepareerd via `buffer(0)` (geen gissing — anders overslaan).
Uitvoer: `sttr-runs/<ts>-kruising/{kruising.json, report.md, manifest.json}`;
doctrine-regel: **geometrisch feit, geen toets** — "raakt" ≠ "verboden".

## Hub-wijzigingen

1. **`build_dso… build_veenendaal()`**: leest (optioneel) de nieuwste
   `*-loketvragen`- en `*-kruising`-runs → compact `VD.loket`-blok:
   regeling/oin/bestanden, GIO-samenvatting (83/30 + top-6 met ha),
   programma-koppelingen, per scenario `n_lagen` + top-3 raak-regels
   (gio, m², objecten), en de grens-zin.
2. **`VSTAGES6`**: nieuwe stap 8 `["het loket","RTR · STTR · GIO-sweep"]` vóór
   "report" (report wordt 9e).
3. **`makeSim6`**: nieuwe stage-log met de gouden getallen en de doctrine-regel;
   "report"-stage schuift door.
4. **Nieuwe telemetry-kaart `loketcard6`**: statisch gevuld in
   `buildStatic6` (functie `buildLoket6()`): GIO-samenvatting + top-lagen,
   programma-koppelingen en de kruising per scenario (compact, één regel per
   scenario met top-raak). Kaart blijft verborgen-inhoudelijk neutraal als
   `VD.loket` ontbreekt (gent-only build onaangetast: view6-init daar uit).

## Gouden getallen (canonieke runs 8-11-2026)

- Loket: 185 STTR-bestanden · OIN `00000001001104470000` · omgevingsplan
  `/akn/nl/act/gm0345/2020/omgevingsplan` · GIO's 30/83 snijden de werkgrens.
- Kruising (`20261108T193749Z-kruising`): BOUW-OP-GROEN raakt **25 lagen, 101
  beschermde bomen** (vs 32 bij bouw-op-verhard); de 18,03-ha-verhard-varianten
  liggen vrijwel volledig in de **boringsvrije zone + grondwaterbeschermingszone
  (18,02 ha van de toedeling)** — de spoorzone zit in het
  grondwaterbeschermingsgebied; 18 gemeentelijke monumenten-objecten;
  **DICHT-15 (11,28 ha)** is overal het zuinigst (24 bomen · 14 monumenten);
  tempo-varianten delen de toedeling met BOUW-OP-VERHARD (tempo verandert
  oppervlak niet).

## Grenzen

- Raakt ≠ verboden; conclusie-enum volgt pas met een concreet voorstel.
- bbox-werkgrens + provisionele zone-indeling blijven de basis van de toedeling.
- STTR-vraag ↔ locatie blijft onkoppelbaar bij Veenendaal (loketvragen-rapport);
  de kaart toont lagen, geen vraag-uitspraken.
- PRE, niet prod.

## Verificatie

- `sttr_kruising.py` print per scenario n_lagen + top-raak.
- `build_simulation.py` print `veenendaal/loket`-samenvatting; gerenderde
  `simulation.html` bevat `loketcard6`, "het loket" in de rail (9 stappen);
  `node --check` groen; browser-smoke: tab 6 → jumpToStage(7) → logs + kaart.

## Update 8-11-2026 (slot): kaart-overlays (optie 2)

Zes gecureerde GIO-lagen zijn nu ook **op de kaart** zichtbaar (klikbaar in de
legenda): regels tijdelijk deel, ecologisch waardevol gebied, boringsvrije
zone, archeologisch waardevol gebied, beschermde bomen (144 punten) en
gemeentelijke monumenten (21 vlakken). Bouw: `build_veenendaal()` ontleedt de
GML's uit het lokale uitwisselpakket (zelfde cache-contract als BAG/BGT),
klipt op de werkgrens en versimpelt voor display; bij meerdere bestandsnamen
per thema (bijv. archeologie *petenbos* vs. *aanleg*) wint de kandidaat met de
grootste overlap met de werkgrens — deterministisch, geen handkeuze. De
loket-stap zet *tijdelijk deel* + *boringsvrije zone* aan en noemt de rest
klikbaar; `buildStatic6` zet bij reset alles uit. Browser-geverifieerd:
toggles aan/uit (met `.on`-legendastatus), stage-aanzet en reset.
