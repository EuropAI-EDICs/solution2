# Bestuurlijke uitleg — wat de AI-pipeline doet met scenario's en what-if (NSPD)

| | |
|---|---|
| **Voor wie** | Bestuur en directie (provincies Zeeland en Oost-Vlaanderen, gemeenten en haven in het North Sea Port District) |
| **Datum** | 17 oktober 2026 · concept voor bespreking |
| **Bronnen** | [POC_BESTUURLIJKE_SAMENVATTING.md](POC_BESTUURLIJKE_SAMENVATTING.md) (Utrecht/Eindhoven), [poc-nspd/README.md](../poc-nspd/README.md) (technische documentatie), [spec](superpowers/specs/2026-10-14-poc-nspd-design.md) |

---

## De kern in één alinea

De NSPD-piloot beantwoordt voor dertien beleidsthema's (wind, zon, bos, water,
wonen, werken, …) dezelfde vraag aan **beide zijden van de grens**: *waar mag
dit, en op grond van welk artikel?* De computer leest de Omgevingsverordening
Zeeland en de Vlaamse plannen (GRUP Zeehavengebied Gent, gewestplan) artikel
voor artikel, knipt de bijbehorende kaarten daaruit, en rekent die om naar één
zonekaart waarin elk vlak terugvalt op een letterlijk citaat. Scenario's en
what-if zijn daarbovenop de **beleidsrekenmachine**: ze laten vooraf zien wat
er verandert als een gekozen regel anders wordt toegepast — niet na de eerste
vergunningaanvraag, maar vóór het besluit. Onbezonnen is dit nog steeds niet:
**geen citaat, geen regel; geen mens, geen besluit.** De AI berekent en stelt
voor; zij signeert en beslist nooit.

## Wat de pipeline met scenario's doet

Een scenario is **geen nieuwe AI-uitvinding maar een beheersbare verandering
van een al vastgestelde regel**. Slechts drie ingrepen zijn mogelijk, en elk
daarvan is een opschuiving van een eerder formeel vastgelegde regel:

1. **Regel laten vallen** — bijvoorbeeld: "wat als het
   concentratielocatiebeleid voor wind (artikel 18.17, bijlage XIV) wordt
   losgelaten?" Het effect is direct zichtbaar: de mogelijk ruimte voor wind
   in het district groeit van 12,2 km² naar 852 km².
2. **Afstand aanpassen** — bijvoorbeeld: "wat als de Natura 2000-uitsluiting
   500 meter eerder begint?" De windruimte krimpt met 15%. Iedereen begrijpt
   dat die 500 meter nergens in de verordening staat; het systeem zegt dat
   zelf ook in het rapport.
3. **Strengere lezing** — bijvoorbeeld de 100-meter-afwegingszone rond
   natuurgebieden niet als aandachtspunt maar als harde uitsluiting
   uitvoeren: 26 km² minder ruimte voor landschapsingrepen.

Drie waarborgen maken dit bestuurlijk betrouwbaar. Ten eerste: **de
rekenmachine herhaalt zichzelf**. Bij elke scenarioberekening wordt de
onveranderde situatie stilletjes opnieuw doorgerekend en vergeleken; wijkt
die herhaling ook maar een duizendste af, dan faalt het rapport. Ten tweede:
**alles wat beweerd wordt, moet in het rapport staan**. De samenvatting
wordt automatisch gecontroleerd op genoemde getallen en artikelnummers —
een tekst die iets claimt dat niet uit de berekening komt, wordt geweigerd.
Ten derde: **de grens is geen lijn maar een vergelijking**. Elk scenario
draait apart voor de Nederlandse en de Vlaamse kant, zodat het district als
één gebied wordt verkend met twee rechtssystemen — precies de
grensoverschrijdende opgave van North Sea Port.

## Wat de pipeline met what-if doet

What-if is de stap vóór het scenario: het **systematisch genereren van de
beleidsvarianten die de moeite van het rekenen waard zijn**. De basisvarianten
komen uit de curator (de mens die de regels heeft vastgelegd); een taalmodel
mag daar aanvullende voorstellen bij doen, maar die komen door precies
dezelfde poorten: onbestaanbare artikelnummers, dubbele varianten en
verzonnen bronnen worden geweigerd en belanden in een openbaar
afgewezen-voorstellen-register. Van iedere geslaagde variant staat in het
rapport: hoeveel ruimte erbij of eraf komt (in km²), hoeveel van het gebied
gelijk blijft, op welke grondslag de variant rust (beleidvariant, uitleg-
variant of verkenning), en een link naar het volledige
grensvergelijkende rapport. In de kaartviewer is dit direct te zien:
grijze vlakken zijn de huidige situatie, groen is wat een variant oplevert,
rood wat hij kost — klik op een laag en het rapport opent.

## Voorbeelden uit de piloot

| Beleidsvraag (what-if) | Effect op mogelijk ruimte |
|---|---|
| Concentratielocatiebeleid wind (NL) losgelaten | + 840 km² |
| Zonnevelden overal behalve Natura 2000 (NL) | + 829 km² |
| Verblijfsrecreatie niet meer beperkt tot badplaatsen (NL) | + 985 km² |
| Natura 2000-uitsluiting 500 m vervroegd (NL, wind) | − 15% |
| 100 m-afwegingszone natuurgebied als harde uitsluiting (NL) | − 26 km² |
| Regionale dijkuitsluiting 250 m verbreed (NL, water) | − 30 km² |
| Turbine-rij-zone aan BE-kant 500 m verbreed | + 15,4 km² |

Waar een thema **geen kaartregels** heeft — de normen zijn er van het type
"emissie-eis", "meldplicht" of "monitorverplichting" — weigert het systeem
een vlak te tekenen en draagt het rapport zelf de inhoud; dat is expliciet
gemarkeerd ("AOI-breed") en het rapport is in de kaartbibliotheek aanklikbaar.

## Voorbehoud en vervolg

Zoals in de Utrecht- en Eindhoven-piloot: **de pijplijn stelt voor, het
bestuur disposeert.** Een scenariouitkomst is een rekenresultaat op
vastgestelde regels en kaarten, geen advies; de menselijke toets is in het
systeem een verplichte, altijd open beslislijn. De volgende stap voor het
district is het kiezen van een beperkt aantal beleidsvragen uit de
hendelslijst hierboven, die door de juristen van beide zijden wordt
betoetst — het systeem maakt die toets prepareerbaar, niet overbodig.
