# Scenario-sweep Spoorzone Veenendaal — 20261106T165924Z-sweep

Nulmeting: run `20261106T151732Z-gebiedscheck` · doctrine: rekenlaag beslist, mens beslist.

| Scenario | Basis | Jaar van 4.500 | Uitloop vs 2040 | Groen eind (ha) | Verhard eind (ha) | Groendoel >30 ha | Dichtheid /km² |
|---|---|---:|---:|---:|---:|---|---:|
| **nulmeting — geen mutaties** (CONTROL) | baseline | 2038 | -2 jr | 32.83 | 50.97 | ✓ 2.83 | 6245 |
| **tempo 150 woningen/jaar** (TEMPO-150) | policy_variant | 2050 | +10 jr | 32.83 | 32.97 | ✓ 2.83 | 6245 |
| **tempo 350 woningen/jaar** (TEMPO-350) | policy_variant | 2033 | -7 jr | 32.83 | 32.97 | ✓ 2.83 | 6245 |
| **nieuwbouw op verhard (5-lagen basis)** (BOUW-OP-VERHARD) | policy_variant | 2038 | -2 jr | 32.83 | 32.97 | ✓ 2.83 | 6245 |
| **nieuwbouw op groen (5-lagen basis)** (BOUW-OP-GROEN) | hypothetical | 2038 | -2 jr | 14.83 | 50.97 | ✗ -15.17 | 6245 |
| **15-lagen accenten (compact, 25 m²/woning)** (DICHT-15) | policy_variant | 2038 | -2 jr | 32.83 | 39.72 | ✓ 2.83 | 6245 |

## Per scenario

### nulmeting — geen mutaties · basis baseline
- rationale: referentie: doelparameters uit het Toekomstbeeld (250/jaar, 4.500 woningen, groen >30 ha) tegen de gemeten stand
- mutaties: {}
- benodigd nieuw grondvlak: 0.0 ha (groen −0.0 · verhard −0.0)
- groen eind 32.83 ha (marge 2.83 t.o.v. doel 30) · verhard eind 50.97 ha · dichtheid 6245/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

### tempo 150 woningen/jaar · basis policy_variant
- rationale: ondergrens: doorbouwtempo zonder extra middelen
- mutaties: {"woningen_per_jaar": 150}
- benodigd nieuw grondvlak: 18.0 ha (groen −0.0 · verhard −18.0)
- groen eind 32.83 ha (marge 2.83 t.o.v. doel 30) · verhard eind 32.97 ha · dichtheid 6245/km²
- jaar van 4500: 2050 (+10 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| Engelenburg West (Ritmeesterkwartier) | 83 | 6.0 |
| Stationsgebied | 294 | 7.12 |
| Het Ambacht | 105 | 3.46 |
| 't Goeie Spoor | 30 | 0.55 |
| Stads- en sportpark | 41 | 0.89 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| 't Franse Gat Noord | 0 | 0 |
| **totaal** | **500** | **18.03** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### tempo 350 woningen/jaar · basis policy_variant
- rationale: versnelling: 4.500 binnen één planperiode-helft
- mutaties: {"woningen_per_jaar": 350}
- benodigd nieuw grondvlak: 18.0 ha (groen −0.0 · verhard −18.0)
- groen eind 32.83 ha (marge 2.83 t.o.v. doel 30) · verhard eind 32.97 ha · dichtheid 6245/km²
- jaar van 4500: 2033 (-7 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| Engelenburg West (Ritmeesterkwartier) | 83 | 6.0 |
| Stationsgebied | 294 | 7.12 |
| Het Ambacht | 105 | 3.46 |
| 't Goeie Spoor | 30 | 0.55 |
| Stads- en sportpark | 41 | 0.89 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| 't Franse Gat Noord | 0 | 0 |
| **totaal** | **500** | **18.03** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### nieuwbouw op verhard (5-lagen basis) · basis policy_variant
- rationale: beleidsvoorkeur: verdichten op verharding; groen onaangetast
- mutaties: {"bouwVoorkeur": "verhard"}
- benodigd nieuw grondvlak: 18.0 ha (groen −0.0 · verhard −18.0)
- groen eind 32.83 ha (marge 2.83 t.o.v. doel 30) · verhard eind 32.97 ha · dichtheid 6245/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| Engelenburg West (Ritmeesterkwartier) | 83 | 6.0 |
| Stationsgebied | 294 | 7.12 |
| Het Ambacht | 105 | 3.46 |
| 't Goeie Spoor | 30 | 0.55 |
| Stads- en sportpark | 41 | 0.89 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| 't Franse Gat Noord | 0 | 0 |
| **totaal** | **500** | **18.03** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### nieuwbouw op groen (5-lagen basis) · basis hypothetical
- rationale: slechtste geval voor de groenbelofte: verdichten ten koste van groen
- mutaties: {"bouwVoorkeur": "groen"}
- benodigd nieuw grondvlak: 18.0 ha (groen −18.0 · verhard −0.0)
- groen eind 14.83 ha (marge -15.17 t.o.v. doel 30) · verhard eind 50.97 ha · dichtheid 6245/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| Engelenburg West (Ritmeesterkwartier) | 127 | 1.7 |
| Stationsgebied | 334 | 3.37 |
| Het Ambacht | 82 | 0.48 |
| 't Goeie Spoor | 363 | 7.06 |
| Stads- en sportpark | 293 | 5.44 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| 't Franse Gat Noord | 0 | 0 |
| **totaal** | **1125** | **18.05** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### 15-lagen accenten (compact, 25 m²/woning) · basis policy_variant
- rationale: p.14: basishoogte 5 lagen met accenten tot 15 — compactere voetafdruk per woning
- mutaties: {"grondvlak_per_woning_m2": 25.0, "bouwVoorkeur": "verhard"}
- benodigd nieuw grondvlak: 11.25 ha (groen −0.0 · verhard −11.25)
- groen eind 32.83 ha (marge 2.83 t.o.v. doel 30) · verhard eind 39.72 ha · dichtheid 6245/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| Engelenburg West (Ritmeesterkwartier) | 36 | 2.92 |
| Stationsgebied | 257 | 6.42 |
| Het Ambacht | 78 | 1.81 |
| 't Goeie Spoor | 3 | 0.13 |
| Stads- en sportpark | 6 | 0.02 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| 't Franse Gat Noord | 0 | 0 |
| **totaal** | **355** | **11.28** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

## Beperkingen

- Grondvlak per nieuwe woning is een aanname (40 m² basis / 25 m² accenten), geen registratiefeit.
- Allocatie groen-vs-verhard is abstract (werkgrens-totaal); de deelgebied-uitsplitsing volgt het vlakzwaartepunt (provisionele zone-indeling).
- Woningtelling is de vbo-proxy uit de nulmeting (panden ≠ woningen).

*V3: pass — invarianten houden stand (woningtotaal, voorraden ≥ 0, doelperiode). Manifest: manifest.json · specs+uitkomsten: scenarios.json.*