# Verordening fase 4 — progress ledger

Branch: `verordening-fase4` · Worktree: `../ldttoolbox-vf4` · Plan: `docs/superpowers/plans/2026-10-05-verordening-fase4-biomassa-energietoets.md`

## H5-eigenaarschapskaart (task 1)

| Artikel | Thuis | Bewijs |
|---|---|---|
| 5.1 Toepassingsbereik | `wind` (context) | `evidence-wind.json` |
| 5.2 Afwijking verstedelijkingsverbod | `wind` (context) | `evidence-wind.json` |
| 5.3 Kleine windturbine | `wind` | `evidence-wind.json` |
| 5.4 Windenergielocatie | `wind` | `evidence-wind.json` |
| 5.5 Zonneveld | `zon` | `evidence-zon.json` |
| **5.6 Biomassa landelijk** | **`biomassa`** | `evidence-biomassa.json` BM-01 |
| **5.7 Biomassa stedelijk** | **`biomassa`** | `evidence-biomassa.json` BM-02 |
| **5.8 Transformatorstation vergunning** | **`energietoets` ledger** | `normcards-rejected-energietoets.json` AET-04 (procedureel) |
| **5.9 Transformatorstation indiening** | **`energietoets` ledger** | `normcards-rejected-energietoets.json` AET-04 (procedureel) |
| **5.10 Energietoets toepassingsbereik** | **`energietoets`** | `evidence-energietoets.json` ET-01 |
| **5.11 Weging elektriciteits-infrastructuur** | **`energietoets`** (conditional + EnergyCast-seam) | `evidence-energietoets.json` ET-02/ET-03; geen GIO; geen netdata in PoC |

## Taken

- [x] Task 1 — worktree + ledger + H5-kaart
- [x] Task 2 — biomassa-recon
- [x] Task 3 — biomassa-zones
- [x] Task 4 — biomassa formalisering + run
- [x] Task 5 — energietoets-recon
- [ ] Task 6 — energietoets formalisering + run
- [ ] Task 7 — docs + regressie + merge
