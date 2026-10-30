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

## Gebruik

    python3 run.py --list-personas
    python3 run.py --persona jeroen
    ../nldt/.venv/bin/python -m pytest tests -q     # volledige testsuite
    python3 eval.py                                  # golden-set evaluatie
    python3 fetch_sources.py --check                 # zone-uitkomsten per adres (offline)

## Fixtures en echte brondata (F1.5)

- `fixtures/personas.json` — persona's incl. edge-cases (onvolledige schets,
  adrescorrectie tijdens H1).
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
