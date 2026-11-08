# STTR/IMTR-kansen voor de RegelRecht-track: van IPLO-standaard naar gemeten DMN-naad

| | |
|---|---|
| **Voor wie** | Ontwikkelaars en architecten van de LDT-toolbox; zuster van [POC_TPOD_IMOW_KANSEN.md](POC_TPOD_IMOW_KANSEN.md) (annotatiekant) en de [bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) |
| **Datum** | 8 november 2026 |
| **Aanleiding** | IPLO-hub [STTR/IMTR](https://iplo.nl/digitaal-stelsel/aansluiten/standaarden/sttr-imtr) (beheer RWS/projectteam Reneso): [STTR 3.0.1](https://iplo.nl/publish/pages/162385/20250801-dso-specificatie-sttr-3-0-1_1.pdf) en [IMTR 3.0.1](https://iplo.nl/publish/pages/162385/20251204-dso-specificatie-imtr-3-0-1-def.pdf) (def. 04-12-2025), DMN 1.1/1.2 |
| **Downloads** | [research/sttr-imtr/](research/sttr-imtr/) — specificaties, 6 officiële voorbeeld-DMN's, XSD's (DMN 1.1+1.2), 3 RTR-OAS'en, alles vastgepinnd op sha256 ([SOURCES.md](research/sttr-imtr/SOURCES.md)) |
| **Code** | [research/sttr-imtr/scan_executies.py](research/sttr-imtr/scan_executies.py) (567-testcase) + de volledige Eindhovense STTR-set uit de PRE-RTR (162 bestanden) en een 20-steekproef van Tilburg; import-keten `nldt/simulation/regelrecht/sttr/` + `dso_overlap/rtr.py`, tests `nldt/tests/test_simulation_sttr.py` |

---

## De kern in één alinea

De STTR is de officiële tegenhanger van onze RegelRecht-laag: *begrijpelijke vertalingen van juridische regels* die als vragen-plus-beslistabellen in het Omgevingsloket draaien, aangeleverd aan de Registratie Toepasbare Regels (RTR) als **DMN 1.1/1.2**-documenten. Deze notitie bevestigt drie aansluitingen met metingen in plaats van aannames: (1) de doctrine wordt drieledig — **DSO annoteert · RegelRecht toetst · STTR toepast** — en Tab 7 kan straks drie statussen tonen; (2) onze executies (EN/≤/=/IF, inputs, outputs) mappen **constructief volledig** op DMN-decisiontables: alle 567 Eindhovense executies gebruiken uitsluitend first-class DMN-dragers (37 FEEL-`<=`-cellen, 594 booleaanse cellen, 63 geo-inputs); (3) de RTR is met de bestaande `DSO_API_KEY` **live bevraagbaar als derde kennisbank-bron** naast Presenteren en Ruimtelijke Plannen — Eindhoven (OIN `00000001001902763000`) blijkt er 162 geldige STTR-bestanden te hebben, alle gedownload. Wat níet 1-op-1 kan — boolean-toets vs. conclusie-enum, artikel- vs. activiteit-granulariteit — staat er expliciet bij; niets verzinnen.

## De kansenkaart

| # | kans | STTR/IMTR-objecten | PoC-naad | status |
|---|---|---|---|---|
| 1 | derde laag in de doctrine: STTR toepast | Conclusie (activiteit, output-enum), functioneleStructuurRef | Tab 7 telt nu twee statussen (uitvoerbaar/onthouding) | **uitgewerkt** (meting Eindhoven: 20 RTR-bestanden; UI-uitbreiding = volgende stap) |
| 2 | DMN als brug: executie ↔ decisiontable | uitvoeringsregel (vraag), geoVerwijzing, rule/inputEntry/outputEntry, hitPolicy | EN/≤/=/IF-executies in de full export | **geleverd als code** (crosswalk + 567-testcase; importer: 2.322/3.465 decisions projecteerbaar; exportroute: XSD-valide + roundtrip-exact) |
| 3 | RTR als derde kennisbank-bron | API *Uitvoeren gegevens toepasbare regels* v2.1.0 (`x-api-key`, `?oin`, `/sttrBestand`) | `dso_overlap/` kent Presenteren + RP + downloaden; RTR ontbreekt | **geleverd als code** (live gemeten, 162 DMN's; `rtr.py` + `dso_kb`-leesfuncties) |

## Kans 1 — Derde laag in de doctrine: DSO annoteert · RegelRecht toetst · STTR toepast

**Wat de standaard zegt.** Toepasbare regels zijn de vraaggemaakte helft van het omgevingsdocument: het bevoegd gezag levert per *activiteit* een STTR-bestand (DMN) aan de RTR aan; het Omgevingsloket voert de tabellen uit en concludeert `Vergunningplicht`, `Toestemmingsvrij`, `Meldingsplicht`, `Informatieplicht`, `Verbod`, `NeemContactOpMet` of `NietVanToepassing` (STTR 3.0.1, Bijlage 1 Tabel 1). De geometrie zit niet in het DMN: locaties komen via STOP/LVBB binnen en het bestand verwijst er alleen naar (`uitv:geoVerwijzing`).

**De naad.** Onze doctrine (kop Tab 7, [bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) "drie lagen"; leitmotif *AI verkent · rekenlaag toetst · mens beslist*) kent annoteert en toetst, maar geen officiële *toepast*-laag. Tab 7 (`kb7InstCard()` in [simulation/template.html](../simulation/template.html)) toont per instrument dan ook maar twee statussen: "X uitvoerbaar · Y onthouding" (Eindhoven 457/56%, Utrecht 7).

**Gemeten** (PRE-RTR, 8-11-2026): de registratie bevat **66.474** actuele toepasbare-regelentries (133 pagina's); op de eerste zes pagina's al 98 bevoegde gezagen. Eindhoven heeft **162 geldige bestanden** (begindata 07-07-2022 t/m 28-10-2026 — actief onderhouden), activiteiten van `BouwwerkSlopen` tot `GeluidProdWindturbine` — dus een smallere, activiteit-gebundleelde set dan onze 567 artikel-executies. Precies daardoor zijn het *aanvullende* statusinformatie, geen concurrentie: STTR zegt wat het loket officieel concludeert per activiteit, RegelRecht toetst het eigen voorstel tegen het hele instrument.

**Volgende stap.** Tab 7-uitbreiding: per instrument een derde statusregel "STTR toepast", gevoed door een RTR-cache (kans 3) — per activiteit `conclusie`-enum en `begindatum`, met expliciete absent-status als het bevoegd gezag geen toepasbare regels aanlevert.

**Update 8-11-2026: Tab 7 toont drie statussen.** De doctrine-kop luidt nu *vier lagen* — **DSO annoteert · RegelRecht toetst · STTR toepast · AI verkent** — met een eigen stap in de stappenrail (`rtr.json · sttr.json`), een derde statuslijn per instrumentkaart (Eindhoven: **162 RTR-bestanden · 2.322/3.465 decisions uitvoerbaar op de engine**; Utrecht: destijds absent-status, inmiddels gekoppeld — zie kans 3) en een eigen STTR-kaart met de projecteerbaar-verdeling plus de expliciete niet-redenen (not(null) 546× · contains() 432× · COLLECT 88×). Ontwerp: [2026-11-08-sttr-toepast-tab7-design.md](superpowers/specs/2026-11-08-sttr-toepast-tab7-design.md); gevoed uit de rtr/v1- en sttr-index/v1-caches, browser-geverifieerd (stappenrail 6 stappen, stage-logs met de gouden getallen).

## Kans 2 — DMN als brug: de executie is al een beslistabel

**Wat de standaard zegt.** Elk regelbeheerobjecttype heeft een vaste DMN-vorm (STTR 3.0.1 §8, IMTR §5–9): inputs zijn **uitvoeringsregels** — vragen met `gegevensType` boolean/string/number/date, optielijsten, `vasteWaarde`, `geoVerwijzing` (met IMOW-locatie-identificatie) of registerbevragingen (Kenmerken); de Conclusie-tabel is single-hit met de enum hierboven; Indieningsvereisten single-hit (voorkeur U); Maatregelen multiple-hit (C/O/R). Cel-expressies zijn (S-)FEEL: `true`/`false`, `"optie"`, `<= 175`, `> 50`, `(50..100)`. Juridische verankering loopt via `dmn:annotationEntry` en `dmn:knowledgeSource` (AKN/wId) en de activiteitskoppeling via `bedr:functioneleStructuurRef` onder het OIN-namespace. Versiefeiten: DMN 1.2 wordt sinds STTR 1.1 (06-01-2020) naast 1.1 ondersteund, DMN 1.3+ niet; STTR 3.0.0 dateert van 24-03-2025, 3.0.1 is tekstueel (04-12-2025).

**De naad.** Onze executions (`nldt/simulation/regelrecht/full_export/`, schema v0.8.11) gebruiken precies vier operatoren — `AND`, `EQUALS`, `LESS_THAN_OR_EQUAL`, `IF` — plus inputs met type en outputs met type. Dat zijn geen "bijna-DMN"-constructies; het zijn letterlijk decisiontable-onderdelen, zie de crosswalk:

| RegelRecht-executie | STTR/DMN | opmerking |
|---|---|---|
| `input[]` (name/type/description/source) | `uitv:uitvoeringsregel` (vraagTekst, gegevensType) + `dmn:inputData/variable` | boolean→boolean, number→number, één-op-één |
| `in_werkingsgebied` (geo-feit, MC-11) | `uitv:geoVerwijzing/uitv:locatie @identificatie` | de GIO-adressen uit de [TPOD-kansen](POC_TPOD_IMOW_KANSEN.md) vullen dit exact |
| `AND` | conjunctie binnen één `dmn:rule` (alle cellen moeten matchen) | hit policy ANY voor booleaanse outputs |
| `LESS_THAN_OR_EQUAL $x v` | FEEL-cel `<= v` | ook ranges `(a..b)`, `> v` |
| `EQUALS $x b` | FEEL-cel `true`/`false`/`"optie"` | |
| `IF cases/when/then/default` | meerdere `dmn:rule`-rijen; `default` = rest-rij | |
| `output: toegestaan_art_X` (boolean, `TOETS`) | boolean decision (ANY) óf Conclusie-enum | enum-vertaling is een juridische keuze, géén automatiek |
| artikel + `url` (CVDR-anker) | `annotationEntry`/`knowledgeSource` (AKN/wId) | zit in standaard én officiële voorbeelden; Eindhovens PRE-materiaal mist het |
| `competent_authority` | OIN-namespace + `bedr:functioneleStructuurRef` | granulariteit: activiteit, niet artikel |

Concreet, art. 1.8 (uit [eindhoven-cvdr696400.yaml](../nldt/simulation/regelrecht/full_export/out/eindhoven-cvdr696400.yaml), reden "template maximaal 1.0 m"):

```yaml
execution:
  input:
    - {name: limiet_m, type: number}          # voorstelafhankelijk feit
    - {name: in_werkingsgebied, type: boolean} # geo-feit (werkingsgebiedRef, MC-11)
  output: [{name: toegestaan_art_1_8, type: boolean}]
  actions:
    - output: toegestaan_art_1_8
      value:
        operation: AND
        conditions:
          - {operation: LESS_THAN_OR_EQUAL, subject: $limiet_m, value: 1.0}
          - {operation: EQUALS, subject: $in_werkingsgebied, value: true}
```

…is als STTR 3.0/DMN 1.2-vorm (projectie op het patroon van het officiële `ConclusieBouwenDakkapel.dmn`; geen aanlevering):

```xml
<uitv:uitvoeringsregel id="uitv_werkingsgebied">
  <uitv:geoVerwijzing>
    <uitv:locatie identificatie="nl.imow-gm0855.gebied.…"/>
    <uitv:vraagTekst>Ligt de locatie in het werkingsgebied van art. 1.8?</uitv:vraagTekst>
  </uitv:geoVerwijzing>
</uitv:uitvoeringsregel>
…
<dmn:decision name="Toegestaan art 1.8">
  <dmn:decisionTable hitPolicy="ANY" typeRef="boolean">
    <dmn:input><dmn:inputExpression typeRef="number"><dmn:text>limiet_m</dmn:text></dmn:inputExpression></dmn:input>
    <dmn:input><dmn:inputExpression typeRef="boolean"><dmn:text>in_werkingsgebied</dmn:text></dmn:inputExpression></dmn:input>
    <dmn:rule><!-- AND(≤ 1.0, in gebied) -->
      <dmn:inputEntry><dmn:text>&lt;= 1.0</dmn:text></dmn:inputEntry>
      <dmn:inputEntry><dmn:text>true</dmn:text></dmn:inputEntry>
      <dmn:outputEntry><dmn:text>true</dmn:text></dmn:outputEntry>
      <dmn:annotationEntry><dmn:text>CVDR696400/4 art. 1.8</dmn:text></dmn:annotationEntry>
    </dmn:rule>
    <dmn:rule><!-- default: de AND dekt de rest -->
      <dmn:inputEntry><dmn:text>-</dmn:text></dmn:inputEntry>
      <dmn:inputEntry><dmn:text>-</dmn:text></dmn:inputEntry>
      <dmn:outputEntry><dmn:text>false</dmn:text></dmn:outputEntry>
    </dmn:rule>
  </dmn:decisionTable>
</dmn:decision>
```

**Gemeten — de 567 Eindhovense executies als testcase** ([scan_executies.py](research/sttr-imtr/scan_executies.py) → [eindhoven-567-dmn-scan.json](research/sttr-imtr/eindhoven-567-dmn-scan.json), herleidbaar tot `sourceSha256` van de export):

| templatevorm | n | DMN-drager |
|---|---|---|
| equivalentie (`IF`/cases, strijd tijdelijk deel) | 504 | meerrijige tabel, één boolean-input |
| limiet (`AND`: `<=` + werkingsgebied) | 37 | FEEL-`<=` cel + `geoVerwijzing` |
| verbod (`AND`: booleans) | 26 | conjunctierij boolean-cellen |
| **totaal** | **567** | 37 numerieke vergelijkingen, 594 booleaanse gelijkheden, 63 geo-inputs, 631 inputs (594 boolean + 37 number) |

Conclusie van de testcase: **100 % van de gebruikte constructieblokken is first-class DMN**; geen enkele executie heeft een operator of type dat de STTR niet kan dragen. De semantiche naad zit niet in de constructies maar in de vertaalslag: onze boolean *toets* per artikel vs. de officiële *conclusie-enum* per activiteit (toegestaan → `Toestemmingsvrij`/`Vergunningplicht`/… is een juridische beslissing), en het samennemen van artikelen tot één activiteit-tabel (`functioneleStructuurRef`).

**Volgende stap — twee richtingen, verschillende rijpheid.**
- **STTR → RegelRecht (vandaag bouwbaar):** importer die de 162 Eindhovense RTR-bestanden (en de officiële voorbeelden) ontleedt tot `machine_readable`-executies en ze met onze reference-engine op dezelfde inputs runt — dan is de officiële tabel executioneerbaar naast de DSO-annotatie en kan drift tussen loket-conclusie en annotatie zichtbaar worden. XSD's van beide dialecten (DMN 1.1 en 1.2) staan in de downloads.
- **RegelRecht → STTR (autorauteitsroute):** export van (nieuwe) toepasbare regels als STTR 3.0.1-bestand, gevalideerd tegen de vastgepinde XSD's en voorbeeldbestanden. Let op de scope: de 63 limiet/verbod-artikelen zijn grotendeels *regels voor omgevingsvergunning* (officieel IMOW-annotatiegebied, zie de [TPOD-notitie](POC_TPOD_IMOW_KANSEN.md)) en de 504 equivalentie-executies zijn conversie-feiten uit `poc-bp2op` — géén van beide hoort thuisloos de RTR in; de route geldt toekomstige, échte toepasbare regels.

**Update 8-11-2026: de brug is gebouwd — STTR → RegelRecht als code.** [`nldt/simulation/regelrecht/sttr/`](../nldt/simulation/regelrecht/sttr/) ontleedt **DMN 1.1 én 1.2** (STTR v1.0- én v2.0-namespaces; prefixen afgeleid uit de xmlns-declaraties, niet aangenomen) tot beslistabellen en projecteert die rij-voor-rij op de engine-subset — single-hit tabellen worden een `IF` met cases in documentvolgorde en de eerste alles-mogelijke rij als `default`; `scenario_run()` draait alle boolean-polariteiten door de reference-engine. Gemeten over de hele RTR-stand van Eindhoven: **162 bestanden → 3.465 decisions, waarvan 2.322 projecteerbaar (67 %) en 2.044 scenario-uitgevoerd, 0 engine-fouten**. De 1.143 niet-projecteerbare decisions zijn expliciet gelabeld — top-redenen: `not(null)`-wachters (546×), COLLECT-multi-hit (88×) en `contains()`-expressies van de leverancierstools — niets stilletjes gemold. De zes officiële IPLO-voorbeelden (STTR 3.0.0/DMN 1.2): 101 decisions, 62 projecteerbaar, mét de verwachte `knowledgeSource`-AKN's (3) en `geoVerwijzing` (1, `nl.imow-gm0345.gebied.gemeentegrens`). Contract `sttr-index/v1` (schema-valide), tests `nldt/tests/test_simulation_sttr.py` — 15 groen, inclusief de volledige gecommitte corpus.

**Update 8-11-2026 (later op de dag): ook de omgekeerde brug — RegelRecht → STTR.** [`sttr/export.py`](../nldt/simulation/regelrecht/sttr/export.py) serialiseert executies (AND/≤/=/IF, booleaanse outputs) naar de officiële STTR 3.0/DMN 1.2-vorm — v2.0-namespaces, `bedr:sttr versie="3"`, `uitv:uitvoeringsregels` als vragen, ANY-hit beslistabellen met vangnetrij, en `annotationEntry`/`knowledgeSource` met het artikelanker. Twee garanties, beide getest: (1) **XSD** — de export valideert tegen de vastgepinnde `DMN_v12.xsd`, hetzelfde schema dat de officiële IPLO-voorbeelden keurt; (2) **roundtrip** — export → eigen parser → eigen projectie geeft per invoercombinatie dézelfde engine-uitkomst (limiet art. 1.8: 6 combinaties, IF art. 10.2: 4, verbod: 4 — 0 verschillen; identifier-vertaling langs de kolomvolgorde is expliciet onderdeel van de bridge). CLI: `python -m nldt.simulation.regelrecht.sttr --export-demo` (demonstrator, expliciet géén aanlevering). Scope-onderstreping: het mechanisme is er; wat erin gaat moeten toekomstige, échte toepasbare regels zijn — de huidige artikel-executies blijven RFOV/conversie-feiten.

## Kans 3 — RTR als derde kennisbank-bron

**Wat de standaard zegt.** De API *Uitvoeren gegevens toepasbare regels* (v2.1.0, [OAS vastgepinnd](research/sttr-imtr/oas-toepasbareregels-uitvoerengegevens-v2.json)) biedt `GET /toepasbareRegels` (filters `oin`, `functioneleStructuurRef`, `datum`/`datumVanaf` — tijdsreizen —, `sttrBestandInhoudFilter`), metadata per entry (`begindatum`, `einddatum`, `laatsteWijzigingDatum`) en `GET /toepasbareRegels/{id}/sttrBestand` dat het complete DMN levert. Authenticatie: `x-api-key`, hetzelfde key-portaal als Presenteren; aanleveren loopt apart via SOAP/ebMS met PKIoverheid (buiten scope).

**De naad.** De kennisbank (`dso_overlap/` + leeslaag `nldt/services/dso_kb.py`) kent Presenteren, Ruimtelijke Plannen en de downloaden-API; de RTR wordt nergens aangeroepen — in de hele repo kwamen `STTR`/`IMTR`/`RTR` vóór deze notitie niet voor.

**Gemeten** (live, 8-11-2026): de bestaande `DSO_API_KEY` uit de gitignored `.env` werkt één-op-één op de PRE-RTR (productie weert de PRE-key met 401 — zelfde beheersmaatregel als bij de IMOW-metingen). Volledige scan: **66.500 entries over 133 pagina's, 410 bevoegde-gezagsbronnen (waarvan 370 gemeenten)**; de metadata kent géén gemeentenamen, dus identificatie loopt via de gm-code in `functioneleStructuurRef`: **Eindhoven = gm0772 = OIN `00000001001902763000`** (daarna rechtstreeks filterbaar met `?oin=…`). Alle **162 geldige STTR-bestanden** zijn gedownload naar [research/sttr-imtr/rtr-pre-eindhoven/](research/sttr-imtr/rtr-pre-eindhoven/) met metadata-cache (22,7 MB). De set is diverser dan verwacht: **118× DMN 1.1 + 44× DMN 1.2**, van drie leveranciers (RuleArts 111, Sogelink 44, Geodan FLO 7), en **0 `uitv:geoVerwijzing`'en** — Eindhoven vraagt locatie als gewone ja/nee-vraag in plaats van via het officiële geo-mechanisme. De importer moet dus beide dialecten lezen (beide XSD's liggen vast) en mag geo niet aannemen.

**Correctie (zelfde dag, bewust genoteerd):** een eerste scan greep `gm0855` als Eindhoven en downloadde 20 bestanden die bij nader inzien **Tilburg** bleken (OIN `00000001001172773000`; de regelgroepnaam "Gemeente Tilburg" in die bestanden was geen testdata maar de waarheid — CBS: gm0772 = Eindhoven, gm0855 = Tilburg). Die 20 liggen als steekproef in [research/sttr-imtr/rtr-pre-tilburg/](research/sttr-imtr/rtr-pre-tilburg/). De les staat bij de eerlijke grenzen.

**Volgende stap.** `dso_overlap/rtr.py` naar het `client.py`-patroon: `fetch_toepasbare_regels(oin)` + `fetch_sttr_bestand(id)`, PRE-base via `RTR_API_BASE`-override, cache als `<oin>.sttr.json` + `.dmn`; daarna leesfuncties in `dso_kb.py` (`lijst_toepasbare_regels`, `lees_sttr`) en de Tab 7-derde status uit kans 1.

**Update 8-11-2026: de RTR is een kennisbank-bron.** [`dso_overlap/rtr.py`](../nldt/simulation/regelrecht/dso_overlap/rtr.py) (client + CLI: paging, `?oin`-filter, `--bestanden` downloadt alle geldige bestanden idempotent in de cache; PRE-default met `RTR_API_BASE`-override, contract `rtr/v1` met sha256 per bestand) en de leesfuncties `lijst_toepasbare_regels()`/`lees_sttr()` in [`dso_kb.py`](../nldt/services/dso_kb.py) sluiten de registratie aan op het bestaande Presenteren/RP-patroon; `instruments.py` draagt Eindhovens OIN (utrecht volgt zodra het bevoegd gezag via de gm-code is gelokaliseerd). Live geverifieerd: **162/162 bestanden in één run gecacht**; de Tab 7-derde status ("STTR toepast" per activiteit) is nu puur een UI-uitbreiding die uit deze cache voedt.

**Update 8-11-2026 (slot): Utrecht gekoppeld.** De full scan leverde **pv26 = OIN `00000001001797864000`** (één OIN, geen dubbelzinnigheid): **115 geldige STTR-bestanden** (45× DMN 1.1 + 70× DMN 1.2; Sogelink 67, Geodan 45, Berkeley Modeler 3), **3.320 decisions, waarvan 1.875 projecteerbaar en 1.297 scenario-uitgevoerd**. Tab 7 toont nu voor béíde instrumenten echte STTR-cijfers in plaats van een absent-status.

**Update 8-11-2026 (Veenendaal meegenomen).** Het officiële IPLO-voorbeeldbestand bleek zich al in Veenendaal af te spelen — `ConclusieBouwenDakkapel.dmn` draait onder OIN `00000001001104470000` = **gm0345**, met de vraag "Ligt het pand binnen de gemeentegrens van Veenendaal?" (`nl.imow-gm0345.gebied.gemeentegrens`) — en de échte registratie doet dat ook: **185 geldige STTR-bestanden** (112× DMN 1.1 + 73× DMN 1.2; RuleArts 112, Berkeley Modeler 62, Knowledge Values 10), begindata 29-06-2022 t/m 24-12-2025, **2.373 decisions, waarvan 1.621 projecteerbaar en 1.555 scenario-uitgevoerd**. Opvallend: Veenendaal gebruikt als enige van de drie gemeenten wél het officiële geo-mechanisme — **20 `uitv:geoVerwijzing`en** naar echte `nl.imow-gm0345`-GIO's (gebieden uit het omgevingsplan-2025, plus één rijkswaterstaatsgebied `Waterkwaliteit`); Eindhoven vraagt locatie als gewone ja/nee-vraag (0 geoVerwijzingen). En er zit een directe Spoorzone-haak in: de activiteit **`WegSpoorwegAanleggenWijz`** ("Weg of spoorweg, zonder geluidproductieplafonds, aanleggen of wijzigen") heeft eigen indieningsvereisten-bestanden, inclusief een *herbruikbare beslissing* — precies de officiële laag die de [tab-6-Spoorzone-piloot](USE_CASE_VEENENDAAL_SPOORZONE.md) straks naast de BAG/BGT-gebiedscheck kan leggen. Koppeling: `veenendaal` is als **RTR-only-instrument** geregistreerd in `instruments.py` (géén Presenteren-koppeling of formalisering — daarom niet in Tab 7); `compare`, `tpod` en de annotatie-leesfuncties van `dso_kb` wijzen het vriendelijk door naar de RTR-route.

**Update 8-11-2026 (doorwerking in de PoC).** [`poc-veenendaal/sttr.py`](../poc-veenendaal/sttr.py) legt de STTR-laag nu over de Spoorzone zelf: het station-anker vindt via Presenteren `regelingen/_zoek` het omgevingsplan (`/akn/nl/act/gm0345/2020/omgevingsplan`, 4e wijziging) en de downloaden-API levert het uitwisselpakket (2,6 MB, 83 GIO's). De 20 geoVerwijzing-vragen zijn daarin **niet hard koppelbaar** — 18 verwijzen naar een leveranciers-identificatiefamilie (`gebiedengroep.0040…`) die niet in het plan zit, 2 naar OP-gebieden zonder geometrie in dit pakket — en dat staat nu per status in het rapport (gekoppeld / aanwezig-als-ow-object / afwezig; nooit gokken). De gebiedsfeit-kant wél gemeten: **30 van 83 officiële GIO-lagen snijden de werkgrens**, waaronder *regels tijdelijk deel* (161 ha — de hele bbox; de Veenendaalse variant van de Eindhovense bruidschat), ecologisch/landschapswaarden, boringsvrije zone + grondwaterbescherming (60,8 ha), archeologie mét diepte-/oppervlaktemaxima, beschermde bomen (9,6 ha) en gemeentelijke monumenten (4,9 ha) — elk met STOP-FRBRWork als anker. Daarnaast 7 bewijs-gebonden programma-koppelingen (spoorlijn in gebied → `WegSpoorwegAanleggenWijz`; 4.500 woningen → bouw-activiteiten; …) met de officiële loket-vragen per activiteit eronder (bijv. 89 vragen voor bijbehorende bouwwerken, incl. de achtererf-animaties). Doctrine-lijn ongewijzigd: dit zijn de officiële **vragen** — geen besluit. Tests: `nldt/tests/test_poc_veenendaal_sttr.py` (7 groen); canonieke run `sttr-runs/20261108T192445Z-loketvragen`.

## Bedienen

```bash
# bronnen staan lokaal vastgepinnd (sha256 in research/sttr-imtr/SOURCES.md)

# RTR als derde kennisbank-bron (PRE; zelfde DSO_API_KEY als Presenteren):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.dso_overlap.rtr \
  --instruments eindhoven --bestanden

# STTR-import (offline op de cache): beslistabellen + engine-projectie + scenario's:
nldt/.venv/bin/python -m nldt.simulation.regelrecht.sttr --instruments eindhoven
nldt/.venv/bin/python -m nldt.simulation.regelrecht.sttr --van-voorbeelden  # officiële IPLO-voorbeelden

# 567-testcase herhalen (offline):
nldt/.venv/bin/python docs/research/sttr-imtr/scan_executies.py

# leeslaag (puriteins: de agent raakt nooit direct bestanden aan):
nldt/.venv/bin/python -c "from nldt.services import dso_kb; \
  print(dso_kb.lijst_toepasbare_regels('eindhoven')['counts']); \
  print(dso_kb.lees_sttr('eindhoven', 53438)['totals'])"

# tests:
nldt/.venv/bin/python -m unittest nldt.tests.test_simulation_sttr

# RTR met de hand (PRE; sleutel in .env — nooit committen):
KEY=$(grep -E '^DSO_API_KEY=' .env | cut -d= -f2-)
curl -sS -H "x-api-key: $KEY" \
  'https://service.pre.omgevingswet.overheid.nl/publiek/toepasbare-regels/api/toepasbareregelsuitvoerengegevens/v2/toepasbareRegels?oin=00000001001902763000'

# …en het complete STTR-bestand (DMN-xml) van één activiteit:
curl -sS -H "x-api-key: $KEY" \
  'https://service.pre.omgevingswet.overheid.nl/publiek/toepasbare-regels/api/toepasbareregelsuitvoerengegevens/v2/toepasbareRegels/173899/sttrBestand'
```

Artefacten: `docs/research/sttr-imtr/` (specificaties + `dmn-voorbeelden-sttr-3.0.0/` + `xsd-sttr-3.0/` + OAS'en + `rtr-pre-eindhoven/` met 162 DMN's en metadata + `rtr-pre-tilburg/` met de 20-steekproef), `eindhoven-567-dmn-scan.json` (provenance: report-sha256, gegenereerd-op). In de (gitignored) cache: `<instrument>.rtr.json` + `<instrument>.rtr.<id>.dmn` (contract `rtr/v1`) en `<instrument>.sttr.json` (contract `sttr-index/v1`), beide schema-valide — een contractbreuk breekt de bouw. Tests: `nldt/.venv/bin/python -m unittest nldt.tests.test_simulation_sttr` (offline, inclusief de gecommitte corpus). NB: de RTR-bestanden (162 Eindhovense + 20 Tilburgse steekproef) zijn *downloads uit PRE*, bewust wél in git (ze zijn het testcase-materiaal; een her-interview kan via bovenstaande curl).

## Eerlijke grenzen

- **PRE, niet prod**: de RTR-meting komt uit pre-productie met een PRE-key; de productie-endpoint weert die met 401. Zelfde beheersmaatregel als in de [bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md).
- **Naamloze metadata vraagt om verificatie — deze notitie is er het bewijs van**: de eerste meting identificeerde Tilburg (gm0855) als Eindhoven; pas de regelgroepnaam "Gemeente Tilburg" in de bestanden dwong tot heridentificatie via de gm-code (Eindhoven = gm0772). Gecorrigeerd; de les is procedureel: bevoegd gezag koppelen uitsluitend via `functioneleStructuurRef`, nooit via leverancier, bestandsinhoud of aanname.
- **Versiedrift**: Eindhovens set is gemengd — 118× DMN 1.1 + 44× DMN 1.2, v1.0-namespaces, 10× `bedr:sttr versie="2"`, nul keer versie 3 — terwijl de standaard inmiddels STTR 3.0.1/DMN 1.2 met `v2.0`-namespaces en `bedr:sttr versie="3"` is. Beide DMN-dialecten zijn vastgepinnd (XSD's), maar de mapping-voorbeelden tonen de 3.0-vorm.
- **Granulariteit en semantiek**: STTR bundelt per *activiteit* met conclusie-enum; wij toetsen per *artikel* met boolean. De constructies mappen 1-op-1, de enum-vertaling (`toegestaan` → `Toestemmingsvrij`/`Vergunningplicht`/…) is per juridisch karakter een beslissing — geen automatische claim.
- **Geen dekkingsclaim**: 20 RTR-bestanden (vooral indieningsvereisten en enkele conclusies) naast 567 artikel-executies is appels naast peren; de 63 geo/limiet/verbod-artikelen zijn bovendien veelal RFOV-vergunningsartikelen (IMOW-annotatiegebied) en de 504 equivalentie-executies zijn interne conversie-feiten (`poc-bp2op`). De RTR is een ándere, aanvullende laag — dat is kans 1, geen dekking.
- **Juridische verankering in de RTR-bestanden**: `knowledgeSource`/`annotationEntry` (AKN) staan in de standaard en de officiële voorbeelden, maar ontbreken in de Eindhovense (0 van 162) en Tilburgse PRE-bestanden; wId-anchoring (IMOW-kans 3) moet het gat aan onze kant dichten.
- **Wat code is**: de STTR→RegelRecht-importer, de RTR-bron (inmiddels beide instrumenten), de Tab 7-derde status én de RegelRecht→STTR-export-demonstrator zijn geleverd met tests (19 groen). Geen van de STTR-exports is een aanlevering — de RTR blijft uitsluitend via het officiële ebMS-pad bereikbaar.

## Verwijzingen

- IPLO STTR/IMTR-hub (beheer RWS/Reneso; alle versies, verificatiematrix's): <https://iplo.nl/digitaal-stelsel/aansluiten/standaarden/sttr-imtr>; IPLO RTR-introductie: <https://iplo.nl/digitaal-stelsel/introductie/landelijke-voorziening/registratie-toepasbare-regels>
- Specificaties 3.0.1 (vastgepinnd): [STTR](https://iplo.nl/publish/pages/162385/20250801-dso-specificatie-sttr-3-0-1_1.pdf) · [IMTR](https://iplo.nl/publish/pages/162385/20251204-dso-specificatie-imtr-3-0-1-def.pdf) · [voorbeeldbestanden 3.0.0](https://iplo.nl/publish/pages/162385/voorbeeldbestanden-sttr-3-0-0.zip) · [XSD's](https://iplo.nl/publish/pages/162385/xsd-3-0-2025-05-01.zip)
- DSO API-register: [Uitvoeren gegevens toepasbare regels](https://developer.omgevingswet.overheid.nl/api-register/api/raadplegen-uitvoeren-gegevens-toepasbare-regels) · [Samengestelde RTR-services](https://developer.omgevingswet.overheid.nl/api-register/api/samengestelde-registratie-toepasbare-regels) · [Toepasbare regels zoeken](https://developer.omgevingswet.overheid.nl/api-register/api/toepasbare-regels-zoeken) · [Aanleveren (ebMS)](https://developer.omgevingswet.overheid.nl/api-register/api/toepasbare-regels-aanleveren)
- GitHub: [RicharddeGraaf1/imtr_voorbeeldbestanden](https://github.com/RicharddeGraaf1/imtr_voorbeeldbestanden) (DMN 1.1 én 1.2) · [Amsterdam/vergunningcheck](https://github.com/Amsterdam/vergunningcheck) · [hdsr-mid/Omgevingswet_archivering_STTR](https://github.com/hdsr-mid/Omgevingswet_archivering_STTR) · [MinBZK/regels.overheid.nl](https://github.com/MinBZK/regels.overheid.nl)
- Zusterpagina's: [POC_TPOD_IMOW_KANSEN.md](POC_TPOD_IMOW_KANSEN.md) (annotatiekant) · [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) · [RUNBOOK_NOTA_EINDHOVEN.md](RUNBOOK_NOTA_EINDHOVEN.md) · [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md)
