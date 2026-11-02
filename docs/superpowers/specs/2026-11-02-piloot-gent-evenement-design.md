# Ontwerp — Piloot Gent: vierde levensgebeurtenis-pakket "evenement organiseren" (demo-omvang)

| | |
|---|---|
| **Datum** | 2 november 2026 |
| **Status** | vast (sessie-keuzes: aanbevolen use case; lean demo-omvang — "alleen een paar voorbeelden om de demo te laten draaien") |
| **Scope** | vierde pakket `gent-evenement-organisator` (GT-EVT-01 "Ik organiseer een evenement"): aanvraag voor een evenement op/aan het openbaar domein als transactie, aanlooptijd als nieuwe engine-capaciteit (`timingChecks`), en een kleine curated Gentse Feesten-cache als `dataChecks`-voorbeeld |
| **Niet in scope** | volledige innames-dataset (10k records) of volledige Feesten-kalender · risicoanalyse/milieuvergunning-toetsing · echte evenementenbackoffice |
| **Bronnen** | [stad.gent — evenementen organiseren](https://stad.gent/nl/evenementen/evenement-organiseren) (aanvraag/toelating openbaar domein) · data.stad.gent `gentse-feesten-evenementen-2026` (5.582 events; API-resolvable locaties) · ontwerpen GT-VERH-01/GT-KOT-01 (dataChecks, gisChecks.attribuut, per-pakket contract) |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Levensgebeurtenis | "Ik organiseer een evenement" (`GT-EVT-01`) — organisator (burger/vereniging) die publieke ruimte wil bezetten |
| Nieuwe engine-capaciteit | **`timingChecks`**: datum-slot → aanlooptijd-klasse (`te-laat`/`kort-op-tijd`/`ruim-op-tijd`, `verleden`, `onbekende-datum`) t.o.v. een vaste `referentie` in het manifest — deterministisch (géén klokkijken in de replay), herkomst `afgeleid — timing:…` |
| Termijnen | Illustratief (config-is-data, zoals het mobiliteitspakket): ≤30 dagen te laat (blokkade), 31–90 kort op tijd (waarschuwing), >90 ruim op tijd |
| Transactie | `evenement-aanvragen` → contract `district09-evenementen`, ontvangstbewijs; validaties: aanlooptijd, groot evenement (risicoanalyse-waarschuwing), feestenzone (coördinatie-waarschuwing) |
| Open data (klein) | **5 echte Gentse Feesten-voorbeelden** (naam, locatie, datum, link — locaties geresolved via de publieke GF-API) als cache `fixtures/source/feestenkalender.json`; `dataChecks`-straatmatch op de Feesten-locatiestraten (`inFeestenzone`); info-dienst toont de voorbeelden |
| Simulatie | Vierde dropdown-optie; kaart hergebruikt de LEZ-laag rond de locatie; feesten-voorbeelden als klein infopaneel; mailpakket (`gent-simulatie.html`) bouwt automatisch mee |

### Overwogen alternatieven

| Alternatief | Waarom niet |
|---|---|
| Volledige innames-dataset verwerken (10k) | Gebruiker kiest expliciet demo-omvang; zware cache en polygonen-overlap voegen voor de demo niets toe |
| Feesten-overlap op datum berekenen (bereik-check) | Datumbereik-logica in beslistabellen is niet exact-matchbaar; de zone-check dekt de demo eerlijk mét vermelde vereenvoudiging |
| Kind-naar-school-pakket | Later; evenementen stond als aanbeveling en introduceert de tijd-dimensie |

## Diensten

| Service | Type | Trigger |
|---|---|---|
| `evenement-aanvragen` | inzending (substantial) | organisator + locatie + datum |
| `info-aanlooptijden` | info | altijd |
| `info-gentse-feesten` | info | altijd (echte voorbeelden + link kalender) |
| `info-lez-bezoekers` | info | locatie in LEZ (verkeer van bezoekers/leveranciers) |

Slots: `applicantType`, `address` (locatie), `datum` (type datum, ISO `jjjj-mm-dd`), `typeEvenement` (klein/groot/manifestatie), `openbaarDomein` (ja/nee). gisCheck: LEZ (hergebruik). dataCheck: `feestenkalender` (fallback). timingCheck: `aanlooptijd`.

## Regels (illustratief, pakketdata)

- RE1: organisator + aanlooptijd `ruim-op-tijd`/`kort-op-tijd` → transactie + info's
- RE2: aanlooptijd `te-laat`/`verleden` → géén transactie, Gentinfo (menselijke beoordeling)
- RE3: `typeEvenement=groot` → + waarschuwing risicoanalyse/veiligheid
- RE4: `inFeestenzone=in` → + info-gentse-feesten + waarschuwing coördinatie feesten (zone-vereenvoudiging: check is straatgebonden, niet datumgebonden — vermeld in de uitleg)

## Persona's (zes) en golden set

fien (ruim op tijd, klein → gereed), mo (kort op tijd → waarschuwing), lorne (te laat → blokkade), nathalie (groot → risico-waarschuwing), gil (Botermarkt 1 — feestenzone → waarschuwing), jef (H4-weigering). Golden 6/6; injectieconfig (address/datum/typeEvenement, 24 aanvallen); drempels per manifest; contract `district09-evenementen`.

## Testing

Unit tests: timingChecks (klassen, verleden, onbekende datum, referentie-herkomst), catalog-validatie, feesten-cache match; pinning: Botermarkt 1 in feestenzone; eval 6/6 GO; simulatie-tests + verify_static met vierde optie; mailpakket herbouwt en verifieert.
