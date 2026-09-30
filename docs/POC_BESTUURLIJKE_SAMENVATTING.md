# Bestuurlijke samenvatting — van regel naar rekenmachine: twee bewezen PoC's en hergebruik van wetgeving

| | |
|---|---|
| **Voor wie** | Bestuur en directie (provincie, gemeenten, GI-beraad / programmaraden) |
| **Datum** | 29 september 2026 · concept voor bespreking |
| **Bronnen** | [POC_RULE_GRAPH.md](POC_RULE_GRAPH.md) (Utrecht), [POC_RULE_GRAPH_EINDHOVEN.md](POC_RULE_GRAPH_EINDHOVEN.md) (Eindhoven), [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md) (landelijke aansluiting), [POC_URBANSTRATEGY_INTEGRATION.md](POC_URBANSTRATEGY_INTEGRATION.md) (stiltegebied-geluid) |

---

## De kern in één alinea

De LDT-toolbox bevat twee werkende proof-of-concepts die laten zien dat
Nederlandse regelgeving **machine-leesbaar, controleerbaar en herbruikbaar**
gemaakt kan worden — zonder dat de AI ooit beslist. PoC-1 (provincie Utrecht)
antwoordt op de vraag *"waar in de provincie kan wat?"*: windturbines,
zonnevelden en nieuwe natuur, met elke claim op de kaart herleidbaar tot een
letterlijk artikelcitaat. PoC-2 (gemeente Eindhoven) ondersteunt de grootste
wetgevingsoperatie van dit moment voor gemeenten — het omzetten van
bestemmingsplannen naar het omgevingsplan — door oude en nieuwe regels
regel-voor-regel te koppelen, met hergebruik van alle conversies die het
college eerder officieel vaststelde. Beide PoC's sluiten aan op
**RegelRecht**, de landelijke open bron van MinBZK die wetgeving als
deterministische beslislogica uitvoert. Onbezonnen is dit niet: geen citaat,
geen regel; geen mens, geen besluit.

## Twee praktijkvraagstukken

**1. "Waar kan wat?" — provincie Utrecht (wind, zon, bos).**
De vraag die iedere provincie en gemeente heeft in de energietransitie en
natuuropgave, is nu beantwoordbaar met een kaart waarvan elk vlak juridisch
onderbouwd is. De verordening wordt per artikel uitgelezen (24 normkaarten
voor wind), alleen de formaliseerbare regels worden rekenregels (de rest gaat
naar de jurist), en de geografische zones uit de officiële
gebiedsinformatie worden samengevoegd tot één opportunity-zone: 859 km² voor
wind, 1168 km² voor zonnevelden, 24 km² zoekgebied nieuwe natuur. Scenario's
("wat als de uitzonderingsbepaling anders wordt toegepast?") zijn
doorgerekend: de grootste beleidshendel voor wind bleek 322 km² extra
mogelijk ruimte. En de kaart maakt conflicten zichtbaar: 95% van het
zoekgebied voor nieuwe natuur ligt tegelijk open voor zonnevelden — een
bestuurlijke afweging die nu op tafel ligt in plaats van te wachten op de
eerste vergunningsaanvraag.

**2. "Hoe verhuizen 311 oude regels naar nieuw recht?" — gemeente Eindhoven.**
Elke gemeente moet haar bestemmingsplannen overzetten naar het omgevingsplan.
Amsterdam schatte er meer dan 1.000 uren per plan mee; landelijk ging het om
honderden medewerkers. De Eindhoven-PoC implementeert de vastgelegde
Amsterdams aanpak en koppelt de 311 oude regels die nog voortleven in het
tijdelijk deel regel-voor-regel aan de 762 nieuwe regels. Cruciaal is het
**hergebruik**: 220 van de 311 koppelingen zijn onderbouwd door conversies
die eerder officieel zijn vastgesteld in wijzigingsbesluiten. De PoC stelt
alleen voor; de status "gekoppeld door AI" bestaat in het systeem gewoon
niet. 70 rijen gaan naar de jurist, eerlijk gemarkeerd.

## Hergebruik van wetgeving — op drie niveaus

**Binnen de eigen organisatie.** Elke formalisatie wordt één keer gemaakt en
daarna steeds hergebruikt: Eindhoven bouwt een groeiende kennisbank van
conversies (nu 274 officiële relaties) waardoor elke volgende
planwijziging sneller en consistenter kan; Utrecht hergebruikt dezelfde
rekenketen voor drie beleidssporen tegelijk.

**Tussen overheden.** De Amsterdamse methode werkt nu ook in Eindhoven; de
Utrechtse verordeningaanpak werkt voor elke provincie. Wie de moeite doet om
een verordening machine-leesbaar te maken, maakt die ook herbruikbaar voor
collega-organisaties met dezelfde opgave — precies het "bouw eens, hergebruik
vaak"-principe uit de Europese tweelingagenda.

**In de landelijke keten.** RegelRecht (MinBZK) bouwt aan het landelijke
corpus van machine-leesbare wetgeving: nu al circa 22.000 wetten, maar nog
**geén enkele gemeentelijke of provinciale verordening**. Onze twee PoC's
kunnen de eerste leveren — het omgevingsplan van Eindhoven en de
omgevingsverordening van Utrecht, als gewone openbare bijdrage via een
controleerbaar werkproces. Eén keer formaliseren betekent daarna: dezelfde
regel ondersteunt de beleidsanalyse, de vergunningscheck en uiteindelijk de
informatievoorziening aan de burger (regels.overheid.nl). Onze
voorbeeldexporten zijn al technisch gevalideerd tegen het officiële
landelijke schema.

## Wat dit bestuurlijk oplevert

- **Snelheid** — de Amsterdamse businesscase: ruwweg twintig keer sneller
  dan handwerk; scenariorekeningen in dagen in plaats van maanden.
- **Weerbaarheid van besluiten** — elk cijfer en elke koppeling is
  herleidbaar tot een letterlijk citaat met wettelijke bron en versie;
  onderbouwing overleeft bezwaar en toetsing.
- **Consistentie** — dezelfde regel levert overal dezelfde uitkomst, en een
  onafhankelijke tweede berekening controleert dat elke run (afwijkingen
  kleiner dan 0,01%).
- **Geen leveranciersafhankelijkheid** — open bron, open standaarden; het
  landelijke corpus is een gewone publieke repository.
- **Zichtbaarheid van afwegingen** — energiedoelen versus natuurdoelen
  worden op één kaart bespreekbaar voor raad, college en burgers.

## Stand van zaken — eerlijk

- **Werkend:** beide PoC's draaien volledig offline en herhaalbaar; een run
  geldt pas als geslaagd als de onafhankelijke validatie op alle niveaus
  slaagt. De voorbeeldexporten naar het landelijke formaat zijn gevalideerd.
- **Nog niet:** de volledige export van beide instrumenten, en de daadwerkelijke
  koppeling met de RegelRecht-engine (nu analyse plus bewijs van haalbaarheid);
  een deel van de officiële geobronnen is alleen via een omweg toegankelijk;
  Urban Strategy-live modelruns en turbine-bronmodellering (slice 2) volgen
  na de huidige offline stiltegebied-screening.
- **Bewust niet:** AI die beslist. Ambigue of onvoldoende onderbouwde regels
  gaan altijd naar de jurist; dat is een vast onderdeel van het ontwerp, geen
  beperking die nog "opgelost" moet worden. Urban Strategy levert alleen
  decision-support bij art. 9.26 (FR-W-11 blijft ambiguous).

## Wat wij bestuurlijk vragen

1. **Ken de werkwijze toe** als standaard voor AI-assistentie bij wet- en
   regelgeving: geen citaat, geen regel; geen mens, geen besluit.
2. **Geef mandaat voor de volledige corpus-export** van de Eindhovense en
   Utrechtse instrumenten en een pilot met de conversie-controle (het
   "equivalentie-orakel"): kleinschalig, dagen tot enkele sprints.
3. **Draag de instrumenten publiek bij** aan het landelijke RegelRecht-corpus
   — eerste gemeente en eerste provincie.
4. **Zet de landelijke aansluiting op de agenda**: de geconstateerde
   beperkingen voor lokale regelgeving (CVDR-herkenning, verwijzingen) bij
   MinBZK inbrengen, aansluiten op de regels.overheid.nl-richting.

## Risico's en beheersing

| Risico | Beheersing |
|---|---|
| AI verzint of mist regels | Citeer-of-onthoud-principe: zonder geverifieerde bron geen regel; afzieningen worden bijgehouden in een openbaar register |
| Bestuurlijke druk richting "autonome AI" | De status "gekoppeld door AI" bestaat technisch niet; de jurittoets staat in elke rapportage als open punt |
| Verkeerde cijfers in besluitvorming | Onafhankelijke tweede berekening bij elke run, met harde marges; bij twijfel geldt "mens nodig" |
| Afhankelijkheid van één landelijk platform | Open standaarden en gewone bestandsformaten; het corpus is vrij hergebruikbaar |
| Verouderde onderbouwing bij wetswijzigingen | Elke claim draagt versie en datum; de komende Utrechtse verordeningwijziging (besluit verwacht november 2026) staat al geagendeerd voor herziening |
