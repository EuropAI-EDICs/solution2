# ZN-2 — Optelbaarheidstest (design)

**Vraag.** Kunnen we aantonen dat indicatordefinities **optelbaar** zijn —
zelfde formules, zelfde schaal — over twee gebieden, zodat een bovenlokaal
beeld geen appels-met-peren is?

Dit sluit ZN-2 uit de ZoN-alignment ([`nldt/24-zichtopnl-alignment.md`](../../../nldt/24-zichtopnl-alignment.md))
en levert het eerste meetbare datapunt voor DT-4 “second-city reuse”
([`nldt/23-dtas-alignment.md`](../../../nldt/23-dtas-alignment.md) §DT-4):
niet “tweede organisatie adopteert live”, wel “zelfde recipe-definities
draaien ongewijzigd over twee gebiedscontexten”.

| | |
|---|---|
| Status | Design 2026-10-04 · MVP offline + live CBS (Breda+Tilburg+Eindhoven) |
| Related | Plane D ([gebiedsafweging](2026-10-04-breda-gebiedsafweging-plane-d-design.md)) · PoC-4 Breda |
| Non-goals | Breda ArcGIS-lagen op stad 2 (parity breekt); fysische modellen; DT-4 organisatie-adoptie |

---

## Aanpak

### Offline MVP
1. Twee synthetische gebieds-lagen met verschillende `gemeentecode`.
2. Identieke `DEFAULT_PARAMS` + formula fingerprint.
3. Rapport met percentile-means, **absoluteMeans** (cross-area) en gewogen combined.

### Live tweede gemeente
1. `fetch_cbs_buurten(gemeente=…)` — OGC-filter op PDOK CBS 2024; aparte cache per slug.
2. `fetch_cbs_area_layers` — **CBS-only** voor élke live gemeente (ook Breda in `--live`), zodat overlays de vergelijking niet scheeftrekken.
3. Default: `--live Breda,Tilburg,Eindhoven`.

```bash
nldt/.venv/bin/python poc-breda/optelbaarheid_run.py --live
```

**Done when:** offline tests groen; live run Breda+Tilburg+Eindhoven verdict `pass` met
`definitions.identical=true` en divergerende `absoluteMeans`.
