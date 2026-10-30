# poc-gent — Piloot Gent (EUROPAI WP3): transactionele levensgebeurtenis-assistent

Fase 1 + 2 (intake → context → GIS → routing → H1 → H2-authenticatie →
Magda-prefill → validatie → H3-concept) van het referentiepakket
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

## Gebruik

    python3 run.py --list-personas
    python3 run.py --persona jeroen
    python3 run.py --persona wim                     # LoA-blokkade + Gentinfo-overname
    python3 run.py --persona nadia                   # geen wallet → ACM/IDM-fallback
    python3 run.py --persona sanne --auth acmidm     # klassieke route forceren
    ../nldt/.venv/bin/python -m pytest tests -q     # volledige testsuite
    python3 eval.py                                  # golden-set evaluatie
    (cd ../simulation && ../nldt/.venv/bin/python build_simulation.py)  # sim-tab 5
    python3 fetch_sources.py --check                 # zone-uitkomsten per adres (offline)

## Fixtures en echte brondata (F1.5)

- `fixtures/personas.json` — persona's incl. edge-cases (onvolledige schets,
  adrescorrectie tijdens H1, lage wallet-waarborg `wim`, geen wallet `nadia`).
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
  (ODbL, attributie in `source.meta.json`; productie-pad: officiële BeSt
  Address API, FOD BOSA — F2).
- Verversen (netwerk, expliciete cache-bouwstap — runs blijven offline):
  `python3 fetch_sources.py [--geocode]`.

De golden set is afgeleid tegen de échte lagen (niet overgenomen uit de
eerdere synthetische fixtures): Korenmarkt 1 → LEZ + autovrij; Sint-Pietersplein
1 → alleen LEZ; Koningin Maria Hendrikaplein 1 (station) → buiten beide.

Nog niet gecached, wel beschikbaar voor F2 (zie `source.meta.json`): KBO/CBE
open data + VKBO (realistische ondernemersdossiers) en GIPOD (innames/werken op
het openbaar domein). Magda, ACM/IDM en de District09-backoffice blijven mock
tot de echte integraties.

Geen echte persoonsgegevens; alle persoonlijke gegevens zijn verzonnen persona's.
