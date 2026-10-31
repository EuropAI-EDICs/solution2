# poc-gent — Piloot Gent (EUROPAI WP3): transactionele levensgebeurtenis-assistent

Fase 1 + 2 + 3 (intake → context → GIS → routing → H1 → H2-authenticatie →
Magda-prefill → validatie → H3-concept → documentencontrole → H4-inzending →
ontvangstbewijs en vervolgsamenvatting) van het referentiepakket
`gent-mobiliteit-ondernemer`. Ontwerp:
[`docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md`](../docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md).

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
  Hergebruik), gecached onder `fixtures/source/`.
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
