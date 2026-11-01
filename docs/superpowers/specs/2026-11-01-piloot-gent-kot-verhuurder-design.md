# Ontwerp — Piloot Gent: derde levensgebeurtenis-pakket "kot verhuren" (verhuurder)

| | |
|---|---|
| **Datum** | 1 november 2026 |
| **Status** | ter review (keuzes perspectief/simulatie/aanpak vast; sectiegoedkeuring via doorlooppatroon) |
| **Scope** | derde levensgebeurtenis-pakket `gent-kot-verhuurder` (GT-KOT-01 "Ik verhuur een kot") naast de bestaande twee: kot-melding via het koteloket als transactie, omliggende info-diensten, en één nieuwe generieke engine-capaciteit: **gisCheck-attribuut** (benoemde zone-lookup) |
| **Niet in scope** | echte koteloket-integratie · omgevingsvergunning-toetsing (Vlaams) · kotbelasting-heffing · kotenzoeker voor studenten · real-time datasets |
| **Bronnen** | [stad.gent — studentenkamers verhuren](https://stad.gent/nl/wonen-bouwen/huren-verhuren/studentenkamers-verhuren) (meldplicht koteloket, omgevingsvergunning bij omzetten, conformiteitsattest) · [Kotatgent](https://kot.stad.gent/nl/vind-een-kot) · data.stad.gent `kotzones-gent` (20 zones, versie 2025-12-12, Modellicentie Gratis Hergebruik) · [ontwerp verhuizen-burger](2026-10-31-piloot-gent-verhuizen-burger-design.md) (dataChecks, per-pakket contract/drempels, dropdown) |
| **Sessie-keuzes** | perspectief: **verhuurder** (transactie = meldplicht, niet de zoekende student) · simulatie: **derde optie in de bestaande dropdown** · zone-naam in de engine: **gisCheck-attribuut** (optie A) |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Levensgebeurtenis | **"Ik verhuur een kot"** (`lifeEventCode: GT-KOT-01`) — verhuurder van studentenkamer/studio/(deel van) woning |
| Pakketvorm | Derde data-pakket `packages/gent-kot-verhuurder/`; engine, gates, validatie, submit, eval en injectiesuite zijn al multi-package |
| Nieuwe engine-capaciteit | `gisChecks.attribuut`: bij een match geeft de check de attribuutwaarde van het treffende feature terug (kotzone-naam) i.p.v. `in`/`niet-in`; zonder `attribuut` ongewijzigd gedrag |
| Transactie | `kot-melden`: inzending naar nieuw backoffice-contract `district09-koteloket` mét idempotent ontvangstbewijs; prefill uit slots + `gent:kotregister` (mock, doelbinding) |
| Info-diensten | omgevingsvergunning (bij `omzetten=ja`), conformiteitsattest, kotbelasting 2027, afvalkalender (hergebruik IVAGO-dataCheck) |
| Open data | `kotzones-gent` → laag `gent-kotzone` mét zone-namen (attribuut `kotzone_na`); IVAGO-afvalkalender ongewijzigd hergebruikt |
| Simulatie | Derde optie in de levensgebeurtenis-dropdown; kaartpanel met kotzone rond het kotadres + zone-naam in het infopaneel |

### Overwogen alternatieven

| Alternatief | Waarom niet |
|---|---|
| Student-perspectief (kot zoeker) | Geen gemeentelijke transactie voor de student; de H1–H4-ket en once-only blijven onbenut |
| Zone-naam via dataCheck-stratentabel | Oneerlijk tegenover de bron: zones zijn polygonen, straten kruisen zonegrenzen — precisieverlies en een kwetsbaarder cache |
| Twintig binaire zone-lagen | Geen engine-wijziging maar absurde configuratieruis, en de zone-namen (nodig voor formulier en kaart) ontbreken |
| Beide perspectieven in één pakket | Verdubbelt persona's, golden sets en teksten voor dezelfde datasets; het verhuurderspad dekt de meldplicht volledig |

## 1. Context en doel

Na "herstelwerken als zelfstandige" (GT-MOB-01) en "verhuizen naar Gent" (GT-VERH-01) bewijst een derde pakket de replicatieclaim (REP-01) opnieuw — en voegt er één nieuwe, generieke capaciteit aan toe: **benoemde zones**. De kotzone-dataset dekt de hele stad met twintig benoemde gebieden; het interessante antwoord op "welke regeling geldt voor dit adres?" is daar de zone-naam, niet in/niet-in. De meldplicht via het koteloket is een echte Gentse transactie die perfect op de bestaande inzendingsketen past.

## 2. Diensten en beslislogica

### 2.1 Diensten (manifest `services`)

| Service | Type | Trigger | Inhoud |
|---|---|---|---|
| `kot-melden` | inzending · `vereistAuth` · `minLoA: substantial` | `applicantType=burger` + geldig kotadres | Melding pand/kot bij het koteloket (meldplicht vóór verhuren). Formulier: kotadres (slot), kotzone (gisCheck-attribuut), type studentenhuisvesting (slot), aantal kamers (slot), koteloket-status (authentiek). Documenten: `[]` — het koteloket controleert zelf vóór publicatie |
| `info-omgevingsvergunning` | info | slot `omzetten=ja` | Woning omzetten/verbouwen naar kot vereist een omgevingsvergunning vóór de melding; stedenbouwkundige voorschriften en Vlaamse Codex Wonen |
| `info-conformiteitsattest` | info | verhuurder | Kot krijgt na kwaliteitscontrole een conformiteitsattest; getoond op de kotenzoeker |
| `info-kotbelasting` | info | verhuurder | Kotbelasting vanaf 2027; niet zomaar doorschuiven naar de student |
| `info-afvalkalender` | info | verhuurder | Ophaaldagen per fractie voor het kotadres (hergebruik `dataChecks`/IVAGO) |

### 2.2 Intake-slots

`applicantType` (enum, vraag) · `address` (kotadres, vraag) · `omzetten` (enum ja/nee, verplichte vraag: "Zet u een woning om naar kot(s)?") · `typeKot` (enum kamer/studio/residentie, verplichte vraag) · `bestaandeMelding` (authentiek: `gent:kotregister`). De gisCheck levert `kotzone` (zone-naam).

### 2.3 Validaties (op het meldingsformulier)

- **V1 (waarschuwing) — al gemeld**: `koteloket-status=gemeld` → "Dit adres staat al als gemeld kot genoteerd: beheer uw melding via het koteloket."
- **V2 (waarschuwing) — omzetten zonder vergunning**: `omzetten=ja` → "Een omzettingsvergunning is nodig vóór u het kot verhuurt; vraag die eerst aan (zie info omgevingsvergunning)."
- **V3 (waarschuwing) — residentie**: `type-kot=residentie` → "Grote studentenresidenties krijgen een voorbehandeling via kot@stad.gent vóór de online melding."

### 2.4 Beslistabellen (vorm)

| Regel | when | then |
|---|---|---|
| RK1 | `applicantType=burger` | transactions `[kot-melden]`, info `[info-afvalkalender, info-conformiteitsattest, info-kotbelasting]` |
| RK2 | `applicantType=burger`, `omzetten=ja` | info `+ [info-omgevingsvergunning]` |
| RK3 | `applicantType=burger`, `kotzone=niet-in` | géén kot-melden, alleen info-diensten (vangnet: adres buiten de kotzone-lagen — dekt de hele stad, dus uitzonderlijk) |

Elke regel `uitleg` + `legalBasis` (kotreglement/koteloket, stad.gent). Onbekend adres → bestaand escalatiepad (Gentinfo).

## 3. Engine-uitbreiding: `gisChecks.attribuut`

```json
{"id": "kotzone", "layer": "gent-kotzone", "input": "address",
 "output": "kotzone", "attribuut": "kotzone_na"}
```

- **Adapter** (`adapters/gis_zones.py`): nieuw attribuut per feature in `gis-zones.geojson` (`properties.attribuut`); `load_zones` levert naast ringen per laag ook de attribuut-map (ring → attribuutwaarde). `apply_checks`: check mét `attribuut` en treffende ring → context krijgt de attribuutwaarde (`"Ledeganck"`); géén treffer → `"niet-in"`; herkomst ongewijzigd `afgeleid — gis:gent-kotzone (<versie>)`.
- **Broncache** (`fetch_sources.py`): `LAYERS["gent-kotzone"]` met `attribuut: "kotzone_na"`; `normaliseer` kopieert het attribuut naar `properties` (bestaande lagen ongewijzigd — geen attribuut, geen wijziging).
- **Catalog** (`core/catalog.py`): `attribuut` is een optioneel niet-leeg stringveld; when-sleutels matchen op de output (zone-naam of `"niet-in"`), identiek aan bestaande gis-outputs.
- **Bewust géén** verdere engine-wijzigingen: dataChecks, per-pakket backoffice-contract, per-pakket KPI-drempels, contextZin en de injectie-config bestaan sinds GT-VERH-01.

## 4. Bronnen en fixtures

- `fetch_sources.py --bronnen` haalt `kotzones-gent` binnen (GeoJSON-export, 20 features) → laag `gent-kotzone` (versie `stad-gent-open-data 2025-12-12`) mét `kotzone_na` per feature; `source.meta.json`-entry volgt het bestaande patroon.
- Fixture-adressen: hergebruik de bestaande zeven plus één kot-typisch adres in een andere kotzone (gepin via `--check`; het rapport drukt voortaan ook de kotzone-attribuutwaarde per adres).
- Persona's (zes, gedeelde fixture-ruimte): `wouter` (happy flow: nieuwe kamermelding), `saartje` (adres al gemeld — V1), `gregory` (omzetten=ja — V2), `lea` (residentie — V3), `milan` (adrescorrectie tijdens H1), `karel` (H4-weigering). Elk met wallet (substantial), identiteit en `gent:kotregister`-record (`gemeld` alleen voor saartje).
- `fixtures/injecties.json → pakketten["gent-kot-verhuurder"]`: attack-persona's wouter/milan/karel, vrije slot `address`, overig slot `omzetten` — zelfde vorm en aantallen als het burgerpakket (24 aanvallen).

## 5. Evaluatie en tests

- Golden set (zes scenario's) gepind tegen de échte kotzone-laag; verwachte statussen: wouter `gereed`, saartje `gereed-met-waarschuwing`, gregory `gereed-met-waarschuwing`, lea `gereed-met-waarschuwing`, milan `gereed`, karel `geweigerd`.
- `eval.py --package gent-kot-verhuurder`: golden 6/6, KPI-rapport met manifest-drempels, exit-test, determinisme; `eval.py --injectie --package gent-kot-verhuurder`: 24/24.
- Unit tests: attribuut-gedrag (treffer → naam, geen treffer → `niet-in`, onbekend adres → `onbekend-adres`), fetch-normalisatie met attribuut, catalog-validatie (`attribuut` zonder layer/output faalt), kotzone-pinning per fixture-adres, contextZin-rendering, submit-contract `district09-koteloket`.
- Bestaande pakketten en suites blijven ongewijzigd groen (regressiesignaal).

## 6. Simulatie (derde dropdown-optie)

- `build_simulation.py`: `GENT_PACKAGE_PERSONAS["gent-kot-verhuurder"]` (zes persona's); kaartblok-functie `_kaart_blok_kot` — zelfde vorm als de burgerkaart (grens + kotzone-ringen + kotadres-startpunt) met de zone-naam prominent in `kaart5info`; data `data["gentKot"]`.
- Template: dropdown krijgt de derde optie "GT-KOT-01 · kot verhuren (landlord)"; kaartmode `kot` (intabelle switch, één benoemde zone-laag in plaats van drie); NL/EN via `vertaal_gent.py`-uitbreiding onder de volledigheidstest; `verify_static.mjs` dekt de derde optie (switch, kaart, switch terug).
- Kotzonekleur vast in de template (paars/blauw-gamma naast bestaande legering); legenda-regel per modus.

## 7. Risico's

| Risico | Maatregel |
|---|---|
| Kotzone-lagen overlappen of laten gaten | Echte laag dekt de hele stad; `--check` drukt de attribuutwaarde per fixture-adres; RK3-vingnet vangt `"niet-in"` op als infopad |
| Regelwijzigingen (kotbelasting 2027, vergunningsbeleid) | Configuratie is data: teksten/tarieven in het manifest; wijziging = pakketversie + golden-update |
| Meldingsvorm schuift (koteloket-productiewijziging) | Backoffice-mock + contractnaam zijn manifest-data; productie-integratie blijft expliciet buiten scope |

## 8. Volgorde van werk (globaal; detail in het implementatieplan)

1. `gisChecks.attribuut` (adapter + fetch-normalisatie + catalog + tests)
2. Broncache: kotzone-laag + `--check`-rapport mét attribuutwaarden; adressen pinning
3. Pakket `gent-kot-verhuurder` (manifest, beslistabellen, teksten) + fixtures (zes persona's, `gent:kotregister`, wallets, identiteiten) + golden set
4. Injectie-config; eval groen voor alle drie de pakketten
5. Simulatie: derde dropdown-optie, `_kaart_blok_kot`, vertalingen, `verify_static`
6. README's (poc-gent en simulation) + eindcontrole
