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
- `h3-krw-monitoring.json` + `h3-krw-blindspots.html` (fase 2, `--no-krw` om te skippen)
- `h3-waterkwaliteit.json` + `h3-waterkwaliteit.html` (fase 2b: gemeten waarden, `--no-wq` skip, `--parameter` kiest stof)

Offline H3-replay: `POC_H3_OFFLINE=1` (gebruikt `poc/data/cache/h3/`).

## Tests

```bash
cd poc-rijnland && ../nldt/.venv/bin/python -m unittest discover -s tests -v
```

Optioneel live fixtures (kleine Leiden-bbox):

```bash
../nldt/.venv/bin/python tests/make_fixtures.py
```

## Fase 2d — Waterpeilen polders & boezem (geïmplementeerd)

Gemeten peilhistorie is niet open: de AGOL-lagen van Rijnland geven alleen
actuele waarden en de publieke HydroNET-chart per station een vast venster
van ±12 dagen. `scripts/fetch_peilen.py` snapshot daarom alle 315 stations
(131 polders, 184 boezem; 178.364 punten → 4.079 stationsdagen) naar een
groeiend archief `data/peilen/peilen.json`; her-runnen breidt het venster
uit. `run_peilen.py` rendert de tijdreeks-pagina (stations + mediaan-
aggregaten, mNAP, min–max-band). Voor 2020–2026-historie is een HydroNET-
account of RWS-waterinfo-sleutel nodig.

## Fase 2c — Tijdreeks 2020–2026 (geïmplementeerd)

`scripts/fetch_wkp.py --monthly --from-year 2020 --to-year 2026` aggregeert
álle jaren tot maandbuckets (mediaan + P25–P75 over locaties per parameter,
±1,44 mln rijen → 792 buckets). `run_timeseries.py` rendert daaruit één
offline pagina: parameter-keuze, maandmediaan met spreidingsband,
12-maands trendlijn, seizoenscyclus en een afspeel-cursor ("simulatie")
over de periode. 2026 is een deels jaar (thans 6 metingen).

## Fase 2b — Gemeten waterkwaliteit (geïmplementeerd)

Werkelijke meetwaarden (niet alleen dekkingsdekking) via het
[Waterkwaliteitsportaal](https://wkp.rws.nl/downloadmodule) van het
Informatiehuis Water: `scripts/fetch_wkp.py --year 2025` haalt álle
Oppervlaktewaterkwaliteit-metingen voor Rijnland via de download-API
(subject 15 "Meetgegeven"; 304.154 rows, 723 locaties) en aggregeert die
naar jaarlijkse locatie-medianen per stof in
`data/wkp/waterkwaliteit-2025.json` (met provenance). Per cel: mediaan
van locatie-medianen, geschaald op het eigen P10–P90-bereik (0=gunstig,
1=ongunstig — geen wettelijke norm), plus Moran's I. 2026 levert thans
slechts 6 metingen; default jaar is 2025.

## Fase 2 — KRW-monitoringdekking (geïmplementeerd)

De Rijnland-stack ontsluit geen gemeten waarden en de KRW-statuswaterlichamen
(KRW/MapServer lagen 1–3) zijn leeg gepubliceerd; wél de meetlocatieslaag
(29.050 punten, `WS_TYPEMETING`-gediscrimineerd). Fase 2 beantwoordt daarom:
*waar wijkt het praktijkpeil af zonder routine waterkwaliteitsmonitoring?*

- routine meetnet (`WS_TYPEMETING = 'routine meetnet waterkwaliteit'`) →
  `h3-spatial-join-points` op de peilgebied-cellen → per-cel meetdichtheid
- Moran's I op die dichtheid via `h3-morans-i` (significant geclusterd = 0.40, p 0.005)
- blinde vlek = conflictcel zonder monitoring in de cel òf haar `grid_disk(1)`-buurt
  → `h3-krw-blindspots.html` (rood) + `h3-krw-monitoring.json
