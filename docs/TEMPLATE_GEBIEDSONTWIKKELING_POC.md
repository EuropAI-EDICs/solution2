# Sjabloon — Gebiedsontwikkeling-PoC (Use Case Canvas → engine)

| | |
|---|---|
| **Doel** | Invulbaar sjabloon waarmee een nieuwe gebiedsontwikkeling wordt omgezet van maatschappelijk vraagstuk naar een gevoede PoC op het nLDT-platform (data, indicatoren, rekenmodellen, proces, beslismomenten). |
| **Geleid door** | [`260806_Rapport_Use_Case_Schiehaven_Noord_geanonimiseerd.md`](260806_Rapport_Use_Case_Schiehaven_Noord_geanonimiseerd.md) (Geonovum, DTAAS Use Case Canvas, 23-07-2026) — de structuur hieronder volgt dat canvas; Schiehaven-Noord dienst als referentie-invulling. |
| **Aansluiting** | PoC-patronen: [`nldt/11-poc-patterns-scenarios-qa.md`](../nldt/11-poc-patterns-scenarios-qa.md) (Planes A–D) · Recepten: [`nldt/04-recipes-and-processes.md`](../nldt/04-recipes-and-processes.md) · Landschapskader: [`SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md) §3.5 (RI-Geo-plaat) · Doctrine: [`GENAI_SEAMS.md`](GENAI_SEAMS.md) — *AI stelt voor · rekenlaag beslist · mens beslist*. |
| **Gebruik** | 1) Kopieer dit bestand naar `docs/USE_CASE_<GEBIED>.md`. 2) Vul elke `<placeholder>` in; Schiehaven-voorbeelden weglaten bij invullen. 3) Niet van toepassing = "n.v.t. + reden" (niet weghalen — ook dat is besluitinformatie). 4) Doe Annex B (Definition of Ready) vóór de eerste sprint van de PoC. |

**Naamgevingsconventies zodra de PoC start:** ingevuld canvas `docs/USE_CASE_<GEBIED>.md` · engine `poc-<gebied>/` · recepten `nldt/recipes/<gebied>-<usecase>.json` · processId `<gebied>-<usecase>` · lake-zones `bronze|silver|gold/<gebied>/…` · demo `nldt/simulation/` met route `?poc=<gebied>`.

---

## 1. Maatschappelijk vraagstuk

### 1.1 Context — opgave & publieke waarde

- **Programma-/beleidskader:** `<initiatief/programma waar het gebied onder valt>` *(Schiehaven: Doorbouwakkoord + PvA Duurzaam Doorbouwen; "Paris Prooftuin")*
- **Opgaven (2–4, genummerd):** `<bijv. woningbouwopgave · duurzaamheid · betaalbaarheid>`
- **Publieke waarde:** `<wat willen bewoners en betrokkenen op korte en lange termijn>`
- **Voor wie:** `<opdrachtgevende organisatie + marktpartijen/kennisinstellingen/corporaties>`
- **Grootste knelpunten:** `<financieel/ruimtelijk/juridisch/technisch>`

### 1.2 Inhoudelijke doelen — toetsbaar gemaakt

| Doel | Toetsbare kader / grenswaarde | Bron van de norm |
|---|---|---|
| `<doel 1>` | `<bijv. kg CO₂-eq per m² BVO ≤ …>` | `<DGBC Paris Proof / EU-taxonomie / …>` |
| `<doel 2>` | `<bijv. koele plek ≥ 200 m² binnen 300 m van elke woning; ≥ 40% schaduw op looproutes>` | `<RIVM stresstest hitte / …>` |

### 1.3 Ethische afwegingen

`<per use-casethema één vraag, bijv. "hoeveel mag de huidige generatie investeren ten gunste van toekomstige generaties?" of "is schaduw/kwaliteit openbare ruimte gelijk verdeeld over het gebied?">`

---

## 2. Belanghebbendenanalyse

| Partij (rol, geen persoonsnamen) | Vraag waarvoor zij oplossing zoeken | Besluit dat zij willen nemen | Wat hen belangrijk is |
|---|---|---|---|
| `<projectteam gebiedsontwikkeling (opdrachtgever masterplan)>` | `<…>` | `<…>` | `<…>` |
| `<ingenieursbureau / toetsende rol>` | `<…>` | `<…>` | `<…>` |
| `<ontwerpconsortium (architect, stedenbouwer, landschapsarchitect, modelleur)>` | `<…>` | `<…>` | `<…>` |
| `<andere: stadsbeheer, GEX, provincie, waterschap, …>` | `<…>` | `<…>` | `<…>` |

- **Eigenaar van het vraagstuk:** `<organisatie, gedelegeerd aan functie>` — verantwoordelijk van initiatief t/m realisatie.
- **Opdrachtgever voor het oplossen:** `<…>`
- **Budgethouder:** `<…>` — `<dekkingslogica, bijv. sluitende grondexploitatie>`

---

## 3. Middelen & operationele capaciteit

`<beschikbare mensen, kennis, tools, data-infrastructuur — of: bewust n.v.t. in canvasfase + reden>`

## 4. Governance

`<verantwoordelijkheden, besluitvorming, samenwerking tussen partijen; escalatielijnen — verwijst door naar §10 (besluitmomenten)>`

## 5. Business-/valuecase

`<verwachte kosten, baten, maatschappelijke waarde van datagedreven samenwerken in dit gebied>`

## 6. Kaders

`<wet- en regelgeving, beleidsdoelen, organisatorische randvoorwaarden (bijv. omgevingswet-instrumenten, EU-taxonomie, WKP, gebiedsprogramma's)>`

---

## 7. User stories

Één blok per use-casethema (Schiehaven had er twee: CO₂ en hitte). Vast format:

### Use-casethema `<naam>` *(Schiehaven: CO₂-budget, CO₂-consumptie, koele plekken, koele routes, buurteffect hittestress)*

| Veld | Invulling |
|---|---|
| Als | `<rol>` |
| Wil ik | `<inzicht/handeling>` |
| In/op | `<digitaal device, zonder specifieke software>` |
| Zo dat | `<besluit dat erdoor mogelijk wordt>` |
| Tijdens | `<processtap uit §10>` |
| Door | `<mechanisme, bijv. BIM-modellen koppelen aan LCA-rapportage>` |

---

## 8. Van user story naar data (de spil van de PoC-voeding)

Per use-casethema invullen:

| Inzicht (wat moet zichtbaar worden) | Informatie + LOIN-niveau *(ISO 19650: geometrie/dimensie/locatie/voorkomen/identificatie/informatie-inhoud)* | Indicator (§9) | Data (§8.1, verwijzing) |
|---|---|---|---|
| `<bijv. hoeveel CO₂ consumeert het ontwerp>` | `<objecten + detailniveau + leveringsmijlpaal>` | `<kg CO₂-eq/m² BVO>` | `<ontwerp-IFC + NMD-kengetallen>` |

### 8.1 Vijf datasoorten (altijd alle vijf duiden)

1. **Ontwerpdata** — nieuwe situatie per objectgroep: `<2D DXF (buitenruimte, NLCS-laagnamen) en/of 3D IFC (gebouwen); leverende partij per asset>`
2. **Bestaande data** — bestaande situatie ín het plangebied + invloedsgebied eromheen: `<BGT, BAG, 3D Basisvoorziening/3DBAG, AHN, bomen (3D Rotterdam of BGT), …>`
3. **Metadata** — herkomst, nauwkeurigheid, kwaliteit, actualiteit: `<DCAT-AP-NL voor datasets & rekenmodellen; PROV-O + logboek dataverwerking (OpenTelemetry) voor berekeningen>`
4. **Rekenmodellen** — welke modellen, aannames, parameters: `<model zelf of logging + documentatie; algoritmeregister-verwijzing>`
5. **Contextdata** — `<plangebied, buffer/invloedsgebied (bijv. 500 m), bounding box; als GeoJSON met CRS + als bbox-coördinaten voor API-gebruik>`

---

## 9. Indicatoren & rekenmodellen

| Indicator | Betekenis | Norm / drempel | Rekenmodel + standaard | Eigenaar model | Validatie |
|---|---|---|---|---|---|
| `<kg CO₂-eq per m² BVO>` | `<CO₂-intensiteit ontwerp; vergelijkt varianten>` | `<Paris Proof grens>` | `<LCA-instrument erkend door Nationale Milieudatabase; DGBC-protocol>` | `<ontwerpconsortium / gemeente>` | `<V3 onafhankelijke herberekening>` |
| `<% CO₂-budget benut>` | `<blijft het ontwerp binnen de CO₂-ruimte>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `<gemiddelde PET>` | `<ervaren temperatuur>` | `<…>` | `<RIVM standaard stresstest hitte>` | `<…>` | `<…>` |
| `<zoekgebied koele plekken / schaduw aandeel looproutes>` | `<verkoeling beschikbaar & bereikbaar>` | `<≥200 m² binnen 300 m; ≥40% schaduw>` | `<schaduwberekening op ontwerp-3D + bestaande omgeving>` | `<…>` | `<…>` |

---

## 10. Informatieproces & besluitvorming

- **Referentieproces:** `<gemeentelijk besluitvormingsmodel + openbare-ruimteplanproces (Schiehaven: BRO + ORP), uitgewerkt in BPMN>`
- **Relevante fase(n) voor deze PoC:** `<bijv. masterplanfase: onderzoeken → ruimtelijke analyse → scenario's/varianten → iteratief "tekenen en rekenen" → voorkeursmodel → masterplandocument>`
- **Subprocessen per use-casethema:** `<bijv. advies klimaatmitigatie (budget opstellen, consumptie berekenen), advies klimaatadaptatie (hittestress, neerslag, …)>`

| Processtap | Wie voert uit | Wie beslist / besluitmoment | Inzicht dat nodig is (→ §8) |
|---|---|---|---|
| `<…>` | `<…>` | `<…; besluit op totaal masterplan ligt bij de raad; escalatie via AMT→DMT→…>` | `<…>` |

---

## 11. Datadrops & levering (ILS-raamwerk)

- **ILS/IDS:** `<naam van de specificatie; open formaten: IFC ≥4.3 voor 3D, DXF + NLCS voor 2D; CRS EPSG:28992 (+NAP); verwijzing IDS-bestand>`
- **Rolverdeling contract:** gemeente levert **ILS + informatieprotocol**, opdrachtnemer antwoordt met **BUP (BIM Uitvoeringsplan)**.
- **Datadrops:**

| Drop | Moment | Inhoud | Vorm |
|---|---|---|---|
| 1 | `<start masterplanfase>` | gebiedsdata + omgevingsdata/afspraken basisregistraties + ILS + protocol | `<file>` |
| 2…n | `<tussentijds, variant-toets>` | submodellen tegen aparte deel-ILS | `<file>` |
| eind | `<einde masterplanfase>` | totaaldossier: ontwerpmodellen + rekenmodellen + omgeving + metadata | `<ICDD-container>` |

- **Levervorm-traject:** file → **ICDD-container (aanbevolen tussenfase)** → API-levering (doelbeeld; vereist formele/materiële historie, logboek dataverwerking en algoritmeregister — noteer hier de actuele knelpunten).
- **Bekende knelpunten/API-beperkingen:** `<bijv. geen historische bevraging, datetime werkt niet op alle endpoints — incl. bevraagtijdstip vastleggen>`

---

## 12. Functionaliteiten

`<simuleren · analyseren · rekenen · visualiseren — per use-casethema duiden welke nodig is>` — landen als OGC Processes (rekenen) en view-tier (visualiseren) in de PoC (Annex A).

## 13. Prototyping & architectuurbesluiten (ADR's)

Vier ADR's als standaard startset (overgenomen uit Schiehaven-Noord, per gebied herbevestigen of vervangen):

1. **ADR-raamwerk** — architectuurbesluiten worden vastgelegd als ADR's (lichter dan PSA).
2. **NLDT-referentiearchitectuur volgen** — open standaarden tussen systemen; geen gesloten consortium-oplossing.
3. **Ontwerpkant is black box; alleen het koppelvlak standaardiseren** — scheiding data/visualisatie/rekenen binnen de gemeente; open standaard als uitwisselingscontract.
4. **Validatie-vorm van berekeningen** — `<kies: (a) ruwe data + algoritme + aannames = exact herrekenen, (b) gemeente stelt rekenmodule, (c) uitkomst + aannames-documentatie + basisdata>` *(Schiehaven koos c)*.

Architectuurschetsen: **huidig** · **gewenst/haalbaar** · **toekomst/wenselijk** — `<verwijzing of beschrijving>`.

## 14. Interoperabiliteit & standaarden

| Domein | Standaarden |
|---|---|
| BIM | `<IFC, IDS, …>` |
| Geo | `<CityGML/CityJSON, NEN3610, IMGeo/MiniGIM, …>` |
| Uitwisseling | `<ICDD, OGC API's, DXF, NLCS>` |
| Metadata | `<DCAT-AP-NL, PROV-O, logboek dataverwerking/OpenTelemetry>` |
| Proces | `<BPMN, Use Case Canvas, LOIN, ISO 19650>` |
| Architectuur | `<ADR, NLDT-RA>` |

## 15. NLDT-referentiearchitectuur & inkoop

Standaard aanbestedingsparagraaf (kant-en-klaar overnemen uit het Schiehaven-rapport §17): opdrachtgever hanteert de NLDT-RA als richtinggevend kader; inschrijvers tonen aan: modulaire/uitbreidbare architectuur, open standaarden voor data/interfaces/semantiek, ondersteuning koppeling/interoperabiliteit met andere tweelingen, aandacht governance/security/privacy/datatoegang conform publieke waarden.

## 16. Conclusie & lessen (achteraf invullen)

`<wat werkte, wat niet, wat hergebruikt het volgende gebied>`

---

## Bijlagen (verplichte structuur bij de PoC)

- **Bijlage 1 — LOIN per object:** per objecttype tabel *waarom/wanneer/wie/wat/hoe* (doel · informatie-actor · object · decompositie · leveringsmijlpaal · geometrische detail · dimensie · locatie/CRS · voorkomen · identificatie · informatie-inhoud · documentatie).
- **Bijlage 2 — API-calls:** per bron de exacte GET (bbox + bbox-crs + datetime), bevraagtijdstip, en respons-snippet (byte-exact bewaren voor reproduceerbaarheid).
- **Bijlage 3 — Processes-specs:** per rekenstap inputs/process/output als OGC API Processes JSON (shadow-calculation, CO₂-calculation, …).
- **Bijlage 4 — File-voorbeelden:** minimale IFC/DXF-voorbeeldfiles conform de ILS.
- **Bijlage 5 — ICDD-containerlayout:** `BIM/ · IDS/ · GEO/{2D,3D,Context}/ · Metadata/ · Reports/ · Scripts/ + Linkset.rdf + Index.rdf`.
- **Bijlage 6 — PROV-O & logboek:** voorbeeld-triple-set + OpenTelemetry-spans per verwerking.

---

## Annex A — Canvas → nLDT PoC-machinery (waarmee het sjabloon de PoC voedt)

| Canvas-element (boven) | Wordt in de PoC | Waar |
|---|---|---|
| Contextdata plangebied/buffer/bbox | contextlagen in de engine-cache (dual-CRS 28992/4326) + `silver/<gebied>/context/` | `poc-<gebied>/data/` · lake |
| Bestaande data (BAG/BGT/3DBV/AHN/…) | registry-entries met rol `inclusion/exclusion/conditional/context/aoi` + fetch-manifest (URL+params, sha256, tijdstip = Bijlage 2) | `poc-<gebied>/data/sources.json` · `nldt/17` source monitor |
| Ontwerpdata (IFC/DXF) | parse-stap als OGC Process (ifcopenshell/ezdxf) achter een recipe-step; ILS/IDS-check als V0-poort op intake | `nldt/services/process_adapter/` · recipe |
| Datadrops 1…n + einddossier (ICDD) | `bronze/<gebied>/drops/<ts>/` met containermanifest; hergebruik in volgende fase | lake bronze · `nldt/13` |
| User stories | recipe-input + use-case-config per use-casethema; processtap-koppeling wordt orchestratievolgorde | `nldt/recipes/<gebied>-<usecase>.json` |
| Indicatoren & rekenmodellen | rekenmodellen als Cook-processes (processId `<gebied>-<indicator>`); LLM-genen alleen achter seams (S1/S2/S7/S8) | `nldt/04` · `GENAI_SEAMS.md` |
| Informatieproces + besluitmomenten | HITL-punten (V4) op de besluitmomenten uit §10; PDCA = Plane B sweeps + monitor | `nldt/12` · V0–V4 (`SOLUTIONS_ARCHITECTURE` §7) |
| Varianten "tekenen en rekenen" | **Plane B** scenario-sweeps (provenance-basis `policy_variant`) en **Plane D** gebiedsafweging (spatial claims tegen meerdere waarden, Breda-patroon) | `nldt/11` |
| Metadata (DCAT/PROV/logboek) | DCAT-record in catalog + PROV-bundle per run (algoritme → run → artefact) | `catalog_adapter` · PROV per run |
| Functionaliteiten visualiseren | single-file HTML-rapport per run + simulatie-hub-route `?poc=<gebied>` | `nldt/simulation/` |
| ADR's + architectuurschetsen | ontwerpdocumenten naast de PoC; koppelen aan NLDT-RA-mapping | `docs/` · `nldt/02` |
| Ethische afwegingen + gelijkheid (§1.3) | expliciete indicator-verdeling in het afwegingsrapport (wie krijgt de koele plek) | Plane D-rapport |

**Doctrine (onveranderd):** *AI stelt voor · rekenlaag beslist · mens beslist* — elk getal in een gebiedsrapport moet herleidbaar zijn naar brondata (Bijlage 2) + rekenmodel (§9) + PROV. Dit sjabloon voedt PoC's die de lagen van de RI-Geo-landschapsplaat ([`SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md) §3.5) voor één gebied concretiseren.

## Annex B — Definition of Ready (PoC-start pas als alles aanstaat)

- [ ] Opdrachtgever, eigenaar vraagstuk en budgethouder benoemd (§2).
- [ ] Minstens twee user stories, elk met indicator + norm (§7, §9), getoetst door domeindeskundige.
- [ ] Plangebied + invloedsgebied (buffer, m) als GeoJSON (EPSG:28992) én bbox-coördinaten vastgelegd.
- [ ] Per databron: URL/formaat/licentie/bevraagtijdstip geregistreerd (Bijlage 2 begonnen).
- [ ] Per indicator: rekenmodel + standaard benoemd, óf expliciet open seam ("nog geen gevalideerd model").
- [ ] ILS-minimum aanvaard door ontwerppartij: open formaten (IFC/DXF), CRS + NAP, NLCS/MiniGIM-classificatie.
- [ ] Besluitmomenten + beslissers bekend; elk wordt HITL-punt (V4) in de PoC.
- [ ] ADR-startset (§13) herbevestigd per gebied.
- [ ] Validatievorm van berekeningen gekozen (ADR 4) en in §9-kolom "Validatie" doorgevoerd.
