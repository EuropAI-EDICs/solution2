# poc-gent — Piloot Gent (EUROPAI WP3): transactionele levensgebeurtenis-assistent

Fase 1 + 2 + 3 (intake → context → GIS → routing → H1 → H2-authenticatie →
Magda-prefill → validatie → H3-concept → documentencontrole → H4-inzending →
ontvangstbewijs en vervolgsamenvatting) van het referentiepakket
`gent-mobiliteit-ondernemer`. Ontwerp:
[`docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md`](../docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md).
Architectuur, uitgelijnd met de pilotdefinitie (D3.1 §2.1 "Operational
workflow and human control"): [`ARCHITECTUUR.md`](ARCHITECTUUR.md).

## Twee levensgebeurtenissen (multi-package)

De engine is pakket-onafhankelijk (`--package` op run.py/eval.py); naast het
ondernemerspakket draait het **burgerpakket `gent-verhuizen-burger`**
(GT-VERH-01 "Ik verhuis naar Gent"; ontwerp:
[2026-10-31](../docs/superpowers/specs/2026-10-31-piloot-gent-verhuizen-burger-design.md))
met vier diensten op échte Gentse open data:

- **`bewonerskaart`** (transactie): aanvraag 1e/2e bewonersvergunning volgens
  de echte Gentse voorwaarden (gedomicilieerd in een bewonerszone, één
  kenteken per vergunning, 1e gratis per gezin, 2e €300/jaar). Validaties:
  V1 al een vergunning op het adres (waarschuwing, via mock-bron
  `gent:parkeervergunningen` mét doelbinding) en V2 eigen parkeergelegenheid
  (waarschuwing); een ontbrekend kenteken is de bestaande V0-blokkade.
  Inzending gaat naar backoffice-contract `district09-parkeervergunningen`
  (`submission.contract` per pakket configureerbaar).
- **`info-afvalkalender`**: ophaaldag per fractie voor de straat, uit de
  IVAGO-ophaalkalender 2026–2027 (171.150 rijen, **2.503 straten — de
  volledige dataset**, Modellicentie Gratis Hergebruik) — via de nieuwe
  generieke **`dataChecks`**-capaciteit naast
  `gisChecks`: dataset-lookups op straatnaam mét herkomstlabel en per check
  `unknownPolicy: escalate|fallback` (onbekende straat valt terug op een
  neutrale tekst; het adres zelf escaleert via de GIS-checks).
- **`info-parkeren-tarief`** en **`info-lez-burger`**: zone-afhankelijke info
  (parkeertariefzones; dagenpas bij oudere wagen in de LEZ).

Nieuwe lagen in `fixtures/gis-zones.geojson`: `gent-bewonerszone`
(bewonerszones-gent, 20 features) en `gent-parkeertariefzone`
(parkeertariefzones-gent, 81 features). Burger-persona's (gedeelde
fixture-ruimte): lisa (happy flow Veldstraat), tomas (Gentbrugge, geen
regeling), farah (2e vergunning), noor (garage), emma (geen voertuig →
blokkade), yana (adrescorrectie), robrecht (H4-weigering). De
injectiesuite draait per pakket (`fixtures/injecties.json → pakketten`):
34 aanvallen (ondernemer) + 24 (burger) + 24 (kot), alle met weerstand
geboden.

## Derde pakket: kot verhuren (GT-KOT-01)

`gent-kot-verhuurder` (ontwerp:
[2026-11-01](../docs/superpowers/specs/2026-11-01-piloot-gent-kot-verhuurder-design.md))
— verhuurdersperspectief: **`kot-melden`** als transactie (meldingsplicht
via het koteloket, inzending naar contract `district09-koteloket`) met
waarschuwingen voor al-gemeld (`gent:kotregister`-mock mét doelbinding),
omzetten-zonder-vergunning en studentenresidenties; info-diensten voor
omgevingsvergunning, conformiteitsattest, kotbelasting 2027 en de
IVAGO-afvalkalender. Nieuwe engine-capaciteit **`gisChecks.attribuut`**:
bij een match geeft de check de attribuutwaarde van het treffende feature
terug — de laag `gent-kotzone` (kotzones-gent, 20 benoemde zones, versie
2025-12-12) levert zo de kotzone-nám per adres (Overpoortstraat →
"Sint-Pietersplein"), die ook als formulierbron dient (gis-uitkomsten
zijn toegestane formulierbronnen). Bronkanttekening: de kotzones-dataset
is zélf de zone-indeling van het koteloket/kotatgent (stad data). Het
kotregister kent géén open API of dataset (kot.stad.gent is
antibot-beveiligd, data.stad.gent publiceert het register niet), maar de
**kotenzoeker zelf is publiek** (robots.txt staat inhoud toe): `python3
fetch_sources.py --kotregister` krapt de beschikbare advertenties — 106
uit de 5.130 kotendatabase — naar `fixtures/source/kotregister.json`, en
`gent:kotregister` valt sindsdien terug op die echte cache (adres als
sleutel; persona-fixtures winnen, zie saartje). Het volledige register
blijft een productie-afhankelijkheid (data-overeenkomst District09). Persona's: wouter, saartje, gregory,
lea, milan, karel. `python3 fetch_sources.py --kaart-kot` bouwt de
kotkaart-cache; `--check` drukt voortaan zone-namen.

    python3 run.py --package gent-kot-verhuurder --persona wouter
    ../nldt/.venv/bin/python eval.py --package gent-kot-verhuurder
    ../nldt/.venv/bin/python eval.py --injectie --package gent-kot-verhuurder

    python3 run.py --package gent-verhuizen-burger --persona lisa
    ../nldt/.venv/bin/python eval.py --package gent-verhuizen-burger
    ../nldt/.venv/bin/python eval.py --injectie --package gent-verhuizen-burger
    python3 fetch_sources.py --afval --kaart-burger   # cache verversen (netwerk)

- Configuratie is data: levensgebeurtenis-pakketten onder `packages/`
  (manifest + beslistabellen + golden set), geladen via `core/catalog.py`.
- LLM stelt voor, engine beslist, mens bevestigt: de F1-replay is volledig
  deterministisch; persona-fixtures zijn de replay stand-in voor de
  LLM-seams S1/S2 (LLM-poot komt in een latere fase).
- Bewijs: elke run schrijft `runs/<runId>/run.json` (schema
  `schemas/gent-run.schema.json`) + `events.jsonl` (sha256-ketting).
- F2 (H2–H3): authenticatie via ACM/IDM-mock, prefill uit de Magda-mock in
  MCP-vorm mét doelbinding, zichtbare herkomstlabels (`authentiek`) per
  formulierveld, deterministische validatie (blokkade/waarschuwing) en de
  H3-conceptbeoordeling; weigering van gegevensgebruik stopt de run netjes.
- IAM — EUDI-wallet (2026-10-30): H2 authenticeert standaard via een
  EUDI-wallet-mock conform de repo-walletdoctrine
  ([`nldt/16`](../nldt/16-eid-wallet-identity.md), optie C — mock-first,
  ARF-vormige enveloppen): `adapters/eudi_wallet.py` vraagt presentaties met
  **selectieve onthulling** (alleen `sub`/`loa`/`mandaten`; de naam in de
  fixture verlaat de wallet nooit), verifieert tegen lokale vertrouwensankers
  (fail-closed) en produceert claims in de vorm van
  [`wallet-claims.schema.json`](../nldt/schemas/wallet-claims.schema.json).
  Diensten declareren `minLoA` in het manifest (LoA-gate vóór de
  mandaatcontrole); wie géén wallet heeft, valt terug op ACM/IDM (vrije
  uitweg) — zie persona `nadia` (fallback) en `wim` (LoA `low` → waarborg-
  blokkade + Gentinfo-overname). Mock-beperking: het ACM/IDM-pad modelleert
  géén LoA; productie-ACM/IDM koppelt zijn eigen waarborg (INT-01): het
  ACM/IDM-equivalent moet minimaal hetzelfde `minLoA`-contract claimen,
  anders is `vereiste_loa` op dat pad een dode letter. Plan:
  [`docs/superpowers/plans/2026-10-30-piloot-gent-iam-eudi-wallet.md`](../docs/superpowers/plans/2026-10-30-piloot-gent-iam-eudi-wallet.md).
- F3 (H3 → inzending): documentencontrole per dienst (FR-12; een ontbrekend
  bewijs is een D0-blokkade — zie persona `ilse`), de H4-inzendingspoort
  (weigering stopt netjes: niets ingediend — zie persona `hanne`), inzending
  bij de District09-backoffice-mock (INT-03) mét **idempotent ontvangstbewijs**
  per transactie (FR-16: vaste referentie per canonieke conceptlading) en de
  **vervolgsamenvatting** (`gereed`/`open` → "nog te doen"). SEC-05
  event-masking: `events.jsonl` bevat geen ruwe situatieschets of feitwaarden —
  alleen hashes en namen; het run-artefact blijft volledig (verantwoording +
  audit).

## Kaart & route (open data)

`python3 fetch_sources.py --kaart` bouwt `fixtures/source/kaart.json`: per
kenteken-persona het VKBO/KBO-bedrijfsadres (deterministische selectie uit de
open-registercache — daar staat het kenteken geregistreerd), geocoding
(adrescache → Nominatim/OSM, ODbL; productiepad BeSt Address), de OSRM-route
mét alternatief (OpenStreetMap), de Gentse gemeentegrens (Nominatim-polygoon)
en innames-punten uit de GIPOD-cache. Het Gent-tabblad in de simulatie plot
daaruit het kaartpanel: gemeentegrens, LEZ/autovrij-zones (echte
Gentse lagen), beide routes, innames, en de **door Gent gewenste route** =
minst vermijdbare innames binnen 150 m (innames bij het gedeelde eindpunt zijn
onvermijdelijk en tellen niet mee; bij gelijkspel de snelste route). Maria
(burger zonder voertuigrecord) krijgt geen kaart. In de simulatie staat de startlocatie
al in de basisweergave (dus ook na een reset), tekenen de routes en
innames zich in vanaf de routing-stap en staat het panel naast de
agentlog, ingezoomd op centrum en route.

## Evaluatielaag (F4)

- **KPI-rapport + go/no-go** (`core/kpis.py`): `python3 eval.py` meet KPI-01
  (routingnauwkeurigheid), KPI-02 (regelcorrectheid), KPI-03
  (brontraceerbaarheid), KPI-04 (transactiesucces E2E), KPI-06 (once-only:
  nooit vragen om authentieke slots) en de H-event-consistentie, met de
  drempels uit de function-baseline; `--rapport <pad>` schrijft het
  JSON-rapport. Het zesde criterium (exit-test) draait standaard mee in het
  go/no-go-oordeel.
- **Injectiesuite** (`core/injectie.py`, `fixtures/injecties.json`):
  `python3 eval.py --injectie` draait 34 adversariële aanvallen op de echte
  seams (vrije-tekst-slots, situatieschets, documentnamen) in vier categorieën
  (direct/indirect/tool-misbruik/exfiltratie), telkens tegen een schone
  zuster-run: gebruikersinhoud blijft data (payload alléén als waarde),
  bronraadpleging blijft binnen de zuster-run (deelverzameling), events blijven
  waardevrij (SEC-05) en gegevens van andere persona's blijven afwezig. Een
  onbekend/adversarieel adres escaleert bewust naar Gentinfo (unknownPolicy:
  escalate — nooit gokken).
- **Exit-test** (`core/exit_test.py`): `python3 eval.py --exit` exporteert
  pakket + fixtures naar een schone root en herleidt de golden set daartegen:
  13/13 canonieke uitslagen identiek (REP-01). Modelsubstitutie is in de
  prototypefase modelvrij ("geen model, zelfde uitkomsten"); de
  productievariant volgt bij de LLM-poot.
- **EDIC-registratie**: voorbereid in het
  [F4-plan](../docs/superpowers/plans/2026-10-31-piloot-gent-f4.md) (taak 4);
  commit geblokkeerd op het lopende NOVEX-werk in
  `nldt/recipes/edic-asset-map.json`.

## Gebruik

    python3 run.py --list-personas
    python3 run.py --persona jeroen
    python3 run.py --persona wim                     # LoA-blokkade + Gentinfo-overname
    python3 run.py --persona nadia                   # geen wallet → ACM/IDM-fallback
    python3 run.py --persona sanne --auth acmidm     # klassieke route forceren
    python3 run.py --persona ilse                    # D0: kentekenbewijs ontbreekt → blokkade
    python3 run.py --persona hanne                   # H4-weigering → niets ingediend
    python3 run.py --status --persona sanne          # statusraadpleging (FR-19-mock)
    ../nldt/.venv/bin/python -m pytest tests -q     # volledige testsuite
    python3 eval.py                                  # golden + KPI-rapport + go/no-go
    python3 eval.py --rapport runs/kpi-rapport.json  # KPI-rapport als JSON
    python3 eval.py --injectie                        # adversariële suite (34 aanvallen)
    python3 eval.py --exit                            # config-export + herleiding
    (cd ../simulation && ../nldt/.venv/bin/python build_simulation.py)  # sim-tab 5
    python3 fetch_sources.py --check                 # zone-uitkomsten per adres (offline)

## CLI-uitvoer en statusraadpleging (FR-19)

Na de status- en bevindingregels print de replay per transactie het
ontvangstbewijs en daarna de vervolgsamenvatting; bij H4-weigering volgt de
stopmelding in dezelfde stijl als de H2-weigering:

    status:     gereed
    auth:       eudi-wallet (loa substantial, onthuld: loa, mandaten, sub)
      ontvangst: ontheffing-lez → GENT-822E3972EF6A (geaccepteerd)
      ontvangst: ontheffing-autovrij → GENT-05FEE042406C (geaccepteerd)
      nog te doen:
        Volg de status van je aanvragen via Gentinfo.
    events:     21 (hash-chained, events.jsonl)

Niet-ingediende transacties tonen `niet ingediend (<reden>)` met de reden uit
de vervolgsamenvatting (`open`). Het run-artefact bevat alleen service-id's
(titels staan in het pakket-manifest), dus de CLI print service-id's —
consistent met de `transactie:`-regels bovenaan; de burgerlijke titels staan
in de `gereed`-regels van de vervolgsamenvatting.

`--status` (combineerbaar met `--persona`/`--auth`) is de FR-19-mockvorm: het
herhaalt de deterministische replay — de idempotentiesleutel levert elke keer
dezelfde referentie — in plaats van een echte backoffice-raadpleging:

    python3 run.py --status --persona sanne
    statusraadpleging (sanne):
      ontheffing-lez: ingediend als GENT-822E3972EF6A · geaccepteerd
      ontheffing-autovrij: ingediend als GENT-05FEE042406C · geaccepteerd

    python3 run.py --status --persona hanne
    statusraadpleging (hanne):
      ontheffing-lez: niet ingediend (Je bevestigde de inzending niet — er is niets ingediend.)
      ontheffing-autovrij: niet ingediend (Je bevestigde de inzending niet — er is niets ingediend.)

Productiepad voor statusraadpleging is polling op het backoffice-contract
(INT-06) met statusmapping technisch → burgerlijk, niet replay.

## Fixtures en echte brondata (F1.5)

- `fixtures/personas.json` — persona's incl. edge-cases (onvolledige schets,
  adrescorrectie tijdens H1, lage wallet-waarborg `wim`, geen wallet `nadia`,
  document-ontbreekt `ilse`, H4-weigering `hanne`).
- `fixtures/wallets.json` — EUDI-wallet-mock per persona: PID-attestatie
  (pseudoniem + loa, mét nooit-aangevraagde `naam`-claim) en machtigings-
  attestatie (EBW-stijl), met lokale vertrouwensankers per attestatietype.
- `fixtures/gis-zones.geojson` — **echte Gentse zone-afbakeningen** uit de open
  data van Stad Gent (beide `Modellicentie Gratis Hergebruik`), gecached onder
  `fixtures/source/` mét `source.meta.json` (bron-URL, versie/datum, licentie,
  feature-aantallen):
  - `gent-lez` ← dataset *Lage Emissie Zone Gent* (versie 2026-06-30)
  - `gent-autovrij` ← dataset *Sectoren/voetgangersstraten/autovrij gebied Gent*
    (versie 2026-09-30), gefilterd op het officiële veld `autovrijgebied`
    (klassen 1–5; voetgangersstraten vallen buiten de laag)
- `fixtures/addresses.json` — adrescoördinaten gehaald via OSM Nominatim
  (ODbL, attributie in `source.meta.json`; productiepad: officiële BeSt
  Address Web API, FOD BOSA).
- Verversen (netwerk, expliciete cache-bouwstap — runs blijven offline):
  `python3 fetch_sources.py [--geocode] [--bronnen]`.

De golden set is afgeleid tegen de échte lagen (niet overgenomen uit de
eerdere synthetische fixtures): Korenmarkt 1 → LEZ + autovrij; Sint-Pietersplein
1 → alleen LEZ; Koningin Maria Hendrikaplein 1 (station) → buiten beide.

Broncatalogus (DATA-02 in het klein): `fixtures/source/source.meta.json` legt
per bron de URL's, versie/datum, licentie en filters vast. Stand van de bronnen:

- Stad Gent-zone-lagen (LEZ, autovrij): **echt** (Modellicentie Gratis
  Hergebruik), gecached onder `fixtures/source/`. Idem de burger-lagen
  `gent-bewonerszone` en `gent-parkeertariefzone`, plus de
  IVAGO-afvalophaalkalender 2026–2027 als `dataChecks`-bron
  (`fixtures/source/afvalkalender.json`: de volledige dataset per straat
  gevatted tot modus-ophaaldag per fractie — records-API capt op 100 rijen,
  dus de fetch gebruikt de export-endpoint; `--afval` verversen).
- VKBO: **echt** — keyless OGC Features van `geo.api.vlaanderen.be` (bbox
  Gent), gecached als `fixtures/source/vkbo-gent.json`.
- GIPOD: **echt-of-mock** — bij verversen wordt de publieke LDES geprobeerd
  (fetch-artefact `gipod-gent-echt.json`, niet gecommit); bij falen blijft de
  meegeleverde mock-testdata `gipod-gent.json` de stabiele offline basis.
- Adressen: OSM Nominatim (ODbL) voor cache-bouw; **productiepad is de
  officiële BeSt Address Web API (FOD BOSA)**.
- Magda, ACM/IDM, de EUDI-wallet en de District09-backoffice blijven mock tot
  de echte integraties (INT-01/INT-03).

Geen echte persoonsgegevens; alle persoonlijke gegevens zijn verzonnen persona's.
