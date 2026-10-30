# poc-gent — Piloot Gent (EUROPAI WP3): transactionele levensgebeurtenis-assistent

Fase 1 (intake → context → GIS → routing → H1) van het referentiepakket
`gent-mobiliteit-ondernemer`. Ontwerp:
[`docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md`](../docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md).

- Configuratie is data: levensgebeurtenis-pakketten onder `packages/`
  (manifest + beslistabellen + golden set), geladen via `core/catalog.py`.
- LLM stelt voor, engine beslist, mens bevestigt: de F1-replay is volledig
  deterministisch; persona-fixtures zijn de replay stand-in voor de
  LLM-seams S1/S2 (LLM-poot komt in een latere fase).
- Bewijs: elke run schrijft `runs/<runId>/run.json` (schema
  `schemas/gent-run.schema.json`) + `events.jsonl` (sha256-ketting).

## Gebruik

    python3 run.py --list-personas
    python3 run.py --persona jeroen
    ../nldt/.venv/bin/python -m pytest tests -q     # volledige testsuite
    python3 eval.py                                  # golden-set evaluatie

## Fixtures

- `fixtures/personas.json` — persona's incl. edge-cases (onvolledige schets,
  adrescorrectie tijdens H1).
- `fixtures/gis-zones.geojson` + `fixtures/addresses.json` — LEZ/autovrije
  zone (illustratieve polygonen; productie: interne GIS-diensten Stad Gent).

Geen echte persoonsgegevens; alle gegevens zijn verzonnen fixtures.
