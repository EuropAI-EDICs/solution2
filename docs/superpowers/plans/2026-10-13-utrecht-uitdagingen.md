# Utrecht-PoC uitdagingen 5×13×3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De Utrecht-PoC scenario-demo wordt geherstructureerd naar 5 uitdagingen (beleidsopgaven) × 13 tracks × exact 3 scenario's per track, gegroepeerd in dashboard, catalog en prompts.

**Architecture:** Pure curation-laag bovenop de bestaande scenario-engine: één nieuw curation-bestand (`poc/scenarios/uitdagingen.json`) + 13 scenario-set-bestanden à 3 scenario's + presentatie-wijzigingen in `deep-agents` (catalog, dashboard, prompts). Geen engine- of schema-wijzigingen.

**Tech Stack:** Python 3.13 stdlib + jsonschema (poc-pijplijn), vanilla JS (dashboard), pytest.

**Spec:** `docs/superpowers/specs/2026-10-13-utrecht-uitdagingen-design.md` (§4 intenties; de exacte ruleIds/mutaties zijn hieronder vastgelegd; afwijkingen worden in Task 12 in de spec vastgelegd).

## Global Constraints

- Geen wijzigingen aan `poc/pipeline/engine.py`, `poc/pipeline/scenarios.py`, `poc/pipeline/scenario_author.py` of schema's onder `poc/schemas/` (de `dataGrounding`-extensie hoort bij plan 2). **Geaccepteerde enabling-uitzondering (Task 3, gecontroleerd):** de objectType/track-enums in de scenario-schema's zijn uitgebreid naar de 13 tracks/objectTypes — zonder die extensie valideren de sweeps van de nieuwe tracks niet; en baseline-`layers.json`-cachePaden die naar een verwijderde worktree wezen zijn gerepareerd (V3-reproductie exact 0). Beide worden in Task 12 in de spec vastgelegd.
- Elke scenario-set valideert tegen `poc/schemas/scenario-set.schema.json` én elke spec tegen `poc/schemas/scenario-spec.schema.json` (`additionalProperties: false` — geen extra velden).
- Basis-verdeling per track volgt spec §3: ≥1 `policy_variant`, ≤1 `norm_variance`, ≥1 `hypothetical` **of** derde `policy_variant` (mobiliteit/energietoets-uitzondering).
- Elke `normCardId` in een `basis` moet voorkomen in de `normcards.json` van de canonieke baseline-run van de track; elke mutation-`ruleId` in de `formalrules.json`.
- Sweeps draaien cache-first; verdict moet `pass` zijn (exit 0). Als h3/netwerk mist: her-run met `--no-h3` en noteer dat in de commit-message van die taak.
- Labels: Nederlands in catalog/dashboard/prompts; Engels in set-JSONs (consistent met bestaande sets).
- Test-commando's draaien vanuit repo-root of `poc/` zoals per stap aangegeven; de volledige suite (`cd poc && python3 -m pytest tests -q`) moet groen blijven.

## Vastgelegde scenario-keuzes (uit spec §4, geconcretiseerd op ruleIds)

| track | scenario | basis | mutaties |
|---|---|---|---|
| wind | SC-W-NNN-EXCEPTION (bestaat) | policy_variant | ongewijzigd |
| wind | SC-W-STILTE-HARD (bestaat) | policy_variant | ongewijzigd |
| wind | SC-W-NATURA-SETBACK (bestaat) | hypothetical | ongewijzigd |
| zon | SC-Z-GROENE-CONTOUR-HARD (bestaat) | policy_variant | ongewijzigd |
| zon | SC-Z-ZONE-BUFFER-500 (nieuw) | hypothetical | FR-Z-02 `set_buffer_distance_m` 500 |
| zon | SC-Z-GEEN-NATURA-CARVE (bestaat) | hypothetical | ongewijzigd |
| biomassa | SC-BM-LANDELIJK-HARD (nieuw) | policy_variant | FR-BM-01 `set_semantics` exclusion |
| biomassa | SC-BM-STEDELIJK-HARD (nieuw) | policy_variant | FR-BM-02 `set_semantics` exclusion |
| biomassa | SC-BM-BUFFER-500 (nieuw) | hypothetical | FR-BM-01 `set_buffer_distance_m` 500 |
| energietoets | SC-ET-TOETS-HARD (nieuw) | policy_variant | FR-ET-01 `set_semantics` exclusion |
| energietoets | SC-ET-GEEN-MOTIVATIE (nieuw) | policy_variant | FR-ET-03 `drop` |
| energietoets | SC-ET-NETCONGESTIE | hypothetical | **plan 2** (dataGrounding, netbeheerder-laag) |
| wonen | SC-WN-ALLEEN-STEDELIJK (nieuw) | policy_variant | drop FR-WN-04, FR-WN-07, FR-WN-08, FR-WN-09 |
| wonen | SC-WN-FLEXWONINGEN-DICHT (nieuw) | policy_variant | FR-WN-08 `drop` |
| wonen | SC-WN-STILTE-1KM (nieuw) | hypothetical | FR-WN-11 + FR-WN-12 `set_semantics` exclusion, FR-WN-12 `set_buffer_distance_m` 1000 |
| werken | SC-WE-DETAILHANDEL-HARD (nieuw) | policy_variant | FR-WE-06 `set_semantics` exclusion |
| werken | SC-WE-ALLEEN-STEDELIJK (nieuw) | policy_variant | FR-WE-03 `drop` |
| werken | SC-WE-BEDRIJVENTERREIN-BUFFER-500 (nieuw) | hypothetical | FR-WE-03 `set_buffer_distance_m` 500 |
| water | SC-WA-OVERSTROOMBAAR-HARD (nieuw) | policy_variant | FR-WA-03 `set_semantics` exclusion |
| water | SC-WA-VRIJWARING-HARD (nieuw) | policy_variant | FR-WA-01 `set_semantics` exclusion |
| water | SC-WA-WATERBERGING-BUFFER-500 (nieuw) | norm_variance | FR-WA-02 `set_buffer_distance_m` 500 |
| bodem | SC-BO-ALLEEN-REKENING-HOUDEN (nieuw) | policy_variant | FR-BO-01 `drop`, FR-BO-03 `drop` |
| bodem | SC-BO-STORTPLAATS-HARD (nieuw) | policy_variant | FR-BO-05 `set_semantics` exclusion |
| bodem | SC-BO-GWB-BUFFER-500 (nieuw) | norm_variance | FR-BO-01 `set_buffer_distance_m` 500 |
| landschap | SC-LS-CHS-HARD (nieuw) | policy_variant | FR-LS-04 `set_semantics` exclusion |
| landschap | SC-LS-AARDKUNDIG-HARD (nieuw) | policy_variant | FR-LS-06 `set_semantics` exclusion |
| landschap | SC-LS-LIMES-BUFFER-100 (nieuw) | norm_variance | FR-LS-02 `set_buffer_distance_m` 100 |
| mobiliteit | SC-MO-GELUID-HARD (nieuw) | policy_variant | FR-MO-02 `set_semantics` exclusion |
| mobiliteit | SC-MO-WEG-HARD (nieuw) | policy_variant | FR-MO-01 `set_semantics` exclusion |
| mobiliteit | SC-MO-LUCHTVAART-ONVOORWAARDELIJK (nieuw) | policy_variant | FR-MO-05 `set_semantics` exclusion |
| bos | SC-B-OUDE-BOS-HARD (bestaat) | policy_variant | ongewijzigd |
| bos | SC-B-COMPENSATIE-HARD (nieuw) | policy_variant | FR-B-02 `set_semantics` exclusion |
| bos | SC-B-EXPAND-1KM (bestaat) | hypothetical | ongewijzigd |
| landbouw | SC-LB-STABILISERING-OPEN (nieuw) | policy_variant | FR-LB-03 `drop` |
| landbouw | SC-LB-BEDRIJVEN-HARD (nieuw) | policy_variant | FR-LB-01 `set_semantics` exclusion |
| landbouw | SC-LB-GLASTUIN-OVERAL (nieuw) | hypothetical | FR-LB-05 `drop` |
| recreatie | SC-RC-ALLEEN-DAGRECREATIE (nieuw) | policy_variant | FR-RC-02 `drop` |
| recreatie | SC-RC-DAGRECREATIE-BUFFER-500 (nieuw) | norm_variance | FR-RC-01 `set_buffer_distance_m` 500 |
| recreatie | SC-RC-DAGRECREATIE-ALLEEN-AANDACHT (nieuw) | policy_variant | FR-RC-01 `set_semantics` attention |

Spec-afwijkingen (in Task 12 vastgelegd in de spec): bos #2 "beperkt tot 500 m-zone rond NNN" → SC-B-COMPENSATIE-HARD (geen NNN-laag in de bos-baseline); landbouw #2 "250 m-buffer rond concentratiegebied" → SC-LB-BEDRIJVEN-HARD (buffer op conditional-marker = Δ0); werken #3 "NNN-zone" → buffer FR-WE-03 (zelfde reden); recreatie #3 "NNN-zone" → attention-variant (zelfde reden); biomassa #2 "Groene contour hard" → SC-BM-STEDELIJK-HARD (geen contour-rule in de biomassa-baseline); energietoets #3 → plan 2.

---

### Task 1: uitdagingen.json + structuurtest

**Files:**
- Create: `poc/scenarios/uitdagingen.json`
- Test: `poc/tests/test_uitdagingen.py`

**Interfaces:**
- Produces: `uitdagingen.json` met shape `{"generatedAt": str, "bron": str, "uitdagingen": [{"id": str, "titel": str, "tracks": [str]}], "scenarioRuns": {track: str|null}}`. Later taken vullen `scenarioRuns[track]` met de geproduceerde run-ids; `scenario_catalog.py` (Task 9) leest dit bestand.

- [ ] **Step 1: Write the failing test**

```python
"""Uitdagingen-curation: 5 opgaven die samen exact de 13 tracks dekken."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UJV = ROOT / "scenarios" / "uitdagingen.json"

ALLE_TRACKS = {
    "wind", "zon", "bos", "water", "bodem", "mobiliteit", "landschap",
    "landbouw", "wonen", "werken", "recreatie", "biomassa", "energietoets",
}


def _load() -> dict:
    return json.loads(UJV.read_text(encoding="utf-8"))


def test_vijf_uitdagingen_dekken_exact_de_13_tracks():
    u = _load()
    assert len(u["uitdagingen"]) == 5
    seen: list[str] = []
    for uit in u["uitdagingen"]:
        assert set(uit) == {"id", "titel", "tracks"}
        assert uit["id"] and uit["titel"]
        seen.extend(uit["tracks"])
    assert sorted(seen) == sorted(ALLE_TRACKS)
    assert len(seen) == len(set(seen)), "elke track in precies één uitdaging"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -v`
Expected: FAIL — `FileNotFoundError` op `uitdagingen.json`

- [ ] **Step 3: Write uitdagingen.json**

```json
{
  "generatedAt": "2026-10-13",
  "bron": "docs/superpowers/specs/2026-10-13-utrecht-uitdagingen-design.md",
  "uitdagingen": [
    {
      "id": "energietransitie",
      "titel": "Energietransitie",
      "tracks": ["wind", "zon", "biomassa", "energietoets"]
    },
    {
      "id": "wonen-werken",
      "titel": "Wonen & Werken",
      "tracks": ["wonen", "werken"]
    },
    {
      "id": "water-bodem",
      "titel": "Water & Bodem",
      "tracks": ["water", "bodem"]
    },
    {
      "id": "landschap-infra",
      "titel": "Landschap & Infrastructuur",
      "tracks": ["landschap", "mobiliteit"]
    },
    {
      "id": "landelijk-gebied",
      "titel": "Landelijk Gebied & Natuur",
      "tracks": ["bos", "landbouw", "recreatie"]
    }
  ],
  "scenarioRuns": {
    "wind": "20260831T074521Z-wind-scen",
    "zon": "20260831T074604Z-zon-scen",
    "bos": "20260831T074610Z-bos-scen",
    "water": null,
    "bodem": null,
    "mobiliteit": null,
    "landschap": null,
    "landbouw": null,
    "wonen": null,
    "werken": null,
    "recreatie": null,
    "biomassa": null,
    "energietoets": null
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add poc/scenarios/uitdagingen.json poc/tests/test_uitdagingen.py
git commit -m "feat(poc): uitdagingen-curation 5 opgaven × 13 tracks (plan 1, task 1)"
```

---

### Task 2: wind/zon/bos-sets hercureren naar 3

**Files:**
- Modify: `poc/scenarios/wind.json` (6 → 3 scenario's)
- Modify: `poc/scenarios/zon.json` (2 → 3)
- Modify: `poc/scenarios/bos.json` (2 → 3)
- Test: `poc/tests/test_uitdagingen.py` (uitbreiding)

**Interfaces:**
- Consumes: bestaande set-bestanden; scenario-spec-schema (`basis` vereist `type` + `provenanceNote`; mutations `{ruleId, action, [zoneSemantics|bufferDistanceM]}`).
- Produces: 12 scenario's over wind/zon/bos die elk `pass`en in de sweep.

- [ ] **Step 1: Voeg set-structuurtest toe (failing)**

Voeg aan `poc/tests/test_uitdagingen.py` toe:

```python
SET_IDS = {
    "wind": 3, "zon": 3, "bos": 3, "water": 3, "bodem": 3, "mobiliteit": 3,
    "landschap": 3, "landbouw": 3, "wonen": 3, "werken": 3, "recreatie": 3,
    "biomassa": 3, "energietoets": 2,  # plan 2 maakt dit 3 (SC-ET-NETCONGESTIE)
}


def test_demo_sets_tellen_exact_3_scenarios_per_track():
    for track, n in SET_IDS.items():
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        assert s["useCase"] == track, track
        assert len(s["scenarios"]) == n, track
        ids = [sc["id"] for sc in s["scenarios"]]
        assert len(ids) == len(set(ids)), f"dubbele ids in {track}"


def test_wind_set_bevat_hetzelfde_drietal():
    s = json.loads((ROOT / "scenarios" / "wind.json").read_text(encoding="utf-8"))
    assert [sc["id"] for sc in s["scenarios"]] == [
        "SC-W-NNN-EXCEPTION", "SC-W-STILTE-HARD", "SC-W-NATURA-SETBACK"]
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -v`
Expected: FAIL — wind heeft 6 scenario's, water/bodem/… bestaan nog niet.

- [ ] **Step 2: wind.json — verwijder de drie AANDACHT-varianten**

Verwijder uit de `scenarios`-array van `poc/scenarios/wind.json` precies de drie objecten met `"id"`:
`"SC-W-AANDACHT-500"`, `"SC-W-AANDACHT-1500"`, `"SC-W-AANDACHT-3000"`.
Laat de overige drie objecten (NNN-EXCEPTION, STILTE-HARD, NATURA-SETBACK) byte-voor-byte staan.

- [ ] **Step 3: zon.json — voeg SC-Z-ZONE-BUFFER-500 toe**

Voeg als derde object toe aan de `scenarios`-array van `poc/scenarios/zon.json`:

```json
{
  "id": "SC-Z-ZONE-BUFFER-500",
  "name": "Gebied zonneveld designation expanded by a 500 m band",
  "description": "Buffers the art.-5.5 designation envelope (FR-Z-02) outward by 500 m — a programming-thought experiment, explicitly hypothetical.",
  "objectType": "solar_field",
  "basis": {
    "type": "hypothetical",
    "rationale": "The designation envelope is a programming area, not a physical boundary; this hypothetical measures what a 500 m band would add. No instrument text supports the 500 m figure.",
    "provenanceNote": "NOT legally grounded: the designation (NC-Z-02, art. 5.5) is cited, the 500 m band is the scenario's own parameter."
  },
  "mutations": [
    {"ruleId": "FR-Z-02", "action": "set_buffer_distance_m", "bufferDistanceM": 500}
  ],
  "proposedBy": "deterministic-scenario-author#poc-v0"
}
```

- [ ] **Step 4: bos.json — voeg SC-B-COMPENSATIE-HARD toe**

Voeg als middelste object toe aan `poc/scenarios/bos.json` (na SC-B-OUDE-BOS-HARD):

```json
{
  "id": "SC-B-COMPENSATIE-HARD",
  "name": "1:1 compensation duty executed as hard exclusion (compensation first)",
  "description": "FR-B-02 (art. 6.5 lid 2 onder d, ≥1:1 compensation on the zoekgebied) is a compensation marker in the baseline; the strictest reading reserves the contour exclusively for compensation, excluding new planting until compensated.",
  "objectType": "forest_planting",
  "basis": {
    "type": "policy_variant",
    "normCardId": "NC-B-02",
    "provenanceNote": "NC-B-02 (art. 6.5 lid 2 onder d) carries the ≥1:1 compensation ratio as a marker on the zoekgebied; this variant executes the strictest 'compensation first' reading as a hard exclusion of the contour itself."
  },
  "mutations": [
    {"ruleId": "FR-B-02", "action": "set_semantics", "zoneSemantics": "exclusion"}
  ],
  "proposedBy": "deterministic-scenario-author#poc-v0"
}
```

- [ ] **Step 5: Run tests to verify wind/zon/bos pass**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -v`
Expected: FAIL alleen nog op ontbrekende sets (water…energietoets); wind/zon/bos-gedeelte PASS.

- [ ] **Step 6: Commit**

```bash
git add poc/scenarios/wind.json poc/scenarios/zon.json poc/scenarios/bos.json poc/tests/test_uitdagingen.py
git commit -m "feat(poc): wind 6→3 scenario's, zon en bos naar 3 (uitdagingen-curation, plan 1)"
```

---

### Task 3: water + bodem sets en sweeps

**Files:**
- Create: `poc/scenarios/water.json`, `poc/scenarios/bodem.json`
- Modify: `poc/scenarios/uitdagingen.json` (scenarioRuns vullen)
- Test: `poc/tests/test_uitdagingen.py` (valt mee via Task 2-rijen)

**Interfaces:**
- Produces: `scenarioRuns["water"]` en `scenarioRuns["bodem"]` gevuld met de geproduceerde run-ids (`poc/scenario-runs/<ts>-water-scen` resp. `-bodem-scen`).

- [ ] **Step 1: Schrijf poc/scenarios/water.json**

```json
{
  "id": "SSET-water-utrecht-uitdagingen",
  "useCase": "water",
  "description": "Uitdagingen-curation (Water & Bodem): drie beleidsknoppen voor riparian development — twee marker-enforcement-varianten en één buffer-variatie.",
  "scenarios": [
    {
      "id": "SC-WA-OVERSTROOMBAAR-HARD",
      "name": "Overstroombaar gebied treated as hard exclusion",
      "description": "FR-WA-03 (art. 2.16, overstroombaar gebied, 1207 km²) is a conditional marker in the baseline; the strictest water-safety reading excludes new riparian development there entirely.",
      "objectType": "riparian_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-WA-03",
        "provenanceNote": "NC-WA-03 (art. 2.16) conditions development on differentiating binnendijks/buitendijks; this variant executes the strictest reading as a hard exclusion of the overstroombaar gebied."
      },
      "mutations": [
        {"ruleId": "FR-WA-03", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-WA-VRIJWARING-HARD",
      "name": "Vrijwaringszone regionale waterkering treated as hard exclusion",
      "description": "FR-WA-01 (art. 2.14, 28 km²) is a conditional marker; this variant protects the waterkering function by excluding development in the vrijwaringszone.",
      "objectType": "riparian_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-WA-01",
        "provenanceNote": "NC-WA-01 (art. 2.14) requires plans to protect the waterkering's function; this variant executes the protective reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-WA-01", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-WA-WATERBERGING-BUFFER-500",
      "name": "Waterbergingsgebied exclusion widened by a 500 m band",
      "description": "Buffers the art.-2.15 waterbergingsgebied exclusion (FR-WA-02) outward by 500 m — a hydrological-safety-margin variant.",
      "objectType": "riparian_development",
      "basis": {
        "type": "norm_variance",
        "normCardId": "NC-WA-02",
        "variedAspect": "exclusion zone widened by an added 500 m buffer; the exclusion itself is cited, the 500 m margin is the scenario's own parameter",
        "provenanceNote": "NC-WA-02 (art. 2.15) rules out new development in the waterbergingsgebied; the 500 m widening is not cited and is the scenario's own parameter."
      },
      "mutations": [
        {"ruleId": "FR-WA-02", "action": "set_buffer_distance_m", "bufferDistanceM": 500}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 2: Schrijf poc/scenarios/bodem.json**

```json
{
  "id": "SSET-bodem-utrecht-uitdagingen",
  "useCase": "bodem",
  "description": "Uitdagingen-curation (Water & Bodem): versoepeling zonder verboden, stortplaats-verstrakking en een buffer op de grondwaterbeschermingszone.",
  "scenarios": [
    {
      "id": "SC-BO-ALLEEN-REKENING-HOUDEN",
      "name": "Groundwater-protection umbrella enforced only as 'rekening houden met'",
      "description": "Drops the two hard exclusions of the grondwaterbeschermingszone umbrella (FR-BO-01 art. 3.7 winning-risk, FR-BO-03 art. 3.9 burial facilities), leaving only the art.-3.10 take-into-account condition — the weakest reading.",
      "objectType": "soil_activity",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-BO-04",
        "provenanceNote": "NC-BO-04 (art. 3.10) deliberately stays a conditional 'rekening houden met' marker; this variant re-adjudicates NC-BO-01/NC-BO-03 from hard exclusions to that weakest reading, returning ~701 km²."
      },
      "mutations": [
        {"ruleId": "FR-BO-01", "action": "drop"},
        {"ruleId": "FR-BO-03", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-BO-STORTPLAATS-HARD",
      "name": "Gesloten stortplaats treated as hard exclusion",
      "description": "FR-BO-05 (art. 3.108, 0.373 km²) is a context marker; this variant excludes the closed-landfill footprint for new soil activity.",
      "objectType": "soil_activity",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-BO-05",
        "provenanceNote": "NC-BO-05 (art. 3.108) carries the gesloten stortplaats as a context marker of provincial jurisdiction; this variant executes the protective reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-BO-05", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-BO-GWB-BUFFER-500",
      "name": "Grondwaterbeschermingszone exclusion widened by a 500 m band",
      "description": "Buffers the art.-3.7 exclusion (FR-BO-01) outward by 500 m — a protection-margin variant for the winning zone.",
      "objectType": "soil_activity",
      "basis": {
        "type": "norm_variance",
        "normCardId": "NC-BO-01",
        "variedAspect": "exclusion zone widened by an added 500 m buffer; the exclusion itself is cited, the 500 m margin is the scenario's own parameter",
        "provenanceNote": "NC-BO-01 (art. 3.7) carries the winning-risk exclusion; the 500 m widening is not cited and is the scenario's own parameter."
      },
      "mutations": [
        {"ruleId": "FR-BO-01", "action": "set_buffer_distance_m", "bufferDistanceM": 500}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 3: Voer de twee sweeps uit en vul scenarioRuns**

```bash
cd /Users/marc/Projecten/ldttoolbox && python3 poc/scenarios/run.py --use-case water
python3 poc/scenarios/run.py --use-case bodem
ls -t poc/scenario-runs/ | grep -E "water-scen|bodem-scen" | head -2
```
Expected: beide runs sluiten met `verdict: pass` (exit 0). Als h3/netwerk mist, her-run met `--no-h3` en noteer in de commit-message.

Zet de geproduceerde run-ids (de mapnamen) in `poc/scenarios/uitdagingen.json`:

```json
"water": "<ts>-water-scen",
"bodem": "<ts>-bodem-scen"
```

(waar `<ts>` de werkelijke timestamp uit de mapnaam is — exact overnemen).

- [ ] **Step 4: Run tests**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -v`
Expected: water/bodem-gedeelte PASS.

- [ ] **Step 5: Commit**

```bash
git add poc/scenarios/water.json poc/scenarios/bodem.json poc/scenarios/uitdagingen.json
git commit -m "feat(poc): water- en bodem-scenario-sets (uitdagingen Water & Bodem, plan 1)"
```

---

### Task 4: landschap + mobiliteit sets en sweeps

**Files:**
- Create: `poc/scenarios/landschap.json`, `poc/scenarios/mobiliteit.json`
- Modify: `poc/scenarios/uitdagingen.json`

**Interfaces:**
- Produces: `scenarioRuns["landschap"]`, `scenarioRuns["mobiliteit"]`.

- [ ] **Step 1: Schrijf poc/scenarios/landschap.json**

```json
{
  "id": "SSET-landschap-utrecht-uitdagingen",
  "useCase": "landschap",
  "description": "Uitdagingen-curation (Landschap & Infrastructuur): CHS- en aardkundige-verstrakking plus een UNESCO-buffer.",
  "scenarios": [
    {
      "id": "SC-LS-CHS-HARD",
      "name": "Cultuurhistorische hoofdstructuur treated as hard exclusion",
      "description": "FR-LS-04 (art. 7.9 op de CHS-umbrella, 847 km²) is a conditional marker; the strictest heritage reading excludes new landscape intervention there.",
      "objectType": "landscape_intervention",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-LS-04",
        "provenanceNote": "NC-LS-04 (art. 7.9) conditions intervention on the cultuurhistorische hoofdstructuur; this variant executes the strictest protective reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-LS-04", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-LS-AARDKUNDIG-HARD",
      "name": "Aardkundige waarden treated as hard exclusion",
      "description": "FR-LS-06 (art. 7.12, 99 km²) is a conditional marker; this variant protects aardkundige waarden by exclusion.",
      "objectType": "landscape_intervention",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-LS-06",
        "provenanceNote": "NC-LS-06 (art. 7.12) conditions intervention on aardkundige waarden; this variant executes the protective reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-LS-06", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-LS-LIMES-BUFFER-100",
      "name": "Limes kernzone exclusion widened by a 100 m band",
      "description": "Buffers the art.-7.3a Neder-Germaanse Limes kernzone exclusion (FR-LS-02) outward by 100 m — a UNESCO-buffer-margins variant.",
      "objectType": "landscape_intervention",
      "basis": {
        "type": "norm_variance",
        "normCardId": "NC-LS-02",
        "variedAspect": "exclusion zone widened by an added 100 m buffer; the kernzone designation is cited (the separate bufferzone exists), the 100 m widening is the scenario's own parameter",
        "provenanceNote": "NC-LS-02 (art. 7.3a) carries the kernzone exclusion; the added 100 m band is not cited and is the scenario's own parameter."
      },
      "mutations": [
        {"ruleId": "FR-LS-02", "action": "set_buffer_distance_m", "bufferDistanceM": 100}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 2: Schrijf poc/scenarios/mobiliteit.json**

```json
{
  "id": "SSET-mobiliteit-utrecht-uitdagingen",
  "useCase": "mobiliteit",
  "description": "Uitdagingen-curation (Landschap & Infrastructuur): drie marker-enforcement-varianten op een all-marker-track — geluid, weg en luchtvaart.",
  "scenarios": [
    {
      "id": "SC-MO-GELUID-HARD",
      "name": "Geluidcontouren treated as hard exclusion for roadside development",
      "description": "FR-MO-02 (art. 4.71, 37.3 km² combined contours) is a conditional marker; this variant excludes new geluidgevoelige roadside development in the contours.",
      "objectType": "roadside_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-MO-02",
        "provenanceNote": "NC-MO-02 (art. 4.71) gates geluidgevoelige gebouwen on dB Lden thresholds; this variant executes the strictest reading as a hard exclusion of the contours."
      },
      "mutations": [
        {"ruleId": "FR-MO-02", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-MO-WEG-HARD",
      "name": "Beperkingengebied provinciale weg treated as hard exclusion",
      "description": "FR-MO-01 (art. 4.7, 7.0 km²) is a kan-mits conditional; this variant excludes roadside development in the beperkingengebied outright.",
      "objectType": "roadside_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-MO-01",
        "provenanceNote": "NC-MO-01 (art. 4.7) conditions construction in the beperkingengebied; this variant executes the strictest reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-MO-01", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-MO-LUCHTVAART-ONVOORWAARDELIJK",
      "name": "Luchtvaartverbod executed without its activity scope",
      "description": "FR-MO-05 (art. 4.65, 1014 km²) is a conditional marker because the verbod is activity-scoped to aviation; the letter 'verbod' executed unconditionally would exclude the luchtvaartterrein zone for the whole roadside object — the scoping lesson as a scenario.",
      "objectType": "roadside_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-MO-05",
        "provenanceNote": "NC-MO-05 (art. 4.65) is an unconditional verbod of the non-permission family but activity-scoped (nieuwvestiging luchtvaartterrein); this variant measures what the unscoped letter reading would cost."
      },
      "mutations": [
        {"ruleId": "FR-MO-05", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 3: Voer de sweeps uit en vul scenarioRuns**

```bash
cd /Users/marc/Projecten/ldttoolbox && python3 poc/scenarios/run.py --use-case landschap
python3 poc/scenarios/run.py --use-case mobiliteit
```
Expected: beide `verdict: pass`.

Vul `"landschap"` en `"mobiliteit"` in `uitdagingen.json` met de geproduceerde mapnamen.

- [ ] **Step 4: Commit**

```bash
git add poc/scenarios/landschap.json poc/scenarios/mobiliteit.json poc/scenarios/uitdagingen.json
git commit -m "feat(poc): landschap- en mobiliteit-scenario-sets (uitdagingen Landschap & Infrastructuur, plan 1)"
```

---

### Task 5: landbouw + recreatie sets en sweeps (bos-set bestaat al)

**Files:**
- Create: `poc/scenarios/landbouw.json`, `poc/scenarios/recreatie.json`
- Modify: `poc/scenarios/uitdagingen.json`

**Interfaces:**
- Produces: `scenarioRuns["landbouw"]`, `scenarioRuns["recreatie"]`.

- [ ] **Step 1: Schrijf poc/scenarios/landbouw.json**

```json
{
  "id": "SSET-landbouw-utrecht-uitdagingen",
  "useCase": "landbouw",
  "description": "Uitdagingen-curation (Landelijk Gebied & Natuur): stabiliserings-versoepeling, bedrijfsgebied-verstrakking en het glastuinbouw-tegenbeeld.",
  "scenarios": [
    {
      "id": "SC-LB-STABILISERING-OPEN",
      "name": "Landbouwstabiliseringsgebied no longer excluded",
      "description": "Drops FR-LB-03 (art. 8.3, 246.8 km²) — expansion of niet-grondgebonden farm plots becomes possible in the stabiliseringsgebied again.",
      "objectType": "agricultural_expansion",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-LB-03",
        "provenanceNote": "NC-LB-03 (art. 8.3) refuses expansion of niet-grondgebonden plots in the Landbouwstabiliseringsgebied; this variant documents the reconsideration reading by dropping the exclusion."
      },
      "mutations": [
        {"ruleId": "FR-LB-03", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-LB-BEDRIJVEN-HARD",
      "name": "Gebied agrarische bedrijven treated as hard exclusion",
      "description": "FR-LB-01 (art. 8.1, verbod nieuwe bouwpercelen + 1,5 ha-voorschrift) is a kan-mits conditional; the strictest reading excludes the agrarische bedrijven designation for agricultural expansion.",
      "objectType": "agricultural_expansion",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-LB-01",
        "provenanceNote": "NC-LB-01 (art. 8.1) conditions agrarische bedrijven via a verbod plus voorschrift; this variant executes the strictest protective reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-LB-01", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-LB-GLASTUIN-OVERAL",
      "name": "Glastuinbouw designation taken at face value (no kassenconcentraties limit)",
      "description": "Drops FR-LB-05 (art. 8.6, 1557.8 km² designation) — glasshouse horticulture everywhere except the remaining two exclusions; the dramatic counterfactual.",
      "objectType": "agricultural_expansion",
      "basis": {
        "type": "hypothetical",
        "rationale": "Art. 8.6 explicitly refuses glasshouse expansion outside the kassenconcentraties (except the Ronde Venen relocation); ignoring it is not a defensible reading — it isolates how much area the concentration policy actually reserves.",
        "provenanceNote": "NOT legally grounded as a reading of the verordening: the designation (NC-LB-05, art. 8.6) is cited; dropping it is purely analytical."
      },
      "mutations": [
        {"ruleId": "FR-LB-05", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 2: Schrijf poc/scenarios/recreatie.json**

```json
{
  "id": "SSET-recreatie-utrecht-uitdagingen",
  "useCase": "recreatie",
  "description": "Uitdagingen-curation (Landelijk Gebied & Natuur): compositie-verscherping, uitbreidingsband en de aandachts-tegenbeeld op een pure-inclusion-track.",
  "scenarios": [
    {
      "id": "SC-RC-ALLEEN-DAGRECREATIE",
      "name": "Only bovenlokale dagrecreatieterreinen remain open",
      "description": "Drops FR-RC-02 (art. 9.23, recreatiezone 136.3 km²) from the inclusion composition — strict programming limited to art. 9.22.",
      "objectType": "recreation_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-RC-02",
        "provenanceNote": "NC-RC-02 (art. 9.23) opens the recreatiezone 'in afwijking van artikel 9.3'; this variant documents the strictest programming reading by dropping it from the composition."
      },
      "mutations": [
        {"ruleId": "FR-RC-02", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-RC-DAGRECREATIE-BUFFER-500",
      "name": "Dagrecreatieterrein designation expanded by a 500 m band",
      "description": "Buffers the art. 9.22 inclusion (FR-RC-01, 81.8 km²) outward by 500 m — an expansion-band variant.",
      "objectType": "recreation_development",
      "basis": {
        "type": "norm_variance",
        "normCardId": "NC-RC-01",
        "variedAspect": "inclusion zone widened by an added 500 m buffer; the designation is cited, the 500 m band is the scenario's own parameter",
        "provenanceNote": "NC-RC-01 (art. 9.22) carries the dagrecreatieterrein designation; the 500 m band is not cited and is the scenario's own parameter."
      },
      "mutations": [
        {"ruleId": "FR-RC-01", "action": "set_buffer_distance_m", "bufferDistanceM": 500}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-RC-DAGRECREATIE-ALLEEN-AANDACHT",
      "name": "Dagrecreatieterrein opening demoted to attention marker",
      "description": "FR-RC-01 re-read as an attention marker instead of an inclusion — measures what the art.-9.22 opening itself is worth (−81.8 km²).",
      "objectType": "recreation_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-RC-01",
        "provenanceNote": "NC-RC-01 (art. 9.22) opens the designation 'in afwijking van artikel 9.3'; this variant documents the counter-reading in which no spatial opening follows, only attention."
      },
      "mutations": [
        {"ruleId": "FR-RC-01", "action": "set_semantics", "zoneSemantics": "attention"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 3: Voer de sweeps uit en vul scenarioRuns**

```bash
cd /Users/marc/Projecten/ldttoolbox && python3 poc/scenarios/run.py --use-case landbouw
python3 poc/scenarios/run.py --use-case recreatie
```
Expected: beide `verdict: pass`.

Vul `"landbouw"` en `"recreatie"` in `uitdagingen.json`.

- [ ] **Step 4: Commit**

```bash
git add poc/scenarios/landbouw.json poc/scenarios/recreatie.json poc/scenarios/uitdagingen.json
git commit -m "feat(poc): landbouw- en recreatie-scenario-sets (uitdagingen Landelijk Gebied & Natuur, plan 1)"
```

---

### Task 6: biomassa + energietoets sets en sweeps

**Files:**
- Create: `poc/scenarios/biomassa.json`, `poc/scenarios/energietoets.json`
- Modify: `poc/scenarios/uitdagingen.json`

**Interfaces:**
- Produces: `scenarioRuns["biomassa"]`, `scenarioRuns["energietoets"]`.
- Note: energietoets heeft 2 scenario's; de derde (SC-ET-NETCONGESTIE) landt in plan 2. `test_demo_sets_tellen_exact_3_scenarios_per_track` verwacht daarom 2 bij energietoets.

- [ ] **Step 1: Schrijf poc/scenarios/biomassa.json**

```json
{
  "id": "SSET-biomassa-utrecht-uitdagingen",
  "useCase": "biomassa",
  "description": "Uitdagingen-curation (Energietransitie): marker-enforcement op de twee vestigingsgebieden plus een buffer-tegenbeeld.",
  "scenarios": [
    {
      "id": "SC-BM-LANDELIJK-HARD",
      "name": "Vestigingsgebied landelijk treated as hard exclusion",
      "description": "FR-BM-01 (art. 5.6, gebied energie uit biomassa landelijk) is a conditional marker; this variant excludes the rural designation for biomass installations.",
      "objectType": "biomass_installation",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-BM-01",
        "provenanceNote": "NC-BM-01 (art. 5.6) conditions biomass siting in the landelijk designation; this variant executes the strictest reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-BM-01", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-BM-STEDELIJK-HARD",
      "name": "Vestigingsgebied stedelijk treated as hard exclusion",
      "description": "FR-BM-02 (art. 5.7, gebied energie uit biomassa stedelijk) is a conditional marker; this variant excludes the urban designation — biomass remains a rural-only option.",
      "objectType": "biomass_installation",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-BM-02",
        "provenanceNote": "NC-BM-02 (art. 5.7) conditions biomass siting in the stedelijk designation; this variant executes the strictest reading as a hard exclusion."
      },
      "mutations": [
        {"ruleId": "FR-BM-02", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-BM-BUFFER-500",
      "name": "Rural designation exclusion widened by a 500 m band",
      "description": "Buffers the FR-BM-01 designation outward by 500 m as exclusion — a living-environment-margin variant.",
      "objectType": "biomass_installation",
      "basis": {
        "type": "hypothetical",
        "rationale": "No instrument text supports a 500 m siting margin for biomass installations (distance norms are abstained topics); this hypothetical measures what such a margin would carve from the province-wide opportunity zone.",
        "provenanceNote": "NOT legally grounded: the designation (NC-BM-01, art. 5.6) is cited, the 500 m margin is the scenario's own parameter."
      },
      "mutations": [
        {"ruleId": "FR-BM-01", "action": "set_buffer_distance_m", "bufferDistanceM": 500}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 2: Schrijf poc/scenarios/energietoets.json**

```json
{
  "id": "SSET-energietoets-utrecht-uitdagingen",
  "useCase": "energietoets",
  "description": "Uitdagingen-curation (Energietransitie): marker-enforcement op de afdeling-5.3-markers — de track is ruimtelijk blind (zone = AOI), precies dat is het verhaal. Derde scenario (netcongestie, data-gegrond) volgt in plan 2.",
  "scenarios": [
    {
      "id": "SC-ET-TOETS-HARD",
      "name": "Art. 5.10 scope executed as spatial blockage",
      "description": "FR-ET-01 (afdeling 5.3 scope over de hele AOI) is a conditional marker; enforcing it as exclusion would block the entire province — the toets has no spatial differentiation, and that is the policy point.",
      "objectType": "energy_storage",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-ET-01",
        "provenanceNote": "NC-ET-01 (art. 5.10) applies to new functions that can overload the grid, province-wide and without a GIO; this variant executes the strictest reading as a hard exclusion of the AOI."
      },
      "mutations": [
        {"ruleId": "FR-ET-01", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-ET-GEEN-MOTIVATIE",
      "name": "Art. 5.11 motivation duty dropped",
      "description": "Drops FR-ET-03 (art. 5.11, energy paragraph with reporting duty) — an all-marker lesson: dropping a procedural marker changes no area at all.",
      "objectType": "energy_storage",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-ET-03",
        "provenanceNote": "NC-ET-03 (art. 5.11) requires an energy paragraph in the plan motivation; this variant documents that the duty is procedural by dropping it — expected delta zero."
      },
      "mutations": [
        {"ruleId": "FR-ET-03", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

- [ ] **Step 3: Voer de sweeps uit en vul scenarioRuns**

```bash
cd /Users/marc/Projecten/ldttoolbox && python3 poc/scenarios/run.py --use-case biomassa
python3 poc/scenarios/run.py --use-case energietoets
```
Expected: beide `verdict: pass`. Let op: SC-ET-TOETS-HARD levert 0 km² / −100% (legaal: de AOI is de hele provincie); SC-ET-GEEN-MOTIVATIE Δ0.

Vul `"biomassa"` en `"energietoets"` in `uitdagingen.json`.

- [ ] **Step 4: Commit**

```bash
git add poc/scenarios/biomassa.json poc/scenarios/energietoets.json poc/scenarios/uitdagingen.json
git commit -m "feat(poc): biomassa- en energietoets-scenario-sets (uitdagingen Energietransitie, plan 1)"
```

---

### Task 7: wonen + werken sets en sweeps

**Files:**
- Create: `poc/scenarios/wonen.json`, `poc/scenarios/werken.json`
- Modify: `poc/scenarios/uitdagingen.json`

**Interfaces:**
- Produces: `scenarioRuns["wonen"]`, `scenarioRuns["werken"]`.

- [ ] **Step 1: Schrijf poc/scenarios/wonen.json**

```json
{
  "id": "SSET-wonen-utrecht-uitdagingen",
  "useCase": "wonen",
  "description": "Uitdagingen-curation (Wonen & Werken): streng stedelijk-alleen, flexwoningen dicht en de stilte-tegenbeeld.",
  "scenarios": [
    {
      "id": "SC-WN-ALLEEN-STEDELIJK",
      "name": "Housing only within existing urban area",
      "description": "Drops the exception composition — kernrandzone (FR-WN-04) and the three uitbreiding-woningbouw rules (FR-WN-07/08/09) — leaving only the stedelijk gebied opening: the strictest anti-verstedelijking reading.",
      "objectType": "housing_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-WN-01",
        "provenanceNote": "NC-WN-01 (art. 9.3) carries the verstedelijkingsverbod of het Landelijk gebied; its tenzij-structure is operationalized by the inclusion composition, which this variant removes (strictest reading)."
      },
      "mutations": [
        {"ruleId": "FR-WN-04", "action": "drop"},
        {"ruleId": "FR-WN-07", "action": "drop"},
        {"ruleId": "FR-WN-08", "action": "drop"},
        {"ruleId": "FR-WN-09", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-WN-FLEXWONINGEN-DICHT",
      "name": "Flexwoningen route closed",
      "description": "Drops FR-WN-08 (art. 9.14a, one-time temporary expansion up to 50 flexwoningen per kern) — the temporary-housing lever disappears.",
      "objectType": "housing_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-WN-08",
        "provenanceNote": "NC-WN-08 (art. 9.14a) is the flexwoningen exception; this variant documents dropping that specific lever."
      },
      "mutations": [
        {"ruleId": "FR-WN-08", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-WN-STILTE-1KM",
      "name": "Stiltegebied protection widened: markers hard, attention at 1 km",
      "description": "Executes FR-WN-11 (stiltegebied) and FR-WN-12 (aandachtsgebied) as hard exclusions and widens the attention zone by 1 km — a hypothetical quietness-buffer for housing.",
      "objectType": "housing_development",
      "basis": {
        "type": "hypothetical",
        "rationale": "Arts. 9.27/9.29 are rekening-houden markers without spatial consequence in the baseline; a 1 km housing buffer around stiltegebieden is not cited anywhere — this hypothetical measures its cost.",
        "provenanceNote": "NOT legally grounded: the stiltegebied designations (NC-WN-11/NC-WN-12) are cited, the hard enforcement and the 1 km widening are the scenario's own parameters."
      },
      "mutations": [
        {"ruleId": "FR-WN-11", "action": "set_semantics", "zoneSemantics": "exclusion"},
        {"ruleId": "FR-WN-12", "action": "set_semantics", "zoneSemantics": "exclusion"},
        {"ruleId": "FR-WN-12", "action": "set_buffer_distance_m", "bufferDistanceM": 1000}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

Let op: als de sweep SC-WN-STILTE-1KM op een dubbele mutatie van FR-WN-12 afkeurt (mutatiesSkipped met reden), verwijder dan de derde mutatie-entry en documenteer dat in de commit-message — de stilte-hard-enforcement blijft dan het scenario.

- [ ] **Step 2: Schrijf poc/scenarios/werken.json**

```json
{
  "id": "SSET-werken-utrecht-uitdagingen",
  "useCase": "werken",
  "description": "Uitdagingen-curation (Wonen & Werken): de WN-03-les als variant, streng stedelijk-alleen en een uitbreidingsband.",
  "scenarios": [
    {
      "id": "SC-WE-DETAILHANDEL-HARD",
      "name": "Detailhandel verbod executed over the whole object",
      "description": "FR-WE-06 (art. 9.20) refuses detailhandel buiten bestaand winkelgebied but is sub-class-scoped (markers never eliminate area for bedrijventerreinen); this variant executes the over-broad reading that nullified the 9.16/9.18 openings in the pipeline's first run (WN-03 lesson) — now as an explicit scenario.",
      "objectType": "business_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-WE-06",
        "provenanceNote": "NC-WE-06 (art. 9.20) is sub-class-scoped to detailhandel; the over-broad area exclusion was re-adjudicated (WN-03). This variant makes that strict reading an explicit, visible policy choice."
      },
      "mutations": [
        {"ruleId": "FR-WE-06", "action": "set_semantics", "zoneSemantics": "exclusion"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-WE-ALLEEN-STEDELIJK",
      "name": "Business development only within existing urban area",
      "description": "Drops FR-WE-03 (art. 9.16, uitbreiding bedrijventerrein onder voorwaarden, 703.4 km²) — companies remain limited to the stedelijk gebied opening (art. 9.18).",
      "objectType": "business_development",
      "basis": {
        "type": "policy_variant",
        "normCardId": "NC-WE-03",
        "provenanceNote": "NC-WE-03 (art. 9.16) is the conditioned bedrijventerrein-uitbreiding exception; this variant documents dropping that lever (strictest anti-expansion reading)."
      },
      "mutations": [
        {"ruleId": "FR-WE-03", "action": "drop"}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    },
    {
      "id": "SC-WE-BEDRIJVENTERREIN-BUFFER-500",
      "name": "Bedrijventerrein designation expanded by a 500 m band",
      "description": "Buffers the art. 9.16 inclusion (FR-WE-03) outward by 500 m — an expansion-band variant.",
      "objectType": "business_development",
      "basis": {
        "type": "hypothetical",
        "rationale": "The designation envelope is a programming area; a 500 m band is not cited anywhere — this hypothetical measures what it would add.",
        "provenanceNote": "NOT legally grounded: the designation (NC-WE-03, art. 9.16) is cited, the 500 m band is the scenario's own parameter."
      },
      "mutations": [
        {"ruleId": "FR-WE-03", "action": "set_buffer_distance_m", "bufferDistanceM": 500}
      ],
      "proposedBy": "deterministic-scenario-author#poc-v0"
    }
  ]
}
```

Let op: verifieer in Step 3 dat `NC-WE-03` bestaat in `poc/runs/20261006T121921Z-werken/normcards.json` (regel-id FR-WE-03 verwijst naar NC-WE-03 in de formalrules-dump). Zo niet, gebruik het normCardId uit de run.

- [ ] **Step 3: Voer de sweeps uit en vul scenarioRuns**

```bash
cd /Users/marc/Projecten/ldttoolbox && python3 poc/scenarios/run.py --use-case wonen
python3 poc/scenarios/run.py --use-case werken
```
Expected: beide `verdict: pass`.

Vul `"wonen"` en `"werken"` in `uitdagingen.json`.

- [ ] **Step 4: Commit**

```bash
git add poc/scenarios/wonen.json poc/scenarios/werken.json poc/scenarios/uitdagingen.json
git commit -m "feat(poc): wonen- en werken-scenario-sets (uitdagingen Wonen & Werken, plan 1)"
```

---

### Task 8: volledige uitdagingen-test (id-resolutie + basis-verdeling)

**Files:**
- Modify: `poc/tests/test_uitdagingen.py`

**Interfaces:**
- Consumes: alle 13 set-bestanden (Task 2–7); canonieke runs (`poc/runs/<id>/normcards.json`, `formalrules.json`); `uitdagingen.json::scenarioRuns` (Task 3–7).
- Produces: het curation-contract als test — elke toekomstige set-wijziging wordt hierop gecontroleerd.

- [ ] **Step 1: Voeg de resolutie- en verdelingstests toe**

```python
BASELINES = {
    "wind": "20260830T113234Z-wind", "zon": "20260830T142439Z-zon",
    "bos": "20260830T142446Z-bos", "water": "20261004T185116Z-water",
    "bodem": "20261004T185509Z-bodem", "mobiliteit": "20261005T072839Z-mobiliteit",
    "landschap": "20261005T070621Z-landschap", "landbouw": "20261005T094244Z-landbouw",
    "wonen": "20261005T100258Z-wonen", "werken": "20261006T121921Z-werken",
    "recreatie": "20261006T114934Z-recreatie", "biomassa": "20261006T120133Z-biomassa",
    "energietoets": "20261006T171730Z-energietoets",
}


def test_elke_basis_normcardid_resolvet_in_baseline():
    for track in ALLE_TRACKS:
        cards = json.loads(
            (ROOT.parent / "runs" / BASELINES[track] / "normcards.json")
            .read_text(encoding="utf-8"))
        cards = cards if isinstance(cards, list) else cards.get("normCards", [])
        card_ids = {c["id"] for c in cards}
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        for sc in s["scenarios"]:
            nc = sc["basis"].get("normCardId")
            if nc:
                assert nc in card_ids, f"{sc['id']}: {nc} niet in baseline {track}"


def test_elke_mutation_ruleid_resolvet_in_baseline():
    for track in ALLE_TRACKS:
        rules = json.loads(
            (ROOT.parent / "runs" / BASELINES[track] / "formalrules.json")
            .read_text(encoding="utf-8"))
        rules = rules.get("formalRules", rules) if isinstance(rules, dict) else rules
        rule_ids = {r["id"] for r in rules}
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        for sc in s["scenarios"]:
            for m in sc["mutations"]:
                assert m["ruleId"] in rule_ids, f"{sc['id']}: {m['ruleId']} niet in baseline {track}"


def test_basis_verdeling_volgt_curation_principe():
    for track in ALLE_TRACKS:
        s = json.loads((ROOT / "scenarios" / f"{track}.json").read_text(encoding="utf-8"))
        types = [sc["basis"]["type"] for sc in s["scenarios"]]
        assert types.count("policy_variant") >= 1, track
        assert types.count("hypothetical") >= 1 or types.count("policy_variant") >= 2, track
        for sc in s["scenarios"]:
            b = sc["basis"]
            if b["type"] == "hypothetical":
                assert "NOT legally grounded" in b["provenanceNote"], sc["id"]


def test_scenarioRuns_wijzen_naar_bestaande_pass_runs():
    for track, run in _load()["scenarioRuns"].items():
        assert run is not None, track
        rep = json.loads(
            (ROOT / "scenario-runs" / run / "scenario-report.json")
            .read_text(encoding="utf-8"))
        assert rep["verdict"] == "pass", track
```

- [ ] **Step 2: Run tests to verify it passes**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -v`
Expected: PASS (7 tests). Als `NC-WE-03` niet bestaat: corrigeer `werken.json` (Step 3 van Task 7) en her-run de werken-sweep.

- [ ] **Step 3: Commit**

```bash
git add poc/tests/test_uitdagingen.py
git commit -m "test(poc): uitdagingen-curation-contract — id-resolutie, basis-verdeling, pass-runs (plan 1)"
```

---

### Task 9: scenario_catalog met uitdaging-groepering

**Files:**
- Modify: `deep-agents/scenario_catalog.py`
- Test: `poc/tests/test_scenario_catalog.py` (uitbreiding)

**Interfaces:**
- Consumes: `poc/scenarios/uitdagingen.json` (Task 1, gevuld in 3–7).
- Produces: `describe_scenario_run(path) -> dict` met extra keys `trackKey: str|None`, `uitdaging: {"id": str, "titel": str}|None`; `list_scenario_runs(root) -> list[dict]` gesorteerd op uitdaging-volgorde, dan track, dan id; featured (★) = de run die in `scenarioRuns[track]` staat. Het dashboard (Task 10) gebruikt `s.uitdaging.titel` voor optgroups.

- [ ] **Step 1: Voeg de failing tests toe in poc/tests/test_scenario_catalog.py**

```python
def test_uitdaging_groepering_wind():
    row = describe_scenario_run(RUNS / "20260831T074521Z-wind-scen")
    u = row.get("uitdaging")
    assert u is not None and u["id"] == "energietransitie" and u["titel"] == "Energietransitie"
    assert row["trackKey"] == "wind"


def test_uitdaging_volgt_trackkey():
    rows = list_scenario_runs(RUNS)
    for r in rows:
        if r["trackKey"] is None or r["id"].startswith("_fixture"):
            assert r["uitdaging"] is None, r["id"]
        else:
            assert r["uitdaging"] is not None, r["id"]
            assert r["uitdaging"]["titel"], r["id"]


def test_scenarioRuns_uit_uitdagingen_json_zijn_featured():
    rows = list_scenario_runs(RUNS)
    featured = [r for r in rows if r["featured"]]
    assert len(featured) >= 13
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_scenario_catalog.py -v`
Expected: FAIL — keys ontbreken.

- [ ] **Step 2: Herschrijf deep-agents/scenario_catalog.py**

```python
"""Human-readable labels for poc/scenario-runs (Utrecht / Crosstrack demos)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_OBJECT_NL: dict[str, str] = {
    "wind_turbine": "windturbines",
    "solar_field": "zonneparken",
    "solar_farm": "zonneparken",
    "forest": "bos",
    "forest_planting": "bosplanting",
}

# track-key → Nederlands label (behavior behouden uit de oude _track_nl)
_TRACK_KEY_NL: dict[str, str] = {
    "wind": "Wind", "zon": "Zon", "bos": "Bos", "water": "Water",
    "bodem": "Bodem", "mobiliteit": "Mobiliteit", "landschap": "Landschap",
    "landbouw": "Landbouw", "wonen": "Wonen", "werken": "Werken",
    "recreatie": "Recreatie", "biomassa": "Biomassa", "energietoets": "Energietoets",
}

# langste tokens eerst: 'energietoets' vóór 'et' nooit nodig, maar
# 'wonen'/'werken' niet laten botsen met 'wind'/'water'
_TRACK_TOKENS: list[tuple[str, str]] = [
    ("energietoets", "energietoets"), ("biomassa", "biomassa"),
    ("recreatie", "recreatie"), ("landschap", "landschap"),
    ("landbouw", "landbouw"), ("mobiliteit", "mobiliteit"),
    ("werken", "werken"), ("wonen", "wonen"), ("water", "water"),
    ("bodem", "bodem"), ("forest", "bos"), ("solar", "zon"), ("zon", "zon"),
    ("wind", "wind"), ("bos", "bos"),
]


def _uitdagingen_doc(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "poc" / "scenarios" / "uitdagingen.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _track_key(run_id: str) -> str | None:
    rid = run_id.lower()
    for token, key in _TRACK_TOKENS:
        if token in rid:
            return key
    return None


def _kind_nl(run_id: str) -> str:
    if run_id.startswith("_fixture"):
        return "Test-fixture (ontwikkeling)"
    if "authorcmp" in run_id:
        return "Authoring vs engine (vergelijking)"
    if "scen" in run_id:
        return "Beleidsvarianten (world scene)"
    return "Scenario-run"


def describe_scenario_run(
    run_dir: Path, utd_doc: dict[str, Any] | None = None
) -> dict[str, Any]:
    run_id = run_dir.name
    report_path = run_dir / "scenario-report.json"
    report: dict[str, Any] = {}
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))

    track_key = _track_key(run_id)
    track = _TRACK_KEY_NL.get(track_key, "Meerdere tracks") if track_key else "Meerdere tracks"
    kind = _kind_nl(run_id)
    obj = _OBJECT_NL.get(str(report.get("objectType", "")), str(report.get("objectType", "") or "locaties"))
    n_var = len(report.get("scenarios") or [])

    uitdaging: dict[str, str] | None = None
    featured = False
    utd_order = ""
    if utd_doc:
        for i, utd in enumerate(utd_doc.get("uitdagingen", [])):
            if track_key and track_key in utd.get("tracks", []):
                uitdaging = {"id": utd["id"], "titel": utd["titel"]}
                j = utd["tracks"].index(track_key)
                utd_order = f"{i}{j:02d}"
                featured = utd_doc.get("scenarioRuns", {}).get(track_key) == run_id
                break

    label_parts = [track, kind]
    if n_var and "authorcmp" not in run_id and not run_id.startswith("_fixture"):
        label_parts.append(f"{n_var} varianten")
    label = " · ".join(label_parts)
    if featured:
        label = f"★ {label}"

    hints: list[str] = []
    if obj and obj != "locaties":
        hints.append(f"Vraagtype: waar mogen {obj}?")
    for sc in (report.get("scenarios") or [])[:2]:
        name = (sc.get("name") or "").strip()
        if name:
            hints.append(name)
    hint = " — ".join(hints) if hints else f"Technische run-id: {run_id}"

    return {
        "id": run_id,
        "label": label,
        "hint": hint,
        "featured": featured,
        "track": track,
        "trackKey": track_key,
        "uitdaging": uitdaging,
        "variantCount": n_var,
        "sortKey": ("0" if featured else "1") + (utd_order or "9") + run_id,
    }


def list_scenario_runs(scenario_runs_root: Path) -> list[dict[str, Any]]:
    if not scenario_runs_root.is_dir():
        return []
    repo_root = scenario_runs_root.parent.parent
    utd_doc = _uitdagingen_doc(repo_root)
    rows = [
        describe_scenario_run(p, utd_doc)
        for p in scenario_runs_root.iterdir()
        if p.is_dir() and (p / "scenario-report.json").is_file()
    ]
    rows.sort(key=lambda r: r["sortKey"])
    return rows
```

Let op: `RUNS = deep-agents/runs/poc/scenario-runs`? Nee — `SCENARIO_RUNS = HERE.parent / "poc" / "scenario-runs"` in live_server; dus `scenario_runs_root.parent.parent` = repo-root. Verifieer met een snelle check: `python3 -c "from pathlib import Path; print((Path('poc/scenario-runs').parent.parent))"` vanuit deep-agents → repo-root.

- [ ] **Step 3: Verwijder de oude _FEATURED_SUFFIXES-code** (staat nu in het nieuwe bestand niet meer; check dat geen enkele import `describe_scenario_run` zonder tweede argument gebruikt op de oude wijze — het tweede argument is optioneel, dus backwards-compatibel).

Run: `grep -rn "_FEATURED_SUFFIXES\|_track_nl" /Users/marc/Projecten/ldttoolbox --include="*.py"`
Expected: alleen nog in tests die de oude namen niet aanroepen (verifieer; pas zo nodig die tests aan).

- [ ] **Step 4: Run beide testbestanden**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_scenario_catalog.py tests/test_uitdagingen.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add deep-agents/scenario_catalog.py poc/tests/test_scenario_catalog.py
git commit -m "feat(deep-agents): scenario_catalog groepeert runs per uitdaging, featured uit uitdagingen.json (plan 1)"
```

---

### Task 10: dashboard optgroups per uitdaging

**Files:**
- Modify: `deep-agents/dashboard.html` (scenario-picker, rond regel 330)

**Interfaces:**
- Consumes: `/api/scenarios` rows met `uitdaging: {id, titel}|null` (Task 9).
- Produces: `<optgroup label="<uitdaging-titel>">` per uitdaging, in de gesorteerde volgorde van de API; runs zonder uitdaging vallen onder "Overig".

- [ ] **Step 1: Vervang de optlist-rendering**

Vervang in `dashboard.html` het blok:

```js
    $('scenario').innerHTML = scen.map(s => {
      const id = typeof s === 'string' ? s : s.id;
      const label = typeof s === 'string' ? s : (s.label || id);
      const hint = typeof s === 'object' && s.hint ? s.hint : '';
      return `<option value="${escapeHtml(id)}" data-hint="${escapeHtml(hint)}">${escapeHtml(label)}</option>`;
    }).join('');
```

door:

```js
    const opt = s => {
      const id = typeof s === 'string' ? s : s.id;
      const label = typeof s === 'string' ? s : (s.label || id);
      const hint = typeof s === 'object' && s.hint ? s.hint : '';
      return `<option value="${escapeHtml(id)}" data-hint="${escapeHtml(hint)}">${escapeHtml(label)}</option>`;
    };
    const groups = new Map();
    for (const s of scen) {
      const titel = (typeof s === 'object' && s.uitdaging) ? s.uitdaging.titel : 'Overig';
      if (!groups.has(titel)) groups.set(titel, []);
      groups.get(titel).push(opt(s));
    }
    $('scenario').innerHTML = [...groups.entries()]
      .map(([titel, opts]) => `<optgroup label="${escapeHtml(titel)}">${opts.join('')}</optgroup>`)
      .join('');
```

(De daaropvolgende regels — `localStorage`-restore en `featured`-selectie — blijven ongewijzigd; `$('scenario').value = ...` werkt met optgroups onveranderd.)

- [ ] **Step 2: Handmatige rooktest**

Start de server en open het dashboard:

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && python3 live_server.py
```
Open http://127.0.0.1:8000 (of de poort uit de log), kies POC "Utrecht".
Expected: de scenario-picker toont 5 optgroups in uitdaging-volgorde (Energietransitie → Landelijk Gebied & Natuur) plus "Overig" voor authorcmp/fixture-runs; de eerste featured run is voorgeselecteerd.

Stop de server daarna (`Ctrl+C`).

- [ ] **Step 3: Commit**

```bash
git add deep-agents/dashboard.html
git commit -m "feat(deep-agents): scenario-picker gegroepeerd per uitdaging (optgroups, plan 1)"
```

---

### Task 11: Utrecht-prompts — uitdaging-overzicht mode

**Files:**
- Modify: `deep-agents/poc_demos.py` (`_UTRECHT_MODES`-lijst, na de laatste entry "keten")
- Modify: `deep-agents/prompts/poc/utrecht.md` (Rules-sectie)

**Interfaces:**
- Consumes: `poc/scenarios/uitdagingen.json`; scenario-reports van de featured runs (velden `scenarios[].scenarioId/name/deltaVsControlPct`).
- Produces: prompt-modus `uitdaging_overzicht` in `/api/modes?poc=utrecht`.

- [ ] **Step 1: Voeg de mode toe aan _UTRECHT_MODES**

Voeg als laatste entry van de lijst `_UTRECHT_MODES` in `poc_demos.py` toe:

```python
    {
        "id": "uitdaging_overzicht",
        "label": "Uitdaging-overzicht (5 opgaven × 3 scenario's)",
        "template": (
            "Delegeer naar utrecht: geef het uitdaging-overzicht — lees "
            "poc/scenarios/uitdagingen.json en geef per uitdaging (5 stuks): de titel, "
            "de tracks, en per track de 3 scenario's met de headline-delta "
            "(deltaVsControlPct uit scenario-report.json van de run in scenarioRuns). "
            "Sluit af met per uitdaging de grootste hefboom (grootste |delta|)."
        ),
    },
```

- [ ] **Step 2: Voeg regel 6 toe aan de Rules van prompts/poc/utrecht.md**

Voeg na regel 5 (`5. Reply in the language the user wrote in.`) toe:

```markdown
6. For uitdaging (policy-challenge) overviews: `poc/scenarios/uitdagingen.json` is the
   single source of truth — 5 uitdagingen, each with its tracks and the featured
   scenario-run per track in `scenarioRuns`. Summarise each track's 3 scenarios with
   their `deltaVsControlPct` from that run's `scenario-report.json`; name the biggest
   lever per uitdaging. Never invent runs or deltas.
```

- [ ] **Step 3: Run de wiring-tests**

Run: `cd /Users/marc/Projecten/ldttoolbox/deep-agents && python3 -m pytest tests/test_agent_wiring.py tests/test_poc_live.py -q`
Expected: PASS. Als een test het mode-aantal telt: verhoog de verwachte telling met 1.

- [ ] **Step 4: Commit**

```bash
git add deep-agents/poc_demos.py deep-agents/prompts/poc/utrecht.md
git commit -m "feat(deep-agents): uitdaging-overzicht mode voor de Utrecht-specialist (plan 1)"
```

---

### Task 12: volledige suite, README-tabel en spec-vastlegging

**Files:**
- Modify: `poc/README.md` (sectie "Scenario planning", regels ~370–376)
- Modify: `docs/superpowers/specs/2026-10-13-utrecht-uitdagingen-design.md` (afwijkingsnotitie)

- [ ] **Step 1: Volledige offline suite + goldens**

```bash
cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests -q
```
Expected: alle tests groen (geen pipeline-wijzigingen, dus geen golden-drift).

- [ ] **Step 2: Vervang de demo-sets-zin in poc/README.md**

Vervang in `poc/README.md` de zin die begint met `Demo sets:
`poc/scenarios/{wind,zon,bos}.json` — headline findings: …` (tot aan
`--author auto` adds: …) door:

```markdown
Demo sets: `poc/scenarios/<track>.json` — **5 uitdagingen × 13 tracks ×
precies 3 scenario's per track** (curation-contract in
`poc/scenarios/uitdagingen.json`, getest in `tests/test_uitdagingen.py`):

| uitdaging | tracks | per track 3 scenario's, o.a. |
|---|---|---|
| Energietransitie | wind, zon, biomassa, energietoets | NNN-uitzondering +322,5 km²; overstroombaar/waterberging-verhalen bij water; energietoets is ruimtelijk blind (−100% bij handhaving) |
| Wonen & Werken | wonen, werken | alleen-stedelijk-tegenbeelden; detailhandel-verbod over het hele object (WN-03-les als variant) |
| Water & Bodem | water, bodem | overstroombaar gebied hard −1207 km²; grondwaterbeschermingsversoepeling +701 km² |
| Landschap & Infrastructuur | landschap, mobiliteit | CHS hard −847 km²; luchtvaartverbod zonder activity-scope −1014 km² |
| Landelijk Gebied & Natuur | bos, landbouw, recreatie | compensatie-eerst −100% zoekgebied; glastuinbouw-tegenbeeld +1557 km² |

Elke track toont drie beleidsknoppen: een gedocumenteerde keuze omgedraaid
(`policy_variant`), een geciteerde parameter gevarieerd (`norm_variance`) en
een expliciet niet-juridisch tegenbeeld (`hypothetical`). Run-ids van de
featured runs staan in `uitdagingen.json::scenarioRuns`.
```

- [ ] **Step 3: Leg de afwijkingen vast in de uitdagingen-spec**

Voeg aan `docs/superpowers/specs/2026-10-13-utrecht-uitdagingen-design.md`
(achteraan) toe:

```markdown
## 9. Vastlegging uitvoering (2026-10-13)

De scenario-keuzes van §4 zijn bij implementatie vastgelegd op de
ruleIds/mutaties in `docs/superpowers/plans/2026-10-13-utrecht-uitdagingen.md`
(tabel "Vastgelegde scenario-keuzes"). Afwijkingen t.o.v. de §4-intenties, met
reden (de sweep muteert alleen regels uit de eigen baseline-run van de track —
lagen die daar niet in zitten, zijn niet muteerbaar):

- **bos #2** "beperkt tot 500 m-zone rond NNN" → SC-B-COMPENSATIE-HARD
  (FR-B-02 als uitsluiting): de bos-baseline heeft geen NNN-laag.
- **landbouw #2** "250 m-buffer rond concentratiegebied" → SC-LB-BEDRIJVEN-HARD
  (FR-LB-01 als uitsluiting): buffer op een conditional-marker levert Δ0.
- **werken #3** "500 m-zone rond NNN" → buffer FR-WE-03 +500 m: geen NNN-laag.
- **recreatie #3** "250 m-zone rond NNN" → SC-RC-DAGRECREATIE-ALLEEN-AANDACHT:
  geen NNN-laag; de aandachts-tegenbeeld meet de opening zelf.
- **biomassa #2** "Groene contour als harde uitsluiting" → SC-BM-STEDELIJK-HARD:
  de biomassa-baseline heeft geen contour-rule.
- **energietoets #3** (netcongestie, data-gegrond) volgt in
  2026-10-13-utrecht-data-kalibratie-design.md; de set telt nu 2 scenario's.
```

- [ ] **Step 4: Commit**

```bash
git add poc/README.md docs/superpowers/specs/2026-10-13-utrecht-uitdagingen-design.md
git commit -m "docs(poc): uitdagingen-tabel in README + spec-vastlegging uitvoering (plan 1 afgerond)"
```
