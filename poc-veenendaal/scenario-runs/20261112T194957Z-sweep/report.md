# Scenario-sweep Spoorzone Veenendaal — 20261112T194957Z-sweep

Nulmeting: run `20261112T194937Z-gebiedscheck` · doctrine: rekenlaag beslist, mens beslist.

| Scenario | Basis | Jaar van 4.500 | Uitloop vs 2040 | Groen eind (ha) | Verhard eind (ha) | Groendoel >30 ha | Dichtheid /km² |
|---|---|---:|---:|---:|---:|---|---:|
| **nulmeting — geen mutaties** (CONTROL) | baseline | 2038 | -2 jr | 25.96 | 37.69 | ✗ -4.04 | 5604 |
| **tempo 150 woningen/jaar** (TEMPO-150) | policy_variant | 2050 | +10 jr | 25.96 | 19.69 | ✗ -4.04 | 5604 |
| **tempo 350 woningen/jaar** (TEMPO-350) | policy_variant | 2033 | -7 jr | 25.96 | 19.69 | ✗ -4.04 | 5604 |
| **nieuwbouw op verhard (5-lagen basis)** (BOUW-OP-VERHARD) | policy_variant | 2038 | -2 jr | 25.96 | 19.69 | ✗ -4.04 | 5604 |
| **nieuwbouw op groen (5-lagen basis)** (BOUW-OP-GROEN) | hypothetical | 2038 | -2 jr | 7.96 | 37.69 | ✗ -22.04 | 5604 |
| **15-lagen accenten (compact, 25 m²/woning)** (DICHT-15) | policy_variant | 2038 | -2 jr | 25.96 | 26.44 | ✗ -4.04 | 5604 |

## Per scenario

### nulmeting — geen mutaties · basis baseline
- rationale: referentie: doelparameters uit het Toekomstbeeld (250/jaar, 4.500 woningen, groen >30 ha) tegen de gemeten stand
- mutaties: {}
- benodigd nieuw grondvlak: 0.0 ha (groen −0.0 · verhard −0.0)
- groen eind 25.96 ha (marge -4.04 t.o.v. doel 30) · verhard eind 37.69 ha · dichtheid 5604/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

### tempo 150 woningen/jaar · basis policy_variant
- rationale: ondergrens: doorbouwtempo zonder extra middelen
- mutaties: {"woningen_per_jaar": 150}
- benodigd nieuw grondvlak: 18.0 ha (groen −0.0 · verhard −18.0)
- groen eind 25.96 ha (marge -4.04 t.o.v. doel 30) · verhard eind 19.69 ha · dichtheid 5604/km²
- jaar van 4500: 2050 (+10 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| 't Franse Gat Noord | 137 | 3.82 |
| 't Goeie Spoor | 45 | 3.98 |
| Engelenburg West (Ritmeesterkwartier) | 173 | 3.92 |
| Stationsgebied | 91 | 4.86 |
| Het Ambacht | 72 | 1.88 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| Stads- en sportpark | 0 | 0 |
| **totaal** | **486** | **18.47** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### tempo 350 woningen/jaar · basis policy_variant
- rationale: versnelling: 4.500 binnen één planperiode-helft
- mutaties: {"woningen_per_jaar": 350}
- benodigd nieuw grondvlak: 18.0 ha (groen −0.0 · verhard −18.0)
- groen eind 25.96 ha (marge -4.04 t.o.v. doel 30) · verhard eind 19.69 ha · dichtheid 5604/km²
- jaar van 4500: 2033 (-7 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| 't Franse Gat Noord | 137 | 3.82 |
| 't Goeie Spoor | 45 | 3.98 |
| Engelenburg West (Ritmeesterkwartier) | 173 | 3.92 |
| Stationsgebied | 91 | 4.86 |
| Het Ambacht | 72 | 1.88 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| Stads- en sportpark | 0 | 0 |
| **totaal** | **486** | **18.47** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### nieuwbouw op verhard (5-lagen basis) · basis policy_variant
- rationale: beleidsvoorkeur: verdichten op verharding; groen onaangetast
- mutaties: {"bouwVoorkeur": "verhard"}
- benodigd nieuw grondvlak: 18.0 ha (groen −0.0 · verhard −18.0)
- groen eind 25.96 ha (marge -4.04 t.o.v. doel 30) · verhard eind 19.69 ha · dichtheid 5604/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| 't Franse Gat Noord | 137 | 3.82 |
| 't Goeie Spoor | 45 | 3.98 |
| Engelenburg West (Ritmeesterkwartier) | 173 | 3.92 |
| Stationsgebied | 91 | 4.86 |
| Het Ambacht | 72 | 1.88 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| Stads- en sportpark | 0 | 0 |
| **totaal** | **486** | **18.47** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### nieuwbouw op groen (5-lagen basis) · basis hypothetical
- rationale: slechtste geval voor de groenbelofte: verdichten ten koste van groen
- mutaties: {"bouwVoorkeur": "groen"}
- benodigd nieuw grondvlak: 18.0 ha (groen −18.0 · verhard −0.0)
- groen eind 7.96 ha (marge -22.04 t.o.v. doel 30) · verhard eind 37.69 ha · dichtheid 5604/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| 't Franse Gat Noord | 97 | 1.22 |
| 't Goeie Spoor | 83 | 2.0 |
| Engelenburg West (Ritmeesterkwartier) | 328 | 2.36 |
| Stationsgebied | 135 | 1.97 |
| Het Ambacht | 104 | 1.65 |
| Bedrijventerrein Overgangszone | 40 | 1.42 |
| Stads- en sportpark | 240 | 7.64 |
| **totaal** | **952** | **18.27** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

### 15-lagen accenten (compact, 25 m²/woning) · basis policy_variant
- rationale: p.14: basishoogte 5 lagen met accenten tot 15 — compactere voetafdruk per woning
- mutaties: {"grondvlak_per_woning_m2": 25.0, "bouwVoorkeur": "verhard"}
- benodigd nieuw grondvlak: 11.25 ha (groen −0.0 · verhard −11.25)
- groen eind 25.96 ha (marge -4.04 t.o.v. doel 30) · verhard eind 26.44 ha · dichtheid 5604/km²
- jaar van 4500: 2038 (-2 t.o.v. 2040)

  **Toedeling per deelgebied** (provisionele indeling):

| Deelgebied | vlakken | genomen (ha) |
|---|---:|---:|
| 't Franse Gat Noord | 120 | 2.99 |
| 't Goeie Spoor | 30 | 0.58 |
| Engelenburg West (Ritmeesterkwartier) | 93 | 2.44 |
| Stationsgebied | 90 | 4.33 |
| Het Ambacht | 42 | 0.92 |
| Bedrijventerrein Overgangszone | 0 | 0 |
| Stads- en sportpark | 0 | 0 |
| **totaal** | **346** | **11.26** |
  regel: hele actuele vlakken · afstand tot station oplopend · bij gelijke afstand grootste eerst · per zone uitgesplitst op oppervlakte (vlak kan in twee zones liggen)

## Beperkingen

- Grondvlak per nieuwe woning is een aanname (40 m² basis / 25 m² accenten), geen registratiefeit.
- Allocatie groen-vs-verhard is abstract (werkgrens-totaal); de deelgebied-uitsplitsing volgt het vlakzwaartepunt (provisionele zone-indeling).
- Woningtelling is de vbo-proxy uit de nulmeting (panden ≠ woningen).

*V3: pass — invarianten houden stand (woningtotaal, voorraden ≥ 0, doelperiode). Manifest: manifest.json · specs+uitkomsten: scenarios.json.*