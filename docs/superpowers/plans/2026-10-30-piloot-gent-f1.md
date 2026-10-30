# Piloot Gent F1 — intake → context → GIS → routing → H1 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bouw F1 van `poc-gent/`: de deterministische replay-pijplijn van het referentiepakket `gent-mobiliteit-ondernemer` — situatieschets → intake-gate-vragen → GIS-zonecheck → H1-contextbevestiging (met correcties) → routing met uitleg — vastgelegd als herreelbaar run-artefact met hash-chained events.

**Architecture:** Config-is-data: het levensgebeurtenis-pakket (manifest + beslistabellen + golden set) is JSON in git; `core/` laadt en executeert het deterministisch (LLM-seams komen in latere fasen; replay gebruikt persona-fixtures als S1/S2-stand-in). Uitkomst is een `gent-transactional-run`-artefact in de vorm van `hcs-run.schema.json` plus een `transaction`-blok, met bewijs in `events.jsonl` (sha256-ketting).

**Tech Stack:** Python 3.11+ stdlib-only voor `core/`, `adapters/`, `run.py`, `eval.py`; `jsonschema` uitsluitend voor run-validatie en tests/eval onder `nldt/.venv`; pytest.

**Spec:** [`docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md`](../specs/2026-10-30-piloot-gent-transactionele-assistent-design.md) (§4 pakketten, §5 tien stappen F1-gedeelte, §11 prototype/fasering).

## Global Constraints

- Alle code draait met `python3` (3.11+) zonder netwerk; geen echte persoonsgegevens — alleen persona-fixtures.
- `core/`, `adapters/`, `run.py`, `eval.py` importeren géén externe packages; alleen stdlib. `jsonschema` mag alléén in `core/runs.py::validate` (binnen een try/guard) en in tests/eval, gedraaid onder `../nldt/.venv/bin/python`.
- Tests: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`.
- Deterministische replay: geen muurklok in de canonieke run-inhoud; `runId`/`generatedAt` worden voor vergelijking gestript via `canonical()`.
- Docstrings en teksten in het Nederlands (NFR-06 plain language); productie-identifiers Engels; testnamen mogen Nederlands zijn (repo-conventie, vergelijk `poc-breda/tests/`).
- Bestandsstructuur volgt ontwerp §11 exact: `poc-gent/{packages,adapters,core,fixtures,schemas,tests}/`, `run.py`, `eval.py`, `runs/` (gitignored).
- Commit per taak, conventional commits met scope `poc-gent`, Nederlandse samenvatting.
- Herkomstlabels: `gebruiker` (uit gesprek), `correctie` (H1-correctie), `afgeleid` (GIS-afgeleid); `authentiek` is gereserveerd voor F2 (Magda).

---

### Task 1: Scaffold + referentiepakket + pakketlader

**Files:**
- Create: `poc-gent/conftest.py`, `poc-gent/.gitignore`, `poc-gent/core/__init__.py` (leeg), `poc-gent/adapters/__init__.py` (leeg), `poc-gent/tests/__init__.py` (leeg)
- Create: `poc-gent/packages/gent-mobiliteit-ondernemer/manifest.json`
- Create: `poc-gent/packages/gent-mobiliteit-ondernemer/decision-tables.json`
- Create: `poc-gent/packages/gent-mobiliteit-ondernemer/golden/scenarios.jsonl`
- Create: `poc-gent/core/catalog.py`
- Test: `poc-gent/tests/test_catalog.py`

**Interfaces:**
- Consumes: niets (eerste taak).
- Produces: `catalog.PackageError(Exception)`; `catalog.Package` (dataclass, frozen: `manifest: dict`, `tables: dict`, `golden: list`); `catalog.load_package(poc_root: Path, package_id: str) -> Package`. Alle latere taken laden pakketten hierdoor. De manifestvorm (`contextSchema.slots` met `type/required/authenticSource/vraag`, `gisChecks` met `id/layer/input/output`, `services`, `texts`, `decisionTables`, `golden`) is dé contractvorm voor taken 3–7.

- [ ] **Step 1: Scaffold directories en paden**

```bash
cd /Users/marc/Projecten/ldttoolbox
mkdir -p poc-gent/{core,adapters,fixtures,schemas,tests,packages/gent-mobiliteit-ondernemer/golden}
touch poc-gent/core/__init__.py poc-gent/adapters/__init__.py poc-gent/tests/__init__.py
```

`poc-gent/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
```

`poc-gent/.gitignore`:

```
runs/
__pycache__/
.pytest_cache/
```

- [ ] **Step 2: Schrijf het referentiepakket (data, definitief voor F1)**

`poc-gent/packages/gent-mobiliteit-ondernemer/manifest.json`:

```json
{
  "packageId": "gent-mobiliteit-ondernemer",
  "version": "0.1.0",
  "status": "concept",
  "lifeEventCode": "GT-MOB-01",
  "title": "GT-MOB-01 — Voertuigtoegang stadcentrum voor ondernemers",
  "texts": {
    "intro": "Ik help je regelen wat je nodig hebt rond voertuigtoegang in Gent, zoals de lage-emissiezone (LEZ) en het autovrije gebied.",
    "scope": "Deze assistent gaat over voertuigtoegang bij werkzaamheden en levensgebeurtenissen in het Gentse stadscentrum.",
    "aiToelichting": "Ik ben een AI-assistent van Stad Gent. Ik stel voor en leg uit; jij beslist en bevestigt.",
    "weigering": "Als ik het niet zeker weet, zeg ik dat eerlijk en verbind ik je door met een medewerker.",
    "escalatie": "Twijfel of een bijzondere situatie? Dan neemt een medewerker van Gentinfo het van me over."
  },
  "contextSchema": {
    "slots": {
      "applicantType": {"type": "enum", "values": ["burger", "ondernemer", "organisatie"], "required": true, "authenticSource": null, "vraag": "Bent u particulier, ondernemer of organisatie?"},
      "address": {"type": "string", "required": true, "authenticSource": null, "vraag": "Op welk adres gaat u aan de slag?"},
      "timing": {"type": "periode", "required": false, "authenticSource": null, "vraag": "Voor welke periode heeft u toegang nodig?"},
      "vehicle": {"type": "kenteken", "required": false, "authenticSource": "magda:kenteken", "vraag": null},
      "activity": {"type": "string", "required": true, "authenticSource": null, "vraag": "Wat gaat u precies doen?"},
      "mandate": {"type": "referentie", "required": false, "authenticSource": "magda:mandate", "vraag": null}
    }
  },
  "gisChecks": [
    {"id": "lez", "layer": "gent-lez", "input": "address", "output": "zoneLez"},
    {"id": "autovrij", "layer": "gent-autovrij", "input": "address", "output": "zoneAutovrij"}
  ],
  "decisionTables": "decision-tables.json",
  "services": {
    "ontheffing-lez": {"type": "inzending", "titel": "Ontheffing LEZ voor zakelijk verkeer", "uitleg": "Vergunning om met een voertuig de lage-emissiezone in te rijden."},
    "ontheffing-autovrij": {"type": "inzending", "titel": "Ontheffing autovrij gebied (laden/lossen)", "uitleg": "Vergunning voor laden en lossen in het autovrije gebied."},
    "info-lez": {"type": "info", "titel": "Informatie over de LEZ in Gent", "uitleg": "Uitleg over wanneer de LEZ geldt en voor wie."}
  },
  "golden": "golden/scenarios.jsonl"
}
```

`poc-gent/packages/gent-mobiliteit-ondernemer/decision-tables.json`:

```json
{
  "id": "R-toegang",
  "version": "2026.10",
  "rules": [
    {"id": "R1", "when": {"zoneLez": "in", "applicantType": "ondernemer"}, "then": {"transactions": ["ontheffing-lez"], "info": ["info-lez"]}, "legalBasis": "Gent LEZ-reglement — ontheffing zakelijk verkeer (illustratief)", "uitleg": "Uw adres ligt in de lage-emissiezone en u bent ondernemer: u hebt een LEZ-ontheffing nodig om met een voertuig het centrum in te rijden."},
    {"id": "R2", "when": {"zoneAutovrij": "in", "applicantType": "ondernemer"}, "then": {"transactions": ["ontheffing-autovrij"]}, "legalBasis": "Gent verkeersplan — autovrij gebied (illustratief)", "uitleg": "Het adres ligt in het autovrije gebied: voor laden en lossen met een voertuig geldt een ontheffing autovrij gebied."},
    {"id": "R3", "when": {"zoneLez": "niet-in", "zoneAutovrij": "niet-in"}, "then": {"transactions": [], "info": ["info-lez"]}, "legalBasis": "—", "uitleg": "Het adres ligt buiten de lage-emissiezone en buiten het autovrije gebied: voor dit adres is geen voertuigtoegangsvergunning nodig."}
  ],
  "unknownPolicy": "escalate"
}
```

`poc-gent/packages/gent-mobiliteit-ondernemer/golden/scenarios.jsonl` (6 regels, één JSON-object per regel):

```jsonl
{"scenarioId": "g1-sanne-korenmarkt-beide-zones", "persona": "sanne", "expect": {"outcome": "paden", "transactions": ["ontheffing-lez", "ontheffing-autovrij"], "info": ["info-lez"]}}
{"scenarioId": "g2-ahmed-sleepstraat-lez", "persona": "ahmed", "expect": {"outcome": "paden", "transactions": ["ontheffing-lez"], "info": ["info-lez"]}}
{"scenarioId": "g3-maria-buiten-zones", "persona": "maria", "expect": {"outcome": "paden", "transactions": [], "info": ["info-lez"]}}
{"scenarioId": "g4-fatima-gate-vraag", "persona": "fatima", "expect": {"outcome": "paden", "transactions": ["ontheffing-lez"], "info": ["info-lez"]}}
{"scenarioId": "g5-jeroen-adrescorrectie", "persona": "jeroen", "expect": {"outcome": "paden", "transactions": ["ontheffing-lez", "ontheffing-autovrij"], "info": ["info-lez"]}}
{"scenarioId": "g6-organisatie-escalatie", "persona": "sanne", "overrideSlots": {"applicantType": "organisatie"}, "expect": {"outcome": "escalatie", "transactions": [], "info": []}}
```

- [ ] **Step 3: Schrijf de falende test**

`poc-gent/tests/test_catalog.py`:

```python
"""Pakketlader: referentiepakket laadt en valideert; fouten geven PackageError."""

import json
from pathlib import Path

import pytest

from core import catalog

POC_ROOT = Path(__file__).resolve().parents[1]


def _schrijf_pkg(tmp_path, manifest, tables):
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "decision-tables.json").write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    geldige_golden = '{"scenarioId": "t1", "persona": "sanne", "expect": {"outcome": "paden", "transactions": [], "info": []}}\n'
    (pkg_dir / "golden" / "scenarios.jsonl").write_text(geldige_golden, encoding="utf-8")


def _basis_manifest():
    return json.loads((POC_ROOT / "packages" / "gent-mobiliteit-ondernemer" / "manifest.json").read_text(encoding="utf-8"))


def _basis_tables():
    return json.loads((POC_ROOT / "packages" / "gent-mobiliteit-ondernemer" / "decision-tables.json").read_text(encoding="utf-8"))


def test_referentiepakket_laadt():
    pkg = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer")
    assert pkg.manifest["lifeEventCode"] == "GT-MOB-01"
    assert len(pkg.tables["rules"]) == 3
    assert len(pkg.golden) == 6


def test_onbekende_dienst_in_regel_faalt(tmp_path):
    manifest = _basis_manifest()
    tables = _basis_tables()
    tables["rules"][0]["then"]["transactions"] = ["bestaat-niet"]
    _schrijf_pkg(tmp_path, manifest, tables)
    with pytest.raises(catalog.PackageError, match="onbekende dienst"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_slot_zonder_vraag_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["contextSchema"]["slots"]["activity"].pop("vraag")
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="vraag"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_kapotte_json_geeft_packageerror(tmp_path):
    manifest = _basis_manifest()
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text("{geen geldige json", encoding="utf-8")
    with pytest.raises(catalog.PackageError, match="ongeldige JSON"):
        catalog.load_package(tmp_path, manifest["packageId"])


@pytest.mark.parametrize("pointer", ["decisionTables", "golden"])
def test_pointer_veld_ontbreekt_faalt(tmp_path, pointer):
    manifest = _basis_manifest()
    del manifest[pointer]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match=pointer):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_kapotte_golden_regel_geeft_packageerror(tmp_path):
    manifest = _basis_manifest()
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "decision-tables.json").write_text(json.dumps(_basis_tables(), ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "golden" / "scenarios.jsonl").write_text('{"scenarioId": "g1"}\n{kapot\n', encoding="utf-8")
    with pytest.raises(catalog.PackageError, match="ongeldige JSON-regel"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_gischeck_input_niet_adres_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["gisChecks"][0]["input"] = "activity"
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="input 'address'"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_regel_zonder_when_faalt(tmp_path):
    manifest = _basis_manifest()
    tables = _basis_tables()
    del tables["rules"][0]["when"]
    _schrijf_pkg(tmp_path, manifest, tables)
    with pytest.raises(catalog.PackageError, match="'when'"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_golden_regel_zonder_expect_faalt(tmp_path):
    manifest = _basis_manifest()
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "decision-tables.json").write_text(json.dumps(_basis_tables(), ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "golden" / "scenarios.jsonl").write_text('{"scenarioId": "g1", "persona": "sanne"}\n', encoding="utf-8")
    with pytest.raises(catalog.PackageError, match="'expect'"):
        catalog.load_package(tmp_path, manifest["packageId"])
```

Let op: `catalog.Path` werkt alleen als catalog.py `from pathlib import Path` heeft — schrijf in de test `from pathlib import Path` en gebruik `Path(__file__)`.

- [ ] **Step 4: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_catalog.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.catalog'` (core/catalog.py bestaat nog niet).

- [ ] **Step 5: Schrijf de minimale implementatie**

`poc-gent/core/catalog.py`:

```python
"""Pakketlader: laadt en valideert een levensgebeurtenis-pakket (manifest +
beslistabellen + golden set). Configuratie is data; de lader dwingt de
contractvorm af (FR-22, ontwerp §4)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class PackageError(Exception):
    """Pakket is onvolledig of houdt zich niet aan het contract."""


@dataclass(frozen=True)
class Package:
    manifest: dict
    tables: dict
    golden: list


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise PackageError(f"bestand ontbreekt: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise PackageError(f"ongeldige JSON in {path}: {err}") from err


def _validate(manifest: dict, tables: dict) -> None:
    for key in ("packageId", "version", "status", "lifeEventCode"):
        if not manifest.get(key):
            raise PackageError(f"manifest: verplicht veld '{key}' ontbreekt")
    for key in ("intro", "scope", "aiToelichting", "weigering", "escalatie"):
        if key not in manifest.get("texts", {}):
            raise PackageError(f"manifest.texts: '{key}' ontbreekt")
    slots = manifest.get("contextSchema", {}).get("slots", {})
    if not slots:
        raise PackageError("manifest.contextSchema.slots is leeg")
    for slot, spec in slots.items():
        if "type" not in spec or "required" not in spec:
            raise PackageError(f"slot '{slot}' mist type/required")
        if spec.get("authenticSource") is None and "vraag" not in spec:
            raise PackageError(f"slot '{slot}' mist vraag-tekst")
    outputs = set()
    for check in manifest.get("gisChecks", []):
        for field_name in ("id", "layer", "input", "output"):
            if field_name not in check:
                raise PackageError(f"gisCheck mist veld '{field_name}': {check}")
        if check["input"] != "address":
            raise PackageError(f"gisCheck '{check['id']}': F1 ondersteunt alleen input 'address' (gekregen: '{check['input']}')")
        if check["input"] not in slots:
            raise PackageError(f"gisCheck '{check['id']}': onbekende input-slot '{check['input']}'")
        outputs.add(check["output"])
    services = manifest.get("services", {})
    if not services:
        raise PackageError("manifest.services is leeg")
    rules = tables.get("rules", [])
    if not rules:
        raise PackageError("beslistabellen: 'rules' is leeg")
    for rule in rules:
        for field_name in ("id", "when", "then", "uitleg", "legalBasis"):
            if not rule.get(field_name):
                raise PackageError(f"regel mist veld '{field_name}' of is leeg: {rule.get('id', '?')}")
    for rule in rules:
        for sv in rule.get("then", {}).get("transactions", []) + rule.get("then", {}).get("info", []):
            if sv not in services:
                raise PackageError(f"regel '{rule.get('id')}': onbekende dienst '{sv}'")
        for key in rule.get("when", {}):
            if key not in slots and key not in outputs:
                raise PackageError(f"regel '{rule.get('id')}': onbekende when-sleutel '{key}'")


def load_package(poc_root: Path, package_id: str) -> Package:
    pkg_dir = poc_root / "packages" / package_id
    manifest = _read_json(pkg_dir / "manifest.json")
    for pointer in ("decisionTables", "golden"):
        if not manifest.get(pointer):
            raise PackageError(f"manifest: verplicht veld '{pointer}' ontbreekt")
    tables = _read_json(pkg_dir / manifest["decisionTables"])
    golden_path = pkg_dir / manifest["golden"]
    if not golden_path.is_file():
        raise PackageError(f"golden-set ontbreekt: {golden_path}")
    golden = []
    for regel in [r for r in golden_path.read_text(encoding="utf-8").splitlines() if r.strip()]:
        try:
            golden.append(json.loads(regel))
        except json.JSONDecodeError as err:
            raise PackageError(f"ongeldige JSON-regel in {golden_path}: {err}") from err
    for rij in golden:
        for field_name in ("scenarioId", "persona", "expect"):
            if field_name not in rij:
                raise PackageError(f"golden-regel mist veld '{field_name}': {rij}")
        for field_name in ("outcome", "transactions", "info"):
            if field_name not in rij["expect"]:
                raise PackageError(f"golden-verwachting mist veld '{field_name}': {rij.get('scenarioId', '?')}")
    _validate(manifest, tables)
    return Package(manifest=manifest, tables=tables, golden=golden)
```

`poc-gent/core/catalog.py` zoals hierboven — geen verdere aanpassingen nodig.

- [ ] **Step 6: Draai de tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_catalog.py -q`
Expected: `7 passed`

- [ ] **Step 7: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): scaffold + referentiepakket + pakketlader"
```

---

### Task 2: GIS-zonecheck-adapter met LEZ/autovrij-fixtures

**Files:**
- Create: `poc-gent/fixtures/gis-zones.geojson`
- Create: `poc-gent/fixtures/addresses.json`
- Create: `poc-gent/adapters/gis_zones.py`
- Test: `poc-gent/tests/test_gis_zones.py`

**Interfaces:**
- Consumes: fixture-bestanden onder `poc-gent/fixtures/`.
- Produces: `gis_zones.AddressError(Exception)`; `gis_zones.load_zones(poc_root: Path) -> dict[str, list[list[tuple[float, float]]]]`; `gis_zones.lookup_address(poc_root: Path, address: str) -> tuple[float, float]` (lon, lat; raiset `AddressError`); `gis_zones.point_in_ring(lon: float, lat: float, ring) -> bool`; `gis_zones.zone_result(zones: dict, layer: str, lon: float, lat: float) -> str` (`"in"` of `"niet-in"`).

- [ ] **Step 1: Schrijf de fixtures**

`poc-gent/fixtures/gis-zones.geojson` (rechthoekige polygonen, bewust ruim zodat testuitslagen ondubbelzinnig zijn; productie vervangt dit door de interne GIS-diensten van Stad Gent, FR-23):

```json
{
  "type": "FeatureCollection",
  "features": [
    {"type": "Feature", "properties": {"layer": "gent-lez", "versie": "fixture-v1"}, "geometry": {"type": "Polygon", "coordinates": [[[3.690, 51.040], [3.760, 51.040], [3.760, 51.075], [3.690, 51.075], [3.690, 51.040]]]}},
    {"type": "Feature", "properties": {"layer": "gent-autovrij", "versie": "fixture-v1"}, "geometry": {"type": "Polygon", "coordinates": [[[3.718, 51.051], [3.730, 51.051], [3.730, 51.057], [3.718, 51.057], [3.718, 51.051]]]}}
  ]
}
```

`poc-gent/fixtures/addresses.json`:

```json
{
  "Korenmarkt 1, Gent": [3.7248, 51.0543],
  "Sleepstraat 1, Gent": [3.7410, 51.0565],
  "Sint-Pietersplein 1, Gent": [3.7108, 51.0379],
  "Veldstraat 1, Gent": [3.7240, 51.0530]
}
```

- [ ] **Step 2: Schrijf de falende test**

`poc-gent/tests/test_gis_zones.py`:

```python
"""GIS-zonecheck: adres → punt → in/niet-in per zone-laag (FR-23)."""

from pathlib import Path

import pytest

from adapters import gis_zones

POC_ROOT = Path(__file__).resolve().parents[1]


def _zones():
    return gis_zones.load_zones(POC_ROOT)


def test_korenmarkt_in_beide_zones():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Korenmarkt 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "in"


def test_sleepstraat_allen_in_lez():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Sleepstraat 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "niet-in"


def test_sintpietersplein_buiten_beide_zones():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Sint-Pietersplein 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "niet-in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "niet-in"


def test_onbekend_adres_faalt_duidelijk():
    with pytest.raises(gis_zones.AddressError):
        gis_zones.lookup_address(POC_ROOT, "Bestaatniet 1, Gent")
```

- [ ] **Step 3: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_gis_zones.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'adapters.gis_zones'`.

- [ ] **Step 4: Schrijf de implementatie**

`poc-gent/adapters/gis_zones.py`:

```python
"""GIS-zonecheck (F1): adres-fixtures + punt-in-polygoon, stdlib-only.

Productie vervangt de fixtures door de interne GIS-diensten van Stad Gent
(FR-23); de adapter-interface blijft gelijk."""

from __future__ import annotations

import json
from pathlib import Path


class AddressError(Exception):
    """Adres staat niet in de fixture; productie: geocoding-service."""


def load_zones(poc_root: Path) -> dict:
    fc = json.loads((poc_root / "fixtures" / "gis-zones.geojson").read_text(encoding="utf-8"))
    zones: dict = {}
    for feat in fc["features"]:
        layer = feat["properties"]["layer"]
        ring = [tuple(p) for p in feat["geometry"]["coordinates"][0]]
        zones.setdefault(layer, []).append(ring)
    return zones


def lookup_address(poc_root: Path, address: str) -> tuple[float, float]:
    addrs = json.loads((poc_root / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    if address not in addrs:
        raise AddressError(f"onbekend adres: {address}")
    lon, lat = addrs[address]
    return lon, lat


def point_in_ring(lon: float, lat: float, ring) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = xi + (lat - yi) * (xj - xi) / (yj - yi)
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def zone_result(zones: dict, layer: str, lon: float, lat: float) -> str:
    for ring in zones.get(layer, []):
        if point_in_ring(lon, lat, ring):
            return "in"
    return "niet-in"


def apply_checks(manifest: dict, context: dict, herkomst: dict, poc_root: Path, suffix: str = "") -> None:
    """Voer alle gisChecks uit het manifest uit op hun input-slot (F1: alleen
    'address' — afgedwongen door de pakketlader) en schrijf de zone-uitkomsten
    weg met afgeleid-herkomst. Mutatie van context/herkomst is bewust: de caller
    geeft kopieën mee (context.build / gates.confirm_h1)."""
    zones = load_zones(poc_root)
    for check in manifest.get("gisChecks", []):
        adres = context.get(check["input"])
        if adres is None:
            continue
        lon, lat = lookup_address(poc_root, adres)
        context[check["output"]] = zone_result(zones, check["layer"], lon, lat)
        herkomst[check["output"]] = {"label": "afgeleid", "bron": f"gis:{check['layer']} (fixture v1{suffix})"}
```

- [ ] **Step 5: Draai de tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `11 passed` (7 catalog + 4 gis).

- [ ] **Step 6: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): GIS-zonecheck-adapter met LEZ/autovrij-fixtures"
```

---

### Task 3: Deterministische beslistabellen-engine met trace

**Files:**
- Create: `poc-gent/core/rules.py`
- Test: `poc-gent/tests/test_rules.py`

**Interfaces:**
- Consumes: `tables`-dict uit `catalog.Package.tables` (vorm: task 1, `decision-tables.json`).
- Produces: `rules.evaluate(tables: dict, context: dict) -> dict` met exact deze vorm: `{"outcome": "paden"|"escalatie", "paths": {"transactions": list[str], "info": list[str]}, "trace": [{"ruleId": str, "fired": bool, "reden": str}], "uitleg": [{"regelId": str, "tekst": str, "bron": str}]}`. Geen enkele regel vuurt → `outcome: "escalatie"` met lege paden (ontwerp `unknownPolicy: escalate`, AI-05).

- [ ] **Step 1: Schrijf de falende test**

`poc-gent/tests/test_rules.py`:

```python
"""Beslistabellen-engine: deterministisch, met volledige trace (FR-06/07)."""

from core import rules

ONDERNEMER_LEZ = {"applicantType": "ondernemer", "zoneLez": "in", "zoneAutovrij": "in"}
ONDERNEMER_BUITEN = {"applicantType": "ondernemer", "zoneLez": "niet-in", "zoneAutovrij": "niet-in"}
ORGANISATIE_LEZ = {"applicantType": "organisatie", "zoneLez": "in", "zoneAutovrij": "in"}


def _tables():
    return {
        "id": "R-toegang", "version": "2026.10",
        "rules": [
            {"id": "R1", "when": {"zoneLez": "in", "applicantType": "ondernemer"},
             "then": {"transactions": ["ontheffing-lez"], "info": ["info-lez"]},
             "legalBasis": "LEZ-reglement (illustratief)", "uitleg": "lez-uitleg"},
            {"id": "R2", "when": {"zoneAutovrij": "in", "applicantType": "ondernemer"},
             "then": {"transactions": ["ontheffing-autovrij"]},
             "legalBasis": "verkeersplan (illustratief)", "uitleg": "autovrij-uitleg"},
            {"id": "R3", "when": {"zoneLez": "niet-in", "zoneAutovrij": "niet-in"},
             "then": {"transactions": [], "info": ["info-lez"]},
             "legalBasis": "—", "uitleg": "buiten-zones-uitleg"},
        ],
        "unknownPolicy": "escalate",
    }


def test_r1_en_r2_vuren_voor_ondernemer_in_beide_zones():
    result = rules.evaluate(_tables(), ONDERNEMER_LEZ)
    assert result["outcome"] == "paden"
    assert result["paths"]["transactions"] == ["ontheffing-lez", "ontheffing-autovrij"]
    assert result["paths"]["info"] == ["info-lez"]


def test_r3_vuurt_buiten_beide_zones():
    result = rules.evaluate(_tables(), ONDERNEMER_BUITEN)
    assert result["outcome"] == "paden"
    assert result["paths"]["transactions"] == []


def test_geen_passende_regel_escalatie():
    result = rules.evaluate(_tables(), ORGANISATIE_LEZ)
    assert result["outcome"] == "escalatie"
    assert result["paths"]["transactions"] == []
    assert result["uitleg"] == []


def test_trace_vermeldt_niet_gevuurde_regels_met_reden():
    result = rules.evaluate(_tables(), ORGANISATIE_LEZ)
    trace = {t["ruleId"]: t for t in result["trace"]}
    assert trace["R3"]["fired"] is False
    assert "zoneLez" in trace["R3"]["reden"]


def test_uitleg_draagt_legalbasis():
    result = rules.evaluate(_tables(), ONDERNEMER_LEZ)
    bronnen = {u["regelId"]: u["bron"] for u in result["uitleg"]}
    assert bronnen["R1"] == "LEZ-reglement (illustratief)"
```

- [ ] **Step 2: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_rules.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.rules'`.

- [ ] **Step 3: Schrijf de implementatie**

`poc-gent/core/rules.py`:

```python
"""Deterministische beslistabellen-engine met volledige trace (FR-06/07).

Het model speelt hier geen rol: dezelfde tabellen + context geven altijd
dezelfde uitkomst, en elke vurende regel draagt zijn uitleg en legalBasis.
Geen passende regel → escalatie (ontwerp unknownPolicy: escalate, AI-05)."""

from __future__ import annotations


def _matches(when: dict, context: dict) -> tuple[bool, str]:
    for key, expected in when.items():
        got = context.get(key)
        if got is None:
            return False, f"slot '{key}' ontbreekt"
        if got != expected:
            return False, f"{key}: '{got}' ≠ '{expected}'"
    return True, "alle voorwaarden voldaan"


def evaluate(tables: dict, context: dict) -> dict:
    trace: list[dict] = []
    uitleg: list[dict] = []
    transactions: list[str] = []
    info: list[str] = []
    for rule in tables["rules"]:
        fired, reden = _matches(rule["when"], context)
        trace.append({"ruleId": rule["id"], "fired": fired, "reden": reden})
        if not fired:
            continue
        for sv in rule["then"].get("transactions", []):
            if sv not in transactions:
                transactions.append(sv)
        for sv in rule["then"].get("info", []):
            if sv not in info:
                info.append(sv)
        uitleg.append({"regelId": rule["id"], "tekst": rule["uitleg"], "bron": rule["legalBasis"]})
    outcome = "paden" if any(t["fired"] for t in trace) else "escalatie"
    return {"outcome": outcome, "paths": {"transactions": transactions, "info": info},
            "trace": trace, "uitleg": uitleg}
```

- [ ] **Step 4: Draai de tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `16 passed` (7 + 4 + 5).

- [ ] **Step 5: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): deterministische beslistabellen-engine met trace"
```

---

### Task 4: Contextpipeline — intake-gate, GIS-koppeling, samenvatting met herkomst

**Files:**
- Create: `poc-gent/core/context.py`
- Test: `poc-gent/tests/test_context.py`

**Interfaces:**
- Consumes: `manifest` uit `catalog.Package`; `gis_zones`-functies uit task 2.
- Produces:
  - `context.open_questions(manifest: dict, slots: dict) -> list[dict]` — elk item `{"slot": str, "vraag": str}`; alléén verplichte slots zonder `authenticSource` die nog niet in `slots` staan (once-only-intakegate, FR-04/FR-11-geest).
  - `context.build(manifest: dict, slots: dict, poc_root: Path) -> tuple[dict, dict]` — `(context, herkomst)`; context = slots plus alle `gisChecks`-outputs; herkomst: per key `{"label": "gebruiker"|"afgeleid", "bron": str}`.
  - `context.summary(manifest: dict, context: dict, herkomst: dict) -> dict` — `{"tekst": str, "regels": [{"feit": str, "waarde": ..., "label": str, "bron": str}]}`.

- [ ] **Step 1: Schrijf de falende test**

`poc-gent/tests/test_context.py`:

```python
"""Contextpipeline: gate vraagt alleen ontbrekende niet-authentieke verplichte
slots; build koppelt GIS; summary draagt herkomst (FR-04/05/23)."""

from pathlib import Path

from core import catalog, context

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def test_gate_vraagt_alleen_verplichte_niet_authentieke_slots():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent"}
    vragen = context.open_questions(MANIFEST, slots)
    assert [v["slot"] for v in vragen] == ["activity"]
    assert vragen[0]["vraag"].startswith("Wat gaat u")


def test_gate_vraagt_noit_om_authentiek_slot_ook_niet_verplicht_beschikbaar():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken"}
    assert all(v["slot"] != "vehicle" for v in context.open_questions(MANIFEST, slots))


def test_build_berekent_zones_met_herkomst_afgeleid():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken"}
    ctx, herkomst = context.build(MANIFEST, slots, POC_ROOT)
    assert ctx["zoneLez"] == "in"
    assert ctx["zoneAutovrij"] == "in"
    assert herkomst["zoneLez"] == {"label": "afgeleid", "bron": "gis:gent-lez (fixture v1)"}
    assert herkomst["address"]["label"] == "gebruiker"


def test_summary_noemt_elk_feit_met_herkomst():
    slots = {"applicantType": "ondernemer", "address": "Sleepstraat 1, Gent", "activity": "herstelwerken"}
    ctx, herkomst = context.build(MANIFEST, slots, POC_ROOT)
    som = context.summary(MANIFEST, ctx, herkomst)
    feiten = {r["feit"] for r in som["regels"]}
    assert {"applicantType", "address", "activity", "zoneLez", "zoneAutovrij"} <= feiten
    assert "Sleepstraat" in som["tekst"]
```

- [ ] **Step 2: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_context.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.context'`.

- [ ] **Step 3: Schrijf de implementatie**

`poc-gent/core/context.py`:

```python
"""Contextpipeline: intake-gate, GIS-koppeling en samenvatting met herkomst
(FR-04/05/23). De gate vraagt nooit om wat uit authentieke bronnen kan komen
(once-only); GIS-uitkomsten zijn afgeleid en dragen hun laag als bron."""

from __future__ import annotations

from pathlib import Path

from adapters import gis_zones


def open_questions(manifest: dict, slots: dict) -> list[dict]:
    vragen = []
    for slot, spec in manifest["contextSchema"]["slots"].items():
        if spec["required"] and spec.get("authenticSource") is None and slot not in slots:
            vragen.append({"slot": slot, "vraag": spec["vraag"]})
    return vragen


def build(manifest: dict, slots: dict, poc_root: Path) -> tuple[dict, dict]:
    context = dict(slots)
    herkomst = {slot: {"label": "gebruiker", "bron": "gesprek"} for slot in slots}
    gis_zones.apply_checks(manifest, context, herkomst, poc_root)
    return context, herkomst


def summary(manifest: dict, context: dict, herkomst: dict) -> dict:
    regels = []
    for slot in manifest["contextSchema"]["slots"]:
        if slot in context:
            regels.append({"feit": slot, "waarde": context[slot], **herkomst[slot]})
    for check in manifest.get("gisChecks", []):
        out = check["output"]
        if out in context:
            regels.append({"feit": out, "waarde": context[out], **herkomst[out]})
    tekst = (f"U bent {context.get('applicantType', 'onbekend')} en wilt: "
             f"{context.get('activity', 'onbekend')}. Adres: {context.get('address', 'onbekend')}.")
    return {"tekst": tekst, "regels": regels}
```

- [ ] **Step 4: Draai de tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `20 passed` (16 + 4).

- [ ] **Step 5: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): contextpipeline met intake-gate en herkomst"
```

---

### Task 5: H1-contextbevestiging met correcties

**Files:**
- Create: `poc-gent/core/gates.py`
- Test: `poc-gent/tests/test_gates.py`

**Interfaces:**
- Consumes: `manifest`; `context`/`herkomst` uit `context.build`; `gis_zones`.
- Produces: `gates.confirm_h1(manifest: dict, context: dict, herkomst: dict, corrections: dict, poc_root: Path) -> tuple[dict, dict]` — past correcties toe als **transactie-input** (label `correctie`, DATA-06), herberekent GIS als het adres wijzigt, en weigert correcties op authentieke slots (`ValueError`).

- [ ] **Step 1: Schrijf de falende test**

`poc-gent/tests/test_gates.py`:

```python
"""H1: context bevestigen of corrigeren; correcties zijn transactie-input en
overschrijven nooit een authentieke bron (FR-05, DATA-06, FR-08-groei)."""

from pathlib import Path

import pytest

from core import catalog, context, gates

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def _build(address):
    slots = {"applicantType": "ondernemer", "address": address, "activity": "herstelwerken"}
    return context.build(MANIFEST, slots, POC_ROOT)


def test_adrescorrectie_herberekent_zones_zonder_geconfirmeerde_feiten_te_verliezen():
    ctx, herkomst = _build("Sint-Pietersplein 1, Gent")
    assert ctx["zoneLez"] == "niet-in"
    ctx2, herkomst2 = gates.confirm_h1(MANIFEST, ctx, herkomst, {"address": "Korenmarkt 1, Gent"}, POC_ROOT)
    assert ctx2["address"] == "Korenmarkt 1, Gent"
    assert ctx2["zoneLez"] == "in"
    assert ctx2["zoneAutovrij"] == "in"
    assert herkomst2["address"] == {"label": "correctie", "bron": "gebruiker (H1)"}
    assert ctx2["applicantType"] == "ondernemer"  # eerder bevestigd feit blijft geldig


def test_correctie_op_authentiek_slot_wordt_geweigerd():
    ctx, herkomst = _build("Korenmarkt 1, Gent")
    with pytest.raises(ValueError, match="authentiek"):
        gates.confirm_h1(MANIFEST, ctx, herkomst, {"vehicle": "1-ABC-123"}, POC_ROOT)
```

- [ ] **Step 2: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_gates.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.gates'`.

- [ ] **Step 3: Schrijf de implementatie**

`poc-gent/core/gates.py`:

```python
"""Bevestigingsmoment H1: de gebruiker bevestigt of corrigeert de context
(FR-05). Correcties zijn transactie-input met eigen herkomstlabel en
overschrijven nooit een authentieke bron — daarvoor wordt de gebruiker naar
de bronhouder verwezen (DATA-06)."""

from __future__ import annotations

from pathlib import Path

from adapters import gis_zones


def confirm_h1(manifest: dict, context: dict, herkomst: dict, corrections: dict, poc_root: Path) -> tuple[dict, dict]:
    slots = manifest["contextSchema"]["slots"]
    context = dict(context)
    herkomst = dict(herkomst)
    for slot, waarde in corrections.items():
        if slot not in slots:
            raise KeyError(f"onbekende correctie-slot: {slot}")
        if slots[slot].get("authenticSource") is not None:
            raise ValueError(f"'{slot}' is een authentiek gegeven: correctie loopt via de bronhouder")
        context[slot] = waarde
        herkomst[slot] = {"label": "correctie", "bron": "gebruiker (H1)"}
    if "address" in corrections:
        gis_zones.apply_checks(manifest, context, herkomst, poc_root, suffix=", na correctie")
    return context, herkomst
```

- [ ] **Step 4: Draai de tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `22 passed` (20 + 2).

- [ ] **Step 5: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): H1-contextbevestiging met correcties"
```

---

### Task 6: Events-ledger + run-artefact + schema

**Files:**
- Create: `poc-gent/core/events.py`
- Create: `poc-gent/core/runs.py`
- Create: `poc-gent/schemas/gent-run.schema.json`
- Test: `poc-gent/tests/test_runs.py`

**Interfaces:**
- Consumes: niets uit eerdere taken (onafhankelijke bouwstenen); taak 7 combineert ze.
- Produces:
  - `events.emit(events: list, kind: str, payload: dict) -> dict` — append sha256-gechained event `{"seq", "ts", "kind", "payload", "prevHash", "hash"}`; genesis `prevHash` = 64 nullen; hash-basis omvat `kind`, `payload`, `prev`, `seq` én `ts` (volledig tamper-evident).
  - `events.verify_chain(events: list) -> bool` — herberekent de ketting met lopende prev en controleert `seq == index`.
  - `runs.new_run_id(persona: str) -> str` — vorm `YYYYMMDDTHHMMSSZ-gent-transactional-<persona>`.
  - `runs.canonical(run: dict) -> dict` — kopie zonder `runId`/`generatedAt`.
  - `runs.validate(run: dict, poc_root: Path) -> None` — `jsonschema.validate` tegen `schemas/gent-run.schema.json` (ImportError als jsonschema ontbreekt; caller vangt af).
  - `runs.write_run(poc_root: Path, run: dict, events: list) -> Path` — schrijft `runs/<runId>/run.json` + `events.jsonl`.

- [ ] **Step 1: Schrijf het schema**

`poc-gent/schemas/gent-run.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldttoolbox.example/poc-gent/schemas/gent-run.schema.json",
  "title": "Gent transactional run (F1: intake→context→GIS→H1→routing)",
  "description": "hcs-run-vorm (nldt/schemas/hcs-run.schema.json) plus transaction-blok, ontwerp 2026-10-30 §5.",
  "type": "object",
  "additionalProperties": false,
  "required": ["schemaVersion", "runId", "generatedAt", "recipeId", "processId", "mode", "scenario", "steps", "stopConditions", "kpiSnapshot", "transaction"],
  "properties": {
    "schemaVersion": {"const": "1.0"},
    "runId": {"type": "string"},
    "generatedAt": {"type": "string"},
    "recipeId": {"type": "string"},
    "processId": {"const": "gent-transactional-run"},
    "mode": {"enum": ["replay", "execute"]},
    "scenario": {"type": "string"},
    "steps": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/runStep"}},
    "stopConditions": {"type": "array"},
    "kpiSnapshot": {"type": "array"},
    "transaction": {"$ref": "#/$defs/transaction"}
  },
  "$defs": {
    "runStep": {
      "type": "object",
      "additionalProperties": false,
      "required": ["stepId", "title", "actor", "genAiTestPoint", "dataUsed", "consent", "handover", "kpiEvents", "prov"],
      "properties": {
        "stepId": {"type": "string"},
        "title": {"type": "string"},
        "actor": {"enum": ["agent", "mens", "partij"]},
        "genAiTestPoint": {"enum": ["G1", "G2", "G3", "G4", "G5", "—"]},
        "dataUsed": {"type": "array", "items": {"type": "string"}},
        "consent": {"enum": ["n.v.t.", "gevraagd", "gegeven", "geweigerd"]},
        "handover": {"oneOf": [{"type": "null"}, {"type": "object", "required": ["reason", "to"], "additionalProperties": false, "properties": {"reason": {"type": "string"}, "to": {"type": "string"}}}]},
        "kpiEvents": {"type": "array", "items": {"type": "object", "required": ["kpi", "effect"], "additionalProperties": false, "properties": {"kpi": {"type": "string"}, "effect": {"type": "string"}}}},
        "prov": {"type": "object", "required": ["sources"], "additionalProperties": false, "properties": {"sources": {"type": "array", "items": {"type": "string"}}}}
      }
    },
    "transaction": {
      "type": "object",
      "additionalProperties": false,
      "required": ["context", "routing", "h1"],
      "properties": {
        "context": {"type": "object", "required": ["tekst", "regels"], "additionalProperties": false, "properties": {"tekst": {"type": "string"}, "regels": {"type": "array", "items": {"$ref": "#/$defs/contextRegel"}}}},
        "routing": {
          "type": "object", "required": ["outcome", "paths", "trace", "uitleg"], "additionalProperties": false,
          "properties": {
            "outcome": {"enum": ["paden", "escalatie"]},
            "paths": {"type": "object", "required": ["transactions", "info"], "additionalProperties": false, "properties": {"transactions": {"type": "array", "items": {"type": "string"}}, "info": {"type": "array", "items": {"type": "string"}}}},
            "trace": {"type": "array", "items": {"type": "object", "required": ["ruleId", "fired", "reden"], "additionalProperties": false, "properties": {"ruleId": {"type": "string"}, "fired": {"type": "boolean"}, "reden": {"type": "string"}}}},
            "uitleg": {"type": "array", "items": {"type": "object", "required": ["regelId", "tekst", "bron"], "additionalProperties": false, "properties": {"regelId": {"type": "string"}, "tekst": {"type": "string"}, "bron": {"type": "string"}}}}
          }
        },
        "h1": {"type": "object", "required": ["verdict", "correcties"], "additionalProperties": false, "properties": {"verdict": {"enum": ["gegeven", "geweigerd"]}, "correcties": {"type": "object"}}}
      }
    },
    "contextRegel": {
      "type": "object", "required": ["feit", "waarde", "label", "bron"], "additionalProperties": false,
      "properties": {"feit": {"type": "string"}, "waarde": {}, "label": {"enum": ["gebruiker", "correctie", "afgeleid", "authentiek"]}, "bron": {"type": "string"}}
    }
  }
}
```

- [ ] **Step 2: Schrijf de falende test**

`poc-gent/tests/test_runs.py`:

```python
"""Events-ledger (hash-chain) en run-artefact: schema-validatie + canonical."""

import copy
from pathlib import Path

from core import events, runs

POC_ROOT = Path(__file__).resolve().parents[1]


def test_chain_is_verifieerbaar():
    log: list = []
    events.emit(log, "start", {"v": 1})
    events.emit(log, "gate_request", {"gate": "H1"})
    assert len(log) == 2
    assert events.verify_chain(log) is True


def test_tamper_breekt_de_ketting():
    log: list = []
    events.emit(log, "start", {"v": 1})
    log[0]["payload"]["v"] = 2
    assert events.verify_chain(log) is False


def test_ts_en_prevhash_tamper_breekt_de_keten():
    log: list = []
    events.emit(log, "start", {"v": 1})
    events.emit(log, "routing", {"outcome": "paden"})
    log[0]["ts"] = "1999-01-01T00:00:00+00:00"
    assert events.verify_chain(log) is False
    log2: list = []
    events.emit(log2, "start", {"v": 1})
    events.emit(log2, "routing", {"outcome": "paden"})
    log2[1]["prevHash"] = "0" * 64
    assert events.verify_chain(log2) is False


def _minimale_run():
    return {
        "schemaVersion": "1.0", "runId": runs.new_run_id("test"), "generatedAt": "2026-10-30T00:00:00+00:00",
        "recipeId": "gent-mobiliteit-ondernemer", "processId": "gent-transactional-run", "mode": "replay",
        "scenario": "test",
        "steps": [{"stepId": "routing", "title": "routing", "actor": "agent", "genAiTestPoint": "G2",
                   "dataUsed": [], "consent": "n.v.t.", "handover": None, "kpiEvents": [],
                   "prov": {"sources": ["test"]}}],
        "stopConditions": [], "kpiSnapshot": [],
        "transaction": {
            "context": {"tekst": "test", "regels": [{"feit": "address", "waarde": "Korenmarkt 1, Gent", "label": "gebruiker", "bron": "gesprek"}]},
            "routing": {"outcome": "paden", "paths": {"transactions": [], "info": []}, "trace": [], "uitleg": []},
            "h1": {"verdict": "gegeven", "correcties": {}},
        },
    }


def test_minimale_run_valideert_tegen_schema():
    runs.validate(_minimale_run(), POC_ROOT)


def test_schema_verwerpt_onbekende_herkomstlabel():
    run = _minimale_run()
    run["transaction"]["context"]["regels"][0]["label"] = "verzonnen"
    import jsonschema
    try:
        runs.validate(run, POC_ROOT)
    except jsonschema.ValidationError:
        return
    raise AssertionError("ValidationError werd verwacht")


def test_canonical_stript_runid_en_generatedat():
    run = _minimale_run()
    canon = runs.canonical(run)
    assert "runId" not in canon and "generatedAt" not in canon
    assert canon == runs.canonical(copy.deepcopy(run))
```

- [ ] **Step 3: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_runs.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.events'`.

- [ ] **Step 4: Schrijf de implementatie**

`poc-gent/core/events.py`:

```python
"""Hash-chained events per run (SEC-04-richting): elke gebeurtenis wordt
onmiskenbaar vastgelegd; tamperen breekt de ketting."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

GENESIS = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(kind: str, payload: dict, prev: str, seq: int, ts: str) -> str:
    basis = json.dumps({"kind": kind, "payload": payload, "prev": prev, "seq": seq, "ts": ts},
                       sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def emit(events: list, kind: str, payload: dict) -> dict:
    prev = events[-1]["hash"] if events else GENESIS
    seq = len(events)
    ts = _now()
    event = {"seq": seq, "ts": ts, "kind": kind, "payload": payload,
             "prevHash": prev, "hash": _hash(kind, payload, prev, seq, ts)}
    events.append(event)
    return event


def verify_chain(events: list) -> bool:
    prev = GENESIS
    for index, ev in enumerate(events):
        if ev["seq"] != index:
            return False
        if ev["prevHash"] != prev or ev["hash"] != _hash(ev["kind"], ev["payload"], prev, ev["seq"], ev["ts"]):
            return False
        prev = ev["hash"]
    return True
```

`poc-gent/core/runs.py`:

```python
"""Run-artefact: hcs-run-vorm + transaction-blok, weggeschreven onder runs/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def new_run_id(persona: str) -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-gent-transactional-{persona}"


def canonical(run: dict) -> dict:
    out = json.loads(json.dumps(run))
    out.pop("runId", None)
    out.pop("generatedAt", None)
    return out


def validate(run: dict, poc_root: Path) -> None:
    import jsonschema  # beschikbaar onder nldt/.venv; caller mag ImportError opvangen
    schema = json.loads((poc_root / "schemas" / "gent-run.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(run, schema)


def write_run(poc_root: Path, run: dict, events: list) -> Path:
    run_dir = poc_root / "runs" / run["runId"]
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (run_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return run_dir
```

- [ ] **Step 5: Draai de tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `28 passed` (22 + 6).

- [ ] **Step 6: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): run-artefact + hash-chained events + schema"
```

---

### Task 7: Replay-pipeline + personas

**Files:**
- Create: `poc-gent/fixtures/personas.json`
- Create: `poc-gent/core/pipeline.py`
- Test: `poc-gent/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `catalog`, `context`, `gates`, `rules`, `events`, `runs` (taken 1–6).
- Produces:
  - `pipeline.load_personas(poc_root: Path) -> dict[str, dict]` — persona-records uit `fixtures/personas.json` met velden `id`, `label {"nl": str}`, `edge`, `situatieschets`, `intentSlots` (dict), `antwoorden` (dict), `corrections` (dict).
  - `pipeline.run_replay(poc_root: Path, package_id: str, persona_id: str, override_slots: dict | None = None) -> tuple[dict, list]` — `(run, events)`; run valideert tegen `schemas/gent-run.schema.json`; events zijn hash-chained; bij `outcome == "escalatie"` bevat de run een extra stap `escalatie` met `handover {"reason", "to": "Gentinfo"}` en `genAiTestPoint "G5"`.
  - Onbekend adres laat `gis_zones.AddressError` opwaarts bubbelen (F1-keuze: uitzondering; F2 maakt daar een escalatie-uitkomst van — vastgelegd in het ontwerp).

- [ ] **Step 1: Schrijf de personas-fixture**

`poc-gent/fixtures/personas.json`:

```json
{
  "scenarioKind": "life-event",
  "personas": [
    {"id": "sanne", "label": {"nl": "Sanne — zelfstandig loodgieter, werk aan de Korenmarkt"}, "edge": null,
     "situatieschets": "Ik ben zelfstandig loodgieter en moet volgende week herstelwerken uitvoeren aan een pand aan de Korenmarkt. Ik kom met mijn bestelwagen.",
     "intentSlots": {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken uitvoeren"},
     "antwoorden": {}, "corrections": {}},
    {"id": "ahmed", "label": {"nl": "Ahmed — klusjesman, werk aan de Sleepstraat"}, "edge": null,
     "situatieschets": "Als klusjesman ga ik volgende week een badkamer renoveren aan de Sleepstraat.",
     "intentSlots": {"applicantType": "ondernemer", "address": "Sleepstraat 1, Gent", "activity": "herstelwerken uitvoeren"},
     "antwoorden": {}, "corrections": {}},
    {"id": "maria", "label": {"nl": "Maria — particuliere verhuizing aan het Sint-Pietersplein"}, "edge": null,
     "situatieschets": "Ik verhuis volgende maand en wil weten of ik iets moet regelen voor mijn auto bij het Sint-Pietersplein.",
     "intentSlots": {"applicantType": "burger", "address": "Sint-Pietersplein 1, Gent", "activity": "verhuizen"},
     "antwoorden": {}, "corrections": {}},
    {"id": "fatima", "label": {"nl": "Fatima — onvolledige situatieschets (gate vraagt aanvulling)"}, "edge": "onvolledige-situatieschets",
     "situatieschets": "Ik ben ondernemer en moet iets komen doen aan de Sleepstraat.",
     "intentSlots": {"applicantType": "ondernemer", "address": "Sleepstraat 1, Gent"},
     "antwoorden": {"activity": "herstelwerken uitvoeren"}, "corrections": {}},
    {"id": "jeroen", "label": {"nl": "Jeroen — corrigeert het adres tijdens de contextcheck"}, "edge": "correctie-tijdens-h1",
     "situatieschets": "Ik ben ondernemer en ga herstelwerken uitvoeren aan een pand — ik noemde eerst het verkeerde adres.",
     "intentSlots": {"applicantType": "ondernemer", "address": "Sint-Pietersplein 1, Gent", "activity": "herstelwerken uitvoeren"},
     "antwoorden": {}, "corrections": {"address": "Korenmarkt 1, Gent"}}
  ]
}
```

- [ ] **Step 2: Schrijf de falende test**

`poc-gent/tests/test_pipeline.py`:

```python
"""F1-replay end-to-end: personas → gate → GIS → H1 → routing (FR-03/04/05/06/07/23)."""

from pathlib import Path

from core import events as events_mod
from core import pipeline, runs

POC_ROOT = Path(__file__).resolve().parents[1]


def test_sanne_krijgt_bele_ontheffingen_met_uitleg():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    runs.validate(run, POC_ROOT)
    routing = run["transaction"]["routing"]
    assert routing["outcome"] == "paden"
    assert routing["paths"]["transactions"] == ["ontheffing-lez", "ontheffing-autovrij"]
    assert all(u["bron"] for u in routing["uitleg"])
    assert events_mod.verify_chain(log) is True


def test_fatima_gate_vraagt_activity_en_antwoord_telt_meer():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "fatima")
    vragen = [e for e in log if e["kind"] == "context_vraag"]
    assert [v["payload"]["slot"] for v in vragen] == ["activity"]
    assert run["transaction"]["context"]["regels"]  # activity is gevuld: context compleet
    assert run["transaction"]["routing"]["paths"]["transactions"] == ["ontheffing-lez"]


def test_jeroen_correctie_herberekent_routing():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "jeroen")
    herkomst = {r["feit"]: r for r in run["transaction"]["context"]["regels"]}
    assert herkomst["address"]["label"] == "correctie"
    assert run["transaction"]["routing"]["paths"]["transactions"] == ["ontheffing-lez", "ontheffing-autovrij"]
    verdict = [e for e in log if e["kind"] == "gate_verdict"][0]
    assert verdict["payload"]["correcties"] == {"address": "Korenmarkt 1, Gent"}


def test_escalatie_levert_handoverstap_gentinfo():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne",
                                   override_slots={"applicantType": "organisatie"})
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["routing"]["outcome"] == "escalatie"
    stappen = {s["stepId"] for s in run["steps"]}
    assert "escalatie" in stappen
    esc = [s for s in run["steps"] if s["stepId"] == "escalatie"][0]
    assert esc["handover"]["to"] == "Gentinfo"
    assert any(e["kind"] == "handover" for e in log)


def test_canonieke_replay_is_deterministisch():
    r1, _ = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "ahmed")
    r2, _ = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "ahmed")
    assert runs.canonical(r1) == runs.canonical(r2)
```

- [ ] **Step 3: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_pipeline.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.pipeline'`.

- [ ] **Step 4: Schrijf de implementatie**

`poc-gent/core/pipeline.py`:

```python
"""F1-replay: intake → intake-gate-vragen → GIS → H1 → routing.

Replay-modus: de uitslagen van seam S1 (intentie-extractie) en S2
(vraagformulering) komen deterministisch uit de persona-fixture; de
LLM-poot komt in een latere fase (ontwerp §5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core import catalog, context, gates, rules, runs
from core import events as events_mod


def load_personas(poc_root: Path) -> dict:
    data = json.loads((poc_root / "fixtures" / "personas.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["personas"]}


def run_replay(poc_root: Path, package_id: str, persona_id: str,
               override_slots: dict | None = None) -> tuple[dict, list]:
    pkg = catalog.load_package(poc_root, package_id)
    persona = load_personas(poc_root)[persona_id]
    events: list = []

    slots = dict(persona["intentSlots"])
    if override_slots:
        slots.update(override_slots)
    events_mod.emit(events, "intake_genomen",
                    {"situatieschets": persona["situatieschets"], "slots_uit_intentie": sorted(slots)})

    vragen = context.open_questions(pkg.manifest, slots)
    antwoorden = persona.get("antwoorden", {})
    for v in vragen:
        if v["slot"] in antwoorden:
            slots[v["slot"]] = antwoorden[v["slot"]]
        events_mod.emit(events, "context_vraag", {"slot": v["slot"], "vraag": v["vraag"],
                                                  "bron": "intake-gate (once-only)"})

    ctx, herkomst = context.build(pkg.manifest, slots, poc_root)
    for check in pkg.manifest.get("gisChecks", []):
        events_mod.emit(events, "gis_check",
                        {"id": check["id"], "layer": check["layer"], "resultaat": ctx.get(check["output"])})

    events_mod.emit(events, "gate_request",
                    {"gate": "H1", "voorstel": context.summary(pkg.manifest, ctx, herkomst)})
    corrections = persona.get("corrections", {})
    if corrections:
        ctx, herkomst = gates.confirm_h1(pkg.manifest, ctx, herkomst, corrections, poc_root)
    events_mod.emit(events, "gate_verdict", {"gate": "H1", "verdict": "gegeven", "correcties": corrections})

    routing = rules.evaluate(pkg.tables, ctx)
    events_mod.emit(events, "routing",
                    {"outcome": routing["outcome"], "transactions": routing["paths"]["transactions"]})

    steps = [
        {"stepId": "intake", "title": "Je vertelt wat je gaat doen", "actor": "agent", "genAiTestPoint": "G1",
         "dataUsed": [persona["situatieschets"]], "consent": "n.v.t.", "handover": None, "kpiEvents": [],
         "prov": {"sources": ["persona-fixture (replay stand-in voor seam S1)"]}},
        {"stepId": "context-vragen", "title": "We vragen alleen wat nog niet bekend is", "actor": "agent",
         "genAiTestPoint": "G1", "dataUsed": [v["vraag"] for v in vragen], "consent": "n.v.t.", "handover": None,
         "kpiEvents": [], "prov": {"sources": ["intake-gate: once-only — authentieke slots worden niet gevraagd"]}},
        {"stepId": "gis-zonecheck", "title": "We checken de zone van je adres", "actor": "agent", "genAiTestPoint": "—",
         "dataUsed": [f"{c['output']}={ctx.get(c['output'])}" for c in pkg.manifest.get("gisChecks", [])],
         "consent": "n.v.t.", "handover": None, "kpiEvents": [],
         "prov": {"sources": [f"gis:{c['layer']} (fixture v1)" for c in pkg.manifest.get("gisChecks", [])]}},
        {"stepId": "h1-contextbevestiging", "title": "Je checkt de verzamelde feiten", "actor": "mens",
         "genAiTestPoint": "—",
         "dataUsed": [f"{r['feit']}={r['waarde']}" for r in context.summary(pkg.manifest, ctx, herkomst)["regels"]],
         "consent": "gegeven", "handover": None, "kpiEvents": [],
         "prov": {"sources": ["H1-bevestiging door gebruiker"]}},
        {"stepId": "routing", "title": "We zeggen welke vergunningen je nodig hebt — en waarom", "actor": "agent",
         "genAiTestPoint": "G2", "dataUsed": [u["tekst"] for u in routing["uitleg"]] or ["geen regel van toepassing"],
         "consent": "n.v.t.", "handover": None, "kpiEvents": [{"kpi": "routingnauwkeurigheid", "effect": routing["outcome"]}],
         "prov": {"sources": [u["bron"] for u in routing["uitleg"]] or ["geen"]}},
    ]
    if routing["outcome"] == "escalatie":
        steps.append({"stepId": "escalatie", "title": "We leggen het voor aan een medewerker", "actor": "mens",
                      "genAiTestPoint": "G5", "dataUsed": [], "consent": "gevraagd",
                      "handover": {"reason": "geen regel van toepassing (unknownPolicy: escalate)", "to": "Gentinfo"},
                      "kpiEvents": [], "prov": {"sources": []}})
        events_mod.emit(events, "handover", {"gate": "H5", "naar": "Gentinfo", "reden": "geen regel van toepassing"})

    run = {
        "schemaVersion": "1.0", "runId": runs.new_run_id(persona_id),
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "recipeId": package_id, "processId": "gent-transactional-run", "mode": "replay",
        "scenario": persona_id, "steps": steps, "stopConditions": [], "kpiSnapshot": [],
        "transaction": {"context": context.summary(pkg.manifest, ctx, herkomst),
                        "routing": routing,
                        "h1": {"verdict": "gegeven", "correcties": corrections}},
    }
    return run, events
```

- [ ] **Step 5: Draai de tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `33 passed` (28 + 5).

- [ ] **Step 6: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): replay-pipeline + personas"
```

---

### Task 8: CLI `run.py` + README

**Files:**
- Create: `poc-gent/run.py`
- Create: `poc-gent/README.md`

**Interfaces:**
- Consumes: `pipeline.run_replay`, `pipeline.load_personas`, `runs.validate`, `runs.write_run`.
- Produces: CLI `python3 run.py [--package ID] [--persona ID] [--list-personas]`; schrijft `runs/<runId>/{run.json, events.jsonl}` en drukt een Nederlandse samenvatting (uitkomst, transacties, waarom-uitleg met bron, event-aantal).

- [ ] **Step 1: Schrijf `run.py`**

`poc-gent/run.py`:

```python
#!/usr/bin/env python3
"""poc-gent CLI — F1: deterministische replay per persona.

Voorbeeld: python3 run.py --persona jeroen
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from core import catalog, pipeline, runs  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Gent transactionele assistent — F1 replay")
    ap.add_argument("--package", default="gent-mobiliteit-ondernemer")
    ap.add_argument("--persona", default="sanne")
    ap.add_argument("--list-personas", action="store_true")
    args = ap.parse_args()

    personas = pipeline.load_personas(POC_ROOT)
    if args.list_personas:
        for pid, p in personas.items():
            regel = f"{pid}: {p['label']['nl']}"
            if p.get("edge"):
                regel += f"  [edge: {p['edge']}]"
            print(regel)
        return 0
    if args.persona not in personas:
        print(f"onbekende persona: {args.persona} (probeer --list-personas)", file=sys.stderr)
        return 2

    try:
        run, events = pipeline.run_replay(POC_ROOT, args.package, args.persona)
    except catalog.PackageError as err:
        print(f"pakketfout: {err}", file=sys.stderr)
        return 2
    try:
        runs.validate(run, POC_ROOT)
    except ImportError:
        print("waarschuwing: jsonschema niet beschikbaar — schema-validatie overgeslagen "
              "(draai onder nldt/.venv voor volledige controle)", file=sys.stderr)
    runs.write_run(POC_ROOT, run, events)

    routing = run["transaction"]["routing"]
    print(f"run:        {run['runId']}")
    print(f"uitkomst:   {routing['outcome']}")
    for sv in routing["paths"]["transactions"]:
        print(f"  transactie: {sv}")
    for sv in routing["paths"]["info"]:
        print(f"  informatie: {sv}")
    for u in routing["uitleg"]:
        print(f"  waarom: {u['tekst']}  [{u['bron']}]")
    if routing["outcome"] == "escalatie":
        print("  overname: Gentinfo-medewerker (geen regel van toepassing)")
    print(f"events:     {len(events)} (hash-chained, events.jsonl)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke-test de CLI voor alle persona's**

Run:

```bash
cd poc-gent && for p in sanne ahmed maria fatima jeroen; do python3 run.py --persona $p | head -4; done
```

Expected: vijf keer een `run:`-regel; sanne en jeroen tonen `ontheffing-lez` + `ontheffing-autovrij`, ahmed en fatima alléén `ontheffing-lez`, maria alléén informatie; geen waarschuwing over jsonschema is ok (systeem-python heeft geen jsonschema → waarschuwingsregel is aanvaard).

Verifieer daarna de artefacten onder `nldt/.venv`:

```bash
ls runs/ | tail -5
../nldt/.venv/bin/python -c "
from pathlib import Path
import json
run_dirs = sorted(Path('runs').iterdir())
laatste = run_dirs[-1]
run = json.loads((laatste / 'run.json').read_text(encoding='utf-8'))
assert run['processId'] == 'gent-transactional-run'
events = (laatste / 'events.jsonl').read_text(encoding='utf-8').splitlines()
print('laatste run ok:', run['runId'], '| events:', len(events))
"
```

Expected: `laatste run ok: …-gent-transactional-<persona> | events: N` met N ≥ 6 (volledige persona's: 6; met gate-vraag of escalatie: 7).

- [ ] **Step 3: Schrijf de README**

`poc-gent/README.md`:

```markdown
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
```

- [ ] **Step 4: Draai de volledige tests en commit**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `33 passed`.

```bash
git add poc-gent
git commit -m "feat(poc-gent): CLI + README"
```

---

### Task 9: Golden-set evaluatie `eval.py`

**Files:**
- Create: `poc-gent/eval.py`
- Test: `poc-gent/tests/test_eval.py`

**Interfaces:**
- Consumes: `catalog.Package.golden` (vorm: task 1, `{"scenarioId", "persona", "overrideSlots"?, "expect": {"outcome", "transactions", "info"}}`); `pipeline.run_replay`; `runs.canonical`.
- Produces: `eval.evaluate(package_id: str) -> int` (0 = alles groen; 1 = falende scenario's of non-determinisme), met rapportregel per scenario; CLI `python3 eval.py [--package ID]`.

- [ ] **Step 1: Schrijf de falende test**

`poc-gent/tests/test_eval.py`:

```python
"""Golden-set: routing-uitkomsten per scenario + determinisme (KPI-01/02/04-basis)."""

import eval as eval_mod


def test_golden_set_is_groen():
    assert eval_mod.evaluate("gent-mobiliteit-ondernemer") == 0
```

- [ ] **Step 2: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_eval.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval'` (conftest zet het pad; bestand ontbreekt nog).

- [ ] **Step 3: Schrijf de implementatie**

`poc-gent/eval.py`:

```python
#!/usr/bin/env python3
"""Golden-set evaluatie: routing-uitkomsten per scenario + determinisme
(KPI-01 routingnauwkeurigheid / KPI-02 regelcorrectheid / KPI-04-basis)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from core import catalog, pipeline, runs  # noqa: E402


def evaluate(package_id: str) -> int:
    pkg = catalog.load_package(POC_ROOT, package_id)
    passed = 0
    failed: list[str] = []
    for scenario in pkg.golden:
        run, _log = pipeline.run_replay(POC_ROOT, package_id, scenario["persona"],
                                        scenario.get("overrideSlots"))
        routing = run["transaction"]["routing"]
        expect = scenario["expect"]
        ok = (routing["outcome"] == expect["outcome"]
              and routing["paths"]["transactions"] == expect["transactions"]
              and routing["paths"]["info"] == expect["info"])
        print(f"{'OK  ' if ok else 'FAAL'} {scenario['scenarioId']}: "
              f"{routing['outcome']} {routing['paths']['transactions']}")
        if ok:
            passed += 1
        else:
            failed.append(scenario["scenarioId"])

    first_persona = pkg.golden[0]["persona"]
    r1, _ = pipeline.run_replay(POC_ROOT, package_id, first_persona)
    r2, _ = pipeline.run_replay(POC_ROOT, package_id, first_persona)
    deterministic = runs.canonical(r1) == runs.canonical(r2)
    print(f"determinisme: {'OK' if deterministic else 'FAAL'}")
    print(f"golden: {passed}/{len(pkg.golden)} geslaagd")
    if failed:
        print("gefaald: " + ", ".join(failed))
    return 0 if (not failed and deterministic) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden-set evaluatie poc-gent")
    ap.add_argument("--package", default="gent-mobiliteit-ondernemer")
    return evaluate(ap.parse_args().package)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Draai de tests en de CLI**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `34 passed` (33 + 1).

Run: `python3 eval.py`
Expected: zes `OK`-regels (g1…g6), `determinisme: OK`, `golden: 6/6 geslaagd`, exit-code 0.

- [ ] **Step 5: Commit**

```bash
git add poc-gent
git commit -m "feat(poc-gent): golden-set evaluatie"
```

---

### Task 10: Centrale recipe- en baseline-registratie

**Files:**
- Create: `nldt/recipes/gent-mobiliteit-ondernemer.json`
- Create: `nldt/recipes/baselines/gent-mobiliteit-ondernemer.baseline.json`
- Test: `poc-gent/tests/test_registratie.py`

**Interfaces:**
- Consumes: manifest uit task 1 (`lifeEventCode` GT-MOB-01) — de registratie herbruikt die key.
- Produces: recipe in de centrale catalogus (vorm volgt `nldt/recipes/thk-08-move-home.json`) + baseline met stopcondities/go-no-go (vorm volgt `nldt/recipes/baselines/thk-08-move-home.baseline.json`). Voor latere fasen: EDIC-assetmap-registratie (`assetClass: hcs-life-event`) valt buiten F1.

- [ ] **Step 1: Schrijf de falende test**

`poc-gent/tests/test_registratie.py`:

```python
"""Centrale registratie: recipe + baseline bestaan en sluiten op het pakket aan."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_recipe_en_baseline_geregistreerd_en_consistent():
    recipe = json.loads((REPO / "nldt" / "recipes" / "gent-mobiliteit-ondernemer.json").read_text(encoding="utf-8"))
    baseline = json.loads((REPO / "nldt" / "recipes" / "baselines" / "gent-mobiliteit-ondernemer.baseline.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPO / "poc-gent" / "packages" / "gent-mobiliteit-ondernemer" / "manifest.json").read_text(encoding="utf-8"))
    assert recipe["service"]["lifeEventCode"] == manifest["lifeEventCode"] == "GT-MOB-01"
    assert baseline["recipeId"] == recipe["id"] == manifest["packageId"]
    assert recipe["requiredProcesses"] == ["gent-transactional-run"]
    assert baseline["stopConditions"] and baseline["goNoGo"]
```

- [ ] **Step 2: Draai de test en verifieer dat hij faalt**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_registratie.py -q`
Expected: FAIL — `FileNotFoundError` (recipe bestaat nog niet).

- [ ] **Step 3: Schrijf recipe en baseline**

`nldt/recipes/gent-mobiliteit-ondernemer.json`:

```json
{
  "id": "gent-mobiliteit-ondernemer",
  "title": "GT-MOB-01 — Voertuigtoegang stadcentrum voor ondernemers (Gent)",
  "description": "Transactionele life-event recipe voor de EUROPAI-WP3-piloot Stad Gent: ondernemers die herstelwerken uitvoeren in het centrum krijgen via gesprek + GIS-zonecheck (LEZ, autovrij gebied) de juiste ontheffingen voorgesteld met uitleg en legalBasis. F1: deterministische replay via gent-transactional-run; prefill/inzending volgen in F2/F3. Ontwerp: docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md.",
  "version": "0.1.0",
  "tags": ["hcs", "gent", "transactioneel", "GT-MOB-01", "europai"],
  "requiredProcesses": ["gent-transactional-run"],
  "inputs": {
    "persona": {"type": "string", "description": "persona-id: sanne|ahmed|maria|fatima|jeroen", "required": false},
    "mode": {"type": "string", "description": "replay|execute", "required": false}
  },
  "outputs": {"run": {"type": "json", "description": "Gent transactional run-artefact (intake→routing, F1)"}},
  "steps": [
    {
      "id": "life-event",
      "processId": "gent-transactional-run",
      "title": "F1-run 'voertuigtoegang voor ondernemers'",
      "inputs": {"recipeId": "gent-mobiliteit-ondernemer", "persona": "${recipe.inputs.persona}", "mode": "${recipe.inputs.mode}"},
      "outputs": {"run": "run"},
      "backend": "local"
    }
  ],
  "riskLevel": "medium",
  "service": {
    "dish": "the-key",
    "lifeEventCode": "GT-MOB-01",
    "serviceType": "reactive",
    "blueprintSteps": [1, 2, 3, 4, 5],
    "parties": [
      {"name": "Stad Gent — mobiliteit", "role": "lead — regels en ontheffingen"},
      {"name": "District09", "role": "backoffice-systemen"},
      {"name": "Digital Vlaanderen", "role": "ACM/IDM + Magda (F2)"}
    ],
    "legalBasis": [
      {"basis": "Gent LEZ-reglement / verkeersplan autovrij gebied (illustratief — vaststelling volgt bij pakkegoedkeuring)", "timeLimit": "beslistermijn volgens pakkegoedkeuring"}
    ],
    "humanMeasure": {
      "handover": ["onbekend adres of geen passende regel → Gentinfo (H5)"],
      "exceptions": ["mandaten/bewind", "collectief vervoer"]
    },
    "localVariant": "zone-lagen LEZ/autovrij via interne GIS-diensten Stad Gent",
    "genAiTestPoints": [
      {"point": "G1", "description": "intake vraagt alleen wat niet uit authentieke bronnen komt (once-only)", "testCases": ["fatima: onvolledige situatieschets", "vehicle-slot wordt nooit gevraagd (magda:kenteken)"]},
      {"point": "G2", "description": "routing draagt uitleg + legalBasis per vurende regel", "testCases": ["golden g1 (beide zones)", "golden g6 (escalatie)"]},
      {"point": "G5", "description": "geen passende regel → menselijke overname Gentinfo", "testCases": ["golden g6"]}
    ],
    "kpis": [
      {"kpi": "routingnauwkeurigheid", "kpiType": "outcome", "unit": "%", "outcomeLens": "Z", "baseline": "n.v.t. (prototypefase)", "target": "≥95", "dataSource": "journal/runs", "frequency": "per release", "kviRollup": "EUROPAI D3.1-ambitie efficiëntie/kwaliteit"}
    ]
  },
  "cookbookUri": "http://localhost:8081/recipes/gent-mobiliteit-ondernemer"
}
```

`nldt/recipes/baselines/gent-mobiliteit-ondernemer.baseline.json`:

```json
{
  "recipeId": "gent-mobiliteit-ondernemer",
  "publicOutcome": "Ondernemers regelen voertuigtoegang tot het Gentse centrum in één gesprek: de juiste ontheffingen voorgesteld met uitleg, klaar om te bevestigen en in te dienen.",
  "disappearingStep": "Uitzoeken welke vergunning nodig is (LEZ? autovrij? allebei? welke afdeling?) verdwijnt; alleen de feiten van de situatie blijven over.",
  "kpis": [
    {"kpi": "routingnauwkeurigheid", "kpiType": "outcome", "unit": "%", "outcomeLens": "Z", "baseline": "n.v.t. (prototypefase)", "target": "≥95", "dataSource": "journal/runs", "frequency": "per release", "kviRollup": "EUROPAI D3.1-ambitie efficiëntie/kwaliteit"}
  ],
  "stopConditions": [
    {"condition": "mens-overnames bij intake > 20% over vier weken", "action": "pauzeer intake-seam — escalatie naar function steward"},
    {"condition": "geen unanieme go op de golden set (eval.py rood)", "action": "geen release — terug naar pakket-/regelontwerp"},
    {"condition": "AI Act-risicoklassering wijzigt naar high-risk", "action": "stop en her-toets de mens-agent-grens (H1–H5)"}
  ],
  "goNoGo": [
    "KPI-01 routingnauwkeurigheid ≥ 90% (minimaal aanvaard)",
    "KPI-02 regelcorrectheid 100% op golden cases",
    "KPI-03 brontraceerbaarheid 100% (uitleg zonder bron = faal)",
    "KPI-04 transactiesucces ≥ 18/20 end-to-end scenario's (F3)",
    "elk H-event correct gelogd in journal/events",
    "exit-test geslaagd (config-export + modelsubstitutie, F4)"
  ]
}
```

- [ ] **Step 4: Draai alle tests en verifieer slagen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `35 passed` (34 + 1).

Run ter controle: `python3 eval.py`
Expected: `golden: 6/6 geslaagd`, exit-code 0.

- [ ] **Step 5: Commit**

```bash
git add nldt/recipes/gent-mobiliteit-ondernemer.json nldt/recipes/baselines/gent-mobiliteit-ondernemer.baseline.json poc-gent/tests/test_registratie.py
git commit -m "feat(poc-gent): centrale recipe- en baseline-registratie"
```

---

## Zelfcheck na afronding (executeur)

1. `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` → `38 passed` (35 + 3 contracttests uit de eindreview-fixgolf).
2. `python3 eval.py` → `golden: 6/6 geslaagd`, `determinisme: OK`, exit 0.
3. `python3 run.py --persona jeroen` → run-artefact met beide ontheffingen na adrescorrectie.
4. `git log --oneline -10` → tien `feat(poc-gent)`-commits.
