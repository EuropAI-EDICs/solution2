# Use cases

# gebiedsontwikkeling in

# Schiehaven Noord

## Geonovum

### Versie 1.0

### Status definitief

### Datum 23 juli 2026

> **Anonimiseringsvermelding:** In deze versie zijn persoonsnamen, e-mailadressen en bedrijfsnamen van consortiumpartijen vervangen door functiebenamingen of generieke partijen ("Ontwerpconsortium", "adviesbureau", "landschapsarchitecten").


## Samenvatting

Dit document beschrijft een use case voor het gebruik van een digitale tweeling services ter ondersteuning van duurzame gebiedsontwikkeling in Schiehaven Noord, Rotterdam. Om te komen tot de juiste Digitale Tweeling Service maakt Geonovum gebruik van het DTAAS Use case canvas. Het gebruik van het Use Case Canvas geeft gestructureerd in de specifieke toepassing van data en technologie. Allereerst is het maatschappelijk vraagstuk in beeld gebracht. Schiehaven Noord kent een woningbouwopgave, een betaalbaarheidsopgave en ook een duurzaamheidsopgave. Schiehaven Noord is een zogenoemde Paris Prooftuin waarin men onderzoekt of men binnen CO2ruimte en met voldoende koele plekken een gebiedsontwikkeling kan realiseren. Uitdaging hierbij is om voldoende woningen te kunnen realiseren, binnen het CO2budget en binnen de financiële haalbaarheid. Het projectteam gebiedsontwikkeling Schiehaven Noord samen met gemeentelijke adviserende partijen als het ingenieursbureau en het externe ontwerpconsortium geven met een masterplanontwerp antwoord op deze opgave. Naast randvoorwaarden voor het ontwerp heeft de gemeente Rotterdam ook behoefte aan afspraken voor data-uitwisseling. De gemeente wil data hergebruiken in vervolgstappen, inzicht krijgen in berekeningen en ontwerp en kunnen toetsen van berekeningen of deze reproduceren.

Samen met de gemeente Rotterdam zijn user stories opgesteld waarin men de specifieke behoefte of functionaliteit vanuit het perspectief van de gebruiker duidt. Ook zijn de functionaliteiten (capabilities) van een Digitale Tweeling hieraan toegevoegd. Deze user stories en functionaliteiten geven richting aan het van toepassing zijnde proces, de benodigde data en de gewenste architectuur. Op basis van de user stories zijn de gewenste inzichten beschreven en daaraan is gekoppeld welke informatie hiervoor nodig is. Er is gebruik gemaakt van het Level Of Information Need (LOIN) om het juiste informatieniveau te duiden. Vervolgens zijn de indicatoren die uiteindelijk het beeld moeten komen beschreven, zoals de hoeveelheid CO₂-eq per m² BVO of het zoekgebied voor koele plekken. Er zijn vijf soorten data geïnventariseerd die benodigd zijn om de gewenste inzichten te leveren. Dit zijn: Ontwerpdata (BIM-Modellen), bestaande assets data (GEO-modellen), rekenmodellen (scripts), metadata en contextdata (zoals Plangebied).

Verschillende bedrijfsbezoeken en interviews hebben plaatsgevonden waarbij Geonovum inzicht verkregen heeft in de werkwijze en mogelijkheden van het ontwerpconsortium. Op basis van dit inzicht is een keuze gemaakt in het soort data dat uitgewisseld kan worden tussen het ontwerpconsortium en de gemeente Rotterdam (BIM en/of GEO, 2D en/of 3D etc.). Er is voor open uitwisselformaat gekozen om software-onafhankelijk gebruik te kunnen maken van hetgeen geleverd is. Voor het gekozen open uitwisselformaat is een Informatie Levering Specificatie (ILS) geschreven. Deze ILS geeft restricties aan de inhoud van de data. Door levering conform deze ILS af te spreken geeft dit de gemeente Rotterdam de zekerheid dat de data die geleverd wordt de input kan zijn voor rekenmodellen en toekomstig (her)gebruik. Er is zowel een ILS voor 3D gebouwen in het open formaat IFC als een ILS voor 2D buitenruimte in het open formaat DXF in combinatie met NLCS classificatie geschreven. Naast specificaties voor het ontwerpmodel zijn er specificaties voor de contextdata, bestaande data en metadata beschreven.

Vervolgens geeft het document advies over de manier van datalevering. Het beschrijft een proces van datadrops in de tijd en beschrijft hoe file-levering, container-levering of API-levering in het project Schiehaven Noord ingezet zou kunnen worden. Momenteel is container-levering (conform ICDD) het hoogst haalbare. Aangezien dit een opmaat is naar API-levering, dat vele voordelen kent, wordt dit geadviseerd. Het document beschrijft de uitdagingen die er zijn voor API-levering en wat dit betekent voor landelijke ontwikkeling en ICT-ontwikkeling bij de gemeente Rotterdam.


De indicatoren en bijpassende rekenmodellen worden vervolgens beschreven. De functionaliteiten die uit de user stories naar voren komen, betreffen: simuleren, analyseren, rekenen en visualiseren. Het proces waarin de data en functionaliteit gebruikt dient te worden is in beeld gebracht met procesplaten conform BPMN. Ook zijn de beslismomenten in beeld gebracht.

De geleverde data dient voor de eindgebruiker inzichtelijk te zijn. Er is een referentiebeeld beschreven in het document hoe een prototype van een digitale tweeling eruit zou kunnen zien zowel in toekomstige visualisatie dashboard als in huidige mogelijkheden in 3D Rotterdam.

Vervolgens zijn een aantal architectuurbesluiten genomen op de gewenste functionaliteiten. Hiervoor is het ADR (Architectural Decision Records) Raamwerk gebruikt. De beslissingen die in dit raamwerk zijn genomen zijn uitgangspunt geweest voor het maken van drie architectuurschetsen. Eén architectuurschets van de huidige situatie, een architectuurschets van de gewenste haalbare situatie en een architectuurschets van de toekomstige meest wenselijke situatie.

De rapportage van de gebiesontwikkeling Schiehaven Noord eindigt met een beknopte beschrijving van de NLDT-referentiearchitectuur en geeft advies hoe in aanbestedingsdocumenten richting markpartijen hier ontwikkeling in te kunnen krijgen. Ten slotte volgt een conclusie waarin beschreven wordt welke manier van werken in Schiehaven Noord geadviseerd wordt. Deze eindrapportage wordt begeleid door fictieve voorbeeldmodellen van ontwerpdata, bestaande data, metadata, rekenmodellen en contextdata die de geadviseerde werkwijze illustreren.


## Inhoudsopgave

#### Inleiding 5

#### Use Case Canvas 6

1. Maatschappelijke vraagstuk 7

1.1 Context – maatschappelijke opgave & publieke waarde 7

2. Belanghebbendenanalyse motivaties, doelen en waarden 9

2.1 Belanghebbenden 9 2.2 Voor welke vragen zoeken zij een oplossing? 9 2.3 Welke beslissingen willen zij nemen? 10 2.4 Wat is voor hen belangrijk? 10 2.5 Wie is eigenaar van het vraagstuk? 10 2.6 Wie is opdrachtgever voor het oplossen? 10 2.7 Wie is budgethouder? 10

3. Belanghebbendenanalyse motivaties, doelen en waarden 10
4. Middelen en operationele capaciteit 10
5. Governance 11
6. Business/Valuecase 11
7. Kaders 11
8. User stories 12

8.1 Wat wil de gebruiker met de Digitale Tweeling kunnen? En wat wil de gebruiker daarmee bereiken? 12 8.2 Welke inzichten zijn nodig? 14 8.3 Welke informatie is nodig om tot deze inzichten te komen? 14 8.4 Welke indicatoren horen hierbij? 15 8.5 Welke data is nodig om deze informatie te genereren? En waar vinden we deze data? 15

9. User stories als verbinding naar de techniek 16
10. Databronnen 16

10.1 Welke data is nodig voor de gewenste inzichten/informatie? 16 10.2 Welke data requirements (ILS) 17 10.3 Informatie Levering 31

11. Indicatoren en rekenmodellen 34
12. Functionaliteiten 35
13. Informatieproces 35


13.1 Wat zijn de processtappen en besluitvormingsmomenten om tot een oplossing voor het vraagstuk te komen? 35 13.2 Wie neemt welke processtap en/of besluit? 40 13.3 Welke inzichten/informatie is daarbij nodig? 40

14. Prototyping 41

14.1 Hoe ziet voor de gebruiker(s) het prototype van de digitale tweeling eruit? 41 14.2 Welke functionaliteiten heb ik nodig voor de functionele architectuur 42

15. Concepten en modellen 46
16. Interoperabiliteit en standaarden 47
17. NLDT referentiearchitectuur 47
18. Marktanalyse en marktconsultatie 48
19. Conclusie 49

#### Bijlage 1 – Level of Information Need per object

#### Bijlage 2 – API Call BAG-PDOK

#### Bijlage 3 – Processes API

#### Bijlage 4 – file-uitwisseling

#### Bijlage 5 – ICDD voor file-uitwisseling

#### Bijlage 6 – API-overzicht

#### Bijlage 7 IDS

#### Bijlage 8 PROV-O en Open Telemetry


## Inleiding

Door oplopende rente en bouwkosten, nam de wethouder van Klimaat, Bouwen en Wonen enkele jaren geleden het initiatief tot het Doorbouwakkoord. Gemeente, vastgoedpartijen en bouwers maakten afspraken voor het zoveel mogelijk op peil houden van de woningproductie. Naast een financieringshobbel heeft woningbouwontwikkeling ook te maken met een duurzaamheidshobbel. Vanuit de EU zijn er nieuwe en verscherpte eisen op dit vlak, zoals de EU- Taxonomie. Met het oog daarop namen de gemeente Rotterdam en het Platform Ontwikkeling Rotterdam (POR) het initiatief tot het opstellen van het Plan van Aanpak (PvA) Duurzaam Doorbouwen. Dat is een nadere invulling van het Doorbouwakkoord.

Uitgangspunt van het Rotterdamse PvA Duurzaam Doorbouwen zijn de doelstellingen van de klimaatconferentie in Parijs. Paris Proof bouwen vraagt concreet om beperking van CO2-uitstoot van bouwmaterialen, circulaire ontwerpen en bouwen, emissieloos bouwen, en klimaatadaptieve

1

maatregelen in de gebouwde omgeving.

1 [https://www.ondernemen010.nl/actueel/interview-duurzaam-doorbouwen-in-rotterdam/](https://www.ondernemen010.nl/actueel/interview-duurzaam-doorbouwen-in-rotterdam/)


## Use Case Canvas

Bovenstaand beeld van de use case canvas is een werkversie.


1. Maatschappelijke vraagstuk

### 1.1 Context – maatschappelijke opgave & publieke waarde

Een tot een passende gebiedsontwikkeling te komen in Schiehaven Noord, waar de volgende uitdagingen spelen:

#### 1.1.0 Paris Prooftuin

De gebiedsontwikkeling Schiehaven Noord is een zogenoemde Paris Prooftuin. Vanuit deze gebiedsontwikkeling wil de gemeente lessen halen die antwoord geven op de manier waarop men binnen de CO2 ruimte die beschikbaar is kan bouwen. Deze antwoorden kunnen worden gebruikt in het duurzaam doorbouwen (Duurzaam doorbouwen | [www.rotterdam.nl](http://www.rotterdam.nl)) initiatief.

#### CO2

Wereldwijd is er aandacht voor uitstoot van broeikasgassen zoals CO₂. Teveel CO₂ leidt tot extremere weersomstandigheden die steeds frequenter voorkomen. Logisch dat er dat er dus veel aandacht is voor het terugdringen van onze uitstoot. Toch is dat niet de dagelijkse realiteit in gebiedsontwikkeling. We meten veel in gebiedsontwikkeling. Aantallen woningen, parkeerplaatsen, stikstofuitstoot, kosten en opbrengsten, verkeersstromen, groenpercentages, enzovoort. Als vakgebied zouden we een stap moeten zetten en ook aandacht gaan besteden aan CO₂-uitstoot die gevolg is van onze beslissingen. Beslissingen in gebieden hebben immers grote gevolgen voor de lange termijn.

#### Hitte

De impact van klimaatverandering groeit. Gezien de steeds extremere en frequentere weersomstandigheden is Rotterdam zich bewust dat zij maatregelen moeten nemen ter voorkoming van nadelige gevolgen hiervan. Rotterdam zet zich in voor klimaatadaptatie en heeft sinds begin 2026 het ‘Water- en KlimaatadaptatieProgramma (WKP)’ vastgesteld. Gezondheidsproblemen, kans op overlijden en, lage arbeidsproductiviteit

Mitigatie, voorkomen van het probleem. Adaptatie [https://rotterdamsweerwoord.nl/content/uploads/2025/10/Water-en-Klimaatadaptatie-](https://rotterdamsweerwoord.nl/content/uploads/2025/10/Water-en-Klimaatadaptatie-) Programma.pdf

#### 1.1.1 Welke maatschappelijke opgave ligt aan het vraagstuk ten grondslag?

- Woningbouwopgave
- Duurzaamheid
- Betaalbaarheidsopgave

#### 1.1.2 Welke maatschappelijke waarde willen we realiseren?

Een fijne leefomgeving realiseren voor bewoners en andere betrokkenen op de korte en lange termijn.

#### 1.1.3 Voor wie is het vraagstuk?

Voor de gemeente en de uiteindelijke betrokkenen in Schiehaven Noord. Gezamenlijkheid met de markt, kennisinstellingen en de corporaties. (geleerde lessen)

#### 1.1.4 Wat zijn de grootste knelpunten?

Financiële en duurzame haalbaarheid icm (ruimtelijke) beperkingen voor bouwen.


#### 1.1.5 Wat zijn onze inhoudelijke doelen?

- Voldoende gebouwen/woningen: voldoende inkomsten om het project financieel haalbaar te laten zijn. CO2 Budget – Binnen de CO2 Grenswaarden: als we deze aanhouden, hoeveel kunnen we dan bouwen binnen het gestelde budget?
- Klimaat adaptieve buitenruimte: voldoende ‘koele plekken’ met een minimale grootte van 200 m2 en beschaduwing op maximaal 300m1 van de woning. Voldoende koele paden en straten met voldoende schaduw (40%).

#### 1.1.6 Welke ethische afwegingen worden gemaakt om tot een oplossing te

#### komen?

Voor de use-case over CO2 is de achterliggende ethische afweging om tot een oplossing te komen:

Hoeveel mag de huidige generatie investeren of inleveren in CO2 ten gunste van toekomstige generaties? Extra investeren in energiezuinige gebouwen kan de bouwkosten verhogen, maar verlaagt toekomstige emissies.

Voor de use-case hitte is de achterliggende ethische afweging om tot een oplossing te komen:

Is schaduw gelijk verdeeld over het gebied? Moet iedere bewoner ongeveer dezelfde kwaliteit openbare ruimte krijgen? Of geef je extra aandacht aan scholen, zorgvoorzieningen en drukke looproutes?

2. Belanghebbendenanalyse motivaties,

## doelen en waarden

### 2.1 Belanghebbenden

De volgende belanghebbende zijn geïdentificeerd tijdens de gesprekken bij aanvang van het project. Hierbij is allereerst gekeken naar de direct betrokkenen bij de gebiedsontwikkeling Schiehaven Noord. Daarna zijn ook de andere (indirect) betrokkenen opgesomd.

- Gemeente Rotterdam: o Projectteam gebiedsontwikkeling (opdrachtgever SHN – masterplan):
- Projectleider 
- Beleidsmedewerkers Duurzaamheid 
- Bouwregisseur  o Ingenieursbureau (adviserende / toetsende rol)
- Beleidsmedewerkers CO2 
- Beleidsmedewerkers Hittestress  o Stadsbeheer
- Beleidsmedewerker CO2openbare ruimte  o Gebiedsexploitatie (GEX)
- Beleidsmedewerker Interne GREX ▪
- Ontwerpende partijen (opdrachtnemers) o het adviesbureau als aanleverende partij:
- parametrisch modelleur – wind geluid en energie 
- Architecten:  – maken wooneenheden parametrisch (carbon berekening gebouwen) 
- Stedenbouwer: woningen 3D model (volume studies uitgeefbaar gebied en openbare ruimte) 
- Landschapsarchitect
- Andere betrokken partijen o Geonovum (GeoBIM integratie) o Ministerie van BZK o Ecosysteem van Toepassingen o Weerwoord (Beleidmaker) Economie (Beleidmaker) 

### 2.2 Voor welke vragen zoeken zij een oplossing?

De voornaamste vraag die aanleiding is geweest, is de vraag: ‘Hoe kan de gemeente Rotterdam de ontwerpende partijen niet alléén randvoorwaarden meegeven waaraan het ontwerp (o.a. ruimtelijk & financieel) aan moet voldoen? Maar ook technische randvoorwaarden meegeven waaraan de data van het ontwerp moet voldoen, zodat de gemeente ook zelf het aangeleverde ontwerp kan gebruiken.

Daarnaast is tijdens de gesprekken met externen gebleken dat er ook in de samenwerking tussen hen behoefte is aan richtlijnen voor data. Zoals bijvoorbeeld rondom

georeferentie en structurering van laagnamen/objecten. Wanneer daar afspraken over gemaakt zijn kunnen deze partijen ook makkelijker samenwerken.

### 2.3 Welke beslissingen willen zij nemen?

Rotterdam: welke aanvullende (technische) randvoorwaarden kunnen wij in de toekomst toevoegen aan een uitvraag bij een duurzame gebiedsontwikkeling zoals Schiehaven Noord.

### 2.4 Wat is voor hen belangrijk?

Inhoudelijk: Hoe kan een gebiedsontwikkeling in goed eventwicht tussen:

- Woningbouwopgave
- Duurzaamheid
- Betaalbaarheidsopgave ontwikkeld worden.

Op data gebied: Rotterdam:

- Herbruikbaarheid van bestanden bij vervolgstappen in gebiedsontwikkeling.
- Inzicht hebben in uitgangspunten/aannames bij berekeningen met het ontwerp.
- Zelf toetsen/controleren van aannames bij bepaalde berekeningen. Reproduceren in andere software.

### 2.5 Wie is eigenaar van het vraagstuk?

De eigenaar van het vraagstuk is de gemeente Rotterdam. Gedelegeerd binnen de gemeente Rotterdam is de eigenaar van het vraagstuk de projectleider van het gebiedsontwikkelingsteam. De projectleider is verantwoordelijk voor het hele proces, van tot en met realisatie.

### 2.6 Wie is opdrachtgever voor het oplossen?

De gemeente Rotterdam is opdrachtgever voor het oplossen van het vraagstuk.

### 2.7 Wie is budgethouder?

De gemeente Rotterdam is budgethouder. De inspanning Schiehaven Noord is erop gericht om tot een sluitende grondexploitatie te komen (mogelijk met inzet van alternatieve dekkingsbronnen).

3. Belanghebbendenanalyse motivaties,

## doelen en waarden

Dit onderdeel van het Use Case Canvas brengt de belangen, motivaties doelen en waarden van de stakdeholders in kaart. Een nadere analyse hiervan valt buiten de scope van dit document.

4. Middelen en operationele capaciteit

Binnen het Use Case Canvas kan men de benodigde middelen, kennis en operationele capaciteit in beeld brengen. Deze aspecten worden in dit document niet verder uitgewerkt.

5. Governance

Governance betreft de inrichting van verantwoordelijkheden, besluitvorming en samenwerking tussen betrokken partijen. Dit onderwerp maakt onderdeel uit van het Use Case Canvas, maar wordt hier niet nader behandeld.

6. Business/Valuecase

De Business/Valuecase beschrijft de verwachte kosten, baten en maatschappelijke waarde van de voorgestelde maatregelen voor digitaal samenwerken. Hierbij kan worden gekeken naar zowel financiële aspecten als bredere effecten op leefbaarheid, gezondheid en klimaatbestendigheid. Een nadere uitwerking van deze afwegingen valt buiten de scope van dit document.

7. Kaders

Onder kaders vallen relevante wet- en regelgeving, beleidsdoelen en organisatorische randvoorwaarden. Deze worden erkend als onderdeel van het Use Case Canvas, maar niet afzonderlijk geanalyseerd in dit document.

8. User stories

### 8.1 Wat wil de gebruiker met de Digitale Tweeling kunnen? En wat

### wil de gebruiker daarmee bereiken?

Om een goed inzicht te krijgen in de informatiebehoefte van de gebruiker en de ondersteuning die nodig is om de werkzaamheden effectief uit te voeren, maken we gebruik van user stories. Deze vormen het uitgangspunt voor het gesprek over de gewenste functionaliteit, behoeften, verwachtingen en de toegevoegde waarde van de oplossing.

#### 8.1.0 User stories voor CO2

User story | CO2 – Budget opstellen

Als een Opdrachtgever (AOG) Wil ik Opdracht geven tot ontwikkelproces dat past binnen CO2 ruimte van de stad In/op In een opdrachtbrief met de juiste randvoorwaarden(spelregels), op een fysieke opgave Zo dat Projecten uitgevoerd worden in lijn met het klimaatakkoord (binnen CO2 budget) Tijdens Opstellen gebiedsambitiedocument, echter nu tijdens opstellen masterplan Door Voor gebouw en gebied de CO2-consumptie inzichtelijk te maken, voor zowel bestaande als nieuw. Processtap Gebiedsambitiedocument Thema

User story | CO2 – Consumptie berekenen van ontwerp

Als een Gemeentemedewerker adviseur duurzaamheid Wil ik Inzicht in de CO2-consumptie van ruimtelijk plannen In/op Een digitaal device, zonder specifieke software Zo dat Inzichtelijk wordt gemaakt hoe het ontwerp bijdraagt aan klimaatdoelen [input geeft aan afwegingskader?] en besluitvorming bevordert / Tijdens Masterplanontwikkeling Door BIM-modellen te koppelen aan LCA-rapportage Processtap Controle/advies CO2. Thema

#### 8.1.1 User stories voor Hittestress

User story | Hittestress - Koele plekken identificeren in variant X van VO-masterplan

Als een Gemeentemedewerker adviseur duurzaamheid Wil ik Inzicht in de zoekgebieden voor koele plekken in het masterplan In/op Een digitaal device, zonder specifieke software Zo dat Inzichtelijk is waar potentieel koele plekken kunnen komen en deze mee te kunnen wegen in het ruimtelijke afwegingskader Tijdens Masterplanontwikkeling Door Schaduwrijke plekken te identificeren Processtap Hittestress - schaduwstudie. Thema

User story | Hittestress - Koele routes identificeren in variant X van VO-masterplan

Als een Gemeentemedewerker adviseur duurzaamheid Wil ik Inzicht in potentiële koele (wandel)routes in het masterplan, vanaf woningen t/m koele plek (zie US hierboven). In/op Een digitaal device, zonder specifieke software Zo dat Inzichtelijk is waar koele routes moeten komen en deze mee te kunnen wegen in het ruimtelijke afwegingskader Tijdens Masterplanontwikkeling Door Schaduwrijke routes te identificeren Processtap Hittestress - schaduwstudie. Thema

User story | Hittestress – Beoordelen bijdrage hittestress (voorkomen) van ontwerp aan aangrenzende buurten

Als een Gemeentemedewerker adviseur duurzaamheid Wil ik Het ontwerp kunnen beoordelen of het ontwerp een positieve of negatieve bijdrage levert aan omliggende buurten op het gebied van hittestress. In/op Een digitaal device, gebruikmakend van het OUP Zo dat Inzichtelijk is wat de impact is van het ontwerp Tijdens Masterplanontwikkeling Door Het ontwerpmodel door een rekenmodel voor de betreffende omliggende buurt(en) te laten doorrekenen en de resultaten inzichtelijk te maken. Processtap Masterplanfase Thema (nader te bepalen)

### 8.2 Welke inzichten zijn nodig?

Om antwoord te kunnen geven op de twee use-cases zijn verschillende inzichten nodig.

CO2-consumptie:

1. De data van CO2-consumptie van nieuwe gebouwen komt bij het ontwerpconsortium vandaan. Het rekenmodel waarin deze consumptie wordt berekend is een blackbox voor gemeente. De gemeente wil inzicht in de data, het rekenmodel én de uitkomst waarmee de CO2-consumptie is berekend.
2. De data van de infrastructuur komt van het ontwerpconsortium. Het rekenmodel van CO2- consumptie van infrastructuur komt van het cluster Stadsbeheer van de gemeente Rotterdam. Input van dit rekenmodel wordt geleverd door het consortium. Aspecten die in het rekenmodel gebruikt worden zijn: openbare ruimte, verharding en ondergrond. Ook hier is inzicht nodig in de data, het rekenmodel en de uitkomst waarmee de CO2-consumptie is berekend. Aangezien dit rekenmodel eigendom is van de gemeente is inzicht hierin krijgen makkelijker.
3. Op masterplanniveau wil men met kengetallen weten of een project haalbaar is. Dat er gebouwd gaat worden op basis van referentiegetallen en gerealiseerde projecten. In verdere fases kan men op basis van dit ontwerp steeds hoge detaillering/data voor berekeningen opleveren.

Hitte:

1. Hittestress bezonning/schaduw, Voor de hittestressberekening is inzicht nodig over waar gebouwen komen, en hoe de buitenruimte is ingericht. Ook is het van belang de bestaande assets in de analyse mee te nemen. Dit kan het omliggend gebied zijn, maar ook bestaande assets binnen het plangebied die blijven bestaan. Voor de hitte-berekening is inzicht nodig van het ontwerp, de bestaande situatie, het rekenmodel en de uitkomst die hier uit komt.

De berekening gaat niet over groene daken/gevels. Dit is het urban-heat-island-effect. Dit effect valt buiten de scope van de hittestress-berekening.

Beide berekeningen, CO2 en hitte, geven een onderbouwing voor EU taxonomy, de plan-MER en validatie van beleid van de gemeente Rotterdam.

### 8.3 Welke informatie is nodig om tot deze inzichten te komen?

Het Level Of Information Need (LOIN) framework conform ISO 7817, of in Nederlands: “het

2

benodigd informatieniveau”, is beschreven in de ISO 19650 . Het LOIN-raamwerk geeft de mogelijkheid om de benodigde kwaliteit, hoeveelheid en granulariteit van informatie te beschrijven. Hiermee vermijdt men het produceren van te veel, te weinig of onbruikbare informatie in een project. Op basis van uitgewerkte processen blijkt onderstaande informatiebehoefte.

2 ISO 19650: Organisatie en digitalisering van informatie over gebouwen en civieltechnische werken, met inbegrip van building information modelling (BIM) - Informatiemanagement met behulp van bouw informatie modelling

CO2 Globaal CO2 Specifiek Hitte  Weg  Gevel  Gebouw  Bodem  Constructie  Boom  Damwand  Fundering  Maaiveld  Sportveld  Wanden  Weg  Woning  Installaties  Weer  Gebouw

De kwaliteit, hoeveelheid en granulariteit van bovenstaande data is uitgewerkt in Bijlage 1 – Level of Information Need per object.

### 8.4 Welke indicatoren horen hierbij?

Voor CO2 zijn er twee indicatoren:

Indicator Betekenis

kg CO₂-eq per m² BVO De CO₂-intensiteit van het ontwerp; maakt vergelijking tussen projecten en varianten mogelijk. Percentage van het CO₂-budget benut Laat zien in hoeverre het ontwerp binnen de (of resterend CO₂-budget) beschikbare CO₂-ruimte blijft.

Voor hitte zijn er drie indicatoren

Indicator Betekenis

Berekende gemiddelde PET (Physiological Equivalent Temperature) is een maat voor de ervaren temperatuur van mensen. Daarbij worden onder andere luchttemperatuur, zoninstraling, wind en luchtvochtigheid meegenomen. Zoekgebied koele plekken Beschikbaarheid van plekken waar mensen verkoeling kunnen vinden tijdens warme periodes. Schaduw loopgebieden Hoeveelheid/aandeel van routes die voldoende schaduw hebben.

### 8.5 Welke data is nodig om deze informatie te genereren? En waar

### vinden we deze data?

Er zijn vijf soorten data nodig om de data voor deze informatie te generen.

1. Ontwerp data: Er is data nodig van een nieuw ontwerp-masterplan. Waar komen welke objecten? In het ontwerp-masterplan kan een ontwikkelende partij verschillende decompositie en detailniveaus hanteren.
2. Bestaande data: Er is data nodig van de bestaande situatie. Welke bestaande objecten, assets en niveaus zijn er momenteel in het plangebied? En welke bestaande objecten, assets en niveaus zijn er buiten het plangebied die effect hebben op het plangebied?
3. Metadata: Er dient metadata beschikbaar te zijn voor de databronnen die worden gebruikt. Deze metadata beschrijft de herkomst van data, de gehanteerde nauwkeurigheid, de datakwaliteit en actualiteitswaarde. Dit is nodig om de betrouwbaarheid en toepasbaarheid van de resultaten te kunnen beoordelen.
4. Rekenmodellen: Er is inzicht nodig in de rekenmodellen die zijn toegepast. Hierbij gaat het om welke modellen zijn gebruikt, welke aannames zijn gehanteerd en welke parameters zijn ingesteld. Dit kan worden geborgd door het beschikbaar stellen van het rekenmodel zelf of door logging en documentatie van het rekenproces.
5. Context-data: Voor de uitvoering van de analyses is informatie nodig over de ruimtelijke afbakening van het project. Hierbij dient inzichtelijk te zijn wat het plangebied betreft en welk onderzoeksgebied wordt gehanteerd. Deze afbakening bepaalt de context waarbinnen de berekeningen en analyses worden uitgevoerd.

9. User stories als verbinding naar de

## techniek

Dit hoofdstuk fungeert als schakel tussen de user stories en de technische uitwerking. Omdat de user stories in dit document reeds deels een technische vertaling bevatten, en verdere technische detaillering buiten de scope van dit document valt, is dit hoofdstuk niet nader ingevuld.

10. Databronnen

Voor het verkrijgen van de data die kan ondersteunen in de gevraagd functionaliteit door de gemeente Rotterdam kunnen verschillende typen bestaande data, rekenmodellen en ontwerpdata worden gebruikt. Afhankelijk van de beschikbare gegevens kan worden gewerkt met 2D-data, 2Ddata die wordt opgewerkt naar een 3D-model, of met beschikbare 3D-ontwerpdata. Hiervoor bestaan verschillende technische uitwerkingsmogelijkheden. In de voorgestelde werkwijze is rekening gehouden met de huidige werkwijze van het ontwerpconsortium, zoals deze naar voren is gekomen uit de gehouden interviews.

### 10.1 Welke data is nodig voor de gewenste inzichten/informatie?

#### 10.1.0 Ontwerp-informatie:

CO2- Globaal

Soort asset Model Leverende partij

Bodem 2D CAD-model landschapsarchitecten Sportveld 2D CAD-model landschapsarchitecten Woning 3D IFC-model Ontwerpconsortium Gebouw 3D IFC-model Ontwerpconsortium

CO2- Specifiek

Soort asset Model Leverende partij

Gevel 3D IFC-model Ontwerpconsortium Constructie 3D IFC-model Ontwerpconsortium Fundering 3D IFC-model Ontwerpconsortium Wanden 3D IFC-model Ontwerpconsortium Installaties 3D IFC-model Ontwerpconsortium

Hitte

Soort asset Model Leverende partij

Gebouw 3D IFC-model Ontwerpconsortium Boom 2D CAD-model Maaiveld 2D CAD-model Weg 2D CAD-model Weer 3D IFC-model Ontwerpconsortium

#### 10.1.1 Bestaande omgeving-informatie:

Soort asset Model Leverende partij

Hoogte maaiveld Hoogtebestand AHN/gemeente Rotterdam Uitgiftepeil Uitgiftepeilbestand Gemeente Rotterdam Gebouwen (2D) BGT PDOK (Kadaster) Gebouwen (3D) 3D-Basisvoorziening PDOK (Kadaster) Bomen BGT PDOK (Kadaster)

#### 10.1.2 Metadata:

Soort metadata Model Leverende partij

Beschrijving assetdata DCAT AP NL Ontwerpconsortium Beschrijving rekenmodel PROV-O Ontwerpconsortium Beschrijving levermodel ICDD Ontwerpconsortium (optioneel)

#### 10.1.3 Rekenmodellen:

Soort data Model Leverende partij

Rekenmodel CO2 C# Ontwerpconsortium Logboek-data-verwerkingen JSON Ontwerpconsortium

#### 10.1.4 Context:

Soort data Model Leverende partij

Projectgebied Geojson Gemeente Rotterdam Bounding Box projectgebied Geojson Gemeente Rotterdam Buffer projectgebied Geojson Gemeente Rotterdam Bouding Box buffer Geojson Gemeente Rotterdam projectgebied

### 10.2 Welke data requirements (ILS)

Op basis van de behoefte van het detailniveau van de informatie van het object (Level of Information Need=LOIN) is onderstaande ‘informatie levering specificatie (ILS)’ opgesteld. Door te voldoen aan deze Informatie Levering Specificatie wordt voorzien aan de Informatiebehoefte opgesteld in de LOIN. De ILS is uitgewerkt voor 2D gemodelleerde data voor het infrastructureel ontwerp en voor 3D gemodelleerde data voor de gebouwen. De opgestelde specificatie sluit aan bij de relevante open standaarden. Voor beide dimensies geldt dat er is gekeken naar welke bestaande werkpraktijk er is in combinatie met open formaten/standaarden. Ieder afzonderlijk benodigd

objecttype is een de ILS gespecificeerd met de vereisten die passen bij de behoefte van het detailniveau van deze masterplanfase.

Tijdens de inventarisatie van de werkwijze en de data die uitgewisseld wordt tussen het consortium blijkt dat hier project-specifieke modelleerafspraken worden gemaakt. Een laagnaam als: “MODELLEN_CONSORTIUM/MODEL_1A_conceptMP_251217_conclusiemodel+/WONEN” heeft alleen betekenis binnen het ontwerpconsortium. Vanuit deze laagnamen zal een vertaling gemaakt kunnen worden naar de in de ILS voorgeschreven structuur. Data die uitgewisseld wordt met de gemeente Rotterdam dient conform deze ILS te zijn opgesteld.

#### 10.2.0 ILS- 3D Informatie Ontwerp

Wanneer de ontwerpinformatie in 3D opgesteld en uitgewisseld wordt, adviseren wij gebruik te maken van het open-BIM formaat IFC. Dit formaat is open, uitwisselbaar, controleerbaar en toekomstbestendig. Het is mogelijk om dit formaat in te laden in verschillende software en tooling. Dit past bij de ambities in de situatie van Schiehaven Noord. Dit sluit daarnaast aan op de

3

uitgangspunten van de BIM Basis ILS . Tot slot sluit het aan bij de actuele ontwikkeling van het

4 5

miniGIM . IFC staat bij forumstandaardisatie op de pas-toe-of-leg-uit-lijst . 3D – tabel.

IFC Entiteit Name ObjectType LOIN Toelichting specificatie

IfcProject naamproject IfcSite naam_terrein IfcSite uitgeefbaar Plangrens miniGIM (niveau 0) IfcSite openbaar Plangrens miniGIM (niveau 0) IfcSite verhard miniGIM (niveau 1) IfcSite Percelen miniGIM (niveau 2) IfcSite mandelig miniGIM (niveau 2) IfcRoad wegen miniGIM (niveau 2) IfcRoad fietspad miniGIM (niveau 2) IfcRoad voetpad miniGIM (niveau 2) IfcSlab parkeervakken MiniGIM (niveau 2) IfcSite Sportveld IfcSite Groen miniGIM (level 1) IfcSite Plantvak miniGIM (level 2) IfcSite Bermen miniGIM (level 2) IfcSite Wadi miniGIM (level 2) IfcSite Park miniGIM (level 2) IfcSite Speelvoorziening miniGIM (level 2) IfcSite Water miniGIM (level 1-2) IfcBridge Kunstwerken miniGIM (level 2) IfcBridge Brug miniGIM (level 2) IfcGeographic boom Boom -Element IfcBuilding Bebouwd Gebouw miniGIM (level 3)

3 [https://www.digigo.nu/ilsen-en-richtlijnen/bim-basis-ils/](https://www.digigo.nu/ilsen-en-richtlijnen/bim-basis-ils/) 4 [https://minigim.nl/](https://minigim.nl/) 5 [https://www.forumstandaardisatie.nl/open-standaarden/verplicht](https://www.forumstandaardisatie.nl/open-standaarden/verplicht)

#### Algemeen

Requirement 1

Een BIM-Model voor Schiehaven Noord dient minimaal in IFC-versie 4.3 ADD2 uitgewisseld te worden

#### IfcProject

Requirement 2

Een BIM-Model voor Schiehaven Noord dient minimaal 1 IFCClass IfcProject te hebben. Het IfcProject bevat verplicht het attribuut Name met de projectnaam.

Attribuut in IfcProject Beschrijving Voorbeeld

Name Verplicht Naam van het project Gebiedsontwikkeling Schiehaven Noord

#### IfcMapConversion

Requirement 3

Een BIM-Model voor Schiehaven Noord moet de IFCClass IFCMAPCONVERSION bevatten met de attributen SourceCRS, TargetCRS, Easting, Northing, OrthogonalHeight, XAxisAbscissa, XAxisOrdinate en Scale ingevuld.

Requirement 4

Het attribuut TargetCRS voor Nederlandse indiening heeft als verplichte waarde een IfcProjectedCRS met attribuut VerticalDatum EPSG:7415 (RD+NAP)of EPSG:28992 (RD) én EPSG:5709 (NAP)

Attribuut in IfcMapconversion Beschrijving Voorbeeld

SourceCRS Verplicht Het broncoördinatenstelsel van IfcGeometrichet BIM model RepresentationContext

TargetCRS Verplicht Doel coördinatenstelsel waarin EPSG 7415 het BIM model geplaatst wordt.

Eastings Verplicht Verplaatsing in Oostrichting om 92370.710706 het BIM model op de goede plek te krijgen.

Northing Verplicht Verplaatsing in Hoogterichting 437455.379788 om het BIM-model op de goede plek te krijgen.

Orthogonal Verplicht De vorm van de eigendom- en 1,3092 Height gebruikseenheid

XAxisAbcissa Verplicht Specificeert de waarde langs de 0,8 oostelijke as van het eindpunt van een vector die de positie van


de lokale x-as van het engineering coördinaatreferentiesysteem aangeeft.

XAxisOrdinate Verplicht Specificeert de waarde langs de 0,1 oostelijke as van het eindpunt van een vector die de positie van de lokale x-as van het engineering coördinaatreferentiesysteem aangeeft.

Scale Verplicht chaal van eenheden in BIM- 1/0.001 model t.o.v. eenheden in target CRS

#### IfcSite

Requirement 5

Een BIM-Model voor Schiehaven Noord dient minimaal één IfcSite op MiniGIM niveau 0 (uitgeefbaar-Openbaar) of specifieker te hebben (Verhard-Groen-Water etc.). Het attribuut ObjectType is ingevuld en duidt het type. Het attribuut Representation is gevuld met een IfcProductDefinitionShape.

Attribuut in IfcSite Beschrijving Voorbeeld

Name Optioneel Naam van het terrein Plandeel A

ObjectType Verplicht Objecttype volgens MiniGIM Uitgeefbaar

Object- Verplicht De plaatsing van het terrein LocalPlacement placement

Representation Verplicht De vorm en de locatie van het IfcProductRepresentation terrein

#### Gebouw

Requirement 6

Een BIM-Model voor Schiehaven Noord dient minimaal 1 IFCClass IfcBuilding te bevatten met een IfcRelAggregates relatie naar 1 of meerdere IfcBuildingStoreys die op hun beurt een IfcRelAggregates relatie hebben naar 1 of meerdere IfcSpace en IfcBuiltElement die een geometrie hebben.

Informatie-item IFC-klasse Vereiste relatie Verplicht/ Opmerkingen optioneel

Gebouw IfcBuilding IfcRelAggregates Verplicht Als relating object naar IfcBuildingStorey

Verdieping IfcBuildingStorey IfcRelAggregates Verplicht Related object vanuit IfcBuilding en relating object naar IfcProduct

Ruimte IfcSpace IfcRelAggregates Optioneel Related object vanuit IfcBuildingStorey

Wanden IfcWall IfcRelAggregates Optioneel Related object vanuit IfcBuildingStorey

Vloeren IfcSlab IfcRelAggregates Optioneel Related object vanuit IfcBuildingStorey

#### Woning

Requirement 7

Een BIM-Model voor Schiehaven Noord dient minimaal 1 IFCClass IfcSpatialZone te bevatten van het objecttype Eigendom- en gebruikseenheid met de attributen: Name, Description, Objecttype. Een eigen geometrie is verplicht met Objectplacement en Representation.

Requirement 8

Voor het modelleren van een eigendoms- & gebruikseenheid is bepalingsmethode Bruto Inhoud zodat hier geen speculatie over kan bestaan.

Attribuut in IfcSpatialZone Beschrijving Opmerking

Name Verplicht Naam van de woning Voorbeeld: Unit S-1

Description Verplicht Bepalingsmethode Verplicht: Bruto Inhoud (nen2580)

Objecttype Verplicht Beschrijving van het soort Verplicht: Eigendom- en ruimtelijk object gebruikseenheid

Object- Verplicht De plaatsing van de LocalPlacement placement eigendom- en gebruikseenheid

Representation Verplicht De vorm van de eigendom- ShapeRepresentation en gebruikseenheid

Longname Verplicht Eenheid-beschrijving Woning

IfcRelReferen Optioneel Eenheden die tot de woning cedInSpatialS toebehoren tructure

#### Boom

Requirement 9

Een BIM-Model voor Schiehaven Noord dient voor bomen de IFCClass IfcGeographicElement te gebruiken met de attributen Objecttype “Boom” en predefinedType “VEGETATION”.


Attribuut in IfcGeographicElement Beschrijving Opmerking

Objecttype Verplicht Beschrijving van het soort Verplicht: Boom vegetatieobject

Object-placement Verplicht De plaatsing van de boom LocalPlacement

Representation Verplicht De vorm van de ShapeRepresentation eigendom- en gebruikseenheid

PredefinedType Verplicht Voorgedefinieerd type van Verplicht: Vegetation IfcGeographicElement

#### Weg

Requirement 10

Een BIM-Model voor Schiehaven Noord dient voor wegen IfcRoad te gebruiken. Het attribuut ObjectType is ingevuld en duidt het type volgens MiniGIM specificatie. Het attribuut Representation is gevuld met een IfcProductDefinitionShape of de geometrie is opgesteld in IfcRoadParts.

Attribuut in IfcRoad Beschrijving Opmerking

Objecttype Verplicht Beschrijving van het soort Voorbeeld: Fietspad weg

Object-placement Verplicht De plaatsing van de weg LocalPlacement

Representation Verplicht De vorm van de weg ShapeRepresentation

#### Materiaal

Requirement 11

Een BIM-Model voor Schiehaven Noord dient voor de materialisatie van wegen, gebouwen, sportvelden en damwanden de relatie IfcRelAssociatesMaterial te gebruiken. Het IfcMaterial is beschreven met materiaal uit de IMBOR specificatie (2026)

Attribuut in IfcMaterial Beschrijving Voorbeeld

Name Verplicht Naam van het materiaal Asfalt

Informatie-item IFC-klasse Vereiste relatie Verplicht/ Opmerkingen optioneel

Materiaal IfcMaterial

Gebouw IfcBuilding IfcRelAssociates Verplicht Als relating object naar Material IfcBuildingStorey en IfcBuiltElement


Weg IfcRoad IfcRelAssociates Verplicht Related object vanuit Material IfcBuilding en relating object naar IfcProduct

Etc.

#### Sportveld

Requirement 12

Een BIM-Model voor Schiehaven Noord dient voor een sportveld IfcSite te gebruiken. Het attribuut ObjectType is ingevuld en duidt het type Sportveld. Het attribuut Representation is gevuld met een IfcProductDefinitionShape of de geometrie is opgesteld in IfcRoadParts.

Attribuut in IfcSite Beschrijving Voorbeeld

Objecttype Verplicht Naam van het terrein Verplicht: Sportveld

Object- Verplicht De plaatsing van de weg LocalPlacement placement

Representation Verplicht De vorm van de weg ShapeRepresentation

#### Damwand

Requirement 13

Een BIM-Model voor Schiehaven Noord dient voor een damwand IfcPile te gebruiken. Het Objecttype is ingevuld en duidt het type Damwand. Het constructiontype is PREFAB_STEEL

Attribuut in IfcPileConstruction Beschrijving Voorbeeld

Objecttype Verplicht Naam van het terrein Verplicht: Damwand

Object- Verplicht De plaatsing van de LocalPlacement placement damwand

Representation Verplicht De vorm van de damwand ShapeRepresentation

ConstructionType Verplicht Het voorgedefinieerde PREFAB_STEEL damwand-type

#### Gevel

Requirement 14

Een BIM-Model voor Schiehaven Noord dient voor een gevel de isExternal property te gebruiken in de psets: WallCommon, WindowCommon, SlabCommon, BeamCommon, RoofCommon.


Informatie- IFC- Property set Property Verplicht/ Opmerkingen item klasse optioneel

Gevelwand IfcWall Pset_Wall IsExternal Verplicht Boolean TRUE voor Common buitenschil

Gevelraam IfcRoom Pset_Window IsExternal Verplicht Boolean TRUE voor Common buitenschil

Geveldeur IfcDoor Pset_Door IsExternal Verplicht Boolean TRUE voor Common buitenschil

Gevelbalk IfcBeam Pset_Beam IsExternal Verplicht Boolean TRUE voor Common buitenschil

#### Constructie

Requirement 15

Een BIM-Model voor Schiehaven Noord dient voor de constructieve onderdelen (BuiltElements) het Pset_*Common Loadbearing is TRUE te gebruiken.

Informatie- IFC- Property set Property Verplicht/ Opmerkingen item klasse optioneel

Draagmuur IfcWall Pset_Wall LoadBearing Verplicht Boolean TRUE Common voor constructieve muur

Draagvloer IfcSlab Pset_Slab LoadBearing Verplicht Boolean TRUE Common voor constructieve vloer

Constructieve IfcBeam Pset_Beam LoadBearing Verplicht Boolean TRUE balk Common voor constructieve balk

Kolom IfcColumn Pset_Column LoadBearing Verplicht Boolean TRUE Common voor constructieve kolom

#### Fundering

Requirement 16

Een BIM-Model voor Schiehaven Noord dient voor de fundering IfcFooting en/of IfcPile te gebruiken.

#### Wanden

Requirement 17

Een BIM-Model voor Schiehaven Noord dient voor de wanden IfcWall of IfcWallStandardCase


#### IfcBuildingElementProxy

Requirement 18

Een BIM-Model voor Schiehaven Noord dient geen gebruik te maken van de vrije entiteit IfcBuildingElementProxy.

Voor deze ILS is ook een IDS gemaakt. Zie hiervoor bijlage 7 IDS.

#### 10.2.1 2D Informatie Ontwerp

Wanneer de ontwerpinformatie in 2D opgesteld en uitgewisseld wordt, adviseren wij gebruik te maken van het CAD-uitwisselformaat DXF. Veel gebruikte formaten zijn .dwg en .dgn, maar dit zijn gesloten formaten. Hoewel dit formaat goed uitwisselbaar en controleerbaar is, bevat het geen semantische informatie en is het daarom minder geschikt voor BIM-toepassingen en minder toekomstbestendig dan IFC. Voor 2D CAD-tekenwerk is dit momenteel de meest geschikte optie. Voor de classificatie van het tekenwerk adviseren wij de NLCS-tekenstructuur te gebruiken. Het is mogelijk om dit formaat in te laden in verschillende software en tooling. Dit past bij de ambities in de situatie van Schiehaven Noord. Tot slot sluit het aan bij de actuele ontwikkeling van

6

CROW en DigiGO . Ook de NLCS-standaard staat op de pas-toe-of-leg-uit-lijst

Requirement 1

Een CAD BIM-Model voor Schiehaven Noord dient uitgewisseld te worden in DXF

Requirement 2

De getekende geometrie bestaat uit gesloten polylines en hatches. Losse lijnen worden vermeden.

Requirement 3

De getekende inhoud moeten echte objecten op de kaart zijn. Waarbij objecten als legenda’s, doorsneden, noordpijlen in uitwisseling weggelaten worden.

Requirement 4

Alle aangeleverde DXF-bestanden dienen getekend te zijn in het Rijksdriehoekcoördinatenstelsel (RD New/EPSG:28992). Er is in meters getekend.

Requirement 5

De aangeleverde DXF bestanden gebruiken onderstaande laagnamen voor de objecten voor Gebouw, Boom, Weg, Bodem, Damwand, Sportveld, Woning, Gebouw waarbij functie en materiaal geduid is.

2D - tabel

6 [https://www.digigo.nu/nieuws/nlcs-objectgericht-werken-bespaart-e-20-tot-e-40-miljoen/](https://www.digigo.nu/nieuws/nlcs-objectgericht-werken-bespaart-e-20-tot-e-40-miljoen/)

Objecttype Laagnaam NLCS functie materie Toelichting

AsfaltWeg VH_GESLOTENVERHARDING x Voor materiaal en functie _ASFALT apart gemodelleerd. AVH-ASFALT (hatch) Hatch en/of geometrie kan gebruikt worden. Straatbakstee VH_OPENVERHARDING_ x Voor materiaal en functie n STRAATBAKSTEEN apart gemodelleerd. weg AVH-SBS (hatch) Hatch en/of geometrie kan etc. gebruikt worden. Autoweg OG_WEG_RIJWEG x Voor materiaal en functie apart gemodelleerd. Fietspad OG_WEG_RIJWIELPAD x Voor materiaal en functie apart gemodelleerd. Voetpad OG_WEG_VOETPAD x Voor materiaal en functie apart gemodelleerd. Parkeervak OG_WEG_PARKEERPLAATS x Voor materiaal en functie apart gemodelleerd. OV-baan | weg OG_WEG_BUSBAAN, x Voor materiaal en functie OG_WEG_TRAMBAAN apart gemodelleerd. Boom GR_BOOM, x Of als symbool, of als GR_BOOM_BOOM_SOLITAIR geometrie of SGR- BOOM_1E_GROOTTE, SGR- BOOM_2E_GROOTTE, SGR- BOOM_3e_GROOTTE Terrein ZZ_GRENS_PROJECT x Totaal terrein, mag ook totaal van uitgeefbaar en openbaar gebied zijn. Terrein OG_TERREIN_UITGEEFBAAR x Uitgeefbaar Terrein OG_TERREIN_OPENBAAR x Openbaar GEBIED gebied Zandbodem GW_GROND_ZAND x

Kleibodem GW_GROND_KLEI x AGW-GROND_KLEI-SO (hatch) Teelaarde GW_GROND_TEELAARDE x

Bodem AGW_WERK_AANVULLEN x AGW_WERK_ONTGRAVEN Damwand GK_KEERWAND_DAMWAND x x Functie en materiaal in beton _BETON een Damwand GK_KEERWAND_DAMWAND x x Functie en materiaal in staal _BETON een Sportveld GR_SPORTVELD_KUNSTGRA x x Functie en materiaal in S een Gebouw OG_BEBOUWING_WONINGB x laagbouw OUW_ LAAGBOUW Gebouw OG_BEBOUWING_WONINGB x middenbouw OUW_ MIDDENBOUW Gebouw OG_BEBOUWING_WONINGB x hoogbouw OUW_ HOOGBOUW

Woning OG_BEBOUWING_WONINGB x OUW_ EENGEZINSWONING Gebouw gevel BEBOUWING_GEVELMUUR x

Gebouw BC_BETONVORM, x x constructie en HC_HOUTVORM, materiaal MW_METSELWERKVORM_B AKSTEEN, SC_STAALVORM Gebouw FC_PAAL_BETON fundering Gebouw BEBOUWING_TUSSENMUUR x wanden

#### 10.2.2 Bestaande situatie 2D

#### Invloedsgebied

Assets rond het plangebied hebben invloed op de gebiedsontwikkeling. Voor de CO2 berekening wordt geen rekening gehouden met bestaande assets. Voor de hitte berekening is dit wel het geval. Bestaande gebouwen en bestaande bomen rond het plangebied kunnen een schaduw werpen binnen het plangebied. Rond de gebiedsontwikkelingsgrens wordt een buffer gecreëerd van 500 meter. De boundingbox van deze buffer definieert het analysegebied van de bestaande situatie dat wordt meegenomen in berekeningen.

Deze werkgrens, en het invloedsgebied (buffer) van Schiehaven Noord is als Geo bestand beschikbaar gemaakt. Ook de coordinaten van de bounding box zijn bekend gemaakt zodat deze in API's kunnen worden gebruikt.

Voor Schiehaven Noord zijn dit in RD:

minX = 4.44503 minY = 51.89773

maxX = 4.46574 maxY = 51.90887

#### Bestaande situatie 2D

Zowel voor de CO2-berekening als voor de hitte-berekening is geen 2D bestaande informatie nodig.

#### 10.2.3 Bestaande situatie 3D

Voor de hitteberekening dient men een schaduwberekening te doen. Voor schaduwwerking heeft men gebouwen, maaiveld en bomen nodig.

#### 3D Maaiveld en 3D gebouwen

Maaiveld en gebouwen van de omgeving kan men vanuit de 3D Basisvoorziening of de 3D BAG halen. Zie voor de bevragingen Bijlage 2 – API BAG- PDOK

#### 3D Bomen

Bestaande bomen rond het project kan men momenteel in Rotterdam het beste downloaden vanuit de 3D Rotterdam omgeving. Het onderzoeksgebied kan men meegeven om de objecten binnen de werkgrens te downloaden. Er zijn nog geen landelijke datasets voor 3D bomen. Wel is het mogelijk om, wanneer bomen niet in 3D beschikbaar zijn hier de 2D data voor te gebruiken. Zie hiervoor Bijlage 2 – API Call BAG-PDOK.

#### 10.2.4 Metadata

#### DCAT-AP-NL voor datasets

Metadata beschrijft de herkomst, inhoud, kwaliteit, actualiteit en geldigheid van datasets en modellen. Hierdoor kunnen betrokkenen in het project de informatie op de juiste manier interpreteren en gebruiken. De metadata van het ontwerp en de gebruikte bronnen kan geleverd worden volgens DCAT-AP-NL specificatie.

Hierin vormt men een catalogus: Eigenschap URI Bereik Contactpunt Dcat:ContactPoint Vcard:Kind Beschrijving Dct:Description rdfs:Literal Publicerende partij Dct:Publisher foaf:Agent Titel Dct:Title rdfs:literal

In de catalogus kan men een relatie naar 1 of meerdere datasets duiden

Deze datasets hanteren onderstaande structuur: Eigenschap URI Bereik Toegangsrechten Dct:accessRights dct:RightStatement Contactpunt Dcat:ContactPoint Vcard:Kind Gemaakt door Dct:creator foaf:Agent Beschrijving Dct:description rdfs:literal Identificatie Dct:identifier rdfs:literal Publicerende partij Dct:publisher foaf:Agent Thema Dcat:theme skos:Concept Titel Dct:title rdfs:literal

Als voorbeeld kunnen de catalogus en de dataset er als onderstaand voorbeeld uitzien:

Catalogus:

Eigenschap Voorbeeld Titel Gebiedsontwikkeling Schiehaven-Noord

Beschrijving Catalogus van Digitale Tweeling data gebruikt bij de Masterplanfase gebiedsontwikkelingsproject Schiehaven Noord Verstrekt door Ontwerpconsortium Contactpunt Ontwerpconsortium b.v. info@consortium-voorbeeld.nl Datasets: Bgt-panden-extract-2026

Dataset:

BGT-panden-extract-2026

Eigenschap Voorbeeld Titel BGT Panden 2026 Beschrijving Extract van BGT pandobjecten binnen het plangebied vanuit de landelijke voorziening (2026 respons JSON) Toegangsrechten Publiek Contactpunt Ontwerpconsortium b.v. info@consortium-voorbeeld.nl Gemaakt door Ontwerpconsortium Publicerende partij Ontwerpconsortium Bron [https://api.pdok.nl/lv/bgt/ogc/v1/collections/pand/](https://api.pdok.nl/lv/bgt/ogc/v1/collections/pand/) Identificatie 45e699c4-96fc-402c-80fd-3ba16a8c9e9c Thema Bestaande Gebouwen

#### DCAT-AP-NL Metadata voor rekenmodellen

Voor rekenmodellen zijn er twee soorten metadata. Enerzijds is er de beschrijving van het rekenmodel als dataset zodat het rekenmodel vindbaar is in een catalogus. Men beschrijft hiermee wat het rekenmodel is, wie het beheert, onder welke voorwaarden het gebruikt kan worden en hoe het toegankelijk is. Bij deze metadata kan men ook gebruik maken van de DCAT-AP-NL structuur. Voor rekenmodellen zullen er in de toekomst een aantal aanvullende attributen om DCATAP-NL beschikbaar komen waarin de standaard beter ondersteund in de gestandaardiseerde informatie waarmee men rekenmodellen kan duiden.

Eigenschap Voorbeeld Titel Woningen tel rekenmodel Beschrijving Dit rekenmodel telt het aantal woningen in een IFC BIM-model. Het rekenmodel maakt gebruik van ifcopenshell. Toegangsrechten Publiek Contactpunt contactpersoon Geonovum info@geonovum.nl Gemaakt door Geonovum Publicerende partij Geonovum Bron [https://github.com/Geonovum/voorbeeld/count_dwellings.py](https://github.com/Geonovum/voorbeeld/count_dwellings.py) Identificatie f2547ba0-62c4-4344-94ef-24206b9473cc Thema Woningen

#### PROV-O en logboek dataverwerking als Metadata voor berekeningen

Metadata volgens het PROV-O-model en/of het logboek dataverwerking op basis van OpenTelemetry legt de herkomst (provenance) van rekenmodellen en de daaruit voortkomende resultaten vast. Hiermee wordt inzichtelijk welke invoergegevens, modelversies, parameters, software, aannames en verantwoordelijke partijen zijn gebruikt om een resultaat te genereren. Door deze informatie systematisch vast te leggen, worden berekeningen reproduceerbaar, controleerbaar en herleidbaar. Dit vergroot het vertrouwen in de resultaten, ondersteunt kwaliteitsborging en maakt het mogelijk om wijzigingen en de impact daarvan gedurende de projectlevenscyclus inzichtelijk te houden. Ook als hierbij verschillende partijen of applicaties samen hebben moeten werken. Daarnaast is het mogelijk om met logboek dataverwerking te refereren naar een beschrijving van een algoritme in het algoritmeregister. Zie als voorbeeld hiervan de beschrijving van

7

Modelleringssoftware Hittestress .

In bijlage 8 PROV-O en logboek dataverwerking is een voorbeeld van een PROV-O en logboek dataverwerking file gegeven.

### 10.3 Informatie Levering

Binnen het project Schiehaven Noord worden twee manieren van informatielevering beschreven: file data levering en API-levering. De file-levering is momenteel haalbaar, terwijl API-levering in de toekomst een interessante mogelijkheid kan vormen.

Bij file data levering worden gegevens periodiek aangeleverd via bestanden. Dit gebeurt bijvoorbeeld via e-mail, upload of een gedeelde opslaglocatie. Deze methode is geschikt voor batchverwerking en minder frequente updates.

De tweede mogelijkheid is API-levering, waarbij gegevens via een API worden uitgewisseld. Dit maakt realtime gegevensuitwisseling mogelijk en is geschikt wanneer systemen direct met elkaar moeten communiceren. Hierdoor zijn actuele gegevens beschikbaar en is geautomatiseerde integratie mogelijk.

#### 10.3.0 Datadrops

De gemeente Rotterdam bevindt zich in de Masterplanfase van in de gebiedsontwikkeling Schiehaven Noord. De gemeente dient de data van het gebiedsambitiedocument beschikbaar te stellen zodat het ontwerpconsortium hier in de masterplanfase op door kan werken. Naast de beschikbare data van de masterplanfase dient de gemeente ook te voorzien in de omgevingsdata of in de afspraken over het gebruik van basisregistraties. Dit is in onderstaande figuur aangegeven als datadrop 1. Naast data levert de gemeente Rotterdam ook een Informatie Levering Specificatie (ILS) en Informatie Protocol. In de ILS beschrijft de gemeente Rotterdam wat voor soort informatie er geleverd dient te worden. In het Informatie Protocol beschrijft de gemeente de juridische afspraken

7 [https://algoritmes.overheid.nl/nl/algoritme/32122905/21577420/modelleringssoftware-hittestress](https://algoritmes.overheid.nl/nl/algoritme/32122905/21577420/modelleringssoftware-hittestress)

voor de data. Het ontwerpconsortium als opdrachtnemer dient een Bim Uitvoerings Plan (BUP) te leveren waarin men antwoord geeft op de ILS en het protocol. In het BUP beschrijft de opdrachtnemer hoe data gecreëerd en geleverd gaat worden. Dit is onderdeel van het contract. Tijdens de masterplanfase kunnen er verschillende onofficiële datadrop moment plaatsvinden. Bijvoorbeeld wanneer het ontwerpconsortium een variant wil laten toetsen aan beleid. Dit kan men doen op basis van een submodel van het totale masterplan. Hier kan men, wanneer gewenst, aparte deel ILS-en voor afspreken. Deze stap is nummer 2 in onderstaande figuur. Aan het eind van de masterplanfase zal het ontwerpconsortium het totaal dossier leveren waarin alle data van het ontwerpmodel, de rekenmodellen en de omgeving in zit. Dit model dient te voldoen aan de ILS en de gemeente mag dit gebruiken zoals in Protocol is afgesproken. Het is wenselijk dat dit masterplanmodel gebruikt kan worden in de volgende fase, het maken van een stedenbouwkundig plan.

#### 10.3.1 File-levering

Het leveren van files van ontwerpmodellen in Schiehaven Noord is een haalbaar scenario. Bij filelevering worden bestanden geleverd via mail of een portaal en van daaruit opgeslagen in een projectmap of centrale projectomgeving. Hierdoor zijn de bestanden intern goed toegankelijk, maar is het in de praktijk vaak lastiger om deze gegevens eenvoudig met derden te delen. De bestanden zijn gebonden aan de projectstructuur en vereisen vaak specifieke rechten, software of kennis van de omgeving om ze te kunnen benaderen. Daarnaast blijk het in de praktijk vaak lastig te zijn om deze bestanden breed te hergebruiken, omdat er specifieke GEO- of CAD-software nodig is om ze te openen en te bewerken. Dit beperkt de toegankelijkheid van de data voor andere toepassingen of systemen. Om dit te verbeteren kan men gebruik maken van open uitwisselformaten, zoals IFC(Industry Foundation Classes), CSV, CityGML, PDF. Deze formaten zijn meer open en softwareonafhankelijk is. Dit vergroot de uitwisselbaarheid en herbruikbaarheid.

Niet elk open formaat is even herbruikbaar. Zo is een PDF vooral bedoeld voor weergave en documentatie, waardoor de data minder goed herbruikbaar is voor verdere verwerking of automatisering.

De in dit document beschreven data-specificatie gaat daarom uit van open bestandsformaat.

Vooorbeelden van files in open formaat worden weergegeven in Bijlage 4- file-uitwisseling.

#### 10.3.2 ICDD

ICDD (Information Container for Data Drop) is een standaard voor het gestructureerd uitwisselen van projectinformatie en modellen. In plaats van losse bestanden te versturen, bundelt ICDD verschillende soorten data zoals modellen, documenten en metadata in één digitale container. Hierdoor blijft de informatie beter georganiseerd en contextueel gekoppeld. Dit maakt het eenvoudiger om gegevens te delen tussen verschillende partijen en toepassingen, terwijl de samenhang binnen het project behouden blijft.

Als het ontwerpconsortium data als ICDD (Information Container for Data Drop) aanlevert, krijgt de gemeente Rotterdam geen losse bestanden meer, maar een gestructureerd pakket (container (.zip file)) met alle projectinformatie én de relaties daartussen. Dit maakt het makkelijk om te zien hoe onderdelen aan elkaar gekoppeld zijn. Bijvoorbeeld welke rekenmodel heeft welke input gebruikt en welke output geleverd. Of welke brondata heeft welke pdf opgeleverd. Dit maakt het vinden van informatie makkelijker. In plaats van zoeken in losse mappen, kan men via de beschreven structuur in de container direct naar de juiste informatie navigeren.

De structuur van een ICDD-container is als voorbeeld in Bijlage 5 – ICDD voor file-uitwisseling uitgewerkt. Daarnaast is er een voorbeeld ICDD-container voor het project Schiehaven Noord uitgewerkt.

Open standaarden en ICDD vormen samen een tussenlaag waarin data beter gestructureerd en contextueel wordt vastgelegd. Dit is een belangrijke opmaat naar API-gestuurde, realtime datatoegang en geavanceerde toepassingen zoals logboekregistratie en metadata-gedreven dataverwerking.

#### 10.3.3 API

API’s zijn te gebruiken voor data van de bestaande situaties (OGC-API’s via PDOK). Ook is het mogelijk dat het ontwerpconsortium een API aanbiedt met de gemodelleerde data (bijvoorbeeld de Building Smart documents-API). Dit zou het principe van een federatief stelsel en data bij de bron volgen.

Organisaties als DigiGO en Geonovum beschrijven deze manier van data delen.

Echter zijn er twee belangrijke bedenkingen bij deze werkwijze:

1. Het ontwerpconsortium bestaat gedurende het project. Na afronding van het project zal het consortium uiteen gaan. Wanneer het consortium verantwoordelijk is voor het aanbieden van de ontwerpdata betekent dit dat het consortium het ontwerp als API aan zal moeten bieden. Het is wenselijk om de data duurzaam toegankelijk te maken en deze API ook lange tijd na het project nog te kunnen bevragen. De vraag is of een consortium dit moet en kan faciliteren.
2. Historische bevragingen van een API blijken, nu nog, over de tijd verschillende uitkomsten te geven. Dit vraagt verbetering van de API's.

Als men berekeningen wil kunnen valideren of exact reproduceren, is het niet voldoende om alleen de actuele (materiële) situatie te hebben. Er is dan ook inzicht nodig in zowel de formele als de materiële historie van de data. De materiële historie beschrijft de feitelijke veranderingen in de werkelijkheid, zoals wanneer een object is gebouwd, gewijzigd of verwijderd. De formele historie legt vast wanneer deze wijzigingen zijn geregistreerd in het informatiesysteem. Zonder deze historische lagen is het niet mogelijk om berekeningen exact te reproduceren, omdat resultaten afhankelijk kunnen zijn van het tijdstip waarop data is opgevraagd. Met historische ondersteuning kan een berekening worden herleid naar de exacte dataset en toestand die op dat moment geldig was, zonder dat de oorspronkelijke instantiedata opnieuw geleverd hoeft te worden. Vanwege de hierboven beschreven bedenkingen lijkt API

#### 10.3.4 Logboek dataverwerking

Naast API-levering is het noodzakelijk om een logboek voor dataverwerking en een register voor data en berekeningen te organiseren zodat de data ook daadwerkelijk gelogd kan worden in een register. In het logboek wordt vastgelegd welke gegevens wanneer zijn verwerkt, welke bewerkingen zijn uitgevoerd en door welke systemen of processen dit is gebeurd. Dit maakt het mogelijk om de volledige verwerkingshistorie te reconstrueren.

Daarnaast dienen gebruikte scripts en rekenmodellen te worden vastgelegd in een algoritmeregister. Hierin wordt bijgehouden welke algoritmes zijn toegepast, welke versies zijn gebruikt en onder welke voorwaarden deze zijn uitgevoerd. Hierdoor wordt inzichtelijk hoe resultaten tot stand komen.

In de huidige ICT-omgeving van de gemeente Rotterdam is de combinatie van API-levering, logboekregistratie, dataverwerking en een algoritmeregister nog niet ingericht. Het is in de situatie van Schiehaven Noord nog niet mogelijk om berekeningen volledig reproduceerbaar en controleerbaar uit te voeren zonder aanvullende instantiedata. Het organiseren van een samenhangend geheel van dataregistratie, verwerkingslogboeken en algoritmeregisters is een belangrijke randvoorwaarde voor verdere volwassenheid in datagedreven werken. Hierover hebben gesprekken plaatsgevonden tussen ICT-architecten van Geonovum en de gemeente Rotterdam.

11. Indicatoren en rekenmodellen

Zoals beschreven in hoofdstuk 8.4 zijn er indicatoren voor CO2 en hitte. Om hier berekeningen voor

2

te kunnen doen zijn rekenmodellen nog die kg CO2-eq per m BVO kunnen berekenen en de gemiddelde PET, koele plekken en loopgebieden.

#### CO2

Een digitaal rekenmodellen voor CO2 dient te voldoen aan de beschrijving van de Dutch Green Building Council (zie [https://www.dgbc.nl/tools/paris-proof-materiaalgebonden-protocol/](https://www.dgbc.nl/tools/paris-proof-materiaalgebonden-protocol/)). Dit document beschrijft dat een berekening dient te worden uitgevoerd in één van de door Stichting Nationale Milieudatabase erkende rekeninstrumenten ([www.milieudatabase.nl](http://www.milieudatabase.nl)). Bij het opstellen van de berekening dient de meest recente versie van de Nationale Milieudatabase te worden gebruikt en bij de resultaten aan te worden gegeven wat de opstellingsdatum van de berekening is.

#### Hitte

Voor hitte wordt gebruik gemaakt van een gestandaardiseerde hitte-berekening. Hiervoor kan men gebruik maken van de beschreven methodiek van het RIVM. Zie ([https://www.rivm.nl/publicaties/ontwikkeling-standaard-stresstest-hitte](https://www.rivm.nl/publicaties/ontwikkeling-standaard-stresstest-hitte)). Het RIVM geeft met de publicatie invulling aan de wens tot standaardisatie en beschrijft een (standaard) methode voor het berekenen van de hittekaarten op basis van de gevoelstemperatuur, en een leidraad om op basis van deze hittekaarten de mogelijke risico’s te identificeren. Hierbij is er voor gekozen om de hittekaarten te baseren op de gevoelstemperatuur (PET).

12. Functionaliteiten

De gemeente Rotterdam wil in het gebiedsontwikkelingproces Schiehaven Noord ontwerpmodellen, bestaande omgevingsdata, metadata en rekenmodellen gebruiken.

Vanuit Geonovum zijn verschillende functionaliteiten geduid. Afhankelijk van de informatiebehoefte kan een digitale tweeling-as-a-service op verschillende manieren worden ingericht. De functionaliteiten die uit de user stories naar voren komen, betreffen onder andere: simuleren, analyseren, rekenen en visualiseren. Deze functionaliteiten zullen eveneens terugkomen in de uitgewerkte architectuurschetsen en de bijbehorende architectuurkeuzes.

13. Informatieproces

### 13.1 Wat zijn de processtappen en besluitvormingsmomenten om

### tot een oplossing voor het vraagstuk te komen?

Binnen de ruimtelijke ordening in Rotterdam is er een veelheid aan mogelijk te doorlopen procedures. Dit maakt het realiseren van goede groei en het ordelijk doorlopen van het besluitvormingsproces complex. De hoofdlijnen voor besluitvorming bij gebiedsontwikkeling en projecten zijn opgenomen in het Besluitvormingsmodel Ruimtelijke Ontwikkelingen Rotterdam (BRO) en het Openbare Ruimte Planproces (ORP).

Voor de use-case Schiehaven Noord hebben wij het Besluitvormingsmodel Ruimtelijke Ontwikkeling verder uitgewerkt. Voor het openbare ruimte planproces is gebruik gemaakt van de procesplaat zoals geleverd door de gemeente Rotterdam.

#### 13.1.0 Hoofdproces gebiedsontwikkeling:

De hierboven genoemde BRO is de basis geweest voor onderstaand uitgewerkt hoofdproces conform BPMN. De geselecteerde use-cases bevinden zich in de masterplan processtap en hebben uiteindelijk te maken met het een besluitvormingsmoment van de gemeenteraad. Zowel op financieel als op ruimtelijk aspect. De besluitvorming vindt plaats tussen de processtappen.

Proces masterplan: De masterplanfase bestaat uit het doen van onderzoeken het inventariseren en analyseren hiervan. Men brengt de ruimtelijke aspecten in beeld in een ruimtelijke analyse. Op basis van deze input worden ruimtelijk-functionele scenario’s en/of varianten geschetst. Deze varianten worden doorgerekend op verschillende aspecten via een iteratief proces van ‘tekenen en rekenen’. Op basis hiervan komt men tot een voorkeursmodel dat uitgewerkt wordt in een masterplandocument. Deze use-case gaat over CO2 en hittestress en zal zich voornamelijk focussen op onderstaande processtappen.

Subproces advies duurzaamheid: Een advies duurzaamheid kan bestaan uit verschillende onderdelen. Men kan onderzoek doen en of advies geven op de aspecten klimaatmitigatie, circulariteit, klimaatadaptatie, water, vervuiling en biodiversiteit. Dit zijn activiteiten die door de EU Taxonomy zijn geduid. De use-case CO2 is onderdeel van klimaatmitigatie. De use-case hitte is onderdeel van klimaatadaptatie.

Activiteiten advies klimaatmitigatie 1 (consumptie CO2 budget): Binnen het advies klimaatmitigatie kan men een CO2-consumptie berekenen. De objecten die doorgerekend worden zijn gebouwen, ondergrond en wegen. Assets als meubilair en groen worden buiten beschouwing gehouden aangezien deze een kleine CO2-footprint hebben. De grootste verschillen kunnen daarom gemaakt worden in deze assets.

Activiteiten advies klimaatmitigatie 2 (opstellen CO2 budget): Binnen het advies klimaatmitigatie stelt men een CO2-budget op voor Gebiedontwikkeling. Dit CO2 budget geeft de kaders voor een ontwerpende partij.

Subproces advies klimaatadapatie: Binnen het advies klimaatadaptatie zijn de subprocessen advies hittestress, neerslag, overstroming, bodemdaling, droogte en grondwater te onderscheiden.

Activiteiten advies hittestress: Binnen de activiteit hittestress voert men een PET-berekening uit en doet men een schaduwanalyse. Op basis van de gestandaardiseerde hittestress berekening van het RIVM kan men gevoelstemperaturen berekenen voor het toekomstige ontwerp van het plangebied. Op basis hiervan berekent men de gemiddelde gevoelstemperatuur binnen het plangebied. Op basis van BIM-modellen van de nieuwe situatie in combinatie met GEO-modellen van de bestaande omgeving berekent men de schaduwplekken. Schaduwplekken, gevoelstemperatuur en gebouwmodellen zijn input voor het bepalen van koele plekken. De schaduwplek in combinatie met verhard oppervlak geeft inzicht in beschaduwing van loopgebieden.

### 13.2 Wie neemt welke processtap en/of besluit?

Het CO2 budget wordt opgesteld door domeindeskundigen bij de gemeente. Voor Hitte gelden er standaard waarden. De uitwerking van Masterplan wordt gedaan door een ontwerpconsortium. De berekening van de CO2 consumptie en hittestress wordt gedaan door het ontwerpconsortium. De controle van de berekening wordt gedaan door de domeindeskundigen bij de gemeente. De Ambtelijk OpdrachtGever (AOG) voert de procesregie over BRO-producten binnen zijn opdracht en is verantwoordelijk voor doorgeleiden naar bestuur. Doorgeleiden naar college/raad vereist voorafgaand akkoord van alle lijnverantwoordelijken wier bevoegdheden zijn gebruikt bij het opstellen van het BRO-product. Voor CO2 en hitte is dit de duurzaamheidsadviseur. Wanneer het Masterplan voldoet aan vakinhoudelijke kaders, de gebruikte bevoegdheden correct zijn toegepast en het product gereed is voor bestuurlijke behandeling.

Wanneer vakinhoudelijke eisen conflicteren met de opdracht of boven het mandaat van de AOG uitstijgen, wordt dit geëscaleerd naar de lijnverantwoordelijke en directeur die het startbesluit heeft genomen voor integrale herafweging binnen de driehoek inhoud-mensen-middelen. Niveau 1: Afdelings-ManagementTeam → Directie-ManagementTeam (binnen directie) Niveau 2: Tussen programma’s via WAT- en HOE-tafel Niveau 3: Directie Team StadsOntwikkeling DTSO (strategische keuzes, clusterbreed) Niveau 4: Bestuurlijk (college/raad bij beleidswijzigingen)

Het besluit op het totale Masterplan wordt gedaan door de Raad.

### 13.3 Welke inzichten/informatie is daarbij nodig?

Inzichtelijk moet worden gemaakt welke gebouwen, woningen en buitenruimte het ontwerpconsortium voorstelt. En hoe dit past binnen de bestaande omgeving.

Daarnaast dient men inzicht te krijgen in de CO2 consumptie en welke objecten dit in welke mate veroorzaken.

Voor hittestress dient men inzicht te krijgen in de temperatuur en de koele plekken en routes.

In alle gevallen wil men weten hoe de geschetste situatie past in het beleid.

14. Prototyping

### 14.1 Hoe ziet voor de gebruiker(s) het prototype van de digitale

### tweeling eruit?

Momenteel maakt het ontwerpconsortium en de gemeente Rotterdam gebruik van Speckle. Dit is proprietary software waarvoor een commerciële licentie vereist is. De gemeente Rotterdam krijgt hiermee dashboardfunctionaliteit van gebiedsontwikkelingsmodellen en berekeningen in dashboard-vorm.

De open standaard data, geleverd in file of in API, zal in een door de eindgebruiker gewenste visualisatie getoond moeten worden. Een mogelijkheid is om de data in het Open Urban Platform of in de 3D Rotterdam omgeving te tonen. Deze omgevingen beschikken over een visualisatie functionaliteit.

Dit is buiten de scope van deze opdracht.

### 14.2 Welke functionaliteiten heb ik nodig voor de functionele

### architectuur

#### 14.2.0 ADR Raamwerk

#### Besluit 1: We leggen architectuurbesluiten voor Schiehaven Noord vast op basis

#### van een ADR raamwerk

Context: De ADR systematiek is een veel gebruikte manier om op een gestructureerde wijze architectuurbesluiten vast te leggen en te documenteren. Door de methode hier in te brengen geven we een concreet voorbeeld van de mogelijke toepassing.

Alternatieven:

- PSA (Project Start Architectuur) – een compleet PSA Document opstellen. Lijkt erg zwaar voor dit traject.
- Geen architectuur vastleggen. Het lijkt goed om vanuit de use case een verbinding te leggen met de nLDT Referentiearchitectuur om de keuzes die in de use case gemaakt worden te onderbouwen.

Consequenties: Om keuzes te kunnen maken, moet het landschap voldoende in kaart zijn. Dus keuzes kun je pas maken als je een beeld hebt van de alternatieven.

Toelichting: In het begin van het Use case proces is dat misschien nog niet het geval en dan is besluiten nemen op basis van ADR wellicht niet mogelijk.

#### Besluit 2: De nLDT Referentiearchitectuur wordt gevolgd

Context: De Gemeente Rotterdam volgt in zijn IT aanpak de landelijke standaarden en ontwikkelingen en sluit daarbij aan op de ZoN nLDT architectuur. Met deze use case sluiten we daar op aan om interoperabel te blijven.

Alternatieven: gesloten oplossing van consortium. Hiervoor kiezen betekent dat gegevensoverdracht tussen consortium en Gemeente moeilijk of onmogelijk wordt. Dat brengt de informatiepositie van de gemeente in gevaar.

Consequenties: nLDT volgen betekent open standaarden tussen systemen implementeren zodat informatie kan stromen in de keten.

- Dat betekent volgen van Architectuurprincipes van nLDT: [https://geonovum.github.io/NLDT-Architectuur/#H3](https://geonovum.github.io/NLDT-Architectuur/#H3)
- En Implicaties van nLDT: [https://geonovum.github.io/NLDT-Architectuur/#H4](https://geonovum.github.io/NLDT-Architectuur/#H4)

#### Besluit 3: We beschouwen het systeem van de consortium partners van

#### Schiehaven Noord als ‘black box’ en standaardiseren alleen op het

#### koppelvlak tussen dat systeem en de Gemeentelijke systemen.

Context: In de gemeentelijke systemen wil je duidelijke scheiding tussen data, visualisatie en rekenen. Hoe dat binnen de systemen van het consortium is geregeld is minder relevant, zolang de gemeente maar op een eenduidige wijze gegevens via een open standaard kan uitwisselen.

Alternatieven:

- Geen eenduidige, open interface afspreken. Levert in de grotere context veel meerwerk op voor de gemeente want elk project vereist dan maatwerk.
- Geen gegevensuitwisseling regelen tussen consortium en gemeente. Puur vertrouwen op beleidsadviezen zonder data onderbouwing. Dit brengt (te?) veel risico’s met zich mee.

Consequenties: Leveringsspecificaties, protocollen en formaten met elkaar afspreken. Deze zijn nog niet allemaal gestandaardiseerd of uitgewerkt dus dat levert in dit project nog meerwerk op, maar dat betaald zich terug in volgende projecten waar deze standaarden hergebruikt kunnen worden.

#### Besluit 4: Validatie van berekening gebeurt doordat een consortium informatie

#### levert over de uitkomst van de analyse en documentatie van de

#### aannames. Hiermee kan de gemeente beredeneren of de uitkomst

#### acceptabel is, zonder deze zelf helemaal na te kunnen rekenen.

Context: De gemeente wil verantwoording kunnen afleggen over de analyses die uitgevoerd zijn om tot ontwerpbeslissingen in het masterplan te komen. De vraag is op welke wijze deze verantwoording het beste tot zijn recht komt.

Alternatieven:

- Consortium levert ruwe data, specificaties van het algoritme en aannames zodat de gemeente de berekening zelf ook exact uit kan voeren.
- Gemeente stelt rekenmodule (met ingestelde aannames?) beschikbaar aan consortium. (bv Tygron Hittestress module op OUP die De landschapsarchitect kan gebruiken)
- Consortium levert uitkomst van de analyse en documentatie van de aannames. En consortium levert basisdata. Hiermee kan de gemeente in de toekomst vergelijkbare berekeningen doen, zonder de garantie dat het tot precies eenzelfde uitkomst komt. Vooral bedoelt voor optimalisatie in de toekomst als nieuwe berekeningen nodig zijn

Consequenties: Bovenstaande alternatieven hebben consequenties voor het datamanagement en eventueel de compatibiliteit van het rekenmodel.

#### 14.2.1 Schets van bestaande architectuur

Allereerst is er een architectuurschets gemaakt van de huidige situatie bij het ontwerpconsortium en de gemeente Rotterdam.

#### 14.2.2 Schets van gewenste architectuur

Deze schets van de gewenste architectuur beschrijft een momenteel haalbare digitale samenwerking tussen het ontwerpconsortium en de gemeente Rotterdam.


#### 14.2.3 Schets van gewenste architectuur inclusief capabilities

#### 14.2.4 Schets van gewenste architectuur toekomst

Deze schets van de gewenste architectuur beschrijft een toekomstig haalbare digitale samenwerking tussen het ontwerpconsortium en de gemeente Rotterdam.

#### 14.2.5 Schets van gewenste architectuur toekomst met capabilities

15. Concepten en modellen

In dit document is data, rekenmodellen en in mindere mate visualisatie beschreven. De capabilities van een Digitale Tweeling zijn geschetst en interoperabiliteit van data is geadresseerd.

Deze concepten en modellen bieden een kader om een van een werkend prototype naar een technisch robuuste digitale tweeling te groeien. Met het vertalen van een prototype naar een meer technisch ontwerp kan de opgave uitgebreid worden met technisch IT-expertise zoals:

- Digitale Tweelingen Architect
- Data engineer
- Software developer
- Infrastructuur en cloud specialist
- Security Specialist
- Het SPIDER-team. Een eerste aanzet is hiervoor gedaan door de clusterarchitect van de gemeente hierbij te betrekken.


16. Interoperabiliteit en standaarden

Om interoperabiliteit na te streven is in deze rapportage gebruik gemaakt van meerdere standaarden.

BIM gebied: Op Geo gebied: Op uitwisselgebied

- IFC - CityGML/CityJSON - ICDD
- IDS - NEN3610 - OGC API's
- NLCS
- DXF
- MiniGIM

Op Metadata gebied Op proces gebied: Op architectuur gebied:

- DCAT-AP-NL - BPMN - ADR
- PROV -
- Logboek Op datamanagement gebied: dataverwerking Open - Use Case Canvas Telemetry - LOIN
- ISO 19650

17. NLDT referentiearchitectuur

Het basispatroon van de NLDT referentiearchitectuur bestaat uit 4 bouwblokken:

De bouwblokken zou je ook als groepering van Applicatiefuncties kunnen beschouwen. Deze indeling helpt om te onderstrepen dat ook vanuit een applicatie- of systeemperspectief een Digitale Tweeling opgebouwd is uit losse, samenwerkende componenten. De diensten van een rekenmodel moeten bijvoorbeeld afgenomen kunnen worden door verschillende visualisatie oplossingen.

Bij het adopteren van een digitale tweeling helpt de NLDT-architectuur organisaties de technische en organisatorische randvoorwaarden expliciet te maken. Dit omvat afspraken over datastandaarden, API’s, semantiek, toegangsbeheer en governance principes, die de digitale tweeling niet alleen functioneel robuust maar ook maatschappelijk verantwoord en toekomstvast maken. Het is daarom van belang dat de NLDT referentiearchitectuur structureel wordt opgenomen in marktconsultaties en aanbestedingen als onderdeel van de eisen en selectiecriteria. Door leveranciers te vragen om oplossingen te ontwerpen conform de NLDT-architectuur, stimuleren opdrachtgevers de markt om open, interoperabele en modulaire oplossingen te leveren die passen in het bredere ecosysteem en bijdragen aan publieke waarden zoals transparantie, hergebruik, FAIR-data en schaalbaarheid.

Hieronder staat een direct inzetbare paragraaf voor een aanbestedingsdocument voor een digitale tweeling (bijv. marktconsultatie, programma van eisen of gunningscriteria).

De opdrachtgever hanteert de NLDT-referentiearchitectuur als richtinggevend kader voor de ontwikkeling en/of levering van de digitale tweeling. Deze referentiearchitectuur, zoals gepubliceerd door Geonovum, beschrijft de architectuurprincipes, bouwblokken en afspraken die nodig zijn om digitale tweelingen interoperabel, schaalbaar en toekomstvast te realiseren binnen het Nederlandse ecosysteem.

Van inschrijvers wordt verwacht dat zij in hun oplossing aantonen hoe deze aansluit op de NLDTreferentiearchitectuur, onder andere door:

- aandacht voor governance, security, privacy en datatoegang conform publieke waarden.
- een modulaire en uitbreidbare architectuur, waarin componenten uitwisselbaar zijn;
- het toepassen van open standaarden voor data, interfaces en semantiek;
- ondersteuning van koppeling en interoperabiliteit met andere digitale tweelingen en informatiesystemen; Het gebruik van de NLDT-referentiearchitectuur heeft als doel vendor lock-in te voorkomen, hergebruik van data en modellen te stimuleren en samenwerking binnen en tussen organisaties mogelijk te maken. De mate waarin de voorgestelde oplossing aantoonbaar aansluit bij dit architectuurkader kan worden betrokken bij de beoordeling van de inschrijving en/of als randvoorwaarde gelden voor de uitvoering van de opdracht.

18. Marktanalyse en marktconsultatie

In het huidige adviesrapport is nog geen uitwerking opgenomen van de marktanalyse van beschikbare digitale tweelingoplossingen. Ook ontbreekt een vertaling naar het benaderen van marktpartijen, inclusief inkoopvoorwaarden en gunningscriteria in relatie tot de NLDTreferentiearchitectuur en open standaarden. Hierdoor is nog geen systematisch overzicht beschikbaar van bestaande oplossingen en is de wijze waarop marktconsultatie en selectie plaatsvinden nog niet gedefinieerd.

19. Conclusie

Gebiedsontwikkeling verschuift van een traditioneel document- en bestandsgebaseerd proces naar een datagedreven en modelgestuurd proces, waarin ontwerpmodellen, omgevingsdata, metadata en rekenmodellen geïntegreerd worden gebruikt. Dit kan het gebiedsontwikkelproces ondersteunen in snelheid, kwaliteit en inzicht. Dit document heeft inzichtelijk gemaakt wat nodig is om in gebiedsontwikkeling Schiehaven Noord datagedreven te werken. De meest wenselijke situatie, waarin gebruik gemaakt wordt van data bij de bron in een federatief stelsel, is nog niet mogelijk. Wel kunnen er stappen gezet worden richting deze manier van werken.

Op basis van een goede use-case beschrijving is het mogelijk om processen, benodigde informatie en databronnen in kaart te brengen. Er dienen afspraken gemaakt te worden over rekenmodellen en metadata per use-case. Het gebiedsontwikkelingsproces kent vele use-cases. Dit zal een ecosysteem van databronnen en -specificaties, rekenmodellen en metadata vormen.

De praktijk van Schiehaven Noord laat zien dat uitwisseling van data momenteel nog grotendeels plaatsvindt via filelevering in niet afgesproken formaat en inhoud. Dit levert beperkingen voor interne en externe ontsluiting. Het niet afspreken van data-formaat, data-inhoud en levering zorgt ervoor dat de herbruikbaarheid van de data gering is. Door hier afspraken over te maken in ILS, Protocol en BUP kan men deze herbruikbaarheid wel waarborgen. Open standaarden en containerlevering (als ICDD) zijn beschikbaar en zijn belangrijke stappen richting betere structuur en contextbehoud van data. Deze manier van werken voorziet nog niet volledig in realtime ontsluiting en volledige integratie met processen en analyses. Een file-gebaseerde uitwisseling vormt daarmee een tussenfase richting meer geavanceerde vormen zoals API-gestuurde datatoegang waarmee data, en berekening getoond kunnen worden aan derden.

Om API-gestuurde datatoegang te gebruiken is niet alleen data-uitwisseling nodig, maar ook structurele borging van informatie over tijd en verwerking. Dit betekent dat naast data ook formele en materiële historie, logboekregistratie van dataverwerking en een algoritmeregister noodzakelijk zijn om berekeningen reproduceerbaar, controleerbaar en uitlegbaar te maken. Niet elke API die gebruikt is binnen de use-case Schiehaven Noord voorziet hierin. Hier vindt momenteel landelijk nog ontwikkeling in plaats.

De huidige werkwijze in Schiehaven Noord laat een mooie samenwerking zien in datavisualisatie. De gemeente Rotterdam kan hierbij de data van het ontwerpconsortium in een applicatie inzien. Er zijn geen afspraken gemaakt over datalevering. Doordat de contractfase al afgerond is blijkt er weinig mogelijkheid te zijn in verandering van datamodellering en uitwisseling. In toekomstige gebiedsontwikkelingsprocessen kan men de in deze use-case uitgewerkte producten gebruiken om goede afspraken te maken voor informatielevering.

De ICT van de gemeente Rotterdam ondersteunt in een meer optimale data-samenwerking tussen ontwerpende partij of consortium en de gemeente Rotterdam. Echter mist het nog een aantal componenten om API-gestuurde datatoegang van gebiedsontwikkelingsinformatie mogelijk te maken.

## Bijlage 1 – Level of Information Need per object

### CO2

#### Weg

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Buitenruimte Weg Autoweg Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerpers Fietspad informatie Klimaatmitigatie/ experts Voetpad Dimensie 2D Berkening CO2 gemeente Parkeervak Locatie Project Coördinaten Consumptie. Rotterdam OV-baan Voorkomen Abstract (symbolisch) (ImGeo) Parametrische Geen Deeloplevering (Mitchel de (De functionaliteit

- VO Masterplan ontwerper landschapsarchitecten) Alfanumerieke Identificatie IFC-GUID of DXF(HexID) ontwerper) (NLCS)* informatie Informatie Materiaal: asfalt, inhoud betonklinkers, betonstraatstenen, houtsnippers, gebakken klinkers, natuursteen (IMGeo) Documentatie Set van nvt documenten

#### Bodem

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Buitenruimte Bodem Grond Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerpers Zand informatie Klimaatmitigatie/ experts Dimensie 3D Berkening CO2 gemeente Locatie Wereld Coördinaten Consumptie. Rotterdam Voorkomen Abstract (symbolisch) Parametrische Geen Deeloplevering (Mitchel de (De functionaliteit

- VO Masterplan ontwerper landschapsarchitecten) Alfanumerieke Identificatie ? ontwerper) informatie Informatie Materiaal Teelaarde inhoud (compost) Teelaarde (veen/compost)

Documentatie Set van nvt documenten


#### Damwand

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Buitenruimte Damwand Beton Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerpers Staal informatie Klimaatmitigatie/ experts Dimensie 2D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract (symbolisch) Parametrische Geen Deeloplevering (Mitchel de (De functionaliteit

- VO Masterplan) Alfanumerieke Identificatie ? ontwerper) informatie Informatie nvt inhoud Documentatie Set van nvt documenten


#### Sportveld

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Buitenruimte Sportveld Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerpers informatie Klimaatmitigatie/ experts Dimensie 2D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract (symbolisch) Parametrische Geen Deeloplevering (Mitchel de (De functionaliteit

- VO Masterplan) Alfanumerieke Identificatie ?) informatie Informatie Materiaal: Kunstgras inhoud Asfalt Rubber Kunststof Gras Documentatie Set van nvt documenten

#### Gebouwen

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Gebouw Gebouw Laagbouw Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerper Middenbouw informatie Klimaatmitigatie/ experts Hoogbouw Dimensie 3D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract/Symbolisch Parametrische Geen Deeloplevering consortiumpartij/adviesbureau functionaliteit

- VO Masterplan Alfanumerieke Identificatie - informatie Informatie inhoud Documentatie Set van nvt documenten

#### Woning

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Gebouw Gebouw Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerper Woning informatie Klimaatmitigatie/ experts Dimensie 3D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract/Symbolisch Parametrische Geen Deeloplevering consortiumpartij/adviesbureau functionaliteit

- VO Masterplan Alfanumerieke Identificatie - informatie Informatie inhoud Documentatie Set van nvt documenten

#### Gevel

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Gebouw Gevel Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerper informatie Klimaatmitigatie/ experts Dimensie 3D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract/Symbolisch Parametrische Geen Deeloplevering consortiumpartij/adviesbureau functionaliteit

- VO Masterplan Alfanumerieke Identificatie - informatie Informatie inhoud Documentatie Set van nvt documenten

#### Constructie

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Gebouw Constructie Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerper informatie Klimaatmitigatie/ experts Dimensie 3D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract/Symbolisch Parametrische Geen Deeloplevering consortiumpartij/adviesbureau functionaliteit

- VO Masterplan Alfanumerieke Identificatie - informatie Informatie inhoud Documentatie Set van nvt documenten

#### Fundering

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Gebouw Fundering Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerper informatie Klimaatmitigatie/ experts Dimensie 3D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract/Symbolisch Parametrische Geen Deeloplevering consortiumpartij/adviesbureau functionaliteit

- VO Masterplan Alfanumerieke Identificatie - informatie Informatie inhoud Documentatie Set van nvt documenten

#### Wanden

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Gebouw Wanden Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerper informatie Klimaatmitigatie/ experts Dimensie 3D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract/Symbolisch Parametrische Geen Deeloplevering consortiumpartij/adviesbureau functionaliteit

- VO Masterplan Alfanumerieke Identificatie - informatie Informatie inhoud Documentatie Set van nvt documenten


#### Installatie

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Actor Actor Object Decompositie Levering Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies CO2- Gebouw Installatie Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ berekening ontwerper informatie Klimaatmitigatie/ experts Dimensie 3D Berkening CO2 gemeente Locatie Project Coördinaten Consumptie. Rotterdam Voorkomen Abstract/Symbolisch Parametrische Geen Deeloplevering consortiumpartij/adviesbureau functionaliteit

- VO Masterplan Alfanumerieke Identificatie - informatie Informatie inhoud Documentatie Set van nvt documenten


### Hitte

#### Gebouw

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Levering Actor Actor Object Decompositie Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) Hittestress Advies Hittestress Buitenruimte Gebouwen Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid/ experts ontwerpers Bruggen ? informatie / Klimaatadaptatie/ gemeente X ? Dimensie 3D schaduw- Hittestress / Rotterdam Locatie Wereld Coordinaten bepaling Schaduwberekening Voorkomen Abstract & PET berekening  Parametrische Geen hitte-adviseur) (De functionaliteit Deeloplevering landschapsarchitecten) Alfanumerieke Identificatie Geen

- VO Masterplan informatie Informatie Geen inhoud Documentatie Set van nvt documenten

#### Boom

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Levering Actor Actor Object Decompositie Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) PET- Advies Hittestress Buitenruimte Boom Geometrische Detail Generiek gemodelleerd berekening& Duurzaamheid > experts ontwerpers / informatie schaduw- Klimaatadaptatie > gemeente landschaps- Dimensie 3D bepaling Hittestress > Rotterdam architecten Locatie Wereld Coördinaten Schaduwberekening Voorkomen Abstract (symbolisch) & PET berekening Parametrische Geen functionaliteit Deeloplevering  (De Alfanumerieke Identificatie -

- VO Masterplan hitte-adviseur) landschapsarchitecten) informatie Informatie Hoogte / inhoud kroonomtrek? (alleen wanneer dimensie 2D is) Documentatie Set van nvt documenten

#### Maaiveld/Terrein

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Levering Actor Actor Object Decompositie Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) PET- Advies Hittestress Buitenruimte Maaiveld/ Wegdeel Geometrische Detail Generiek gemodelleerd berekening& Duurzaamheid > experts ontwerpers / Terrein Ondersteunend informatie schaduw- Klimaatadaptatie > gemeente landschaps- wegdeel Dimensie 3D bepaling Hittestress > Rotterdam architecten Sppor Locatie Wereld Coördinaten Schaduwberekening Onbegroeid Voorkomen Abstract (symbolisch) & PET berekening terreindeel Parametrische Geen Waterdeel functionaliteit Deeloplevering  (De Ondersteunend Alfanumerieke Identificatie -

- VO Masterplan hitte-adviseur) landschapsarchitecten) waterdeel informatie Informatie - inhoud Documentatie Set van nvt documenten

#### Weg

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Levering Actor Actor Object Decompositie Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies Hittestress Buitenruimte Weg Autoweg Geometrische Detail Generiek gemodelleerd berekening Duurzaamheid > experts ontwerpers Fietspad informatie Klimaatadaptatie > gemeente Voetpad Dimensie 2D Hittestress > Rotterdam Parkeervak Locatie Wereld Coordinaten Schaduwberekening OV-baan Voorkomen Abstract (symbolisch) & PET berekening (ImGeo) Parametrische Geen (De functionaliteit Deeloplevering  landschapsarchitecten) Alfanumerieke Identificatie -

- VO Masterplan hitte-adviseur) (NLCS)* informatie Informatie - inhoud Documentatie Set van nvt documenten

#### Weer

Vereisten Level Of Information Need (Informatiebehoefteniveau)

Waarom Wanneer Wie Wat Hoe Doel Informatie Levering Actor Actor Object Decompositie Mijlpaal (Informatie (Informatie- (Breakdown -ontvanger leverancier) structure) CO2 Advies Hittestress Buitenruimte Weer Luchttemperatuur Geometrische Detail Geen berekening Duurzaamheid > experts ontwerpers (zonne)straling informatie Klimaatadaptatie > gemeente Wind Dimensie nvt Hittestress > Rotterdam Luchtvochtigheid Locatie Wereld Coordinaten Schaduwberekening Zonshoogte Voorkomen nvt & PET berekening Parametrische Geen (De functionaliteit Deeloplevering  landschapsarchitecten) Alfanumerieke Identificatie -

- VO Masterplan hitte-adviseur) informatie Informatie Meteo-data inhoud van weerstations Documentatie Set van nvt documenten


## Bijlage 2 – API Call BAG-PDOK

### 19.1 Bounding Box

Bounding Box voor de API-call

Deze bounding box in JSON (CRS = Rijksdriehoek (RD_NEW)):

{ "type": "FeatureCollection", "name": "Bounding_Box_Buffer_Schiehaven_Noord", "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:EPSG::28992" } }, "xy_coordinate_resolution": 1e-15, "features": [ { "type": "Feature", "properties": { "id": null, "width": 1425.934295, "height": 1221.436944, "area": 1741688.828272, "perimeter": 5294.742479 }, "geometry": { "type": "Polygon", "coordinates": [ [ [ 90152.893502269886085, 434777.840596681518946 ], [ 91578.827797646576073, 434777.840596681518946 ], [ 91578.827797646576073, 435999.277540809474885 ], [ 90152.893502269886085, 435999.277540809474885 ], [ 90152.893502269886085, 434777.840596681518946 ] ] ] } } ] }

Heeft minimale en maximale coördinaten in RD_NEW:

minX = 90152.893502269886085 minY = 434777.596681518946 maxX = 91578.827797646576073 maxY = 435999.277540809474885

Deze zelfde bounding box in WGS_84

minX = 4.445030811399675 minY = 51.897731940012342 maxX = 4.465745803053609 maxY = 51.908873672258657

Het tijdstip van de bevraging: 2026-04-30

### 19.2 2D informatie

#### 19.2.0 Pand

#### BAG PDOK:

Gebaseeerd op PDOK: Basisregistratie Adressen en Gebouwen - OpenAPI specification

In een API bevraging: GET:

[https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?bbox=90152.8935,434777](https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?bbox=90152.8935,434777). 8406,91578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP) SG/0/28992

[https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?bbox=4.445030811399675](https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?bbox=4.445030811399675) ,51.897731940012342,4.465745803053609,51.908873672258657&crs=[http://www.opengis.n](http://www.opengis.n) et/def/crs/EPSG/0/28992

Probleem: Hier werkt datetime niet.

Gebruik maken van de property:

- De documentdatum is de datum waarop het brondocument is vastgesteld, op basis waarvan een opname, mutatie of een verwijdering van gegevens ten aanzien van een object heeft plaatsgevonden.

Alles met een documentdatum na: 2026-04-30 dient bekeken te worden. Levert deze wijziging andere resultaten op?

Een snippet van het resultaat laat zien dat op deze manier ook verblijfsobjecten van gesloopte panden opgehaald worden.

Afgesproken kan worden dat het in een GIS-system de volgende filter toegepast moet worden:

En daarna de bounding box met:

Controle van de documentdatum:

Bijvoorbeeld

Deze panden hebben sindsdien nog een aanpassing gekregen. Meer is niet bekend. Beter is om hier ook het resultaat, de respons, als json mee te geven. Of om het kadaster te benaderen over historische data.

#### BAG Kadaster:

Gebaseeerd op Kadaster: [https://lvbag.github.io/BAG-API/Technische%20specificatie/](https://lvbag.github.io/BAG-API/Technische%20specificatie/) hier bestaat geldigOp

Men kan onderstaande API overeenkomen of loggen:

[https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2/panden?geldigOp=2026-04-](https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2/panden?geldigOp=2026-04-) 30&huidig=true&page=1&pageSize=20&bbox=90152.893502269886085,434777.5966815189 46,91578.827797646576073,435999.277540809474885&statusPand=Pand%20in%20gebruik% 20%28niet%20ingemeten%29&statusPand=Pand%20in%20gebruik&statusPand=Verbouwing%2 0pand&statusPand=Sloopvergunning%20verleend&statusPand=Pand%20buiten%20gebruik& bouwjaar%5Bmin%5D=9999&bouwjaar%5Bmax%5D=9999

#### BGT

PDOK Basisregistratie Grootschalige Topografie - OpenAPI specification

In een API bevraging:

GET:

[https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?bbox=4.445030811399675](https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?bbox=4.445030811399675) ,51.897731940012342,4.465745803053609,51.908873672258657&crs=[http://www.opengis.n](http://www.opengis.n) et/def/crs/EPSG/0/28992

Kan men werken met DateTime:

[https://api.pdok.nl/lv/bgt/ogc/v1/collections/pand/items?bbox=90152.8935,434777.8406,9](https://api.pdok.nl/lv/bgt/ogc/v1/collections/pand/items?bbox=90152.8935,434777.8406,9) 1578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP) SG/0/28992&datetime=2026-04-30T00:00:00Z

#### 19.2.1 Bomen

Begroeidterreindeel

GET:

[https://api.pdok.nl/lv/bgt/ogc/v1/collections/begroeidterreindeel/items?bbox=90152.8935,434777.8406,91578.827](https://api.pdok.nl/lv/bgt/ogc/v1/collections/begroeidterreindeel/items?bbox=90152.8935,434777.8406,91578.827) 8,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/28992&datetime](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/28992&datetime) =2015-01-01T00:00:00Z&limit=500

Respond:

"features": [ { "type": "Feature", "properties": { "bronhouder": "G0599", "creation_date": "2009-01-04T23:00:00Z", "eind_registratie": null, "fysiek_voorkomen": "groenvoorziening", "fysiek_voorkomen_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#FysiekVoorkomenBegroeidTerrein"](http://www.geostandaarden.nl/imgeo/def/2.1#FysiekVoorkomenBegroeidTerrein"), "in_onderzoek": null, "in_onderzoek_leeg": "geenWaarde", "kruinlijn_leeg": "waardeOnbekend", "lokaal_id": "G0599.16fca6c774c436560e050210a7e247d7", "lv_publicatiedatum": "2016-01-17T11:38:23Z", "op_talud": null, "op_talud_leeg": "waardeOnbekend", "plus_fysiek_voorkomen": "gras- en kruidachtigen", "plus_fysiek_voorkomen_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#FysiekVoorkomenBegroeidTerreinPlus"](http://www.geostandaarden.nl/imgeo/def/2.1#FysiekVoorkomenBegroeidTerreinPlus"), "plus_fysiek_voorkomen_leeg": null, "plus_status": null, "plus_status_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#VoidReasonValue"](http://www.geostandaarden.nl/imgeo/def/2.1#VoidReasonValue"), "plus_status_leeg": "geenWaarde", "relatieve_hoogteligging": 0, "status": "bestaand", "status_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#Status"](http://www.geostandaarden.nl/imgeo/def/2.1#Status"), "status_leeg": null, "termination_date": null, "termination_date_leeg": "geenWaarde", "tijdstip_registratie": "2009-01-05T08:06:08Z", "version": "e3c4ed35-b865-3e11-2d7c-a6cd5c7260d3" }, "geometry": { "type": "Polygon", "coordinates": [ [[91480.317, 434769.234 ], [91476.22, 434778.62], [91452.05, 434774.55], [91444.19, 434773.26], [91388.87, 434764.41], [91401.7, 434734.77], [91480.48, 434768.86], [91480.317, 434769.234]] ] }, "id": "1cf90f19-9edb-5480-8beb-e4d5fc1cf4f7" },

Vegetatie_object_lijnen

GET:

[https://api.pdok.nl/lv/bgt/ogc/v1/collections/vegetatieobject_lijn/items?bbox=90152.8935](https://api.pdok.nl/lv/bgt/ogc/v1/collections/vegetatieobject_lijn/items?bbox=90152.8935), 434777.8406,91578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP) SG/0/28992&datetime=2015-01-01T00:00:00Z&limit=500

Respond:

], "features": [], "numberReturned": 0 }

Vegetatie_object_punt

[https://api.pdok.nl/lv/bgt/ogc/v1/collections/vegetatieobject_punt/items?bbox=90152.8935](https://api.pdok.nl/lv/bgt/ogc/v1/collections/vegetatieobject_punt/items?bbox=90152.8935) ,434777.8406,91578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP) SG/0/28992&datetime=2015-01-01T00:00:00Z&limit=500

Respond:

"features": [ { "type": "Feature", "properties": { "bronhouder": "G0599", "creation_date": "2008-01-14T23:00:00Z", "eind_registratie": "2018-10-03T05:13:46Z", "in_onderzoek": null, "in_onderzoek_leeg": "geenWaarde", "lokaal_id": "G0599.16fd01788386dcac9e050210a7e24119", "lv_publicatiedatum": "2017-07-12T08:50:49Z", "plus_status": null, "plus_status_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#VoidReasonValue"](http://www.geostandaarden.nl/imgeo/def/2.1#VoidReasonValue"), "plus_status_leeg": "geenWaarde", "plus_type": "boom", "plus_type_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#TypeVegetatieObjectPlus"](http://www.geostandaarden.nl/imgeo/def/2.1#TypeVegetatieObjectPlus"), "plus_type_leeg": null, "relatieve_hoogteligging": 0, "status": "bestaand", "status_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#Status"](http://www.geostandaarden.nl/imgeo/def/2.1#Status"), "status_leeg": null, "termination_date": null, "termination_date_leeg": "geenWaarde", "tijdstip_registratie": "2008-01-15T09:09:00Z", "type": "niet-bgt", "type_codespace": "[http://www.geostandaarden.nl/imgeo/def/2.1#TypeVegetatieObject"](http://www.geostandaarden.nl/imgeo/def/2.1#TypeVegetatieObject"), "version": "b46234d6-cf68-56d9-32d4-173fa374c4c1" }, "geometry": { "type": "Point", "coordinates": [91556.61, 434798.06] }, "id": "44fc58b1-f02a-5fcd-b767-1113aa653735" },

Vegetatie_object_vlak

[https://api.pdok.nl/lv/bgt/ogc/v1/collections/vegetatieobject_vlak/items?bbox=90152.8935](https://api.pdok.nl/lv/bgt/ogc/v1/collections/vegetatieobject_vlak/items?bbox=90152.8935) ,434777.8406,91578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EP) SG/0/28992&datetime=2015-01-01T00:00:00Z&limit=500

Respond:

], "features": [], "numberReturned": 0 }

### 19.3 3D informatie

PDOK 3D Basisvoorziening - OpenAPI specification

Gebouwen: GET:

[https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/basisbestand_gebouwen/items?bbox=90152.8935,434777.8406,91578](https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/basisbestand_gebouwen/items?bbox=90152.8935,434777.8406,91578) .8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/28992&](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/28992&)

Respond snippet:

{ "type": "Feature", "properties": { "bladnr": "90000_434000", "download_link": "[https://download.pdok.nl/kadaster/basisvoorziening-](https://download.pdok.nl/kadaster/basisvoorziening-) 3d/v1_0/2024/gebouwen/buildings_2024_90000_434000.zip", "download_size_bytes": 3664789, "einddatum": "2024-12-31T23:59:59Z", "jaargang_luchtfoto": 2024, "startdatum": "2024-01-01T00:00:00Z" }, "geometry": { "type": "Polygon", "coordinates": [ [ [90000, 434000 ], [92000, 434000 ], [92000, 436000], [90000, 436000 ], [90000, 434000 ] ] ] }, "id": "d8e1d1e5-f733-5518-85d3-bc646136fda3", "links": [ { "rel": "enclosure", "title": "Download feature", "type": "application/zip", "href": "[https://download.pdok.nl/kadaster/basisvoorziening-](https://download.pdok.nl/kadaster/basisvoorziening-) 3d/v1_0/2024/gebouwen/buildings_2024_90000_434000.zip" } ] }

Gebouwen en terreinen: GET:

[https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/basisbestand_gebouwen_terreinen/items?bbox=90152.8935,4347](https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/basisbestand_gebouwen_terreinen/items?bbox=90152.8935,4347) 77.8406,91578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/2899](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/2899) 2&

Respond snippet:

{ "type": "Feature", "properties": { "bladnr": "90000_434000", "download_link": "[https://download.pdok.nl/kadaster/basisvoorziening-](https://download.pdok.nl/kadaster/basisvoorziening-) 3d/v1_0/2022/volledig/volledig_2022_90000_434000.zip", "download_size_bytes": 17742211, "einddatum": "2022-12-31T23:59:59Z", "jaargang_luchtfoto": 2022, "startdatum": "2022-01-01T00:00:00Z" }, "geometry": { "type": "Polygon", "coordinates": [ [ [90000, 434000 ], [92000, 434000 ], [92000, 436000], [90000, 436000 ], [90000, 434000 ]] ] }, "id": "0d6b7688-80a1-5819-9286-0652a4692212", "links": [ { "rel": "enclosure", "title": "Download feature", "type": "application/zip", "href": "[https://download.pdok.nl/kadaster/basisvoorziening-](https://download.pdok.nl/kadaster/basisvoorziening-) 3d/v1_0/2022/volledig/volledig_2022_90000_434000.zip" } ] }

Digitaal Digitaal Terrein model GET:

[https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_8cm/items?bbox=90152.8935,434777](https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_8cm/items?bbox=90152.8935,434777). 8406,91578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/2899](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/2899) 2&

Respond snippet:

"features": [ { "type": "Feature", "properties": { "bladnr": "0900_4347", "download_link": "[https://download.pdok.nl/kadaster/basisvoorziening-](https://download.pdok.nl/kadaster/basisvoorziening-) 3d/v1_0/2025/dsm8/laz/DSM_0900_4347.laz", "download_size_bytes": 23269386, "einddatum": "2025-12-31T23:59:59Z", "jaargang_luchtfoto": 2025, "startdatum": "2025-01-01T00:00:00Z" }, "geometry": { "type": "Polygon", "coordinates": [ [ [90000, 434000 ], [92000, 434000 ], [92000, 436000], [90000, 436000 ], [90000, 434000 ]] ] }, "id": "d6c9630c-147c-5fca-af19-701c182a2cda", "links": [ { "rel": "enclosure", "title": "Download feature", "type": "application/octet-stream", "href": "[https://download.pdok.nl/kadaster/basisvoorziening-](https://download.pdok.nl/kadaster/basisvoorziening-) 3d/v1_0/2025/dsm8/laz/DSM_0900_4347.laz" } ] },

Rotterdam 3D:

Kent geen API, gaat uit van downloads.

BAG 3D:

[https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_8cm/items?bbox=90152.8935,434777](https://api.pdok.nl/kadaster/3dbasisvoorziening/ogc/v1/collections/digitaaloppervlaktemodel_8cm/items?bbox=90152.8935,434777). 8406,91578.8278,435999.2775&bboxcrs=[http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/2899](http://www.opengis.net/def/crs/EPSG/0/28992&crs=http://www.opengis.net/def/crs/EPSG/0/2899) 2&

IFC:

Kent de documents API.

Voorbeeld:

POST /select-documents Body: { "server_context": "711c0744-0a92-489f-8ca1-13813aa2dee7", "callback": { "url": "[http://localhost:8080/cde-callback-example"](http://localhost:8080/cde-callback-example"), "expires_in": 3600 }, "supported_file_extensions": [ ".ifc", ".ifczip" ]

Zie: [https://github.com/buildingSMART/documents-APIHiermee](https://github.com/buildingSMART/documents-APIHiermee) kunnen totale modellen gedownload worden. Geen snippets mogelijk. Dit is beoogd voor de IFC X ontwikkeling.

## Bijlage 3 – Processes API

Voor Hitte en schaduw:

input:

- pand geometrie
- zonstand (tijd + locatie)

process:

- shadow calculation

Output:

- schaduwpolygons
- of raster (shadow map) -of vector overlay

POST /processes/shadow/execution Body: { "inputs": { "buildings": { "type": "FeatureCollection", "features": [...] }, "datetime": "2026-04-30T12:00:00Z", "location": { "lat": 52.08, "lon": 5.12 } } }

Voor Co2:

Input:

- Geobuwen
- Wegen

Process:

- CO2 calculation

Output:


Voorbeeld:

{ "id": "countFeatures", "title": "Count features", "description": "Count the total number of features from an API Features endpoint.", "version": "0.0.1", "jobControlOptions": ["sync-execute"], "outputTransmission": ["value", "reference"], "inputs": { "uri": { "title": "Features endpoint", "description": "Uri to dataset.", "schema": { "type": "string", "format": "url" } } }, "outputs": { "count": { "id": "Result", "title": "Feature count", "description": "Total number of features provided by OGC API Endpoint.", "schema": { "type": "number", "format": "integer" } } } }

{ "id": "calculateCO2", "title": "Calculate CO2 consumption", "description": "Count the amount of CO2 for a new urban development” "version": "0.0.1", "jobControlOptions": ["sync-execute"], "outputTransmission": ["value", "reference"], "inputs": { "uri": { "title": "Features endpoint", "description": "Uri to dataset.", "schema": { "type": "string", "format": "url" } } }, "outputs": { "count": { "id": "Result", "title": "Feature count", "description": "Total number of features provided by OGC API Endpoint.", "schema": { "type": "number", "format": "integer" } } } }

## Bijlage 4 – file-uitwisseling ontwerp

ISO-10303-21; HEADER; FILE_DESCRIPTION(('ViewDefinition [CoordinationView_V2.0]'),'2;1'); FILE_NAME('gebiedsontwikkeling.ifc','2026-05-5T12:00:00',('Anoniem'),('Geonovum'),'IfcOpenShell', 'ChatGPT',''); FILE_SCHEMA(('IFC4')); ENDSEC; DATA; #1=IFCPERSON($,$,'Anoniem',$,$,$,$,$); #2=IFCORGANIZATION($,'Geonovum',$,$,$); #3=IFCPERSONANDORGANIZATION(#1,#2,$); #4=IFCAPPLICATION(#2,'1.0','ChatGPT IFC Generator','CHATGPT'); #5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,$,$,0); #10=IFCCARTESIANPOINT((0.,0.,0.)); #11=IFCDIRECTION((0.,0.,1.)); #12=IFCDIRECTION((1.,0.,0.)); #13=IFCAXIS2PLACEMENT3D(#10,#11,#12); #14=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#13,$); #20=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.); #21=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.); #22=IFCUNITASSIGNMENT((#20,#21)); #30=IFCPROJECT('3dXAu5K4z2ReY$7xg4KfQ1',#5,'Gebiedsontwikkeling',$,$,$,$,(#14),#22); #40=IFCPROJECTEDCRS('EPSG:28992','Amersfoort / RD New',$,$,$,$,$); #41=IFCMAPCONVERSION(#14,#40,155000.,463000.,0.,1.,0.,1.); #50=IFCLOCALPLACEMENT($,#13); /* UITGEEFBAAR */ #100=IFCCARTESIANPOINT((0.,0.,0.)); #101=IFCCARTESIANPOINT((100.,0.,0.)); #102=IFCCARTESIANPOINT((100.,100.,0.)); #103=IFCCARTESIANPOINT((0.,100.,0.)); #104=IFCPOLYLOOP((#100,#101,#102,#103)); #105=IFCFACEOUTERBOUND(#104,.T.); #106=IFCFACE((#105)); #107=IFCCLOSEDSHELL((#106)); #108=IFCFACETEDBREP(#107); #109=IFCSHAPEREPRESENTATION(#14,'Body','Brep',(#108)); #110=IFCPRODUCTDEFINITIONSHAPE($,$,(#109)); /* VERHARD */ #120=IFCCARTESIANPOINT((120.,0.,0.)); #121=IFCCARTESIANPOINT((220.,0.,0.)); #122=IFCCARTESIANPOINT((220.,100.,0.)); #123=IFCCARTESIANPOINT((120.,100.,0.)); #124=IFCPOLYLOOP((#120,#121,#122,#123)); #125=IFCFACEOUTERBOUND(#124,.T.); #126=IFCFACE((#125)); #127=IFCCLOSEDSHELL((#126)); #128=IFCFACETEDBREP(#127); #129=IFCSHAPEREPRESENTATION(#14,'Body','Brep',(#128)); #130=IFCPRODUCTDEFINITIONSHAPE($,$,(#129)); /* GROEN */ #140=IFCCARTESIANPOINT((240.,0.,0.)); #141=IFCCARTESIANPOINT((340.,0.,0.)); #142=IFCCARTESIANPOINT((340.,100.,0.)); #143=IFCCARTESIANPOINT((240.,100.,0.)); #144=IFCPOLYLOOP((#140,#141,#142,#143)); #145=IFCFACEOUTERBOUND(#144,.T.); #146=IFCFACE((#145)); #147=IFCCLOSEDSHELL((#146)); #148=IFCFACETEDBREP(#147); #149=IFCSHAPEREPRESENTATION(#14,'Body','Brep',(#148)); #150=IFCPRODUCTDEFINITIONSHAPE($,$,(#149)); /* WATER */ #160=IFCCARTESIANPOINT((360.,0.,0.)); #161=IFCCARTESIANPOINT((460.,0.,0.)); #162=IFCCARTESIANPOINT((460.,100.,0.)); #163=IFCCARTESIANPOINT((360.,100.,0.)); #164=IFCPOLYLOOP((#160,#161,#162,#163)); #165=IFCFACEOUTERBOUND(#164,.T.); #166=IFCFACE((#165)); #167=IFCCLOSEDSHELL((#166)); #168=IFCFACETEDBREP(#167); #169=IFCSHAPEREPRESENTATION(#14,'Body','Brep',(#168)); #170=IFCPRODUCTDEFINITIONSHAPE($,$,(#169)); #200=IFCSITE('0A1B2C3D4E5F6G7H8I9J0K',#5,'Uitgeefbaar',$,$,#50,#110,$,.ELEMENT.,$,$,$,$,$); #201=IFCSITE('1A1B2C3D4E5F6G7H8I9J0K',#5,'Verhard',$,$,#50,#130,$,.ELEMENT.,$,$,$,$,$); #202=IFCSITE('2A1B2C3D4E5F6G7H8I9J0K',#5,'Groen',$,$,#50,#150,$,.ELEMENT.,$,$,$,$,$); #203=IFCSITE('3A1B2C3D4E5F6G7H8I9J0K',#5,'Water',$,$,#50,#170,$,.ELEMENT.,$,$,$,$,$); #300=IFCRELAGGREGATES('5A1B2C3D4E5F6G7H8I9J0K',#5,'Project Structure',$,#30,(#200,#201,#202,#203)); ENDSEC; END-ISO-10303-21;


Voorbeeld IFC

Nieuw ontwerp (.dxf)

SECTION 2 HEADER 0 ENDSEC 0 SECTION 2 TABLES 0 TABLE 2 LAYER 70 1 0 LAYER 2 OG_BEBOUWING_WONINGBOUW_LAAGBOUW 70 0 62 7 6 CONTINUOUS 0 ENDTAB 0 ENDSEC 0 SECTION 2 ENTITIES 0 LWPOLYLINE 8 OG_BEBOUWING_WONINGBOUW_LAAGBOUW 90 4 70 1 10 100.000 20 100.000 10 120.000 20 100.000 10 120.000 20 115.000 10 100.000 20 115.000 0 ENDSEC 0 EOF


## Bijlage 5 – ICDD voor file-uitwisseling

Masterplan_Schiehaven_Noord.icdd │ ├── Ontology resources/ │ ├── Container.rdf │ ├── Linkset.rdf ├── Payload documents/ │ ├── BIM/ │ │ └── Ontwerpmodel.ifc │ ├── IDS/ │ │ └── IDS_Schiehaven_Noord.docx │ │ └── IDS_Schiehaven_Noord.ids │ ├── Drawings/ │ │ └── Ontwerpmodel.pdf │ ├── GEO/ │ │ ├── 2D/ │ │ │└── bag_pand_respons_2026.json │ │ │└── bgt_boom_respons_2026.json │ │ │└── bgt_pand_respons_2026.json │ │ ├── 3D/ │ │ │└── 3DBAG_respons_2026.city.json │ │ │└── 3D_basisvoorziening_totaal_respons_2026.city.json │ │ │└── 3D_basisvoorziening_gebouwen_respons_2026.city.json │ │ │└── Digital_Surface_Model_0900_4350.laz │ │ ├── Context/ │ │ │└── Werkgrens_Schiehaven_Noord.json │ │ │└── Invloedsgebied_Schiehaven_Noord.json │ ├── Metadata/ │ │ └── metadata_datasets_Schiehaven_Noord.ttl │ │ └── metadata_provenance_Schiehaven_Noord.ttl │ └── Reports/ │ └── Aantal_Gebouwen_en_BVO_Schiehaven_Noord.docx │ └── Logboek_Dataverwerking.jsonl │ └── Scripts/ │ └── Tel_Gebouwen_en_BVO_rekenmodel.py ├── Payload triples/ │ └── links.rdf ├── Index.rd

## Bijlage 6 – API-overzicht

BGT - [https://api.pdok.nl/lv/bgt/ogc/v1/](https://api.pdok.nl/lv/bgt/ogc/v1/) BAG (kadaster) – [https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2/](https://api.bag.kadaster.nl/lvbag/individuelebevragingen/v2/) BAG (PDOK) - [https://api.pdok.nl/kadaster/bag/ogc/v2/](https://api.pdok.nl/kadaster/bag/ogc/v2/) 3D Basisvoorziening - [https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/](https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/)

## Bijlage 7 IDS

De IDS is gemaakt in de online IDSeditor van ACCA. Hieronder beelden van hoe dit gemaakt is.

## Bijlage 8 PROV-O en Open Telemetry

Voorbeeld PROV-O

@prefix rdam: <[http://data.gemeente.rotterdam.nl/prov/>](http://data.gemeente.rotterdam.nl/prov/>) . @prefix prov: <[http://www.w3.org/ns/prov#>](http://www.w3.org/ns/prov#>) . @prefix foaf: <[http://xmlns.com/foaf/0.1/>](http://xmlns.com/foaf/0.1/>) . @prefix xsd: <[http://www.w3.org/2001/XMLSchema#>](http://www.w3.org/2001/XMLSchema#>) .

\# Bronbestand uit de ICDD-container GEO of BIM en script <urn:icdd:file:bgt_pand_respons_2026.json> a prov:Entity .

<urn:icdd:file:Merwehaven_Stedenbouwkundig_Plan-geo.ifc> a prov:Entity .

<urn:icdd:file:Count_dwellings_with_logbook.py> a prov:Entity .

\# Het proces rdam:pythonRuntime a prov:SoftwareAgent.

rdam:Medewerker_x a prov:Agent, prov:Person; foaf:givenName "[persoon]"^^xsd:string; foaf:mbox <mailto:contact@example.nl>; prov:actedOnbehalfOf rdam:gemeenteRotterdam; .

rdam:gemeenteRotterdam a prov:Agent, prov:Organization; foaf:name "gemeente Rotterdam"; .

rdam:processing_count_Dwelling a prov:Activity ; prov:used <urn:icdd:file:Merwehaven_Stedenbouwkundig_Plan-geo.ifc> ; prov:used <urn:icdd:file:Count_dwellings_with_logbook.py> ;

prov:wasAssociatedWith rdam:pythonRuntime ; prov:wasAssociatedWith rdam:Medewerker_x .

\# Het resultaat <urn:icdd:file:ifc_dwellings_rapport.docx> a prov:Entity ; prov:wasGeneratedBy rdam:processing_count_Dwelling .

Voorbeeld logboek dataverwerking

{ "trace_id": "08eedd5a72354304bb7d51f951ac1b56", "span_id": "4e3e05e0db794e05", "parent_span_id": "608c35fad7214d57", "name": "IFC bestand openen", "start_time": 1781124315537, "end_time": 1781124318741, "status": "Unset", "attributes": {"ifc.file.path": "./Payload documents/BIM/Merwehaven_Stedenbouwkundig_Plan-geo.ifc"}, "resource": null } { "trace_id": "08eedd5a72354304bb7d51f951ac1b56", "span_id": "5f30f98c91d24971", "parent_span_id": "608c35fad7214d57", "name": "Gebouwen tellen", "start_time": 1781124318741, "end_time": 1781124318742, "status": "Unset", "attributes": { "count": 1 }, "resource": null } { "trace_id": "08eedd5a72354304bb7d51f951ac1b56", "span_id": "c88f307dcb1349b3", "parent_span_id": "608c35fad7214d57", "name": "Verdiepingen tellen", "start_time": 1781124318742, "end_time": 1781124318742, "status": "Unset", "attributes": { "count": 52 }, "resource": null } { "trace_id": "08eedd5a72354304bb7d51f951ac1b56", "span_id": "608c35fad7214d57", "parent_span_id": null, "name": "IFC analyse volledige run", "start_time": 1781124315419, "end_time": 1781124318817, "status": "Ok", "attributes": { "dpl.core.processing_activity_id": 14, "ifc.file.path": "./Payload documents/BIM/Merwehaven_Stedenbouwkundig_Plan-geo.ifc", "ifc.file.type": "IFC", "ifc.file.hash": "not_calculated", "analysis.gebouwen": 1, "analysis.verdiepingen": 52, "analysis.woningen": 0, "analysis.type": "ifc_woninganalyse "}, "resource": { "attributes": { "process.executable.name": "python", "process.runtime.version": "3.13.7", "process.runtime.name": "python", "process.os": "Windows", "process.os.version": "10.0.26200", "process.command": "Count_dwellings_with_logbook.py", "process.command_line": "python Count_dwellings_with_logbook.py", "dependency.ifcopenshell.version": "0.8.3.post2", "dependency.ifcopenshell.source": "github.com/IfcOpenShell/IfcOpenShell"} } }
