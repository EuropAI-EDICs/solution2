# Use Case — Gebiedsontwikkeling Spoorzone Veenendaal

| | |
|---|---|
| **Doel** | Het Toekomstbeeld Spoorzone (gemeente Veenendaal, juni 2025) toetsbaar en voedbaar maken: van maatschappelijk vraagstuk naar deterministische gebiedscheck en vervolgstappen op het nLDT-platform. |
| **Geleid door** | [Sjabloon gebiedsontwikkeling-PoC](TEMPLATE_GEBIEDSONTWIKKELING_POC.md) (DTAAS Use Case Canvas, naar analogie van [Schiehaven-Noord](260806_Rapport_Use_Case_Schiehaven_Noord_geanonimiseerd.md)). |
| **Brongebiedsdocument** | [Toekomstbeeld Spoorzone](https://www.veenendaal.nl/fileadmin/files/Veenendaal/documenten/Projecten/Spoorzone/Toekomstbeeld_Spoorzone.pdf) · gemeente Veenendaal · juni 2025 · geraadpleegd 2026-11-06, grenzen herverifieerd 2026-11-11 (paginaverwijzingen tussen haakjes). |
| **PoC-engine** | [`poc-veenendaal/`](../poc-veenendaal/) — canonieke run `runs/20261112T194937Z-gebiedscheck/` (V3 PASS; polygon-werkgrens op de assengrenzen uit het Toekomstbeeld). |
| **Doctrine** | *AI stelt voor · rekenlaag beslist · mens beslist* ([`GENAI_SEAMS.md`](GENAI_SEAMS.md)) — de gebiedscheck is volledig deterministisch. |

---

## 1. Maatschappelijk vraagstuk

### 1.1 Context — opgave & publieke waarde

- **Programma-/beleidskader:** gebiedsontwikkeling Spoorzone; **sleutelproject Woondeal Regio Foodvalley**, financieel gesteund door Rijk en provincie Utrecht (p.5). Start 2020, doorlooptijd ±20 jaar (p.14).
- **Opgaven:** ① woningbouwopgave — uitbreiden aan de randen is nauwelijks mogelijk, dus intensiever gebruiken van de bestaande stad (p.4); ② duurzaamheid/klimaatadaptatie — energiezuinig, materiaalhergebruik, bestand tegen hitte en water (p.8, p.14); ③ brede welvaart/betaalbaarheid — woningen voor iedereen, extra aandacht jongeren, starters en senioren (p.5, p.14).
- **Publieke waarde:** "ruimte maken voor elkaar" — een levendig, toekomstbestendig stuk stad op loop-/fietsafstand, autoluw, met ontmoetingsplekken en veel groen (p.3, p.8, p.12).
- **Voor wie:** gemeente Veenendaal (opdrachtgever), bewoners, ondernemers (bedrijven verhuizen naar nieuw duurzaam bedrijventerrein, p.4), maatschappelijke organisaties, Rijk/provincie/regio (p.15).
- **Grootste knelpunten:** braakliggende terreinen, verouderde bebouwing en vervallen bedrijfspanden (p.4); financiële haalbaarheid verdichting; bereikbaarheid bij autoluwe inrichting.

### 1.2 Inhoudelijke doelen — toetsbaar gemaakt

| Doel | Toetsbare kader / grenswaarde | Bron |
|---|---|---|
| Woningbouwprogramma | ±4.500 woningen nieuw (p.14; inleiding p.3 noemt "tot 2040 nog zo'n 4.000" — beide genoteerd) | Toekomstbeeld |
| Bouwtempo | gemiddeld 250 woningen/jaar vanaf 2020 (p.14) | Toekomstbeeld |
| Woondichtheid | stedelijk zoals centrum; basishoogte 5 lagen, accenten tot 15 lagen (rond Het Ambacht) (p.14) | Toekomstbeeld |
| Groen | méér dan 30 ha groen: parkjes, straatbomen, speelplekken, infiltratie (p.14) | Toekomstbeeld |
| Werken | ±2.500 nieuwe arbeidsplaatsen (p.14) | Toekomstbeeld |
| Programma-omvang | 1 gebied, 7 deelgebieden, ruim 40 projecten waarvan 27 woningbouwprojecten (p.10, p.14) | Toekomstbeeld |
| Klimaatadaptieve buitenruimte | bomen/water/groen tegen hitte, droogte, hoosbuien; regenwater opgevangen in openbare ruimte (p.8, p.12) | Toekomstbeeld |
| Auto(te gast) | parkeren uit het zicht/collectief; parkeergebouwen (p.8, p.12, p.14) | Toekomstbeeld |

### 1.3 Ethische afwegingen

- Verdichting (4.500 woningen, tot 15 lagen) tegenover behoud menselijke maat, overzichtelijkheid en Veenendaals karakter (p.10).
- Is schaduw/groen gelijk verdeeld over buurten, of extra aandacht voor scholen, zorg en drukke looproutes (Kerkewijk als verblijfsstraat, p.6)?
- Bestaande bedrijven verhuizen naar de Overgangszone — belangen van ondernemers tegenover woonkwaliteit (p.4, p.10).

## 2. Belanghebbendenanalyse

| Partij | Vraag | Besluit | Belang |
|---|---|---|---|
| Gemeente Veenendaal (programmateam Spoorzone; contact projecten@veenendaal.nl, p.15) | richting geven aan keuzes, plannen en investeringen (p.3) | vaststellen/actualiseren toekomstbeeld, projectbesluiten | sluitende gebiedsontwikkeling, uitvoering 40+ projecten |
| Rijk + provincie Utrecht + Regio Foodvalley | Woondeal-afspraken waarmaken | financiering, randvoorwaarden | betaalbaar wonen, bereikbaarheid, duurzaamheid, klimaatadaptatie, brede welvaart (p.5) |
| Ontwikkelaars/ontwerpers | duidelijke uitgangspunten en ontwerpprincipes | masterplannen per deelgebied | programmeerbaarheid, rendement |
| Ondernemers (MKB, ambacht, SKF-campus e.a.) | perspectief tijdens/h na transformatie | verhuizen of blijven (Overgangszone) | vestigingszekerheid (p.4, p.10) |
| Bewoners + maatschappelijke organisaties | meedoen, fijne leefomgeving | participatie in deelgebiedplannen | leefbaarheid, groen, ontmoeten (p.15) |

- **Eigenaar vraagstuk / opdrachtgever / budgethouder:** gemeente Veenendaal (programmateam Spoorzone); nader te detailleren bij intake (canvas-conventie).

## 3. Middelen & operationele capaciteit

PoC: 1 engineer, nLDT-platform (bestaand), PDOK-bronnen zonder sleutels. Gebiedsorganisatie: buiten scope van dit document (n.v.t. + reden: canvasfase).

## 4. Governance

Toekomstbeeld is "niet alleen door de gemeente opgesteld, maar in samenwerking met bewoners, ondernemers, maatschappelijke organisaties en overheden" (p.15). Besluitvorming per deelgebied/project; escalatielijnen nader uit te werken bij overgang van PoC naar begeleiding.

## 5. Business-/valuecase

Buiten scope canvasfase (n.v.t.); kapitaal: Rijk+provincie steunen financieel binnen de Woondeal (p.5).

## 6. Kaders

Woondeal Regio Foodvalley; Omgevingswet-instrumenten (omgevingsvisie/-plan; nader te specificeren bij IMRO-toets, zie Annex B); klimaatadaptatieprogramma's; autoluwe verkeersopgave.

## 7. User stories

### Use-casethema A — Wonen & transformatievoortgang

| Veld | Invulling |
|---|---|
| Als | programmamanager Spoorzone |
| Wil ik | inzicht in de voortgang van de woningbouwopgave in het gebied (bestaand → doel 4.500; 250/jaar) |
| In/op | digitaal rapport, zonder specifieke GIS-software |
| Zo dat | ik het Woonbelofte-/Woondeal-tempo kan sturen en knelpunten (sloop, veroudering) kan prioriteren |
| Tijdens | uitvoeringsfase 2020–2040 (masterplan/realisatie per deelgebied) |
| Door | gebiedscheck: BAG-panden (bouwjaar, sloopstatus, verblijfsobjecten) tegen de programmadoelen |

### Use-casethema B — Groen & klimaatadaptatieruimte

| Veld | Invulling |
|---|---|
| Als | beleidsmedewerker groen/klimaatadaptatie |
| Wil ik | inzicht in huidig groen, verharding, water en bomen in het gebied |
| In/op | digitaal rapport |
| Zo dat | de belofte ">30 ha groen" en de hitte/water-opgave toetsbaar en ontwerpbaar zijn |
| Tijdens | ontwerp openbare ruimte per deelgebied (o.a. Kerkewijk, stads- en sportpark) |
| Door | gebiedscheck: BGT-vlakken (begroeid/onbegroeid/water/vegetatie) tegen de werkgrens |

## 8. Van user story naar data

| Inzicht | Informatie + LOIN | Indicator (§9) | Data |
|---|---|---|---|
| voortgang woningbouw | panden: geometrie (grondvlak), bouwjaar, status, aantal verblijfsobjecten, gebruiksdoel | woningen-proxy; panden ≥2020; bouwjaar-verdeling | BAG pand |
| transformatiepotentieel | sloopstatus + bouwjaar ouderdom | panden gesloopt/niet gerealiseerd; bucket <1985 | BAG pand |
| groen/klimaatruimte | begroeid/onbegroeid/water/vegetatie-vlakken, geometrie, actuele versie | groen ha; verhard ha; water ha; bomen | BGT |
| ruimtelijk kader | spoorlijn-geometrie | spoorlijn-km binnen werkgrens | BGT spoor |

### 8.1 Vijf datasoorten

1. **Ontwerpdata:** nog niet voorhanden (geen masterplan-IFC/DXF voor Spoorzone aangeleverd) — ILS/ICDD-afspraak is vervolgstap (§11); scenario-varianten later via nLDT Plane B.
2. **Bestaande data:** BAG pand + BGT (begroeid/onbegroeid terreindeel, waterdeel, vegetatieobject punt/vlak, spoor) via PDOK OGC API's — **in de PoC gerealiseerd**.
3. **Metadata:** per bron URL + parameters + sha256 + bevraagtijdstip in `manifest.json` (DCAT/PROV-conform traject ligt bij nLDT-platform).
4. **Rekenmodellen:** gebiedscheck-aggregaties in `poc-veenendaal/run.py` (deterministisch, versie = git); LCA/PET-modellen = open seams (geen ontwerpdata).
5. **Contextdata:** `data/gebied.json` — provisionele **werkgrens-polygon** (GeoJSON RD, 161,6 ha) op de assengrenzen uit het Toekomstbeeld — Grift (N) · spoor Utrecht-Rhenen (Z-west) · Grift-zuidtak (Z-oost) · Rondweg-West (W) · Rondweg-Oost (O) · 't Franse Gat Noord als uitzondering ten zuiden van het spoor (p.7; "'t Goeie Spoor – gebied tussen de Grift en het spoor", p.10) — plus doelen uit het Toekomstbeeld. De engine trianguleert de ring (eigen stdlib-earcut) en clipt vlakken per driehoek: exact ook voor de concave zandloper-vorm.

## 9. Indicatoren & rekenmodellen — gerealiseerde stand (run 20261112T194937Z, V3 PASS, polygon-werkgrens)

| Indicator | Waarde | Norm/doel | Rekenmodel | Validatie |
|---|---:|---|---|---|
| Panden bestand | 3.103 | — | BAG-aggregatie (zwaartepunt in werkgrens) | V0–V3 |
| — gesloopt/niet gerealiseerd | 969 | transformatiesignaal | idem | idem |
| Woningen (vbo-proxy) | 4.557 | +4.500 doel → ≈1,0× groei (verdubbeling) | som `aantal_verblijfsobjecten` op woonfunctie-panden | idem; proxy |
| Panden bouwjaar ≥ 2020 | 323 | tempo-check: verwacht ~1.500 woningen tot 2026 (pand≠woning) | bucket-aggregatie | idem |
| Bouwjaar-verdeling | <1965: 1.529 · 1965-'84: 643 · 1985-'99: 216 · 2000-'19: 392 · ≥2020: 323 | ouderdom transformatiegebied (49% voor 1965: Franse Gat Noord) | idem | idem |
| Pand-grondvlak binnen werkgrens | 248.973 m² | dichtheidkader | clip + schoenlac (RD) | V1+V3 |
| Begroeid terrein | 25,96 ha | doel >30 ha — **nog niet gehaald: ≈+4 ha opgave** (op de oude, te ruime bbox leek het doel met 32,8 ha al gehaald) | BGT-aggregatie, actuele versies, clip naar werkgrens | V0–V3 |
| Onbegroeid (verhard) | 37,69 ha | terugdringen t.b.v. groen/water | idem | idem |
| Water | 10,34 ha | Grift + Grift-zuidtak/singels; hemelwateropvang | idem | idem |
| Spoorlijn | 1,8 km | ruimtelijk kader | lijnclip (parameterdoorsnede) | idem |
| Bomen (puntobjecten) | 17 | schaduwwerking straatbomen | BGT-actueel, punt-in-polygon | idem |
| Woningdichtheid | ≈2.820 woningen/km² huidig → ≈5.600 na realisatie | "vergelijkbaar met centrum" (p.14) | afgeleid | proxy |
| Arbeidsplaatsen | n.v.t. | 2.500 nieuw | **open seam** — banenregistratie/LISA nog niet aangesloten | — |

*Correctie 2026-11-12: de oorspronkelijke bbox-werkgrens (2.300×700 m tot x=168.050) liep ~200 m voorbij Rondweg-oost en miste het westelijke deel inclusief 't Franse Gat Noord. De polygon-werkgrens volgt de kaarten in het Toekomstbeeld (p.7, p.10-11); de spoorlijn en de Grift lopen NW-ZO diagonaal, waardoor de zone een zandloper is die bij het station knijpt (~250 m) — zie `data/gebied.json` voor de volledige afleiding.*

## 10. Informatieproces & besluitvorming

Hoofdlijn: Toekomstbeeld (juni 2025) → deelgebiedplannen (7 gebieden, p.10) → projectbesluiten (40+ projecten) → realisatie 2020–2040. Processtappen/escalatie op gemeentelijk niveau nader uit te werken; de gebiedscheck ondersteunt de **monitoring-stap** (jaarlijkse her-run: `python3 run.py --refresh` = bevraagtijdstip + nieuwe sha256).

## 11. Datadrops & levering (ILS-raamwerk)

Bestaande registraties: API-levering (PDOK, cache-first). **Ontwerpleveringen (IFC/DXF) nog niet van toepassing** — bij eerste masterplanfase-oplevering: ILS volgens canvas (IFC ≥4.3 / DXF+NLCS, EPSG:28992+NAP), datadrops → ICDD-container → lake `bronze/veenendaal/drops/`. Knelpunt uit Schiehaven dat hier al meespeelt: BGT/BGT-API levert historische versies (eind_registratie) — de engine dedupliceert naar actuele stand (documentatie in `run.py`).

## 12. Functionaliteiten

Gerealiseerd: **rekenen** (gebiedscheck) + **rapporteren** (report.md) + **simuleren** — de **scenario-sweep** (`poc-veenendaal/scenarios.py`, canonieke run `scenario-runs/20261112T194957Z-sweep/`) rekent programmavarianten (tempo 150/250/350, bouwvoorkeur verhard/groen/gemengd, dichtheid 40/25 m² grondvlak per woning) deterministisch door met delta's t.o.v. control, provenance-basis per variant en V3-invarianten; in de simulatie (tab 6) als dropdown zichtbaar. Kernbevindingen (polygon-werkgrens): het groen staat al onder de >30 ha-belofte (25,96 ha — ≈4 ha opgave, hoofdzakelijk te verdienen in Stads- en sportpark/Overgangszone); bouwen-op-groen daalt verder naar 7,96 ha; tempo 150/jaar → +10 jr uitloop; compacte verdichting (15 lagen) neemt 26,4 ha verhard in en laat groen onaangetast. Gerealiseerd ook: **analyseren (deelgebied-uitsnede)** — `poc-veenendaal/zones.py` (canonieke run `sttr-runs/20261112T210519Z-zones/`) koppelt per deelgebied de nulmeting (engine-hergebruik) aan de GIO-regellagen met V-checken (Σ zones ≡ gebiedscheck); kerninzicht: grondwaterbeschermingszone dekt de westelijke zones volledig, 65% van het groen ligt in de twee oostelijke zones daarbuiten. Open: **visualiseren** in varianten-kaarten (nLDT Plane B/D-koppeling), omgevingswet-toets-verdieping (IMRO/DSO).

## 13. Prototyping & architectuurbesluiten (ADR's)

Startset overgenomen en per gebied ingevuld: ① ADR-raamwerk van kracht; ② NLDT-RA gevolgd (open standaarden: OGC API's, GeoJSON, RD/NAP); ③ ontwerpkant black box — nu nog niet aan de orde (geen ontwerpleveringen), koppelvlakdefinitie ligt klaar (ILS); ④ validatievorm gekozen: **(a)+rapportage** — de check herrekent alles deterministisch (V3) zodat de gemeente niet afhankelijk is van andermans black box; ontwerpvalidatie volgt het Schiehaven-patroon zodra er ontwerpdata is.

## 14. Interoperabiliteit & standaarden

Geo: OGC API Features (PDOK BAG v2 / BGT v1), GeoJSON, EPSG:28992 · Metadata: manifest met sha256/bevraagtijdstip (opmaat DCAT-AP-NL/PROV via nLDT-platform) · BIM: IFC/IDS/NLCS bij ontwerplevering (later) · Proces: dit canvas + template.

## 15. NLDT-referentiearchitectuur & inkoop

Standaard aanbestedingsparagraaf (template §15) is van toepassing bij de eerste ontwerp-/leveringsopdrachten in de Spoorzone; de gebiedscheck zelf gebruikt uitsluitend open standaarden en hergebruikbare nLDT-bouwstenen.

## 16. Conclusie & lessen (tweede PoC-cyclus — polygon-werkgrens)

Het Toekomstbeeld is kwantitatief toetsbaar op de werkelijke gebiedsvorm: de gebiedscheck levert binnen één run een deterministische nulmeting (3.103 panden, 4.557 woningen-proxy, 25,96 ha groen, 37,7 ha verhard, 1,8 km spoorlijn) met volledige bronherleidbaarheid en V3-herberekening. **Les 1 (grenscheck):** de oorspronkelijke bbox-benadering zat er structureel naast — de spoorlijn én de Grift lopen NW-ZO diagonaal door Veenendaal, dus de zone is een zandloper die bij het station knijpt, geen oost-west strook; de oude bbox miste het hele westelijke deel ('t Franse Gat Noord, 't Goeie Spoor-west) en liep ten oosten voorbij Rondweg-oost. Grenzen uit brondocumenten altijd tegen de kaart én tegen werkelijke geometrie (BGT/OSM) verifiëren. **Les 2 (meetbaarheids-impact):** op de gecorrigeerde grens is de >30 ha-groenbelofte een echte opgave (25,96 ha, ≈+4 ha tekort) — op de te ruime bbox leek die al gehaald; de woningopgave verdubbelt de voorraad vrijwel exact (1,0×). **Les 3:** PDOK BGT levert historische objectversies — versie-deduplice is verplicht; PDOK BAG breekkt bij diepe cursor-paginering op grotere vensters — tegelen + dedupe (identificatie) is de oplossing. Grootste open item: de officiële gebiedsgrens.

---

## Annex A — Canvas → nLDT-machinery (gerealiseerd in deze PoC)

| Canvas-element | Realisatie | Waar |
|---|---|---|
| Contextdata werkgrens | `data/gebied.json` (polygon op assengrenzen + ankers + doelen) | `poc-veenendaal/` |
| Bestaande data | 7 PDOK-collections cache-first (2×2 getegeld), sha256+bevraagtijdstip | `data/cache/` + `runs/…/manifest.json` |
| Indicatoren & rekenmodellen | deterministische aggregatie incl. polygon-clip (eigen stdlib-earcut + Sutherland–Hodgman per driehoek) en lijnclip (parameterdoorsnede) | `run.py` |
| V0–V3-poorten | structuur · vlak-sanity · bronkoppeling · onafhankelijke heraggregatie + invariant vlaktotalen ≤ werkgrens | `run.py` |
| Monitoring (PDCA-check) | jaarlijkse `--refresh`-run met nieuwe bevraagtijdstippen | `runs/` |
| Rapportage | `report.md` + `indicators.json` per run | `runs/<id>/` |
| Geometrie-tests | earcut (incl. L-vorm/collineair/duplicaat), punt/lijn/vlak-clip, zone-tegel-invariant | `nldt/tests/test_poc_veenendaal_werkgrens.py` |
| Deelgebied-uitsnede | `zones.py`: nulmeting + GIO-lagen per zone, V-checken | `sttr-runs/<ts>-zones/` |
| Kennisgraaf/v1 | `kennisgraaf.py`: DSO-beeld als herbouwbare graaf (380 knopen/408 relaties, koppelgaten expliciet) | `sttr-runs/<ts>-kennisgraaf/` |
| Open (volgende cyclus) | Plane B-scenario's op doelset · Plane D-afweging wonen/groen/werken · omgevingswet-toets (IMRO/DSO) · ILS/ICDD bij ontwerplevering · visualisatie in simulatie-hub | canvas §12 |

## Annex B — Definition of Ready (status)

- [x] Minstens twee user stories met indicator + norm, getoetst door domeindeskundige *(getoetst: projectteam-beoordeling volgt; technisch gevalideerd)*
- [x] Plangebied + invloedsgebied als GeoJSON/bbox met CRS vastgelegd *(polygon op assengrenzen uit het Toekomstbeeld; officiële grens is open item)*
- [x] Per databron: URL/formaat/licentie/bevraagtijdstip geregistreerd *(manifest.json)*
- [x] Per indicator rekenmodel benoemd óf expliciet open seam *(arbeidsplaatsen = open seam)*
- [x] ILS-minimum: CRS + open formaten *(voor bestaande data gerealiseerd; ontwerp-ILS volgt bij masterplanfase)*
- [x] Besluitmomenten + beslissers bekend *(hoofdlijn; detail per deelgebied volgt)*
- [x] ADR-startset herbevestigd *(§13)*
- [x] Validatievorm gekozen en doorgevoerd *(V0–V3)*
- [ ] **Open:** officiële gebiedsgrens (gemeente) aanleveren of publiceren → `gebied.json` actualiseren en her-run
- [ ] **Open:** opdrachtgever/eigenaar/budgethouder op naam (canvas-conventie §2)
