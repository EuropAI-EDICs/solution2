# Utrecht-PoC data-kalibratie + landelijke bronnen — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een herhaalbare kalibratieloop (CVDR-diff, geo-versheid, zone-drift, rapport) plus landelijke aanvulbronnen (CBS, RCE, DINO, RWS/NGR, netbeheerders) als contextlaag en scenario-basis, waarmee het energietoets-scenario SC-ET-NETCONGESTIE data-gegrond wordt.

**Architecture:** Nieuwe fetcher-module (`poc/pipeline/national_data.py`) met cache-first-opslag onder `poc/data/cache/national/`; schema-uitbreiding `basis.dataGrounding` in het scenario-contract; V2-grounding in de sweep; kalibratiescript `poc/data/calibrate.py`; context-visualisatie als zelfstandige Leaflet-pagina's gegenereerd door `poc/pipeline/context_map.py` en gelinkt vanuit het dashboard via `simulationPages`.

**Tech Stack:** Python 3.13 stdlib (urllib, json, csv), bestaande poc-pijplijn, pytest.

**Spec:** `docs/superpowers/specs/2026-10-13-utrecht-data-kalibratie-design.md`. Vereist dat plan 1 (`2026-10-13-utrecht-uitdagingen.md`) is uitgevoerd (uitdagingen.json + sets bestaan).

## Global Constraints

- Landelijke bronnen krijgen uitsluitend `role: "context"` of `role: "scenario-basis"` in `poc/data/sources.json`; nooit `inclusion`/`exclusion`/`conditional` — die zijn voorbehouden aan geciteerde verordening-zones.
- Geen juridische claims uit nationale bronnen: normcards, formalrules en de engine (zoneSemantics-berekening) worden niet gewijzigd. De enige pijplijn-aanpassing is de V2-dataGrounding-check (Task 2).
- Alles cache-first: offline tests draaien op fixtures onder `poc/tests/fixtures/national/`; live-fetch alleen bij `refresh=True` of expliciete stappen.
- Elke taak eindigt groen op: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests -q` (volledige suite) plus de nieuwe tests.
- URLs van externe diensten worden als module-constante gedefinieerd en in de eerste live-stap van elke fetcher-taak geverifieerd; als een dienst is verplaatst, wordt de constante bijgewerkt vanuit de genoemde cataloguspagina en wordt dat in de commit-message vermeld.
- Commit-formaat: `feat(poc): … (kalibratie, plan 2, task N)`.

---

### Task 1: schema-uitbreiding `basis.dataGrounding`

**Files:**
- Modify: `poc/schemas/scenario-spec.schema.json` (basis-properties)
- Test: `poc/tests/test_scenarios.py` (uitbreiding)

**Interfaces:**
- Produces: optioneel veld `basis.dataGrounding` — shape `{"sourceId": str, "retrieved": str(ISO-datum), "note": str}` (note optioneel), `additionalProperties: false`. Alleen zinvol bij `basis.type: "hypothetical"` (validator ziet alleen structuur, niet het type). Task 2 consumeert dit in de V2-check.

- [ ] **Step 1: Write the failing test**

Voeg aan `poc/tests/test_scenarios.py` toe (aan het einde van het bestand):

```python
def test_data_grounding_is_toegestaan_op_hypothetical_basis():
    spec = {
        "id": "SC-T-DG", "name": "test", "objectType": "energy_storage",
        "basis": {
            "type": "hypothetical",
            "rationale": "data-grounded variant",
            "provenanceNote": "NOT legally grounded: data-grounded only.",
            "dataGrounding": {"sourceId": "netbeheerder-netcongestie",
                              "retrieved": "2026-10-13"},
        },
        "mutations": [{"ruleId": "FR-ET-01", "action": "drop"}],
        "proposedBy": "test",
    }
    contracts.validate(spec, "scenario-spec")  # moet door de V0-gate


def test_data_grounding_verplicht_retrieved():
    spec = {
        "id": "SC-T-DG2", "name": "test", "objectType": "energy_storage",
        "basis": {
            "type": "hypothetical",
            "provenanceNote": "NOT legally grounded.",
            "dataGrounding": {"sourceId": "netbeheerder-netcongestie"},
        },
        "mutations": [{"ruleId": "FR-ET-01", "action": "drop"}],
        "proposedBy": "test",
    }
    with pytest.raises(contracts.ValidationError):
        contracts.validate(spec, "scenario-spec")
```

(Importeer zo nodig bovenin: `import pytest` — staat er al; `contracts` idem. Run anders eerst `head -30 poc/tests/test_scenarios.py` en gebruik dezelfde importstijl.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_scenarios.py -k data_grounding -v`
Expected: FAIL — `additionalProperties`-violatie op `dataGrounding`.

- [ ] **Step 3: Patch het schema**

In `poc/schemas/scenario-spec.schema.json`, binnen `properties.basis.properties`, voeg toe:

```json
"dataGrounding": {
  "type": "object",
  "description": "Optional non-legal grounding: a national data source that parameterises this hypothetical. Never a legal claim.",
  "additionalProperties": false,
  "required": ["sourceId", "retrieved"],
  "properties": {
    "sourceId": {"type": "string", "minLength": 1},
    "retrieved": {"type": "string", "format": "date"},
    "note": {"type": "string"}
  }
}
```

(Plaatsing: in het `properties`-object van `basis`, naast `type`/`normCardId`/`variedAspect`/`rationale`/`provenanceNote`. Controleer of de test-runner `format: date` afdwingt — jsonschema doet dat alleen met een format-checker; de pooc-contracts.validate gebruikt dat mogelijk niet. Task 2 controleert de ISO-vorm daarom deterministisch in Python.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_scenarios.py -k data_grounding -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add poc/schemas/scenario-spec.schema.json poc/tests/test_scenarios.py
git commit -m "feat(poc): scenario-spec basis.dataGrounding — niet-juridische data-onderbouwing (kalibratie, plan 2, task 1)"
```

---

### Task 2: V2-dataGrounding-check in de sweep

**Files:**
- Modify: `poc/pipeline/scenarios.py` (sweep-loop rond regel 452–470 + rapport-regel 558)
- Test: `poc/tests/test_scenarios.py`

**Interfaces:**
- Consumes: `basis.dataGrounding` (Task 1); de registry-lookup die de sweep-runner al heeft (`sources`-variabele in de sweep-loop van `pipeline/scenarios.py`).
- Produces: V2-check `v2-data-grounding` in elk scenario-validation report — fail bij onbekende sourceId, verkeerde rol of onparsebare retrieved-datum.

- [ ] **Step 1: Verifieer de registry-vorm in de sweep-scope**

```bash
grep -n "sources" /Users/marc/Projecten/ldttoolbox/poc/scenarios/run.py | head -10
grep -n "def sweep\|sources=" /Users/marc/Projecten/ldttoolbox/poc/pipeline/scenarios.py | head -10
```
Expected: bevestigt hoe `sources` in de sweep-loop binnenkomt (dict met registry-entries of lijst). Pas in de code hieronder één regel aan als de vorm een lijst is: `SRC = {s["id"]: s for s in sources}` i.p.v. directe lookup.

- [ ] **Step 2: Write the failing test**

Voeg aan `poc/tests/test_scenarios.py` toe:

```python
def test_v2_data_grounding_berekent_fouten():
    from pipeline.scenarios import _data_grounding_errors
    src = {"netbeheerder-netcongestie": {"id": "netbeheerder-netcongestie",
                                         "role": "scenario-basis"}}
    assert _data_grounding_errors(src, {"sourceId": "netbeheerder-netcongestie",
                                        "retrieved": "2026-10-13"}) == []
    assert "onbekende sourceId" in _data_grounding_errors(
        src, {"sourceId": "bestaat-niet", "retrieved": "2026-10-13"})[0]
    assert "role" in _data_grounding_errors(
        src, {"sourceId": "netbeheerder-netcongestie",
              "retrieved": "2026-10-13"})[0] or "context" in _data_grounding_errors(
        {"netbeheerder-netcongestie": {"id": "x", "role": "context"}},
        {"sourceId": "netbeheerder-netcongestie", "retrieved": "2026-10-13"})[0]
    assert "ISO" in _data_grounding_errors(
        src, {"sourceId": "netbeheerder-netcongestie", "retrieved": "gisteren"})[0]
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_scenarios.py -k v2_data_grounding -v`
Expected: FAIL — ImportError (`_data_grounding_errors` bestaat niet).

- [ ] **Step 3: Implementeer de helper en de V2-koppeling**

In `poc/pipeline/scenarios.py` voeg bovenaan (bij de bestaande imports) toe: `import datetime` (als die nog niet bestaat). Voeg toe (bijv. vlak boven `evaluate_scenario_run`):

```python
def _data_grounding_errors(
    source_ids: Mapping[str, Any], dg: Mapping[str, Any]
) -> List[str]:
    """V2-hulp: fouten op een basis.dataGrounding-blok (leeg = geen fouten)."""
    errs: List[str] = []
    sid = str(dg.get("sourceId", ""))
    entry = source_ids.get(sid) if isinstance(source_ids, Mapping) else None
    if entry is None:
        errs.append(f"onbekende sourceId {sid} in sources.json")
        return errs
    role = str(entry.get("role", ""))
    if role != "scenario-basis":
        errs.append(f"sourceId {sid} heeft role {role or '?'}, verwacht scenario-basis")
    try:
        datetime.date.fromisoformat(str(dg.get("retrieved", "")))
    except ValueError:
        errs.append(f"retrieved {dg.get('retrieved')!r} is geen ISO-datum")
    return errs
```

In de sweep-loop (na de bestaande `nc`-normcard-check, rond regel 465) voeg toe:

```python
        if isinstance(spec["basis"], dict):
            for dg_err in _data_grounding_errors(
                    source_ids, spec["basis"].get("dataGrounding") or {}):
                if dg_err:
                    v2_datagrounding.append(f"{sid}:{dg_err}")
```

met boven de loop (naast `v2_unknown`/`v2_normcard_missing`, regel ~455):

```python
    v2_datagrounding: List[str] = []
```

en waar `source_ids` niet bestaat in de sweep-scope, bouw het uit de registry zoals Step 1 aantoonde (lijst → dict met id-key). Geef de check door aan de critic door bij de `evaluate_scenario_run(...)`-aanroep (regel ~558) toe te voegen:

```python
        extra_v2_checks=[{
            "id": "v2-data-grounding",
            "status": "fail" if v2_datagrounding else "pass",
            "detail": ("dataGrounding: " + "; ".join(v2_datagrounding))
                      if v2_datagrounding else
                      "elk dataGrounding-blok: sourceId met role scenario-basis in "
                      "sources.json, retrieved ISO-datum",
        }],
```

- [ ] **Step 4: Run test to verify it passes + volledige scenario-tests**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_scenarios.py -q`
Expected: PASS (bestaande scenario-tests blijven groen — sets zonder dataGrounding krijgen de nieuwe check op `pass`).

- [ ] **Step 5: Commit**

```bash
git add poc/pipeline/scenarios.py poc/tests/test_scenarios.py
git commit -m "feat(poc): V2-dataGrounding-check in de scenario-sweep (kalibratie, plan 2, task 2)"
```

---

### Task 3: registry-entries voor de landelijke bronnen

**Files:**
- Modify: `poc/data/sources.json` (8 nieuwe entries)
- Test: `poc/tests/test_uitdagingen.py` (uitbreiding — dit bestand is het curation-contract)

**Interfaces:**
- Produces: source-ids die Task 4–6 fetchen en Task 6/7 consumeren: `cbs-grid-kerncijfers-100m`, `cbs-landgebruik-100m`, `rce-monumenten`, `rce-iam-archeologie`, `dino-bro-ondergrond`, `rws-nwb-wegen`, `prorail-spoor`, `netbeheerder-netcongestie`.

- [ ] **Step 1: Write the failing test**

Voeg aan `poc/tests/test_uitdagingen.py` toe:

```python
NATIONALE_BRONNEN = {
    "cbs-grid-kerncijfers-100m": "context",
    "cbs-landgebruik-100m": "context",
    "rce-monumenten": "context",
    "rce-iam-archeologie": "context",
    "dino-bro-ondergrond": "context",
    "rws-nwb-wegen": "context",
    "prorail-spoor": "context",
    "netbeheerder-netcongestie": "scenario-basis",
}


def test_nationale_bronnen_staan_in_registry_met_juiste_rol():
    reg = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    items = reg.get("sources", reg) if isinstance(reg, dict) else reg
    by_id = {it["id"]: it for it in items}
    for sid, role in NATIONALE_BRONNEN.items():
        assert sid in by_id, sid
        assert by_id[sid].get("role") == role, sid
        assert "serviceUrl" in by_id[sid] or "url" in by_id[sid], sid


def test_nationale_bronnen_dragen_geen_juridische_rol():
    reg = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    items = reg.get("sources", reg) if isinstance(reg, dict) else reg
    juridisch = {"inclusion", "exclusion", "conditional", "attention", "compensation"}
    for it in items:
        if it["id"] in NATIONALE_BRONNEN:
            assert it.get("role") not in juridisch, it["id"]
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -k nationaal -v`
Expected: FAIL — entries bestaan niet.

- [ ] **Step 2: Voeg de 8 entries toe aan poc/data/sources.json**

Voeg binnen de bestaande `sources`-lijst deze entries toe (serviceUrl-pinnen gebeurt live in Task 4/5/6 — zet hier de kandidaat-URL en werk die daar bij als de live-check een andere oplevert):

```json
{"id": "cbs-grid-kerncijfers-100m", "title": "CBS — Kerncijfers per vierkant (100m)", "serviceUrl": "https://opendata.cbs.nl/ODataApi/odata/84583NED", "role": "context", "publisher": "Centraal Bureau voor de Statistiek", "note": "statistische context, nooit een juridische zone"},
{"id": "cbs-landgebruik-100m", "title": "CBS — Landgebruik per vierkant (100m)", "serviceUrl": "https://opendata.cbs.nl/ODataApi/odata/", "role": "context", "publisher": "Centraal Bureau voor de Statistiek", "note": "dataset-id wordt gepind in plan-2 task 4"},
{"id": "rce-monumenten", "title": "RCE — Rijksmonumenten (WFS)", "serviceUrl": "https://services.rce.geovrijening.nl/", "role": "context", "publisher": "Rijksdienst voor het Cultureel Erfgoed", "note": "service-paden worden gepind in plan-2 task 5"},
{"id": "rce-iam-archeologie", "title": "RCE — Indicatieve Archeologische Waarden", "serviceUrl": "https://services.rce.geovrijening.nl/", "role": "context", "publisher": "Rijksdienst voor het Cultureel Erfgoed", "note": "service-paden worden gepind in plan-2 task 5"},
{"id": "dino-bro-ondergrond", "title": "DINO Loket — BRO-ondergrond (grondwater, bodemopbouw)", "serviceUrl": "https://www.dinoloket.nl/", "role": "context", "publisher": "TNO — DINO Loket", "note": "service-paden worden gepind in plan-2 task 5"},
{"id": "rws-nwb-wegen", "title": "RWS — NWB wegen (Nationaal Georegister)", "serviceUrl": "https://www.nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search", "role": "context", "publisher": "Rijkswaterstaat", "note": "WFS-endpoint wordt gepind in plan-2 task 5"},
{"id": "prorail-spoor", "title": "ProRail — spoorlijnen (Nationaal Georegister)", "serviceUrl": "https://www.nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search", "role": "context", "publisher": "ProRail", "note": "WFS-endpoint wordt gepind in plan-2 task 5"},
{"id": "netbeheerder-netcongestie", "title": "Netbeheerders — netcongestie/capaciteitskaart (Liander, Enexis, Stedin)", "serviceUrl": "https://www.netbeheernederland.nl/", "role": "scenario-basis", "publisher": "Netbeheer Nederland / Liander / Enexis / Stedin", "note": "downloadcache onder poc/data/cache/national/netcongestie/; basis voor SC-ET-NETCONGESTIE"}
```

- [ ] **Step 3: Run test to verify it passes**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py -v`
Expected: PASS (alles).

- [ ] **Step 4: Commit**

```bash
git add poc/data/sources.json poc/tests/test_uitdagingen.py
git commit -m "feat(poc): registry-entries landelijke bronnen (context + scenario-basis, kalibratie, plan 2, task 3)"
```

---

### Task 4: CBS-fetchers (grid + landgebruik)

**Files:**
- Create: `poc/pipeline/national_data.py`
- Create: `poc/tests/fixtures/national/cbs_grid_sample.json` (fixture)
- Test: `poc/tests/test_national_data.py`

**Interfaces:**
- Produces: `fetch_cbs_dataset(dataset_id: str, cache_name: str, refresh: bool = False, transport=None) -> dict` — cache-first, returnvorm `{"sourceId": str, "retrieved": str, "records": list[dict]}`; `record_in_utrecht_bbox(rec: dict) -> bool` voor de cel-filter. Task 7 (kalibratie) en Task 8 (context_map) consumeren dit.

- [ ] **Step 1: Pinn de dataset-id's live (verificatiestap)**

```bash
curl -s "https://opendata.cbs.nl/ODataApi/odata/84583NED/TableInfos" | head -c 400
```
Expected: JSON met `"Name": "Kerncijfers per vierkant (100m)"` (of vergelijkbaar). 404/leeg → zoek de opvolger via https://opendata.cbs.nl/#/ (zoek "kerncijfers per vierkant 100m") en zet `CBS_GRID_DATASET` op de gevonden id. Herhaal voor landgebruik: zoek-id vastgesteld door `curl -s "https://opendata.cbs.nl/ODataApi/odata/{id}/TableInfos"` tot de titel "Land…" + "vierkant" of "100m" matcht. Noteer beide id's + de naam van de cel-kolom (`$top=2` op TypedDataSet toont de dimensiekolommen).

- [ ] **Step 2: Write the failing test (fixture-gebaseerd)**

Maak `poc/tests/fixtures/national/cbs_grid_sample.json` (representatieve OData-pagina):

```json
{
  "value": [
    {"Vierkant100m": "b13044000", "AantalInwoners_5": 12, "AantalWoningen_11": 6, "Huurwoningen_22": 2, "Koopwoningen_23": 4},
    {"Vierkant100m": "b16047000", "AantalInwoners_5": 3, "AantalWoningen_11": 2, "Huurwoningen_22": 1, "Koopwoningen_23": 1},
    {"Vierkant100m": "b09030000", "AantalInwoners_5": 40, "AantalWoningen_11": 20, "Huurwoningen_22": 10, "Koopwoningen_23": 10}
  ],
  "next": null
}
```

(Noot: de echte kolomnamen worden in Step 1 geconstateerd; pas fixture + filter exact aan op wat de live-API toont. Het cel-formaat van het CBS-100m-grid codeert RD-coördinaten als `b` + x + y in meters ÷ 100 — b13044000 ≈ (130000, 440000), binnen de Utrecht-bbox; b09030000 buiten.)

Voeg `poc/tests/test_national_data.py` toe:

```python
"""National-data fetchers — offline, via fixtures en fake transport."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import national_data as nd  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "national"


def _fake_transport(payload: dict):
    def _t(url: str) -> dict:
        return payload
    return _t


def test_record_in_utrecht_bbox():
    assert nd.record_in_utrecht_bbox({"Vierkant100m": "b13044000"}) is True
    assert nd.record_in_utrecht_bbox({"Vierkant100m": "b16047000"}) is True
    assert nd.record_in_utrecht_bbox({"Vierkant100m": "b09030000"}) is False
    assert nd.record_in_utrecht_bbox({}) is False


def test_fetch_cbs_dataset_cache_en_filter(tmp_path):
    calls = []

    def transport(url: str) -> dict:
        calls.append(url)
        return nd.json.loads((FIXTURES / "cbs_grid_sample.json").read_text())

    out = nd.fetch_cbs_dataset(
        dataset_id="84583NED", cache_name="test-grid.json",
        refresh=True, transport=transport)
    assert out["sourceId"] == "cbs-grid-kerncijfers-100m"
    assert len(out["records"]) == 2          # alleen Utrecht-bbox-cellen
    assert out["records"][0]["Vierkant100m"] == "b13044000"
    # cache-hit: tweede call raakt de transport niet meer
    calls.clear()
    out2 = nd.fetch_cbs_dataset(
        dataset_id="84583NED", cache_name="test-grid.json",
        refresh=False, transport=transport)
    assert calls == []
    assert out2["records"] == out["records"]
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_national_data.py -v`
Expected: FAIL — module bestaat niet.

- [ ] **Step 3: Implementeer poc/pipeline/national_data.py**

```python
"""Landelijke context/scenario-basis bronnen — cache-first fetchers.

Rollen (zie poc/data/sources.json): 'context' (rapportage, nooit zone-bepalend)
en 'scenario-basis' (onderbouwt basis.dataGrounding van een hypothetical).
Cache: poc/data/cache/national/<cache_name>; offline replays via cache of
fixture-transport. Geen enkele functie hier schrijft juridische claims.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "national"

# In plan-2 task 4 stap 1 live gepinde waarden; hier bijgewerkt houden.
CBS_ODATA = "https://opendata.cbs.nl/ODataApi/odata"
CBS_GRID_DATASET = "84583NED"          # Kerncijfers per vierkant (100m)
CBS_LANDUSE_DATASET = ""               # wordt in task 4 stap 1 gepind
SOURCE_BY_CACHE = {
    "test-grid.json": "cbs-grid-kerncijfers-100m",  # test-fixture
    "cbs-grid-kerncijfers-100m.json": "cbs-grid-kerncijfers-100m",
    "cbs-landgebruik-100m.json": "cbs-landgebruik-100m",
}

Transport = Callable[[str], dict]

# Utrecht AOI in RD (EPSG:28992), gelijk aan de request-AOI van de poc
UTRECHT_BBOX_RD = (130_000.0, 440_000.0, 160_000.0, 470_000.0)


def _default_transport(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "nLDT-toolbox-poc/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _cell_rd(key: str) -> tuple[float, float] | None:
    """CBS 100m-celcode 'b' + x-m/100 + y-m/100 → RD-middelpunt (x+50, y+50)."""
    if not key.startswith("b") or not key[1:].isdigit() or len(key[1:]) != 8:
        return None
    x = int(key[1:5]) * 100
    y = int(key[5:9]) * 100
    return (x + 50.0, y + 50.0)


def record_in_utrecht_bbox(rec: dict, cell_key: str = "Vierkant100m") -> bool:
    xy = _cell_rd(str(rec.get(cell_key, "")))
    if xy is None:
        return False
    x0, y0, x1, y1 = UTRECHT_BBOX_RD
    return x0 <= xy[0] <= x1 and y0 <= xy[1] <= y1


def fetch_cbs_dataset(
    *,
    dataset_id: str,
    cache_name: str,
    refresh: bool = False,
    transport: Transport | None = None,
    cell_column: str = "Vierkant100m",
) -> dict:
    """Paged OData3 TypedDataSet-download, gefilterd op de Utrecht-bbox."""
    t = transport or _default_transport
    cache = CACHE / cache_name
    if cache.is_file() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))
    records: list[dict] = []
    url: str | None = f"{CBS_ODATA}/{dataset_id}/TypedDataSet"
    while url:
        page = t(url)
        records.extend(page.get("value", []))
        url = page.get("next") or None
    kept = [r for r in records if record_in_utrecht_bbox(r, cell_column)]
    payload = {
        "sourceId": SOURCE_BY_CACHE.get(cache_name, cache_name),
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": kept,
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload
```

Pas in hetzelfde bestand `CBS_LANDUSE_DATASET` toe op de in Step 1 gepinde waarde en werk ook `serviceUrl` van `cbs-landgebruik-100m` in `poc/data/sources.json` bij naar `https://opendata.cbs.nl/ODataApi/odata/<gepind-id>`. Voeg de landgebruik-fetcher toe als doorverwijzing:

```python
def fetch_landgebruik(refresh: bool = False, transport: Transport | None = None) -> dict:
    assert CBS_LANDUSE_DATASET, "dataset-id pinnen (plan-2 task 4 stap 1)"
    return fetch_cbs_dataset(
        dataset_id=CBS_LANDUSE_DATASET,
        cache_name="cbs-landgebruik-100m.json",
        refresh=refresh, transport=transport,
        cell_column="Vierkant100m",  # bevestig de kolomnaam uit stap 1
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_national_data.py -v`
Expected: PASS (3 tests). Daarna eenmalige live-warmloop (netwerk):

```bash
cd /Users/marc/Projecten/ldttoolbox/poc && python3 -c "
from pipeline import national_data as nd
p = nd.fetch_cbs_dataset(dataset_id=nd.CBS_GRID_DATASET, cache_name='cbs-grid-kerncijfers-100m.json')
print(len(p['records']), 'cellen in de Utrecht-bbox')
"
```
Expected: een positief aantal (orde van grootte: duizenden t/m tienduizenden cellen). Als de echte cel-kolom anders heet dan `Vierkant100m`: pas `cell_column` én `record_in_utrecht_bbox`-default aan op de geconstateerde naam en her-run de tests.

- [ ] **Step 5: Commit**

```bash
git add poc/pipeline/national_data.py poc/tests/test_national_data.py poc/tests/fixtures/national/cbs_grid_sample.json poc/data/cache/national
git commit -m "feat(poc): CBS-fetchers (kerncijfers/landgebruik 100m, cache-first, Utrecht-bbox) (kalibratie, plan 2, task 4)"
```

Let op: `poc/data/cache/national/` alleen de Utrecht-filters committen als de bestanden < ~5 MB zijn; zo niet, voeg de cache-map toe aan `.gitignore` en documenteer de warmloop-stap in de README (zie Task 9).

---

### Task 5: RCE / DINO / RWS-NGR-fetchers

**Files:**
- Modify: `poc/pipeline/national_data.py` (WFS-helper + 4 fetchers)
- Create: `poc/tests/fixtures/national/wfs_sample.json` (fixture)
- Test: `poc/tests/test_national_data.py` (uitbreiding)
- Modify: `poc/data/sources.json` (gepinde service-paden in serviceUrl)

**Interfaces:**
- Produces: `fetch_wfs(service_url: str, type_name: str, bbox_rd: tuple, cache_name: str, refresh: bool = False, transport=None) -> dict` — returnvorm als Task 4 (`sourceId/retrieved/records`, records = GeoJSON-features); `fetch_rce_erfgoed()`, `fetch_dino_ondergrond()`, `fetch_infra()` als genoemde wrappers. Task 8 (context_map) consumeert deze.

- [ ] **Step 1: Pinn de WFS-endpoints live**

```bash
# NGR-catalogus: zoek per bron het WFS GetCapabilities-endpoint
open "https://www.nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/search?facet=q=rijksmonumenten"
curl -s "https://services.rce.geovrijening.nl/geoserver/ows?service=WFS&version=2.0.0&request=GetCapabilities" | head -c 300
curl -s "https://www.dinoloket.nl/asgs-wfs/regionaal/wfs?service=WFS&version=2.0.0&request=GetCapabilities" | head -c 300
```
Expected: XML-capabilities per endpoint. Werk de exacte URL + `typeNames` (bijv. `rce:rce_monumenten`) vast in de constants van `national_data.py` en in `poc/data/sources.json` (serviceUrl). Als een endpoint verplaatst is: gebruik de NGR-cataloguslink hierboven, werk de constante bij en vermeld dat in de commit-message.

- [ ] **Step 2: Write the failing test**

Fixture `poc/tests/fixtures/national/wfs_sample.json`:

```json
{
  "type": "FeatureCollection",
  "features": [
    {"type": "Feature", "properties": {"naam": "Testmonument"}, "geometry": {"type": "Point", "coordinates": [5.10, 52.08]}}
  ]
}
```

Test (aan `poc/tests/test_national_data.py`):

```python
def test_fetch_wfs_filtert_bbox_en_cache(tmp_path):
    payload = nd.json.loads((FIXTURES / "wfs_sample.json").read_text())
    def transport(url: str) -> dict:
        assert "bbox=" in url
        return payload
    out = nd.fetch_wfs(
        service_url="https://example/wfs", type_name="test:laag",
        bbox_rd=nd.UTRECHT_BBOX_RD, cache_name="test-wfs.json",
        refresh=True, transport=transport,
        source_id="rce-monumenten")
    assert out["sourceId"] == "rce-monumenten"
    assert out["records"]["type"] == "FeatureCollection"
    calls = []
    def transport2(url: str) -> dict:
        calls.append(url)
        return payload
    nd.fetch_wfs(service_url="https://example/wfs", type_name="test:laag",
                 bbox_rd=nd.UTRECHT_BBOX_RD, cache_name="test-wfs.json",
                 refresh=False, transport=transport2, source_id="rce-monumenten")
    assert calls == []
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_national_data.py -v`
Expected: FAIL — `fetch_wfs` bestaat niet.

- [ ] **Step 3: Implementeer fetch_wfs + de wrappers**

```python
def fetch_wfs(
    *,
    service_url: str,
    type_name: str,
    bbox_rd: tuple[float, float, float, float],
    cache_name: str,
    source_id: str,
    refresh: bool = False,
    transport: Transport | None = None,
) -> dict:
    """WFS 2.0 GetFeature (GeoJSON), begrensd op de Utrecht-bbox (RD)."""
    t = transport or _default_transport
    cache = CACHE / cache_name
    if cache.is_file() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))
    x0, y0, x1, y1 = bbox_rd
    url = (f"{service_url}?service=WFS&version=2.0.0&request=GetFeature"
           f"&typeNames={type_name}&outputFormat=application/json"
           f"&bbox={x0},{y0},{x1},{y1},urn:ogc:def:crs:EPSG::28992")
    fc = t(url)
    payload = {
        "sourceId": source_id,
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": fc,
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def fetch_rce_erfgoed(refresh: bool = False, transport: Transport | None = None) -> dict:
    return fetch_wfs(service_url=RCE_WFS, type_name=RCE_MONUMENTEN_TYPENAME,
                     bbox_rd=UTRECHT_BBOX_RD, cache_name="rce-monumenten.json",
                     source_id="rce-monumenten", refresh=refresh, transport=transport)


def fetch_dino_ondergrond(refresh: bool = False, transport: Transport | None = None) -> dict:
    return fetch_wfs(service_url=DINO_WFS, type_name=DINO_TYPENAME,
                     bbox_rd=UTRECHT_BBOX_RD, cache_name="dino-bro-ondergrond.json",
                     source_id="dino-bro-ondergrond", refresh=refresh, transport=transport)


def fetch_infra(refresh: bool = False, transport: Transport | None = None) -> dict:
    """NWB-wegen + ProRail-spoor als twee WFS-caches onder één aanroep."""
    return {"wegen": fetch_wfs(service_url=NWB_WFS, type_name=NWB_TYPENAME,
                               bbox_rd=UTRECHT_BBOX_RD, cache_name="rws-nwb-wegen.json",
                               source_id="rws-nwb-wegen", refresh=refresh, transport=transport),
            "spoor": fetch_wfs(service_url=PRORAIL_WFS, type_name=PRORAIL_TYPENAME,
                               bbox_rd=UTRECHT_BBOX_RD, cache_name="prorail-spoor.json",
                               source_id="prorail-spoor", refresh=refresh, transport=transport)}
```

met de constants (uit Step 1) bovenin:

```python
RCE_WFS = ""            # gepind in task 5 stap 1, bijv. https://services.rce.geovrijening.nl/geoserver/ows
RCE_MONUMENTEN_TYPENAME = ""   # uit de GetCapabilities-lijst
DINO_WFS = ""
DINO_TYPENAME = ""
NWB_WFS = ""
NWB_TYPENAME = ""
PRORAIL_WFS = ""
PRORAIL_TYPENAME = ""
```

(Deze constants vullen zich in Step 1; het assert-pattern van `fetch_landgebruik` is hier niet nodig omdat `fetch_wfs` direct faalt op een lege URL — vóórdat er iets gecachet wordt.)

- [ ] **Step 4: Run tests + live warmloop**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_national_data.py -v`
Expected: PASS. Daarna live vullen (netwerk): vier keer `fetch_* (refresh=True)` aanroepen via een python -c éénliner en de record-aantallen printen. Als een dienst geen GeoJSON outputFormat ondersteunt (sommige WFS'en alleen GML): zet `outputFormat=json`-variabele — GIS-bestanden converters via `ogr2ogr` (staat op de machine, zie poc/README) als noodpad, noteer het in de commit-message.

- [ ] **Step 5: Commit**

```bash
git add poc/pipeline/national_data.py poc/tests/test_national_data.py poc/tests/fixtures/national/wfs_sample.json poc/data/sources.json
git commit -m "feat(poc): WFS-fetchers RCE/DINO/NWB/ProRail (context-lagen, kalibratie, plan 2, task 5)"
```

---

### Task 6: netcongestie + energietoets-scenario #3

**Files:**
- Modify: `poc/pipeline/national_data.py` (netcongestie-loader)
- Create: `poc/tests/fixtures/national/netcongestie_sample.json`
- Modify: `poc/scenarios/energietoets.json` (3e scenario)
- Modify: `poc/tests/test_uitdagingen.py` (`SET_IDS["energietoets"]` 2 → 3)
- Modify: `poc/scenarios/uitdagingen.json` (energietoets-scenarioRunId bijwerken)
- Test: `poc/tests/test_national_data.py` (uitbreiding)

**Interfaces:**
- Produces: `load_netcongestie(refresh: bool = False) -> dict` — leest de handmatige download-cache `poc/data/cache/national/netcongestie/netcongestie.geojson` (FeatureCollection, RD of WGS84 met crs-veld); gebruikt door de energietoets-set (dataGrounding) en Task 8 (context_map).

- [ ] **Step 1: Download en leg de congestion-data vast**

Netbeheerders publiceren netcapaciteit/-congestie als download (per regio; voor Utrecht: Liander + Enexis):

```bash
mkdir -p poc/data/cache/national/netcongestie
open "https://www.liander.nl/particulieren/over-liander/over-ons/netcongestie"
open "https://www.enexis.nl/over-ons/uitdagingen/netcongestie"
```
Zet de actuele GeoJSON/CSV-export als `poc/data/cache/national/netcongestie/netcongestie.geojson` (bij CSV: converteer met ogr2ogr naar GeoJSON in EPSG:4326 of 28992 en houd het crs-veld aan). Werk `serviceUrl` van `netbeheerder-netcongestie` in `sources.json` bij naar de gebruikte download-URL. Als er géén machine-leesbare export is: maak de laag uit de gepubliceerde kaartlagen van de netbeheerder (veelal ArcGIS FeatureServers — zelfde connector als de provincie) en documenteer de URL. Acceptatie: een FeatureCollection met ≥1 feature in de Utrecht-bbox.

- [ ] **Step 2: Write the failing test**

Fixture `poc/tests/fixtures/national/netcongestie_sample.json`:

```json
{"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
 "features": [{"type": "Feature", "properties": {"netgebied": "Utrecht-Stad", "type": "transformatorruimte-schaarste"}, "geometry": {"type": "Polygon", "coordinates": [[[5.05, 52.05], [5.15, 52.05], [5.15, 52.12], [5.05, 52.12], [5.05, 52.05]]]}}]}
```

Test:

```python
def test_load_netcongestie_leest_cache(tmp_path, monkeypatch):
    cache = tmp_path / "netcongestie" / "netcongestie.geojson"
    cache.parent.mkdir(parents=True)
    cache.write_text((FIXTURES / "netcongestie_sample.json").read_text())
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    out = nd.load_netcongestie()
    assert out["sourceId"] == "netbeheerder-netcongestie"
    assert out["records"]["features"][0]["properties"]["netgebied"] == "Utrecht-Stad"
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_national_data.py -v`
Expected: FAIL — `load_netcongestie` bestaat niet.

- [ ] **Step 3: Implementeer load_netcongestie**

```python
def load_netcongestie(refresh: bool = False, transport: Transport | None = None) -> dict:
    """Netcongestie-cache (handmatige of API-download) als scenario-basis."""
    cache = CACHE / "netcongestie" / "netcongestie.geojson"
    if not cache.is_file() or refresh:
        # De netbeheerder-export is een document-download, geen stabiele API:
        # verversen gebeurt via de gedocumenteerde download-URL in sources.json.
        if refresh and transport is None:
            raise FileNotFoundError(
                "netcongestie-cache ontbreekt; download volgens sources.json")
        if refresh:
            CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(transport("netcongestie"), ensure_ascii=False),
                             encoding="utf-8")
    payload = {
        "sourceId": "netbeheerder-netcongestie",
        "retrieved": datetime.fromtimestamp(
            cache.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
        "records": json.loads(cache.read_text(encoding="utf-8")),
    }
    return payload
```

- [ ] **Step 4: Voeg SC-ET-NETCONGESTIE toe aan poc/scenarios/energietoets.json**

```json
{
  "id": "SC-ET-NETCONGESTIE",
  "name": "Netcongestie zones as spatial blockage (data-grounded)",
  "description": "Excludes the transformer-capacity shortage zones published by the grid operators — a data-grounded hypothetical: no norm, but real data. Measures what data-driven congestion siting would cost versus the legally blind art. 5.10 marker.",
  "objectType": "energy_storage",
  "basis": {
    "type": "hypothetical",
    "rationale": "Art. 5.10/5.11 have no provincial zone layer (the marker is province-wide); grid-capacity zones are not a legal designation, so this scenario stays hypothetical — grounded in operator data instead of an arbitrary parameter.",
    "provenanceNote": "NOT legally grounded: grounded in netbeheerder congestion data (see dataGrounding); the AOI-wide marker (NC-ET-01) is cited.",
    "dataGrounding": {
      "sourceId": "netbeheerder-netcongestie",
      "retrieved": "<datum van de download in stap 1, ISO-vorm>",
      "note": "transformatorruimte-schaarste zones, Liander/Enexis export"
    }
  },
  "mutations": [
    {"ruleId": "FR-ET-01", "action": "set_semantics", "zoneSemantics": "attention"}
  ],
  "proposedBy": "deterministic-scenario-author#poc-v0"
}
```

Let op de mutatie: de AOI-marker demoot naar `attention` — de zone wordt niet door de toets geblokkeerd (Δ0), zodat de data-laag zélf de ruimtelijke differentiatie toont in de contextkaart van Task 8; exclusie van willekeurige polygonen uit de provincie-breed AOI via `drop`/`set_semantics` is niet uitdrukkbaar in de bestaande mutatie-vocabulary — dat is precies de grens van de curation-laag en bewust gedocumenteerd.

- [ ] **Step 5: Test-telling 2 → 3 + sweep her-run**

Werk `SET_IDS["energietoets"]` in `poc/tests/test_uitdagingen.py` aan naar `3` en verwijder de `# plan 2…`-comment. Draai:

```bash
cd /Users/marc/Projecten/ldttoolbox && python3 poc/scenarios/run.py --use-case energietoets
```
Expected: `verdict: pass`, 3 scenario's, `v2-data-grounding` op pass. Werk `scenarioRuns["energietoets"]` in `uitdagingen.json` bij met de nieuwe run-id.

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_uitdagingen.py tests/test_national_data.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add poc/pipeline/national_data.py poc/tests/test_national_data.py poc/tests/fixtures/national/netcongestie_sample.json poc/scenarios/energietoets.json poc/scenarios/uitdagingen.json poc/tests/test_uitdagingen.py poc/data/sources.json poc/data/cache/national/netcongestie
git commit -m "feat(poc): SC-ET-NETCONGESTIE data-gegrond via netbeheerdercongestie (kalibratie, plan 2, task 6)"
```

---

### Task 7: kalibratieloop `poc/data/calibrate.py`

**Files:**
- Create: `poc/data/calibrate.py`
- Test: `poc/tests/test_calibrate.py`

**Interfaces:**
- Consumes: `fetch_omgevingsverordening.py` (repo-root, bestaand), `poc/data/sources.json`, `uitdagingen.json::scenarioRuns`, `national_data`.
- Produces: `python3 poc/data/calibrate.py [--refresh]` → `poc/data/calibration/<datum>-calibratierapport.{md,json}` met per uitdaging: bronnen × rol × lastChecked × wijzigingen × gaps + de vlag "her-kalibreren na PS-besluit 18-11-2026"; exit 0 zolang de zone-drift ≤0,1% is.

- [ ] **Step 1: Write the failing test**

```python
"""Kalibratieloop — offline, op fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))

import calibrate as cal  # noqa: E402


def test_drift_verdict():
    assert cal.drift_verdict(859.463, 859.463) == "pass"
    assert cal.drift_verdict(859.463, 859.549) == "pass"   # 0.01% < 0.1%
    assert cal.drift_verdict(859.463, 860.400) == "drift"  # 0.109% > 0.1%


def test_rapport_bevat_uitdagingen_en_amendementsvlag(tmp_path):
    md = cal.render_markdown({
        "datum": "2026-10-13",
        "amendement": "PS-besluit wijziging Omgevingsverordening verwacht 18-11-2026 — herkalibreren na vaststelling",
        "uitdagingen": [{
            "id": "energietransitie", "titel": "Energietransitie",
            "tracks": [{"track": "energietoets", "drift": "pass",
                        "lastChecked": "2026-10-13", "wijzigingen": 0}],
        }],
    })
    assert "Energietransitie" in md
    assert "18-11-2026" in md
    assert "energietoets" in md
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_calibrate.py -v`
Expected: FAIL — module bestaat niet.

- [ ] **Step 2: Implementeer poc/data/calibrate.py**

```python
"""Kalibratieloop van de Utrecht-PoC (herhaalbaar, ook ná 18-11-2026).

Stappen:
1. CVDR-diff: her-fetch van de Omgevingsverordening (bestaand fetch-script) en
   diff tegen poc/corpus/cvdr704250-tekst-extract.txt.
2. Geo-versheid: per featured run de gebruikte lagen checken via een goedkope
   ArcGIS-count ($returnCountOnly) en lastChecked vullen.
3. Zone-drift: control-zones herreproduceren door een verse sweep per track;
   drift ≤0,1% = pass.
4. Rapport: poc/data/calibration/<datum>-calibratierapport.{md,json}.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
POC = REPO / "poc"
CALIB = POC / "data" / "calibration"
DRIFT_TOLERANCE = 0.001  # 0,1% — gelijk aan de V3-control-tolerantie

AMENDEMENT = ("PS-besluit wijziging Omgevingsverordening verwacht 18-11-2026 — "
              "herkalibreren na vaststelling")


def drift_verdict(baseline_km2: float, control_km2: float) -> str:
    if not baseline_km2:
        return "drift"
    return "pass" if abs(control_km2 - baseline_km2) / baseline_km2 <= DRIFT_TOLERANCE \
        else "drift"


def cvdr_diff() -> dict:
    """Her-fetch de verordening en diff tegen de corpus-snapshot."""
    corpus = POC / "corpus" / "cvdr704250-tekst-extract.txt"
    before = corpus.read_text(encoding="utf-8") if corpus.is_file() else ""
    subprocess.run([sys.executable, str(REPO / "fetch_omgevingsverordening.py")],
                   check=True, capture_output=True)
    after = corpus.read_text(encoding="utf-8")
    return {"gewijzigd": before != after, "for_kenmerk": len(after)}


def arcgis_count(service_url: str, layer_id: int) -> int | None:
    """Goedkope versheid-check: feature-count van de live laag."""
    url = f"{service_url}/{layer_id}/query?f=json&where=1%3D1&returnCountOnly=true"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        return int(data.get("count"))
    except Exception:
        return None


def layer_freshness() -> list[dict]:
    rows = []
    for track, run_id in _scenario_runs().items():
        layers_path = POC / "runs" / run_id / "layers.json"
        if not layers_path.is_file():
            continue
        manifest = json.loads(layers_path.read_text(encoding="utf-8"))
        for zid, laag in manifest.items():
            if laag.get("geometrySource") == "national_source":
                continue  # energietoets-AOI: geen live laag
            n = arcgis_count(laag["serviceUrl"], int(laag.get("layerId", 0)))
            rows.append({"track": track, "zoneId": zid,
                         "count": n, "cached": laag.get("lastChecked")})
    return rows


def zone_drift() -> list[dict]:
    rows = []
    for track, run_id in _scenario_runs().items():
        rep = json.loads((POC / "scenario-runs" / run_id / "scenario-report.json")
                         .read_text(encoding="utf-8"))
        control = rep["control"]["finalAreaKm2"]
        base = rep["control"]["baselineFinalAreaKm2"]
        rows.append({"track": track, "verdict": drift_verdict(base, control),
                     "baselineKm2": base, "controlKm2": control})
    return rows


def _scenario_runs() -> dict[str, str]:
    uj = json.loads((POC / "scenarios" / "uitdagingen.json").read_text(encoding="utf-8"))
    return {k: v for k, v in uj["scenarioRuns"].items() if v}


def render_markdown(rapport: dict) -> str:
    lines = [f"# Kalibratierapport {rapport['datum']}", "",
             f"**Amendement:** {rapport['amendement']}", ""]
    for uit in rapport["uitdagingen"]:
        lines += [f"## {uit['titel']}", ""]
        lines += ["| track | drift | lastChecked | wijzigingen |", "|---|---|---|---|"]
        for t in uit["tracks"]:
            lines.append(f"| {t['track']} | {t['drift']} | {t['lastChecked']} | "
                         f"{t['wijzigingen']} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    datum = date.today().isoformat()
    diff = cvdr_diff()
    fresh = layer_freshness()
    drift = zone_drift()
    uitdagingen = json.loads(
        (POC / "scenarios" / "uitdagingen.json").read_text(encoding="utf-8"))
    rapport = {
        "datum": datum,
        "amendement": AMENDEMENT,
        "cvdr": diff,
        "lagen": fresh,
        "uitdagingen": [
            {"id": u["id"], "titel": u["titel"],
             "tracks": [{"track": d["track"],
                         "drift": d["verdict"],
                         "lastChecked": next((l["cached"] for l in fresh
                                              if l["track"] == d["track"]), "-"),
                         "wijzigingen": sum(1 for l in fresh
                                            if l["track"] == d["track"]
                                            and l["count"] is None)}
                        for d in drift if d["track"] in u["tracks"]]}
            for u in uitdagingen["uitdagingen"]],
    }
    CALIB.mkdir(parents=True, exist_ok=True)
    (CALIB / f"{datum}-calibratierapport.json").write_text(
        json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8")
    (CALIB / f"{datum}-calibratierapport.md").write_text(
        render_markdown(rapport), encoding="utf-8")
    print(f"kalibratie {datum}: {len(drift)} tracks, cvdr gewijzigd={diff['gewijzigd']}")
    return 0 if all(d["verdict"] == "pass" for d in drift) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 3: Run test to verify it passes**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_calibrate.py -v`
Expected: PASS (2 tests).

- [ ] **Step 4: Controleer het fetch-script-contract**

```bash
head -30 /Users/marc/Projecten/ldttoolbox/fetch_omgevingsverordening.py | grep -n "corpus\|extract\|write"
```
Expected: bevestigt dat het script naar `poc/corpus/cvdr704250-tekst-extract.txt` schrijft. Als het script elders schrijft, pas `cvdr_diff()` aan op het werkelijke output-pad.

- [ ] **Step 5: Commit**

```bash
git add poc/data/calibrate.py poc/tests/test_calibrate.py
git commit -m "feat(poc): kalibratieloop — CVDR-diff, geo-versheid, zone-drift, rapport (kalibratie, plan 2, task 7)"
```

---

### Task 8: context_map.py — contextpagina's per uitdaging + dashboard-links

**Files:**
- Create: `poc/pipeline/context_map.py`
- Modify: `deep-agents/poc_demos.py` (Utrecht-entry: `simulationPages`)
- Test: `poc/tests/test_context_map.py`

**Interfaces:**
- Consumes: `national_data.fetch_cbs_dataset / fetch_wfs / load_netcongestie`; control-zones van de featured runs (`scenario-runs/<id>/scenarios/CONTROL.geojson`).
- Produces: `python3 poc/pipeline/context_map.py` schrijft `deep-agents/runs/utrecht-context-<uitdaging-id>.html` (zelfstandige Leaflet-pagina: control-zone + contextlagen met uitschakel-toggle, expliciet gelabeld "context — geen juridische zone"); `/api/scenarios` en prompts blijven ongewijzigd.

- [ ] **Step 1: Write the failing test**

```python
"""Context-map generator — offline, op fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import context_map as cm  # noqa: E402


def test_context_layers_voor_uitdaging(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    # netcongestie-fixture op de verwachte plek (nd.CACHE = tmp_path)
    nc = tmp_path / "netcongestie" / "netcongestie.geojson"
    nc.parent.mkdir(parents=True)
    nc.write_text('{"type": "FeatureCollection", "features": []}')
    layers = cm.context_layers("energietransitie")
    names = [l["name"] for l in layers]
    assert "Netcongestie (context)" in names
    assert all(l["legal"] is False for l in layers)


def test_html_legt_toggle_en_label_vast(tmp_path):
    html = cm.render_html("Energietransitie", control_geojson='{"type":"FeatureCollection","features":[]}',
                          layers=[{"name": "Netcongestie (context)", "geojson": '{"type":"FeatureCollection","features":[]}', "color": "#c0392b", "legal": False}])
    assert "context" in html.lower()
    assert "geen juridische zone" in html
    assert "overlay" in html.lower() or "toggled" in html.lower()
    (tmp_path / "x.html").write_text(html)  # schrijft zonder fout
```

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_context_map.py -v`
Expected: FAIL — module bestaat niet.

- [ ] **Step 2: Implementeer poc/pipeline/context_map.py**

```python
"""Contextpagina's per uitdaging — zelfstandige Leaflet-pagina's.

De pagina's tonen de control-zone van de featured run samen met
contextlagen (CBS/netbeheerder/RCE/DINO/RWS). Elke contextlaag draagt in
de legenda 'context — geen juridische zone'. De pagina's zijn besluit-
ondersteuning, nooit een juridisch advies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline import national_data as nd

REPO = Path(__file__).resolve().parents[2]
CONTEXT_DIR = nd.CACHE  # poc/data/cache/national
OUT_DIR = REPO / "deep-agents" / "runs"

UITDAGINGEN = json.loads(
    (REPO / "poc" / "scenarios" / "uitdagingen.json").read_text(encoding="utf-8"))


def context_layers(uitdaging_id: str) -> list[dict[str, Any]]:
    """Contextlagen die bij een uitdaging horen (cache-waarnemend)."""
    layers: list[dict[str, Any]] = []
    if uitdaging_id == "energietransitie":
        try:
            nc = nd.load_netcongestie()
            layers.append({"name": "Netcongestie (context)",
                           "geojson": json.dumps(nc["records"], ensure_ascii=False),
                           "color": "#c0392b", "legal": False})
        except FileNotFoundError:
            pass
    grid = CONTEXT_DIR / "cbs-grid-kerncijfers-100m.json"
    if grid.is_file():
        layers.append({"name": "CBS 100m-kerncijfers (context)",
                       "geojson": "",  # puntwolk: losse generator in stap 4
                       "color": "#2980b9", "legal": False,
                       "cells": json.loads(grid.read_text(encoding="utf-8"))["records"]})
    return layers


_LEAFLET = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Utrecht context — {titel}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>body{{margin:0}}#map{{height:100vh}}.legend{{background:#fff;padding:8px;font:12px sans-serif}}
</style></head><body><div id="map"></div><div class="legend">
<b>{titel}</b><br>{legend}</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map = L.map('map').setView([52.08, 5.12], 9);
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{attribution: '© OpenStreetMap'}}).addTo(map);
{layers_js}
</script></body></html>"""


def render_html(titel: str, control_geojson: str, layers: list[dict[str, Any]]) -> str:
    parts = [f'var control = {control_geojson};',
             'L.geoJSON(control, {style: {color: "#145a32", weight: 2, fillOpacity: 0.05}})'
             '.addTo(map).bindPopup("Control — juridische zone (Omgevingsverordening)");']
    legend = ["control-zone (juridisch)"]
    for l in layers:
        if not l.get("geojson"):
            continue
        parts.append(
            f'var overlay = L.geoJSON({l["geojson"]}, {{style: {{color: "{l["color"]}", '
            f'dashArray: "5 5", fillOpacity: 0.15}}}});'
            f'overlay.addTo(map).bindPopup("context — geen juridische zone");')
        legend.append(f'{l["name"]} — context, geen juridische zone')
    return _LEAFLET.format(titel=titel, layers_js="\n".join(parts),
                           legend="<br>".join(legend))


def main() -> int:
    scenario_runs = REPO / "poc" / "scenario-runs"
    for uit in UITDAGINGEN["uitdagingen"]:
        run_id = UITDAGINGEN["scenarioRuns"].get(uit["tracks"][0])
        control_path = (scenario_runs / (run_id or "") / "scenarios" / "CONTROL.geojson")
        control = control_path.read_text(encoding="utf-8") if control_path.is_file() \
            else '{"type": "FeatureCollection", "features": []}'
        html = render_html(uit["titel"], control, context_layers(uit["id"]))
        out = OUT_DIR / f"utrecht-context-{uit['id']}.html"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run test to verify it passes**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests/test_context_map.py -v`
Expected: PASS (2 tests).

- [ ] **Step 4: Genereer de pagina's en link ze in het dashboard**

```bash
cd /Users/marc/Projecten/ldttoolbox/poc && python3 pipeline/context_map.py
```
Expected: 5 regels met uitvoerpaden onder `deep-agents/runs/`.

Voeg in `deep-agents/poc_demos.py` aan de Utrecht-POC-entry (in `POC_DEMOS`, het dict met `"id": "utrecht"`) toe — naast bestaande keys zoals `viz`/`highlightRecipes`:

```python
        "simulationPages": [
            {"title": "Context — Energietransitie", "path": "utrecht-context-energietransitie.html"},
            {"title": "Context — Wonen & Werken", "path": "utrecht-context-wonen-werken.html"},
            {"title": "Context — Water & Bodem", "path": "utrecht-context-water-bodem.html"},
            {"title": "Context — Landschap & Infrastructuur", "path": "utrecht-context-landschap-infra.html"},
            {"title": "Context — Landelijk Gebied", "path": "utrecht-context-landelijk-gebied.html"},
        ],
```

(Als de Utrecht-entry al `simulationPages` heeft: voeg de vijf items toe aan de bestaande lijst.)

- [ ] **Step 5: Run wiring-tests + rooktest**

Run: `cd /Users/marc/Projecten/ldttoolbox/deep-agents && python3 -m pytest tests/test_agent_wiring.py tests/test_poc_live.py -q`
Expected: PASS. Open één gegenereerde pagina in de browser en controleer de legenda-regel "context — geen juridische zone".

- [ ] **Step 6: Commit**

```bash
git add poc/pipeline/context_map.py poc/tests/test_context_map.py deep-agents/poc_demos.py deep-agents/runs/utrecht-context-*.html
git commit -m "feat(poc): contextpagina's per uitdaging met netcongestie/CBS-lagen (kalibratie, plan 2, task 8)"
```

---

### Task 9: eerste kalibratie-run, README en afsluiting

**Files:**
- Modify: `poc/README.md` (kalibratiesectie)
- Modify: `docs/superpowers/specs/2026-10-13-utrecht-data-kalibratie-design.md` (vastlegging)

- [ ] **Step 1: Volledige suite**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && python3 -m pytest tests -q`
Expected: alles groen (303+ nieuwe tests).

- [ ] **Step 2: Draai de eerste kalibratie**

```bash
cd /Users/marc/Projecten/ldttoolbox && python3 poc/data/calibrate.py
```
Expected: exit 0, `poc/data/calibration/2026-XX-XX-calibratierapport.{md,json}` met 13 tracks. Een track met drift → exit 1: los op door die baseline opnieuw te draaien (`python3 poc/run.py --use-case <track> --refresh`) en de sweep te herhalen, en vermeld dat in de commit.

- [ ] **Step 3: README-kalibratiesectie**

Voeg aan `poc/README.md` toe (na de sectie "Scenario planning"):

```markdown
## Datakalibratie (uitdagingen-profielen + landelijke bronnen)

`python3 poc/data/calibrate.py` — herhaalbare kalibratieloop: CVDR-diff van de
Omgevingsverordening, geo-versheid per gebruikte laag (goedkope count-checks,
cache-first) en zone-drift-gate (≤0,1%, gelijk aan V3) over de 13 featured
scenario-runs. Rapport: `poc/data/calibration/<datum>-calibratierapport.{md,json}`.
**Herhaal dit na het PS-besluit van 18-11-2026 over de verordening-wijziging.**

Landelijke bronnen (CBS 100m-kerncijfers/landgebruik, RCE-monumenten + IAM,
DINO/BRO, NWB/ProRail, netbeheerdercongestie) zijn context- of
scenario-basis-rollen in `poc/data/sources.json` — nooit juridische zones.
Fetchers: `poc/pipeline/national_data.py` (cache-first onder
`poc/data/cache/national/`). Contextpagina's per uitdaging:
`python3 poc/pipeline/context_map.py` → `deep-agents/runs/utrecht-context-*.html`.
De energietoets-scenario SC-ET-NETCONGESTIE is data-gegrond
(`basis.dataGrounding`, V2-gecontroleerd in elke sweep).
```

- [ ] **Step 4: Spec-vastlegging**

Voeg aan `docs/superpowers/specs/2026-10-13-utrecht-data-kalibratie-design.md` toe:

```markdown
## 9. Vastlegging uitvoering (2026-10-13)

- Contextvisualisatie is geïmplementeerd als zelfstandige contextpagina's
  per uitdaging (`poc/pipeline/context_map.py`, gelinkt via
  `simulationPages`) in plaats van embedding in `report.html`/de
  h3-panelen — zelfde inhoud, minder pipeline-impact.
- CBS-dataset-id's, WFS-endpoints (RCE/DINO/NWB/ProRail) en de
  netcongestie-download zijn live gepind tijdens taken 4–6 en staan als
  constante in `poc/pipeline/national_data.py` en in `sources.json`.
- SC-ET-NETCONGESTIE demoot de AOI-marker naar `attention` (Δ0) zodat de
  data-laag zelf de ruimtelijke differentiatie toont; een polygon-uitsluiting
  uit de provinciebrede AOI is niet uitdrukkbaar in de bestaande
  mutatie-vocabulary en is bewust buiten scope gehouden.
```

- [ ] **Step 5: Commit**

```bash
git add poc/README.md docs/superpowers/specs/2026-10-13-utrecht-data-kalibratie-design.md poc/data/calibration
git commit -m "docs(poc): kalibratie eerste run + README + spec-vastlegging (plan 2 afgerond)"
```
