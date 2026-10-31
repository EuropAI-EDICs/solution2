# Ontwerp — Piloot Gent: tweede levensgebeurtenis-pakket "verhuizen naar Gent" (burger)

| | |
|---|---|
| **Datum** | 31 oktober 2026 |
| **Status** | ter review (na keuzes uit sessie 2026-10-31) |
| **Scope** | tweede levensgebeurtenis-pakket `gent-verhuizen-burger` naast `gent-mobiliteit-ondernemer`: gemeentelijke regelingen voor burgers (bewonersvergunning, afval, parkeren, LEZ-info) gevoed door echte Gentse open data, inclusief engine-uitbreiding `dataChecks` en een tweede Gent-simulatietab |
| **Niet in scope** | productie-integraties (District09-parkeerbackoffice, echte Magda/ACM-IDM) · LLM-seams live maken · premies/tarieven buiten de vier diensten · historiek-datasets (parkeertariefversies) · real-time data (parkeergaragebezetting) |
| **Bronnen** | [Ontwerp 2026-10-30 transactionele assistent](2026-10-30-piloot-gent-transactionele-assistent-design.md) (architectuur, principes, H1–H5) · [`poc-gent/README.md`](../../poc-gent/README.md) (stand F1–F4) · [stad.gent — bewonersvergunningen](https://stad.gent/nl/mobiliteit-openbare-werken/parkeren/parkeren-op-straat/parkeervergunningen/bewonersvergunningen-voor-parkeren) (regels 2026) · data.stad.gent-datasets `bewonerszones-gent`, `parkeertariefzones-gent`, `afvalophaalkalender-ivago-woongebied-gent-2026-2027` (allen Modellicentie Gratis Hergebruik) |
| **Sessie-keuzes** | use case: **verhuizen naar Gent** (meerdere regelingen achter één levensgebeurtenis) · simulatie: **ja, eigen tab naast het ondernemerstab** · niet-ruimtelijke data: **generiek `dataChecks`-mechanisme in de engine** (optie A), geen statische infoteksten |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Use case | Levensgebeurtenis **"Ik verhuis naar Gent"** (`lifeEventCode: GT-VERH-01`) — eerste life event uit het EUROPAI-pilootplan (naast herstelwerken-als-ondernemer) |
| Pakketvorm | Tweede data-pakket `packages/gent-verhuizen-burger/` (manifest + beslistabellen + golden set); engine, gates, validatie, documenten, submit en eval zijn al multi-package en blijven ongewijzigd in gedrag |
| Nieuwe engine-capaciteit | `dataChecks`: generieke, data-gedreven dataset-lookups naast `gisChecks` (input: adres → straatnaam → lookup in gecachte open data → context-slots mét herkomstlabel), met per check een `unknownPolicy: escalate\|fallback` |
| Regels | Bewonerskaart volgens de echte Gentse voorwaarden: gedomiceleerd in bewonerszone, één kenteken per vergunning, 1e gratis per gezin/adres, 2e €300/jaar (sinds 1-4-2026), eigen parkeergelegenheid beperkt recht |
| Open data | Drie échte Gentse datasets via het bekende data.stad.gent-portaal: `bewonerszones-gent` (20), `parkeertariefzones-gent` (81), IVAGO-afvalophaalkalender 2026-2027 (±171k records: straat × fractie × datum); Modellicentie Gratis Hergebruik, gecached onder `fixtures/source/` mét `source.meta.json` |
| Simulatie | `build_gent()` geparametriseerd; nieuw tabblad `gentBurger` met eigen kaartpanel (bewonerszones, tariefzones, LEZ, startpunt = nieuwe woning), NL/EN via `vertaal_gent.py`-uitbreiding onder de bestaande volledigheidstest |

### Overwegen alternatieven

| Alternatief | Waarom niet |
|---|---|
| **B. Alleen parkeren/bewonerskaart** (smalste transactie) | Werkt, maar toont één regeling; verhuizen bundelt transactie + informatie-diensten en toont daarmee de routing naar meerdere gemeentelijke regelingen — precies de pilotobjective |
| **Afvalinfo statisch in beslistabellen** (optie B uit sessie) | Sneller, maar de engine "weet" dan niets uit de echte IVAGO-data: zwakke brontraceerbaarheid (DATA-01), golden set toetst alleen routing, en het patroon is niet herbruikbaar voor volgende regelingen |
| **C. Live API's + echte LLM-seams er meteen bij** | Buiten de PoC-doctrine (mock-first, deterministische replay, offline runs); de LLM-poot is expliciet een latere fase |
| **Bestaande ondernemerspakket uitbreiden met burger-slots** | Mixt twee levensgebeurtenissen in één pakket: beslistabellen, golden set en teksten worden diffuus; de pakket-scheiding is het demonstratiepunt (configuratie is data) |

## 1. Context en doel

De Gent-piloot (EUROPAI WP3) draait in `poc-gent/` als deterministische replay van de
levensgebeurtenis "herstelwerken als zelfstandige" (LEZ/autovrij-ontheffingen). Het pilootplan
noemt als kerngebeurtenissen óók **verhuizen** — voor burgers de meest raakvlakkende entree op
Gemeente Gent: parkeren, afval, en zoneregels hangen allemaal af van het nieuwe adres. De
huidige PoC bewijst de keten intake → ontvangstbewijs alleen voor ondernemers; dit ontwerp
voegt het eerste **burgerpakket** toe en bewijst dat de engine ongewijzigd meerdere
levensgebeurtenissen aankan, met één nieuwe, generieke capaciteit: niet-ruimtelijke open data
(per straat, niet per polygoon) als first-class bron mét herkomstlabels.

## 2. Diensten en beslislogica

### 2.1 Diensten (manifest `services`)

| Service | Type | Trigger (beslistabel) | Inhoud |
|---|---|---|---|
| `bewonerskaart` | inzending · `vereistAuth` · `minLoA: substantial` | `applicantType=burger` ∧ `zoneBewoners=in` | Aanvraag 1e/2e bewonersvergunning, prefill uit slots + Magda-kenteken + bestaande vergunningen op adres; documenten: geen (domicilie- en voertuigcontrole lopen via authentieke bronnen — de D0-documentenflow blijft gedekt door het ondernemerspakket) |
| `info-afvalkalender` | info | `applicantType=burger` (altijd) | Ophaaldagen per fractie voor de straat (uit `dataChecks`), met fallback-tekst bij onbekende straat |
| `info-parkeren-tarief` | info | `zoneBewoners=niet-in` ∧ `zoneTarief=in` | Geen recht op bewonerskaart; tariefzone-uitleg + doorverwijzing stad.gent |
| `info-lez-burger` | info | `zoneLez=in` | Dagenpas-advies bij oudere wagen; hergebruik bestaande `gent-lez`-laag (één laag voedt twee regelingen) |

Beslistabellen volgen het bestaande when/then-formaat (`when`-sleutels zijn slot-namen en
GIS/dataCheck-outputs; `then.transactions`/`then.info` verwijzen naar service-id's; per regel
`uitleg` + `legalBasis`). Geen vuurregel → `escalatie` naar Gentinfo (bestaand `unknownPolicy:
escalate`).

### 2.2 Bewonerskaart-regels en validaties (manifest `validaties`, per dienst)

Regels conform [stad.gent](https://stad.gent/nl/mobiliteit-openbare-werken/parkeren/parkeren-op-straat/parkeervergunningen/bewonersvergunningen-voor-parkeren). De validatie-matcher gebruikt exacte gelijkheid per `wanneer`-sleutel (bestaand mechanisme), dus bronnen leveren afgeleide enum-waarden in plaats van aantallen:

- **V1 (waarschuwing) — al een vergunning op het adres**: `bestaandeVergunningen=aanwezig` → "dit wordt de 2e bewonersvergunning (€300/jaar, tarief 2026)". Gevoed door nieuwe mock-bron `gent:parkeervergunningen` (per adres, levert afgeleide waarde `aanwezig`/`geen`, doelbinding vastgelegd in `authenticSources`).
- **V2 (waarschuwing) — eigen parkeergelegenheid**: slot `parkeergelegenheid=ja` (intake-vraag) → recht beperkt tot hooguit een tijdelijke vergunning.
- **V3 (blokkade) — geen voertuig**: `kenteken=onbekend` uit de Magda-prefill (mock levert geen kenteken) → bewonerskaart kan niet (vergunning koppelt aan exact één kenteken).

### 2.3 Intake-slots (`contextSchema.slots`)

`applicantType` (enum, vraag) · `address` (string, vraag) · `parkeergelegenheid` (enum ja/nee,
verplichte intake-vraag via `open_questions`) · `vehicle` (kenteken, authentiek: `magda:kenteken`)
· `bestaandeVergunningen` (authentiek: `gent:parkeervergunningen`). De intake-gate vraagt alleen
wat niet al in een bron staat (bestaand beginsel); het formulier toont de antwoorden pas waar
ze doorwerken (V2).

## 3. Nieuwe engine-capaciteit: `dataChecks`

Spiegel van `gisChecks`, in het manifest naast de bestaande velden:

```json
"dataChecks": [
  {
    "id": "afvalkalender",
    "dataset": "ivago-ophaalkalender",
    "input": "address",
    "outputs": ["afvalRest", "afvalPmd", "afvalGlas", "afvalPapier"],
    "unknownPolicy": "fallback"
  }
]
```

- **Uitvoering**: nieuwe adapter `adapters/data_lookups.py`, aangeroepen vanuit `core/context.py::build` en na H1-correctie (zelfde plekken als `apply_checks`): normaliseer de straatnaam uit het adres (kadasterstripping: huisnummer, gemeente, casing/diakritiek), zoek op in `fixtures/source/afvalkalender.json` (cache: straatnaam → per fractie weekdag + eerstvolgende datum(s)), schrijf uitkomsten als context-slots met herkomst `{"label": "afgeleid", "bron": "dataset:ivago-ophaalkalender (2026-2027)"}`.
- **`unknownPolicy`**: `fallback` (onbekende straat → outputs `onbekend`, neutrale tekst in de info-service: raadpleeg IVAGO/Recycle!) versus `escalate` (default, gelijk aan GIS). Afval is beslissend-nee: een onbekende straat mag de run nooit blokkeren; het adres zelf blijft escalerend via de GIS-checks.
- **Catalog-validatie** (`core/catalog.py`): `input` moet een bestaand slot zijn; `dataset` moet geregistreerd staan in `fixtures/source/source.meta.json`; `outputs` mogen niet botsen met bestaande slotnamen of GIS-outputs; `unknownPolicy ∈ {escalate, fallback}`.
- **Bewust géén** algemene query-taal: één lookup per (dataset, input, outputs) — het patroon is herbruikbaar voor toekomstige regelingen (bijv. school-aanwijzingszones) zonder de determinisme- en auditgaranties op te geven.

## 4. GIS-lagen en broncache

- Twee nieuwe lagen in `fixtures/gis-zones.geojson` (features mét `properties.layer` + `properties.versie`): `gent-bewonerszone` (uit `bewonerszones-gent`) en `gent-parkeertariefzone` (uit `parkeertariefzones-gent`); LEZ-laag hergebruikt.
- `gisChecks` in het manifest: `zoneBewoners` (input `address`, laag `gent-bewonerszone`), `zoneTarief` (`gent-parkeertariefzone`), `zoneLez` (`gent-lez`).
- `fetch_sources.py --bronnen` haalt de twee zone-datasets en de IVAGO-kalender binnen via dezelfde GeoJSON/export-endpoints als LEZ/autovrij (zelfde ODS-portaal), bouwt `afvalkalender.json` (alleen straten die in `addresses.json` voorkomen — cache klein houden; runs blijven offline deterministisch) en vult `source.meta.json` aan (dataset-id, URL, versie/datum, licentie, filterbeschrijving).
- Golden-setadressen worden — F1.5-doctrine — afgeleid tegen de échte lagen: ≥1 adres in bewonerszone, ≥1 alleen in tariefzone, ≥1 buiten beide, ≥1 in LEZ.

## 5. Kleine engine-aanpassingen (targeted)

1. `core/submit.py`: hardcode `BACKOFFICE_CONTRACT = "district09-vergunningen"` → per-pakket `submission.contract` uit het manifest (default huidige waarde → ondernemerspakketbyt-gedrag onveranderd). Nieuw contract: `district09-parkeervergunningen`.
2. `core/context.py::summary`: hardcoded slotnamen (`applicantType/activity/address`) → generieke weergave over alle gevulde slots met hun `vraag`-labels uit het manifest, zodat burgerslots (`parkeergelegenheid`) vanzelf renderen.
3. `core/kpis.py`: drempels per pakket configureerbaar (bijv. baseline-bestand per packageId; default = huidige waarden) — de mobiliteitsdrempels blijven het referentiepunt, het burgerpakket begint met dezelfde eisen.
4. `core/exit_test.py`: exportlijst breidt uit met `afvalkalender.json` en de nieuwe zone-lagen (herleiding golden set tegen de schone export blijft de REP-01-maatstaf).

Geen van deze aanpassingen verandert gedrag van het bestaande pakket; de volledige bestaande
testsuite moet ongewijzigd groen blijven als regressiesignaal.

## 6. Persona's en fixtures

Nieuwe burger-persona's in de gedeelde `fixtures/personas.json`, elk volledig in
`fixtures/wallets.json`, `identiteiten.json`, `magda.json` (kenteken; plus de nieuwe tool-bron
`gent:parkeervergunningen` — in de PoC bedienen alle authentieke-bron-tools dezelfde
Magda-mockvorm met doelbinding):

| Persona | Situatie | Dekking |
|---|---|---|
| `lisa` | happy flow: verhuist naar adres in bewonerszone | bewonerskaart-transactie + afvalinfo + ontvangstbewijs |
| `tomas` | buiten bewonerszone, wél tariefzone | alleen info-diensten (geen transactie) |
| `farah` | al een vergunning op het nieuwe adres | V1-waarschuwing 2e vergunning €300 |
| `noor` | eigen garage | V2-waarschuwing tijdelijk recht |
| `emma` | geen voertuig in Magda | V3-blokkade, nette uitleg |

Bestaande edge-persona's krijgen burgerequivalenten voor de golden set: **`yana`** (adrescorrectie
tijdens H1 — verhuist binnen Gent naar een ander zone-uitkomst-adres) en **robrecht** (H4-weigering
→ niets ingediend), zodat het burgerpakket dezelfde veiligheidsgaranties aantoont als het
ondernemerspakket. `fixtures/injecties.json`: tijdens implementatie verifiëren dat
de adversariële aanvallen óók de nieuwe slots (address-varianten, parkeergelegenheid) dekken;
anders burger-injecties toevoegen in de bestaande categorieën.

## 7. Simulatie (tab 6 `gentBurger`)

- `simulation/build_simulation.py::build_gent()` → geparametriseerd (`package_id`, root, persona-selectie); nieuw datablok `data["gentBurger"]` naast `data["gent"]`.
- Kaartpanel: gemeentegrens, bewonerszones, tariefzones (nieuwe lagen), LEZ, startpunt = nieuwe woning (personaadres). Geen routes/innames — dat is ondernemersmobiliteit; de burgerkaart toont regeling-zones.
- Panelen/opbouw volgen het bestaande Gent-tab (per-tab kop, agentlog, kaart naast de log, NL/EN-toggle); `simulation/vertaal_gent.py` uitbreiden — de volledigheidstest (`test_vertaal_gent.py`) dwingt af dat elke getoonde tekst vertaald is.
- Nieuwe personen en teksten krijgen geen eigen vertaalmechanisme: zelfde woordenboekpatroon + `*En`-twins.

## 8. Evaluatie en tests

- `eval.py --package gent-verhuizen-burger`: golden set (uitkomsten exact: outcome, transactions, info, status), KPI-rapport met per-pakket drempels, exit-test, determinisme-check — alle bestaande maatstaven, geen nieuwe categorie.
- Nieuwe unittests naar bestaand voorbeeld: `tests/test_data_lookups.py` (straatnormalisatie, onbekend → fallback, herkomstlabel), catalog-testvormen voor `dataChecks`-validatie (kapotte varianten), submit-contract per pakket, generieke `summary`, gis-zonetests voor de twee nieuwe lagen (`test_gis_zones.py`-stijl).
- Acceptatie: bestaande suite groen; golden set 100% tegen de échte lagen; exit-test herleidt 100%; simulatiebouwtab bouwt met beide tabs; `fetch_sources.py --check` toont zone-uitkomsten per adres inclusief bewonerszone/tariefzone.

## 9. Risico's en bewaking

| Risico | Maatregel |
|---|---|
| IVAGO-dataset is groot (±171k records) en per ronde geordend | Cache bouwt alleen de straten uit `addresses.json` (deterministisch, klein); versie/datum in `source.meta.json`; kalenderjaar-wissel = expliciete cache-verversing |
| Bewonerszone/tariefzone overlappen of adressen vallen in geen van beide | Golden set kiest adressen met eenduidige uitkomsten tegen de echte lagen; overlappende zones zijn geen probleem (beslistabellen matchen onafhankelijk) |
| Regels wijzigen (tarief 2e kaart, zoneherindeling) | Configuratie is data: tarief/tekst in het manifest, zoneversie in `source.meta.json`; wijziging = nieuw pakketversietje + golden-setupdate |
| Gedeelde persona-ruimte groeit | Persona's blijven uniek-geïdentificeerd met edge-labels; het burgerpakket refereert alleen eigen persona's in manifestteksten en golden set |

## 10. Volgorde van werk (globaal; detail in het implementatieplan)

1. Broncache + lagen (`fetch_sources.py`, `source.meta.json`, gis-zones, adresuitbreiding)
2. `dataChecks` + adapter + catalog-validatie + summary-generiek
3. Pakket `gent-verhuizen-burger` (manifest, beslistabellen, teksten) + fixtures (persona's, magda incl. `gent:parkeervergunningen`, wallets, identiteiten)
4. Submit-contract per pakket + KPI-drempels per pakket + exit-test-uitbreiding
5. Golden set + tests + eval groen
6. Simulatie: parametrisering + tab `gentBurger` + vertalingen + volledigheidstest
7. README-updates (poc-gent en simulatie)
