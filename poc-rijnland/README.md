# PoC-3 — Rijnland peil-conflict (H3)

**Vraag (MVP):** waar wijkt peilbeheer in de praktijk af van het vigerend peilbesluit
in het beheergebied van het Hoogheemraadschap van Rijnland?

**Data:** [Rijnland Filter Gallery](https://rijnland.maps.arcgis.com/apps/instant/filtergallery/index.html?appid=cc74a510ca1644d78dfb914e09cb1b5a)
via ArcGIS REST (`rijnland.enl-mcs.nl`), peilgebied (vigerend) × peilafwijking (praktijk).

**Stack:** dunne wrapper die PoC-1 hergebruikt:

- `poc.pipeline.geodata` — fetch + dual-CRS cache
- `poc.pipeline.h3step` / `h3report` — nldt H3-processen + Leaflet-heatmap

Design: [`docs/superpowers/specs/2026-09-10-poc3-rijnland-h3-design.md`](../docs/superpowers/specs/2026-09-10-poc3-rijnland-h3-design.md).

## Run

```bash
# demo-slice (Leiden / Haarlemmermeer bbox, default)
nldt/.venv/bin/python poc-rijnland/run.py

# heel Rijnland (zwaarder)
nldt/.venv/bin/python poc-rijnland/run.py --full --out /tmp/rijnland-peil

# alleen polygon-headline, geen H3
nldt/.venv/bin/python poc-rijnland/run.py --no-h3
```

Output onder `poc-rijnland/runs/<ts>-rijnland-peil/`:

- `peil-conflict-report.json` / `.md`
- `h3-peil-conflict.json` + `h3-peil-conflict.html` (gestitchte NL-legenda)

Offline H3-replay: `POC_H3_OFFLINE=1` (gebruikt `poc/data/cache/h3/`).

## Tests

```bash
cd poc-rijnland && ../nldt/.venv/bin/python -m unittest discover -s tests -v
```

Optioneel live fixtures (kleine Leiden-bbox):

```bash
../nldt/.venv/bin/python tests/make_fixtures.py
```

## Fase 2 (niet in MVP)

KRW-waterkwaliteit: meetpunten → `h3-spatial-join-points` → `h3-morans-i` op dezelfde package.
