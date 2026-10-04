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
| Status | Design 2026-10-04 · MVP offline fixtures |
| Related | Plane D ([gebiedsafweging](2026-10-04-breda-gebiedsafweging-plane-d-design.md)) · PoC-4 Breda |
| Non-goals v1 | Live tweede gemeente (Tilburg/…); Breda ArcGIS-lagen voor stad 2; fysische modellen |

---

## Aanpak MVP

1. Twee synthetische gebieds-lagen (zelfde CBS-velden + indicatorpad) met
   verschillende `gemeentecode` / `gemeentenaam`.
2. `indicators.compute_scan` + **identieke** `DEFAULT_PARAMS` op beide.
3. Rapport `optelbaarheid-report`:
   - `definitionsIdentical` (formula fingerprint + params hash)
   - per gebied: n land-buurten, mean score per waarde
   - `combined`: gewogen mean (gewicht = n land-buurten met score)
   - V0 schema; geen LLM; geen winnaar

**Done when:** offline test toont twee gebieden met gelijke fingerprint en
een gecombineerde mean die algebraïsch volgt uit de deel-means.
