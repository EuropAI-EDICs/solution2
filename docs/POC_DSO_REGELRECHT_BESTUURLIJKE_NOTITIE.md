# Bestuurlijke notitie — DSO-plekinfo versus RegelRecht: deterministische toets voor AI-scenario's

| | |
|---|---|
| **Voor wie** | Bestuur en directie (gemeente Eindhoven, provincie Utrecht, GI-beraad / programmaraden) |
| **Datum** | 19 oktober 2026 · concept voor bespreking |
| **Bronnen** | [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md), [POC_BESTUURLIJKE_SAMENVATTING.md](POC_BESTUURLIJKE_SAMENVATTING.md), technische run: `nldt/simulation/regelrecht/dso_overlap/` |

---

## De kern in één alinea

Wie vandaag op [Regels op de kaart](https://omgevingswet.overheid.nl/regels-op-de-kaart/) op een perceel klikt, krijgt een **overzicht van toepasselijke regels** — nuttig, maar geen herhaalbaar ja/nee over een concreet voorstel. De landelijke DSO-API's (Presenteren voor het omgevingsdocument, Ruimtelijke plannen voor het tijdelijke deel) maken die annotatie machine-leesbaar. **RegelRecht** (MinBZK) kan daar een deel van als deterministische beslislogica uitvoeren. Een eerste meting op twee echte instrumenten — omgevingsplan Eindhoven en omgevingsverordening Utrecht — laat zien hoeveel van de DSO-hit al uitvoerbaar is, en waarom dat voor AI-scenario's bestuurlijk verschil maakt: **AI verkent; de rekenlaag toetst; de mens beslist.**

## Wat we hebben gedaan

1. **DSO Presenteren (pre-productie)** bevraagd voor het Eindhovense omgevingsplan en de Utrechtse omgevingsverordening op een vastgepind RD-punt (zelfde geometrie → zelfde annotaties bij herhaal).
2. Die annotaties **gekoppeld** aan de bestaande RegelRecht-exporten van beide instrumenten (formaliseringsrapport: formalized / unmatched / ambiguous).
3. Optioneel **Ruimtelijke plannen V4** meegenomen als context voor het tijdelijke deel / legacy-plannen.
4. Resultaat vastgelegd in herhaalbare overlap-rapporten (technisch: `nldt/simulation/regelrecht/dso_overlap/out/`).

Dit is géén vervanging van het Omgevingsloket. Het is een **meetbare brug** tussen “wat staat hier op de kaart” en “wat volgt uit formaliseerbare regels voor dit voorstel”.

## Meetresultaat (19 oktober 2026)

Op de bevroren locaties (Presenteren-hit → overlap met RegelRecht):

| Instrument | Locatie (fixture) | Artikelen in DSO-hit | Daarvan uitvoerbaar (formalized) | Aandeel |
|---|---|---|---|---|
| Omgevingsplan Eindhoven | Woensel (proxy-punt) | 811 | **457** | **56%** |
| Omgevingsverordening Utrecht | Domplein | 107 | **7** | **6,5%** |

Ter duiding — over het **hele** instrument (niet alleen wat op één punt valt):

| Instrument | Artikelen in export | Formalized |
|---|---|---|
| Eindhoven (CVDR696400) | 1.074 | 567 |
| Utrecht (CVDR704250) | 427 | 60 |

**Leeswijzer.** “Uitvoerbaar” betekent: er bestaat een goedgekeurde, template-gebaseerde `machine_readable`-sectie die dezelfde feiten altijd tot dezelfde uitkomst leidt, met uitlegbare rekenstappen. De rest blijft **onthouding** (open norm, procedureel, of nog geen template) — bewust geen verzonnen ja/nee.

## Drie lagen — niet door elkaar

| Laag | Bron | Antwoordt op | Determinisme |
|---|---|---|---|
| **1. Annotatie** | DSO Presenteren / plekinfo | Welke regels horen bij deze plek? | Stabiele *retrieval* |
| **2. Toets** | RegelRecht (formalized subset) | Mag dit voorstel, gegeven feiten X? | Stabiele *uitvoering* + trace |
| **3. Verkenning** | AI-scenario's / what-if | Welke varianten zijn het proberen waard? | Zoekruimte; geen juridisch besluit |

Zonder laag 2 gooit AI DSO-tekst en creativiteit door elkaar. Met laag 2 krijgen scenario's een **scorecard**: wat al hard sneuvelt, wat open blijft, en wat de mens moet wegen.

## Voordeel bij AI-scenario's

Bestuurlijk levert dit vijf concrete voordelen:

1. **Rolverdeling.** AI mag ruimte, tijd en ontwerpvarianten voorstellen. De formaliseerbare regels leveren daarna een herhaalbaar oordeel. De LLM formuleert geen “mag het?”-antwoord over wetstekst.
2. **Snellere filter.** Voorstellen die al op formalized artikelen afketsen, hoeven niet verder te worden “beleden” in een narratief. Ambtelijke en bestuurlijke aandacht gaat naar echte afwegingen.
3. **Vergelijkbare scenario's.** Twee AI-paden (jaar A vs B, variant X vs Y) worden op dezelfde feiten en dezelfde engine afgezet. Verschillen komen uit de mutatie, niet uit een andere formulering van dezelfde wet.
4. **Weerbare uitleg.** Scenario-rapporten kunnen artikelnummer + reken-trace tonen naast het voorstel — sterker bij bezwaar, audit en dualiteitscontrole dan een gegenereerde samenvatting van plekinfo.
5. **Eerlijke dekking.** Waar coverage laag is (zoals Domplein: ~6%), is dat zichtbaar. AI-verkenning daar blijft gelabeld als *onthouding*, niet als *toegestaan*. Dat voorkomt schijnzekerheid.

**Samengevat:** AI verkent het ontwerpruimte; RegelRecht op de DSO-hit maakt van een deel daarvan een deterministische toets — zodat scenario's vergelijkbaar, uitlegbaar en niet “juridisch klinkend maar verzonnen” worden.

## Stand van zaken — eerlijk

**Werkend**

- Overlap-pipeline Eindhoven + Utrecht (Presenteren → formaliseringsrapport → rapport).
- Punt-toets: formalized artikelen uit de DSO-hit geëxecuteerd op de TPOD-geo-feiten. Op de fixture-punten: Utrecht 7/7 getoetst; Eindhoven 434 scenario-runs + 23 onthoudingen zonder voorstel, en met het bouwhoogte-voorstel **457/457 getoetst (447 waar / 10 onwaar, 0 onthouding)** — het end-to-end use-case-antwoord op vraag 3.
- Verkenning (laag 3, mechanisch): de variant-sweep over 8 bouwhoogte-stappen (4→20 m) toont de kantelpunten — de ladder loopt van 450 naar 446 "waar", **4 artikelen zijn gevoelig** (22.140, 5.81, 6.44, 6.7). Deterministische onderlaag voor AI-scenarioverkenning.
- Geo-kruisvalidatie: de DSO-puntselectie is punt-in-polygoon gecontroleerd tegen de echte GIO-geometrie uit de aanlevering — Eindhoven 34/34 overeenstemming; Utrecht via geometrie-sweep + naam-afstemming 8/8 (registratie-onafhankelijk).
- OW-uitwisselpakketten via de downloaden-API: GIO-geometrie-adressen (151 GML's voor Eindhoven, 119 voor Utrecht) en de pons-beantwoording — Eindhovens pakket geïnspecteerd: géén pons-objecten; de gebiedsaanwijzing "ruimtelijke regels tijdelijk deel nog in werking" (16 artikelen) is daar de functionele bruidschatgrens.
- Hele-instrument documentstructuur (wId-boom) per instrument in de index: anchoring en toekomstige wId-grounding los van het bevraagde punt.
- Alles geland in de data lake (bronze pakket / silver caches+indices+export / gold runs) voor beide instrumenten.
- Herhaalbare offline-herberekening op gecachte DSO-antwoorden.
- Bestaande RegelRecht-exporten en demo's voor beide instrumenten.

**Nog niet / beperkingen van deze meting**

- Bevraging op **pre-productie**-DSO; 1:1-vergelijking met de publieke productie-viewer vraagt een productie-API-sleutel.
- Eindhoven-locatie is een **Woensel-proxy** (kadastraal perceel uit de plekinfo-URL was via open geocode niet eenduidig te pinnen).
- Utrecht-punt (Domplein) raakt bewust weinig zone-gebonden regels (bijv. art. 5.3 kleine windturbine valt daar niet); coverage is locatie-afhankelijk.
- Uitvoerbaarheid: met een expliciet voorstel (fixture `voorstel/v1`) is de volledige formalized-hit getoetst; zonder voorstel blijven numerieke parameters en scenario's onthouding/scenario. De Utrechtse *artikel*-niveau GIO-koppeling (regel→GIO) blijft registratiezijdig; zones zijn inmiddels registratie-onafhankelijk bevestigd.
- Geen autonome goedkeuring: formalisering blijft cite-or-abstain; mens op de knop blijft staan.

**Bewust niet**

- AI die zelf rechtsgevolgen verbindt.
- Vervanging van bevoegd gezag of van het Omgevingsloket.

## Wat wij bestuurlijk vragen

1. **Ken de driedeling annotatie / toets / verkenning toe** als uitgangspunt voor AI-scenario's in de omgevingswet-praktijk.
2. **Accepteer “onthouding” als volwaardig resultaat** — liever zichtbaar niet-rekenbaar dan een verzonnen besluit.
3. **Geef mandaat voor de volgende technische stap:** de geleverde end-to-end-keten (DSO-feiten → RegelRecht-trace → voorstel-scorecard + kantelpunt-sweep) uitbreiden naar meer bestuurlijk herkenbare use-cases en meer instrumenten (zonevraag Utrecht art. 5.3; andere gemeenten).
4. **Regel productie-DSO-toegang** waar nodig voor vergelijking met wat burgers en ambtenaren in het loket zien.
5. **Blijf bijdragen aan RegelRecht** (MinBZK): lokale regelgeving in het landelijke corpus vergroot hergebruik tussen overheden.

## Risico's en beheersing

| Risico | Beheersing |
|---|---|
| Verwarren van plekinfo met een vergunningsbesluit | Expliciete lagen in rapportage; formulering “annotatie” vs “toets” vs “verkenning” |
| Overclaimen van coverage | Percentages per locatie + status formalized/unmatched in elk rapport |
| AI die open normen invult | Geen `machine_readable` zonder template; open norm → onthouding |
| Afhankelijkheid van API-sleutels / omgeving (PRE vs prod) | Keys buiten de repo; omgeving en sha256 van responses in het rapport |
| Verouderde export t.o.v. actuele consolidatie | Tijdreisparameters DSO vastleggen; periodieke her-export van instrument-YAML |

## Bijlagen (technisch)

- Overlap-index: `nldt/simulation/regelrecht/dso_overlap/out/overlap-index.json`
- Eindhoven-rapport: `…/eindhoven__eindhoven-woensel-proxy.overlap.json`
- Utrecht-rapport: `…/utrecht__utrecht-domplein.overlap.json`
- TPOD/IMOW-index (wId-anchoring, geo-feiten + GIO-adressen, activiteitstructuur, documentstructuur, pons-status): `…/*.tpod-index.json`; punt-toets: `…/*.toets.json`; kansenkaart: [POC_TPOD_IMOW_KANSEN.md](POC_TPOD_IMOW_KANSEN.md)
- Alles in de data lake: `bronze/<poc>/dso-uitwisselpakket`, `silver/<poc>/dso-presenteren`, `silver/<poc>/regelrecht-export`, `gold/<poc>/regelrecht-runs` (sync via `nldt/scripts/lake_sync.py --poc eindhoven --poc utrecht`)
- Aanroep: `python -m nldt.simulation.regelrecht.dso_overlap.compare --instruments eindhoven,utrecht --pakket` (sleutels in `.env`); index + toets: `python -m nldt.simulation.regelrecht.tpod --instruments eindhoven,utrecht --toets` (offline)
- Integratieanalyse RegelRecht: [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md)
