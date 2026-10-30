# Piloot Gent F2 — H2-authenticatie → Magda-prefill → validatie → H3-concept (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bouw F2 van `poc-gent/`: na de routing volgt — wanneer een voorgestelde transactie dat vereist — de H2-poort (authenticatie via ACM/IDM-mock + expliciete toestemming gegevensgebruik), prefill uit de Magda-mock mét herkomstlabel `authentiek` (once-only, doelbinding), deterministische validatie met correctiepad (geen autonome eindbeslissing), en de H3-conceptbeoordeling; alles vastgelegd in het run-artefact (schema v1.1) en de events-ketting, met golden-scenario's voor weigering en blokkade.

**Architecture:** Voortbouwend op F1/F1.5 (config-is-data, LLM stelt voor / engine beslist / mens bevestigt). Nieuw: twee adapters (`acm_idm_mock`, `magda_mock` in MCP-vorm met doelbinding), twee engines (`core/prefill.py`, `core/validate.py`), H2/H3-gatesemantiek in `core/gates.py`, en de pipeline-fase-2. Persoonlijke gegevens blijven mocks (persona-gekoppelde fixtures); geen netwerk.

**Tech Stack:** Python 3.11+ stdlib-only voor `core/` en `adapters/`; jsonschema alléén voor run-validatie onder `../nldt/.venv`; pytest.

**Spec:** [`docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md`](../specs/2026-10-30-piloot-gent-transactionele-assistent-design.md) §5 (stappen 5–7, H2/H3), §6 (adapters), §11 (fasering F2 = FR-09/10/11/13). F1-plan: `2026-10-30-piloot-gent-f1.md` (inclusief F1.5-addendum).

## Global Constraints

- Alle code draait met `python3` (3.11+) zonder netwerk; geen echte persoonsgegevens — alleen persona-fixtures (mocks).
- `core/`, `adapters/`, `run.py`, `eval.py` importeren géén externe packages; alleen stdlib. `jsonschema` mag alléén in `core/runs.py::validate` (binnen de functie) en in tests/eval, gedraaid onder `../nldt/.venv/bin/python`.
- Tests: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` (na F2: `74 passed`).
- Deterministische replay: geen muurklok in canonieke run-inhoud; `runId`/`generatedAt` gestript via `canonical()`.
- Docstrings en teksten in het Nederlands (plain language); productie-identifiers Engels; testnamen mogen Nederlands zijn (repo-conventie).
- Commit per taak, conventional commits met scope `poc-gent`, Nederlandse samenvatting.
- Herkomstlabels: `gebruiker`, `correctie`, `afgeleid`, en vanaf F2 `authentiek` (uitsluitend uit de Magda-mock; schema-enum stond al klaar).
- Statuswaarden (nieuwe contractvorm): `gereed | gereed-met-waarschuwing | blokkade | geweigerd | escalatie`.

---

### Task 1: Pakketconfig v0.2.0 — authenticSources met doelbinding, formulieren, validaties

**Files:**
- Modify: `poc-gent/packages/gent-mobiliteit-ondernemer/manifest.json`
- Modify: `poc-gent/core/catalog.py`
- Test: `poc-gent/tests/test_catalog.py`

**Interfaces:**
- Consumes: F1-manifest (slots met `authenticSource`, `services`, `decisionTables`, `golden`).
- Produces (contract voor taken 4, 5, 6, 8):
  - Top-level `authenticSources: [{"slot": str, "source": str, "purpose": str}]` — voor élk slot met `authenticSource != null` precies één entry mét niet-lege `purpose`, en omgekeerd.
  - `services[<id>].vereistAuth: bool`; `services[<id>].formulier: [{"veld": str, "bron": str}]` met bronnen van de vorm `slot:<slotnaam>` of `magda:<tool>.<pad>` (pad = punt-gescheiden keys in het Magda-record); `services[<id>].validaties: [{"id", "wanneer": {veld: waarde}, "ernst": "blokkade"|"waarschuwing", "melding"}]`. Inzendingsdienken hebben een niet-lege `formulier`; `vereistAuth`-diensten eveneens.
  - `catalog` valideert: bronverwijzingen in `formulier` verwijzen naar een bestaand slot óf naar een authenticSource `source`; `validaties.wanneer`-sleutels komen voor in het `formulier` van die dienst; `ernst` in het enum.

- [ ] **Step 1: Schrijf de falende tests**

Voeg toe aan `poc-gent/tests/test_catalog.py`:

```python
def test_authenticsources_hebben_doelbinding_en_dekken_slots():
    pkg = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer")
    bronnen = {b["slot"]: b for b in pkg.manifest["authenticSources"]}
    authentieke_slots = {s for s, spec in pkg.manifest["contextSchema"]["slots"].items()
                         if spec.get("authenticSource")}
    assert set(bronnen) == authentieke_slots
    assert all(b["purpose"] for b in bronnen.values())


def test_authenticsource_zonder_purpose_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["authenticSources"].append({"slot": "activity", "source": "magia:bestaat-niet", "purpose": ""})
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="purpose"):
        catalog.load_package(tmp_path, manifest["packageId"])


@pytest.mark.parametrize("referentie", ["bestaat-niet:ergens", "magda:kenteken"])
def test_formulierbron_moet_slot_of_magda_met_pad_zijn(tmp_path, referentie):
    manifest = _basis_manifest()
    manifest["services"]["ontheffing-lez"]["formulier"][0]["bron"] = referentie
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="formulierbron"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_formulierregel_zonder_veld_faalt(tmp_path):
    manifest = _basis_manifest()
    del manifest["services"]["ontheffing-lez"]["formulier"][0]["veld"]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="'veld'"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_dubbele_authenticsource_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["authenticSources"].append(dict(manifest["authenticSources"][0]))
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="meerdere entries"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_validatiesleutel_moet_in_formulier_zitten(tmp_path):
    manifest = _basis_manifest()
    manifest["services"]["ontheffing-lez"]["validaties"][0]["wanneer"] = {"bestaatniet": "Euro 4"}
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="validatie"):
        catalog.load_package(tmp_path, manifest["packageId"])
```

- [ ] **Step 2: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_catalog.py -q`
Expected: FAIL — `test_authenticsources_hebben_doelbinding` faalt op `KeyError: 'authenticSources'`; de drie foutgevallen missen de nieuwe validatie (DID NOT RAISE).

- [ ] **Step 3: Breid het manifest uit (v0.2.0)**

In `poc-gent/packages/gent-mobiliteit-ondernemer/manifest.json`: zet `"version": "0.2.0"`, voeg direct na `gisChecks` toe:

```json
"authenticSources": [
  {"slot": "vehicle", "source": "magda:kenteken", "purpose": "beoordelen van het recht op een LEZ-ontheffing"},
  {"slot": "mandate", "source": "magda:mandate", "purpose": "vaststellen of u namens een ander mag handelen"}
]
```

En vervang het `services`-blok door:

```json
"services": {
  "ontheffing-lez": {
    "type": "inzending", "vereistAuth": true,
    "titel": "Ontheffing LEZ voor zakelijk verkeer",
    "uitleg": "Vergunning om met een voertuig de lage-emissiezone in te rijden.",
    "formulier": [
      {"veld": "kenteken", "bron": "magda:kenteken.kenteken"},
      {"veld": "euroklasse", "bron": "magda:kenteken.euroklasse"},
      {"veld": "brandstof", "bron": "magda:kenteken.brandstof"},
      {"veld": "adres-werkzaamheden", "bron": "slot:address"},
      {"veld": "omschrijving-werkzaamheden", "bron": "slot:activity"},
      {"veld": "aanvrager", "bron": "slot:applicantType"}
    ],
    "validaties": [
      {"id": "V1-euroklasse", "wanneer": {"euroklasse": "Euro 4"}, "ernst": "blokkade",
       "melding": "Uw voertuig (Euro 4) mag de lage-emissiezone niet in. Vervang het voertuig of vraag een menselijke beoordeling via Gentinfo."},
      {"id": "V2-euroklasse", "wanneer": {"euroklasse": "Euro 5"}, "ernst": "waarschuwing",
       "melding": "Controleer of uw diesel Euro 5 een geregistreerd roetfilter heeft; anders geldt de ontheffing niet."}
    ]
  },
  "ontheffing-autovrij": {
    "type": "inzending", "vereistAuth": true,
    "titel": "Ontheffing autovrij gebied (laden/lossen)",
    "uitleg": "Vergunning voor laden en lossen in het autovrije gebied.",
    "formulier": [
      {"veld": "kenteken", "bron": "magda:kenteken.kenteken"},
      {"veld": "adres-werkzaamheden", "bron": "slot:address"},
      {"veld": "omschrijving-werkzaamheden", "bron": "slot:activity"}
    ],
    "validaties": []
  },
  "info-lez": {"type": "info", "vereistAuth": false,
    "titel": "Informatie over de LEZ in Gent",
    "uitleg": "Uitleg over wanneer de LEZ geldt en voor wie.",
    "formulier": [], "validaties": []}
}
```

- [ ] **Step 4: Breid `catalog._validate` uit**

Voeg in `_validate` toe, ná de gisChecks-lus en vóór de regelvalidatie (en gebruik daarna de nieuwe hulpfuncties ook voor de bestaande controles waar aangegeven):

```python
    bronnen = manifest.get("authenticSources", [])
    for bron in bronnen:
        if not bron.get("purpose"):
            raise PackageError(f"authenticSource '{bron.get('slot')}' mist een niet-lege purpose")
        if slots.get(bron.get("slot", ""), {}).get("authenticSource") != bron.get("source"):
            raise PackageError(f"authenticSource '{bron.get('slot')}' wijkt af van het slot-authenticSource")
    gedeclareerd = {b.get("slot") for b in bronnen}
    if len(bronnen) != len(gedeclareerd):
        raise PackageError("authenticSources bevat meerdere entries voor hetzelfde slot")
    authentieke_slots = {s for s, spec in slots.items() if spec.get("authenticSource")}
    if gedeclareerd != authentieke_slots:
        raise PackageError(f"authenticSources dekken de authentieke slots niet: {gedeclareerd} ≠ {authentieke_slots}")
    for service_id, service in services.items():
        if service.get("type") == "inzending":
            if not service.get("formulier"):
                raise PackageError(f"dienst '{service_id}': inzending zonder formulier")
        for regel in service.get("formulier", []):
            if not regel.get("veld"):
                raise PackageError(f"dienst '{service_id}': formulierregel mist een niet-lege 'veld'")
            referentie = regel.get("bron", "")
            if referentie.startswith("slot:"):
                geldig = referentie[5:] in slots
            else:
                tool, _, pad = referentie.partition(".")
                geldig = bool(pad) and tool in {b["source"] for b in bronnen}
            if not geldig:
                raise PackageError(f"dienst '{service_id}': onbekende of onvolledige formulierbron '{referentie}'")
        velden = {regel["veld"] for regel in service.get("formulier", [])}
        for check in service.get("validaties", []):
            for veld in check.get("wanneer", {}):
                if veld not in velden:
                    raise PackageError(f"dienst '{service_id}': validatie '{check.get('id')}' verwijst naar onbekend formulierveld '{veld}'")
            if check.get("ernst") not in ("blokkade", "waarschuwing"):
                raise PackageError(f"dienst '{service_id}': validatie '{check.get('id')}' heeft ongeldige ernst")
```

(Let op: de `services`-variabele bestaat al in `_validate`; plaats dit blok ná de bestaande `services`-controle. De regelvalidatie voor beslistabellen blijft ongewijzigd.)

- [ ] **Step 5: Draai alle tests**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `50 passed` (43 + 7).

- [ ] **Step 6: Commit**

```bash
git add poc-gent/packages/gent-mobiliteit-ondernemer/manifest.json poc-gent/core/catalog.py poc-gent/tests/test_catalog.py
git commit -m "feat(poc-gent): pakketconfig v0.2.0 — doelbinding, formulieren en validaties als contract"
```

---

### Task 2: ACM/IDM-mock + identiteiten-fixture

**Files:**
- Create: `poc-gent/adapters/acm_idm_mock.py`
- Create: `poc-gent/fixtures/identiteiten.json`
- Test: `poc-gent/tests/test_acm_idm.py`

**Interfaces:**
- Consumes: `fixtures/identiteiten.json` (per persona: `pseudoniem`, `naam`, `type`, `mandaten`).
- Produces: `acm_idm_mock.authenticate(poc_root: Path, persona_id: str) -> dict` met exact: `{"pseudoniem": str, "naam": str, "type": str, "mandaten": list[dict]}` (dictvorm `{"rol": str, "voor": str|None}`); onbekende persona → `KeyError`. `acm_idm_mock.geldig_mandaat(identiteit: dict, context: dict) -> bool` — `True` als geen mandaten, of als `context["mandate"]` overeenkomt met een mandaat-`rol`.

- [ ] **Step 1: Schrijf de fixture**

`poc-gent/fixtures/identiteiten.json`:

```json
{
  "personas": {
    "sanne": {"pseudoniem": "rrn-••••481", "naam": "Sanne De Vries", "type": "ondernemer", "mandaten": []},
    "ahmed": {"pseudoniem": "rrn-••••227", "naam": "Ahmed Yilmaz", "type": "ondernemer", "mandaten": []},
    "maria": {"pseudoniem": "rrn-••••035", "naam": "Maria Okafor", "type": "burger", "mandaten": []},
    "fatima": {"pseudoniem": "rrn-••••912", "naam": "Fatima El Amrani", "type": "ondernemer", "mandaten": []},
    "jeroen": {"pseudoniem": "rrn-••••664", "naam": "Jeroen Van Dam", "type": "ondernemer", "mandaten": []},
    "ellen": {"pseudoniem": "rrn-••••158", "naam": "Ellen Peeters", "type": "ondernemer", "mandaten": [{"rol": "bewindvoering", "voor": "moeder"}]},
    "dirk": {"pseudoniem": "rrn-••••773", "naam": "Dirk Maes", "type": "ondernemer", "mandaten": []}
  }
}
```

- [ ] **Step 2: Schrijf de falende test**

`poc-gent/tests/test_acm_idm.py`:

```python
"""ACM/IDM-mock: authenticatie levert identiteit en mandaten (FR-09, INT-01)."""

from pathlib import Path

import pytest

from adapters import acm_idm_mock

POC_ROOT = Path(__file__).resolve().parents[1]


def test_authenticate_levert_identiteit_met_pseudoniem():
    identiteit = acm_idm_mock.authenticate(POC_ROOT, "sanne")
    assert identiteit["pseudoniem"] == "rrn-••••481"
    assert identiteit["type"] == "ondernemer"
    assert identiteit["mandaten"] == []


def test_onbekende_persona_faalt_duidelijk():
    with pytest.raises(KeyError):
        acm_idm_mock.authenticate(POC_ROOT, "bestaatniet")


def test_geldig_mandaat_controleert_rol_tegen_context():
    identiteit = acm_idm_mock.authenticate(POC_ROOT, "ellen")
    assert acm_idm_mock.geldig_mandaat(identiteit, {"mandate": "bewindvoering"}) is True
    assert acm_idm_mock.geldig_mandaat(identiteit, {"mandate": "iets-anders"}) is False
    assert acm_idm_mock.geldig_mandaat(identiteit, {}) is False
```


- [ ] **Step 3: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_acm_idm.py -q`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` op `adapters.acm_idm_mock`.

- [ ] **Step 4: Schrijf de implementatie**

`poc-gent/adapters/acm_idm_mock.py`:

```python
"""ACM/IDM-mock (F2): authenticatie en mandaten via Digital Vlaanderen-
dienstvorm, in replay vormgegeven door een identiteiten-fixture per persona.
Productie vervangt dit door de echte ACM/IDM-integratie (INT-01)."""

from __future__ import annotations

import json
from pathlib import Path


def _laad(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "identiteiten.json").read_text(encoding="utf-8"))["personas"]


def authenticate(poc_root: Path, persona_id: str) -> dict:
    personas = _laad(poc_root)
    if persona_id not in personas:
        raise KeyError(f"onbekende persona voor authenticatie: {persona_id}")
    return personas[persona_id]


def geldig_mandaat(identiteit: dict, context: dict) -> bool:
    rollen = {m["rol"] for m in identiteit.get("mandaten", [])}
    if not rollen:
        return True
    return context.get("mandate") in rollen
```

- [ ] **Step 5: Draai alle tests**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `53 passed` (50 + 3).

- [ ] **Step 6: Commit**

```bash
git add poc-gent/adapters/acm_idm_mock.py poc-gent/fixtures/identiteiten.json poc-gent/tests/test_acm_idm.py
git commit -m "feat(poc-gent): ACM/IDM-mock met identiteiten-fixture"
```

---

### Task 3: Magda-mock in MCP-vorm met doelbinding

**Files:**
- Create: `poc-gent/adapters/magda_mock.py`
- Create: `poc-gent/fixtures/magda.json`
- Test: `poc-gent/tests/test_magda.py`

**Interfaces:**
- Consumes: `fixtures/magda.json` (`{"personas": {<persona>: {"magda:kenteken": {...}, "magda:mandate": {...}}}}`); `manifest["authenticSources"]`.
- Produces:
  - `magda_mock.beschikbare_tools(manifest: dict) -> list[dict]` — `[{"tool": source, "purpose": purpose}]` uit het manifest (MCP-toolregister-vorm).
  - `magda_mock.raadpleeg(manifest: dict, tool: str, purpose: str, poc_root: Path, persona_id: str) -> dict` — het record voor die persona; raiset `MagdaPurposeError` als `purpose` niet exact de in het manifest gedeclareerde doelbinding is (FR-10), en `KeyError` als de persona/geen record.

- [ ] **Step 1: Schrijf de fixture**

`poc-gent/fixtures/magda.json` (alleen records voor persona's die in golden-scenario's een voertuig nodig hebben):

```json
{
  "personas": {
    "sanne": {"magda:kenteken": {"kenteken": "1-ABC-123", "euroklasse": "Euro 6", "brandstof": "diesel"}},
    "ahmed": {"magda:kenteken": {"kenteken": "2-DEF-456", "euroklasse": "Euro 5", "brandstof": "diesel"}},
    "fatima": {"magda:kenteken": {"kenteken": "3-GHI-789", "euroklasse": "Euro 5", "brandstof": "diesel"}},
    "jeroen": {"magda:kenteken": {"kenteken": "4-JKL-012", "euroklasse": "Euro 6", "brandstof": "benzine"}},
    "ellen": {"magda:kenteken": {"kenteken": "5-MNO-345", "euroklasse": "Euro 6", "brandstof": "diesel"}},
    "dirk": {"magda:kenteken": {"kenteken": "6-PQR-678", "euroklasse": "Euro 4", "brandstof": "diesel"}}
  }
}
```

- [ ] **Step 2: Schrijf de falende test**

`poc-gent/tests/test_magda.py`:

```python
"""Magda-mock in MCP-vorm: toolregister uit het manifest, raadpleging alléén
onder de gedeclareerde doelbinding (FR-10, once-only INT-02)."""

from pathlib import Path

import pytest

from adapters import magda_mock
from core import catalog

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def test_toolregister_volgt_het_manifest():
    tools = magda_mock.beschikbare_tools(MANIFEST)
    assert {"tool": "magda:kenteken", "purpose": MANIFEST["authenticSources"][0]["purpose"]} in tools


def test_raadpleeg_levert_record_bij_correcte_doelbinding():
    record = magda_mock.raadpleeg(MANIFEST, "magda:kenteken", MANIFEST["authenticSources"][0]["purpose"],
                                  POC_ROOT, "sanne")
    assert record["kenteken"] == "1-ABC-123"
    assert record["euroklasse"] == "Euro 6"


def test_raadpleeg_met_verkeerde_doelbinding_wordt_geweigerd():
    with pytest.raises(magda_mock.MagdaPurposeError):
        magda_mock.raadpleeg(MANIFEST, "magda:kenteken", "doel die niet gedeclareerd is", POC_ROOT, "sanne")


def test_raadpleeg_zonder_record_faalt_duidelijk():
    with pytest.raises(KeyError):
        magda_mock.raadpleeg(MANIFEST, "magda:kenteken", MANIFEST["authenticSources"][0]["purpose"],
                             POC_ROOT, "maria")
```

- [ ] **Step 3: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_magda.py -q`
Expected: FAIL — `ImportError` op `adapters.magda_mock`.

- [ ] **Step 4: Schrijf de implementatie**

`poc-gent/adapters/magda_mock.py`:

```python
"""Magda-mock in MCP-vorm (F2): het manifest declareert het toolregister met
doelbinding; raadpleging zonder exact die doelbinding wordt geweigerd (FR-10).
Records zijn persona-gekoppelde fixtures — productie vervangt dit door de
Magda-diensten van Digital Vlaanderen (INT-02)."""

from __future__ import annotations

import json
from pathlib import Path


class MagdaPurposeError(Exception):
    """Raadpleging buiten de gedeclareerde doelbinding."""


def beschikbare_tools(manifest: dict) -> list[dict]:
    return [{"tool": bron["source"], "purpose": bron["purpose"]}
            for bron in manifest.get("authenticSources", [])]


def raadpleeg(manifest: dict, tool: str, purpose: str, poc_root: Path, persona_id: str) -> dict:
    declaratie = {bron["source"]: bron["purpose"] for bron in manifest.get("authenticSources", [])}
    if tool not in declaratie:
        raise KeyError(f"onbekende magda-tool: {tool}")
    if declaratie[tool] != purpose:
        raise MagdaPurposeError(f"doelbinding schiet tekort voor {tool}: '{purpose}' ≠ gedeclareerde doelbinding")
    personas = json.loads((poc_root / "fixtures" / "magda.json").read_text(encoding="utf-8"))["personas"]
    if persona_id not in personas or tool not in personas[persona_id]:
        raise KeyError(f"geen {tool}-record voor persona: {persona_id}")
    return personas[persona_id][tool]
```

- [ ] **Step 5: Draai alle tests**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `57 passed` (53 + 4).

- [ ] **Step 6: Commit**

```bash
git add poc-gent/adapters/magda_mock.py poc-gent/fixtures/magda.json poc-gent/tests/test_magda.py
git commit -m "feat(poc-gent): Magda-mock in MCP-vorm met doelbinding"
```

---

### Task 4: Prefill-engine — authentiek-gelabelde formulieren (once-only)

**Files:**
- Create: `poc-gent/core/prefill.py`
- Test: `poc-gent/tests/test_prefill.py`

**Interfaces:**
- Consumes: `manifest` (services met `formulier`, `authenticSources`); `context`/`herkomst` uit `context.build`/`gates.confirm_h1`; Magda-records: dict `records: {"magda:kenteken": {...}}` (pipeline haalt die op).
- Produces: `prefill.bouw(manifest: dict, service_id: str, context: dict, herkomst: dict, records: dict) -> dict` met exact:
  `{"service": service_id, "velden": [{"veld": str, "waarde": Any|None, "label": "authentiek"|"gebruiker"|"correctie"|"afgeleid", "bron": str}], "ontbrekend": [veld, ...]}`.
  Resolutie: `slot:<x>` → `context[x]` mét het herkomstlabel/bron van `herkomst[x]` (afwezig slot → waarde `None`, label `gebruiker`, bron `gesprek (niet verstrekt)`); `magda:<tool>.<pad>` → geneste lookup in `records[<tool>]` op label `authentiek`, bron `f"{tool} (mock v1)"`; pad-resolutiefout of afwezig record → waarde `None` en het veld komt in `ontbrekend`.

- [ ] **Step 1: Schrijf de falende test**

`poc-gent/tests/test_prefill.py`:

```python
"""Prefill-engine: elk formulierveld draagt zichtbaar herkomstlabel en bron;
authentieke velden komen uit de Magda-mock, gespreksvelden uit de context
(FR-11, once-only)."""

from pathlib import Path

from core import catalog, context, prefill

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest
RECORDS = {"magda:kenteken": {"kenteken": "1-ABC-123", "euroklasse": "Euro 6", "brandstof": "diesel"}}


def _context():
    slots = {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken"}
    return context.build(MANIFEST, slots, POC_ROOT)


def test_authentiek_en_gebruiker_labels_zichtbaar_per_veld():
    ctx, herkomst = _context()
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, RECORDS)
    velden = {v["veld"]: v for v in formulier["velden"]}
    assert velden["kenteken"] == {"veld": "kenteken", "waarde": "1-ABC-123", "label": "authentiek", "bron": "magda:kenteken (mock v1)"}
    assert velden["adres-werkzaamheden"]["waarde"] == "Korenmarkt 1, Gent"
    assert velden["adres-werkzaamheden"]["label"] in ("gebruiker", "correctie", "afgeleid")
    assert formulier["ontbrekend"] == []


def test_afwezig_magda_record_landt_in_ontbrekend():
    ctx, herkomst = _context()
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, {})
    velden = {v["veld"]: v for v in formulier["velden"]}
    assert velden["kenteken"]["waarde"] is None
    assert velden["kenteken"]["label"] == "authentiek"
    assert set(formulier["ontbrekend"]) == {"kenteken", "euroklasse", "brandstof"}


def test_h1_correctie_draagt_door_naar_het_formulier():
    from core import gates
    ctx, herkomst = _context()
    ctx, herkomst = gates.confirm_h1(MANIFEST, ctx, herkomst, {"address": "Veldstraat 1, Gent"}, POC_ROOT)
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, RECORDS)
    velden = {v["veld"]: v for v in formulier["velden"]}
    assert velden["adres-werkzaamheden"]["waarde"] == "Veldstraat 1, Gent"
    assert velden["adres-werkzaamheden"]["label"] == "correctie"


def test_labelset_is_gesloten():
    ctx, herkomst = _context()
    formulier = prefill.bouw(MANIFEST, "ontheffing-lez", ctx, herkomst, RECORDS)
    assert {v["label"] for v in formulier["velden"]} <= {"authentiek", "gebruiker", "correctie", "afgeleid"}
```

- [ ] **Step 2: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_prefill.py -q`
Expected: FAIL — `ImportError` op `core.prefill`.

- [ ] **Step 3: Schrijf de implementatie**

`poc-gent/core/prefill.py`:

```python
"""Prefill-engine (F2): zet het formulier van één dienst klaar met per veld een
zichtbaar herkomstlabel (FR-11). Authentieke velden komen uitsluitend uit de
Magda-records; gespreksvelden uit de bevestigde context. Ontbrekende velden
worden benoemd, nooit verzonnen (AI-05-geest)."""

from __future__ import annotations


def _uit_record(record: dict, pad: str):
    waarde: object = record
    for stap in pad.split("."):
        if not isinstance(waarde, dict) or stap not in waarde:
            return None
        waarde = waarde[stap]
    return waarde


def bouw(manifest: dict, service_id: str, context: dict, herkomst: dict, records: dict) -> dict:
    formulier_regels = manifest["services"][service_id]["formulier"]
    velden: list[dict] = []
    ontbrekend: list[str] = []
    for regel in formulier_regels:
        bron_referentie = regel["bron"]
        if bron_referentie.startswith("slot:"):
            slot = bron_referentie[5:]
            waarde = context.get(slot)
            herkomst_regel = herkomst.get(slot) or {"label": "gebruiker", "bron": "gesprek (niet verstrekt)"}
            veld = {"veld": regel["veld"], "waarde": waarde, **herkomst_regel}
            if waarde is None:
                ontbrekend.append(regel["veld"])
        else:
            tool, _, pad = bron_referentie.partition(".")
            record = records.get(tool)
            waarde = _uit_record(record, pad) if record else None
            veld = {"veld": regel["veld"], "waarde": waarde, "label": "authentiek", "bron": f"{tool} (mock v1)"}
            if waarde is None:
                ontbrekend.append(regel["veld"])
        velden.append(veld)
    return {"service": service_id, "velden": velden, "ontbrekend": ontbrekend}
```

- [ ] **Step 4: Draai alle tests**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `61 passed` (57 + 4).

- [ ] **Step 5: Commit**

```bash
git add poc-gent/core/prefill.py poc-gent/tests/test_prefill.py
git commit -m "feat(poc-gent): prefill-engine met zichtbare herkomstlabels"
```

---

### Task 5: Validatie-engine — geen autonome eindbeslissing

**Files:**
- Create: `poc-gent/core/validate.py`
- Test: `poc-gent/tests/test_validate.py`

**Interfaces:**
- Consumes: `manifest` (`services[].validaties`), prefill-formulier uit `prefill.bouw`.
- Produces: `validate.valideer(manifest: dict, service_id: str, formulier: dict) -> dict` met exact:
  `{"status": "gereed"|"gereed-met-waarschuwing"|"blokkade", "bevindingen": [{"id": str, "ernst": str, "melding": str}]}`.
  Semantiek: eerst een automatische `V0-ontbrekend`-blokkade per veld in `formulier["ontbrekend"]` (id `V0-<veld>`, melding `f"Ontbrekend gegeven: {veld} — vraag het aan bij de bronhouder."`); daarna de geconfigureerde `validaties` waarvan álle `wanneer`-voorwaarden matchen met de formulierwaarden (veld → `waarde`); blokkade domineert waarschuwing. Hergebruik de match-semantiek: importeer `from core.rules import matches` en maak in `core/rules.py` de bestaande `_matches` publiek beschikbaar als `matches = _matches` (alias-regel direct onder de definitie) zonder gedrag te wijzigen.

- [ ] **Step 1: Schrijf de falende test**

`poc-gent/tests/test_validate.py`:

```python
"""Validatie-engine: geconfigureerde voorwaarden en ontbrekende velden worden
gecontroleerd; het systeem beslist niet autonoom maar benoemt blokkades en
waarschuwingen met correctiepad (FR-13)."""

from pathlib import Path

from core import catalog, validate

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def _formulier(euroklasse="Euro 6", ontbrekend=None):
    waarden = {"kenteken": "1-ABC-123", "euroklasse": euroklasse, "brandstof": "diesel",
               "adres-werkzaamheden": "Korenmarkt 1, Gent", "omschrijving-werkzaamheden": "herstelwerken",
               "aanvrager": "ondernemer"}
    velden = [{"veld": v, "waarde": w, "label": "authentiek" if v in ("kenteken", "euroklasse", "brandstof") else "gebruiker",
               "bron": "test"} for v, w in waarden.items()]
    return {"service": "ontheffing-lez", "velden": velden, "ontbrekend": ontbrekend or []}


def test_euro6_is_gereed_zonder_bevindingen():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier())
    assert resultaat == {"status": "gereed", "bevindingen": []}


def test_euro5_geeft_waarschuwing():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier(euroklasse="Euro 5"))
    assert resultaat["status"] == "gereed-met-waarschuwing"
    assert resultaat["bevindingen"][0]["id"] == "V2-euroklasse"


def test_euro4_geeft_blokkade_met_correctiepad():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier(euroklasse="Euro 4"))
    assert resultaat["status"] == "blokkade"
    assert resultaat["bevindingen"][0]["ernst"] == "blokkade"
    assert "Vervang" in resultaat["bevindingen"][0]["melding"]


def test_ontbrekend_gegeven_is_automatische_blokkade():
    resultaat = validate.valideer(MANIFEST, "ontheffing-lez", _formulier(ontbrekend=["kenteken"]))
    bevindingen = {b["id"] for b in resultaat["bevindingen"]}
    assert "V0-kenteken" in bevindingen
    assert resultaat["status"] == "blokkade"
```

- [ ] **Step 2: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_validate.py -q`
Expected: FAIL — `ImportError` op `core.validate`.

- [ ] **Step 3: Schrijf de implementatie**

In `poc-gent/core/rules.py`, direct onder de definitie van `_matches`:

```python
matches = _matches
```

`poc-gent/core/validate.py`:

```python
"""Validatie-engine (F2): beoordeelt het conceptformulier tegen de
geconfigureerde voorwaarden. Blokkades en waarschuwingen krijgen een melding
met correctiepad — een autonome eindbeslissing is er niet (FR-13)."""

from __future__ import annotations

from core.rules import matches


def valideer(manifest: dict, service_id: str, formulier: dict) -> dict:
    waarden = {v["veld"]: v["waarde"] for v in formulier["velden"]}
    bevindingen: list[dict] = []
    for veld in formulier.get("ontbrekend", []):
        bevindingen.append({"id": f"V0-{veld}", "ernst": "blokkade",
                            "melding": f"Ontbrekend gegeven: {veld} — vraag het aan bij de bronhouder."})
    for check in manifest["services"][service_id].get("validaties", []):
        vuurde, _reden = matches(check["wanneer"], waarden)
        if vuurde:
            bevindingen.append({"id": check["id"], "ernst": check["ernst"], "melding": check["melding"]})
    if any(b["ernst"] == "blokkade" for b in bevindingen):
        status = "blokkade"
    elif any(b["ernst"] == "waarschuwing" for b in bevindingen):
        status = "gereed-met-waarschuwing"
    else:
        status = "gereed"
    return {"status": status, "bevindingen": bevindingen}
```

- [ ] **Step 4: Draai alle tests**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `65 passed` (61 + 4).

- [ ] **Step 5: Commit**

```bash
git add poc-gent/core/rules.py poc-gent/core/validate.py poc-gent/tests/test_validate.py
git commit -m "feat(poc-gent): validatie-engine met blokkades en waarschuwingen"
```

---

### Task 6: H2/H3-gatesemantiek

**Files:**
- Modify: `poc-gent/core/gates.py`
- Test: `poc-gent/tests/test_gates.py`

**Interfaces:**
- Consumes: `manifest` (`authenticSources` purposes); `acm_idm_mock`.
- Produces:
  - `gates.h2_uitleg(manifest: dict, service_ids: list[str]) -> dict` — `{"bronnen": [{"tool", "purpose"}], "waarom": str}`: de Magda-bronnen die de gegeven inzendingsdiensten nodig hebben (via hun formulier `magda:`-bronnen), met de gedeclareerde doelbinding, plus een Nederlandse zin waarom authenticatie nodig is (FR-09).
  - `gates.decide_h2(manifest: dict, context: dict, identiteit: dict, service_ids: list[str]) -> dict` — `{"doorgang": bool, "reden": str}`: `doorgang False` als het identiteitsmandaten vereist (`geldig_mandaat False`) — reden verwijst naar menselijke controle; anders `True`.

- [ ] **Step 1: Schrijf de falende tests**

Voeg toe aan `poc-gent/tests/test_gates.py`:

```python
def test_h2_uitleg_noemt_bronnen_en_doelbinding():
    uitleg = gates.h2_uitleg(MANIFEST, ["ontheffing-lez"])
    bronnen = {b["tool"] for b in uitleg["bronnen"]}
    assert bronnen == {"magda:kenteken"}
    assert all(b["purpose"] for b in uitleg["bronnen"])
    assert "authenticatie" in uitleg["waarom"].lower() or "authenticatie" in uitleg["waarom"]


def test_decide_h2_blokkeert_zonder_geldig_mandaat():
    from adapters import acm_idm_mock
    identiteit = acm_idm_mock.authenticate(POC_ROOT, "ellen")
    besluit = gates.decide_h2(MANIFEST, {}, identiteit, ["ontheffing-lez"])
    assert besluit["doorgang"] is False
    assert "mandaat" in besluit["reden"].lower() or "mandaat" in besluit["reden"]


def test_decide_h2_sta_door_zonder_mandaten():
    from adapters import acm_idm_mock
    identiteit = acm_idm_mock.authenticate(POC_ROOT, "sanne")
    assert gates.decide_h2(MANIFEST, {}, identiteit, ["ontheffing-lez"])["doorgang"] is True
```

- [ ] **Step 2: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_gates.py -q`
Expected: FAIL — `AttributeError: module 'core.gates' has no attribute 'h2_uitleg'`.

- [ ] **Step 3: Schrijf de implementatie**

Voeg toe aan `poc-gent/core/gates.py` (met de bestaande import-structuur; voeg bovenaan toe: `from adapters import acm_idm_mock`):

```python
def h2_uitleg(manifest: dict, service_ids: list[str]) -> dict:
    """Leg uit welke authentieke bronnen nodig zijn, waarvoor en waarom (FR-09)."""
    doelen = {bron["source"]: bron["purpose"] for bron in manifest.get("authenticSources", [])}
    benodigd: set[str] = set()
    for service_id in service_ids:
        for regel in manifest["services"][service_id].get("formulier", []):
            referentie = regel["bron"]
            if not referentie.startswith("slot:"):
                benodigd.add(referentie.split(".")[0])
    bronnen = [{"tool": tool, "purpose": doelen[tool]} for tool in sorted(benodigd) if tool in doelen]
    waarom = ("Voor deze aanvraag hebben we een paar gegevens nodig die we niet aan u mogen vragen: "
              "die halen we veilig op bij de officiële bronnen, alléén voor het doel hierboven. "
              "Daarom vragen we u eerst om een korte authenticatie.")
    return {"bronnen": bronnen, "waarom": waarom}


def decide_h2(manifest: dict, context: dict, identiteit: dict, service_ids: list[str]) -> dict:
    """Mandaatcontrole vóór gegevensgebruik: zonder geldig mandaat geen doorgang
    — de menselijke route geldt (AI-05-geest)."""
    if not acm_idm_mock.geldig_mandaat(identiteit, context):
        return {"doorgang": False, "reden": "Mandaat niet geverifieerd: overname door een medewerker (Gentinfo) voor de mandatencontrole."}
    return {"doorgang": True, "reden": "geverifieerd"}
```

- [ ] **Step 4: Draai alle tests**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `68 passed` (65 + 3 nieuwe gates-tests).

- [ ] **Step 5: Commit**

```bash
git add poc-gent/core/gates.py poc-gent/tests/test_gates.py
git commit -m "feat(poc-gent): H2-gatesemantiek — uitleg gegevensgebruik en mandaatcontrole"
```

---

### Task 7: Run-schema v1.1 — auth, prefill, validatie, h3

**Files:**
- Modify: `poc-gent/schemas/gent-run.schema.json`
- Test: `poc-gent/tests/test_runs.py`

**Interfaces:**
- Consumes: F1-schema.
- Produces: `schemaVersion` const `"1.1"`; `transaction` krijgt vereiste velden `auth`, `prefill`, `validatie`, `h3`, `status`:
  - `status`: enum `["gereed", "gereed-met-waarschuwing", "blokkade", "geweigerd", "escalatie"]`
  - `auth`: `{"authenticatie": "uitgevoerd"|"niet-uitgevoerd", "toestemming": "gegeven"|"geweigerd"|"n.v.t.", "mandaten": array}`
  - `prefill`: `{"transacties": [{"service": str, "velden": [{"veld","waarde","label" (enum incl. `authentiek`), "bron"}], "ontbrekend": [str]}]}`
  - `validatie`: `{"transacties": [{"service": str, "status": enum("gereed","gereed-met-waarschuwing","blokkade"), "bevindingen": [{"id","ernst","melding"}]}]}`
  - `h3`: `{"verdict": "gegeven"|"geweigerd"|"n.v.t.", "correcties": object}`
  - Bij weigering/escalatie mogen `prefill`/`validatie` leeg zijn (`transacties: []`); `h3.verdict` wordt dan `"n.v.t."`.
- `runs.validate` ongewijzigd van signatuur.

- [ ] **Step 1: Werk het schema bij**

Vervang in `poc-gent/schemas/gent-run.schema.json`: `"schemaVersion": {"const": "1.0"}` → `{"const": "1.1"}`; voeg aan de `required` van `transaction` toe: `"status", "auth", "prefill", "validatie", "h3"` (huidige `context`/`routing`/`h1` blijven); voeg in `properties.transaction.properties` toe:

```json
"status": {"enum": ["gereed", "gereed-met-waarschuwing", "blokkade", "geweigerd", "escalatie"]},
"auth": {"type": "object", "additionalProperties": false,
  "required": ["authenticatie", "toestemming", "mandaten"],
  "properties": {"authenticatie": {"enum": ["uitgevoerd", "niet-uitgevoerd"]},
                 "toestemming": {"enum": ["gegeven", "geweigerd", "n.v.t."]},
                 "mandaten": {"type": "array"}}},
"prefill": {"type": "object", "additionalProperties": false, "required": ["transacties"],
  "properties": {"transacties": {"type": "array", "items": {"$ref": "#/$defs/prefillTransactie"}}}},
"validatie": {"type": "object", "additionalProperties": false, "required": ["transacties"],
  "properties": {"transacties": {"type": "array", "items": {"$ref": "#/$defs/validatieTransactie"}}}},
"h3": {"type": "object", "additionalProperties": false, "required": ["verdict", "correcties"],
  "properties": {"verdict": {"enum": ["gegeven", "geweigerd", "n.v.t."]}, "correcties": {"type": "object"}}}
```

en voeg aan `$defs` toe:

```json
"prefillTransactie": {"type": "object", "additionalProperties": false, "required": ["service", "velden", "ontbrekend"],
  "properties": {"service": {"type": "string"}, "ontbrekend": {"type": "array", "items": {"type": "string"}},
    "velden": {"type": "array", "items": {"type": "object", "additionalProperties": false,
      "required": ["veld", "waarde", "label", "bron"],
      "properties": {"veld": {"type": "string"}, "waarde": {}, "bron": {"type": "string"},
        "label": {"enum": ["gebruiker", "correctie", "afgeleid", "authentiek"]}}}}}},
"validatieTransactie": {"type": "object", "additionalProperties": false, "required": ["service", "status", "bevindingen"],
  "properties": {"service": {"type": "string"},
    "status": {"enum": ["gereed", "gereed-met-waarschuwing", "blokkade"]},
    "bevindingen": {"type": "array", "items": {"type": "object", "additionalProperties": false,
      "required": ["id", "ernst", "melding"],
      "properties": {"id": {"type": "string"}, "ernst": {"enum": ["blokkade", "waarschuwing"]}, "melding": {"type": "string"}}}}}}
```

- [ ] **Step 2: Werk de tests aan en voeg er één toe**

In `poc-gent/tests/test_runs.py`: pas `_minimale_run()` aan — `"schemaVersion": "1.1"` en het `transaction`-blok wordt:

```python
        "transaction": {
            "context": {"tekst": "test", "regels": [{"feit": "address", "waarde": "Korenmarkt 1, Gent", "label": "gebruiker", "bron": "gesprek"}]},
            "routing": {"outcome": "paden", "paths": {"transactions": [], "info": []}, "trace": [], "uitleg": []},
            "h1": {"verdict": "gegeven", "correcties": {}},
            "status": "geweigerd",
            "auth": {"authenticatie": "niet-uitgevoerd", "toestemming": "geweigerd", "mandaten": []},
            "prefill": {"transacties": []},
            "validatie": {"transacties": []},
            "h3": {"verdict": "n.v.t.", "correcties": {}},
        },
```

Nieuwe test:

```python
def test_schema_verwerpt_oude_versie():
    run = _minimale_run()
    run["schemaVersion"] = "1.0"
    import jsonschema
    try:
        runs.validate(run, POC_ROOT)
    except jsonschema.ValidationError:
        return
    raise AssertionError("ValidationError werd verwacht")
```

- [ ] **Step 3: Draai en verifieer**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_runs.py -q`
Expected: eerst faalt `test_minimale_run_valideert_tegen_schema` op het oude transaction-blok (RED), na de aanpassingen `7 passed` (6 + 1). Daarna faalt de volledige suite nog in `test_pipeline` — alleen de twee tests die `runs.validate` aanroepen (sanne + escalatie) falen op `ValidationError: 'status' is a required property` (verwacht — pipeline produceert nog v1.0-runs; taak 8 lost dat op).

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: enkel `test_pipeline`-tests falen (5 stuks), de rest groen.

- [ ] **Step 4: Commit**

```bash
git add poc-gent/schemas/gent-run.schema.json poc-gent/tests/test_runs.py
git commit -m "feat(poc-gent): run-schema v1.1 met auth, prefill, validatie, h3 en status"
```

---

### Task 8: Pipeline fase-2 + personas/golden voor weigering en blokkade

**Files:**
- Modify: `poc-gent/core/pipeline.py`
- Modify: `poc-gent/fixtures/personas.json`
- Modify: `poc-gent/packages/gent-mobiliteit-ondernemer/golden/scenarios.jsonl`
- Test: `poc-gent/tests/test_pipeline.py`

**Interfaces:**
- Consumes: taken 1–7 (`acm_idm_mock`, `magda_mock`, `prefill`, `validate`, `gates.h2_uitleg`/`decide_h2`, schema v1.1).
- Produces: `pipeline.run_replay(poc_root, package_id, persona_id, override_slots=None) -> tuple[dict, list]` met fase-2:
  1. Fase-1 zoals bekend (intake → vragen → GIS → H1 → routing; escalatie → status `"escalatie"`, korte run mét `auth: niet-uitgevoerd/n.v.t.`, lege prefill/validatie, `h3: n.v.t.`).
  2. `transacties = routing.paths.transactions`; als geen enkele `vereistAuth` heeft → status afgeleid uit validatie van niets: `"gereed"`, `auth: niet-uitgevoerd/n.v.t.` (maria-case).
  3. Anders: stap `h2-gegevensgebruik` (actor `mens`, consent `gevraagd` → verdict): persona-veld `gebruikGegevens` (`"gegeven"` standaard, ellen: `"geweigerd"`). Event `gate_request`/`gate_verdict` met gate `H2` en de `h2_uitleg`-payload. Weigering → consent `"geweigerd"`, run stopt netjes: status `"geweigerd"`, geen prefill.
  4. Doorgang: stap `acm-authenticatie` (actor `partij`), `acm_idm_mock.authenticate`; `gates.decide_h2` — geen doorgang (mandaat) → stap `h2-mandaatblokkade` (actor `mens`, handover Gentinfo), status `"blokkade"` (ellen komt hier niet: die weigert al; nieuw mandaat-scenario niet nodig — decide_h2-dekking loopt via de unit tests).
  5. Magda-raadpleging per benodigde tool (`h2_uitleg(...).bronnen`) met gedeclareerde purpose; event `bron_raadpleging` per call met `{"tool", "purpose", "sleutels": [..]}` — alléén sleutelnamen van het record, géén waarden (SEC-05-geest). Persona zonder record (maria-achtig bij transactie) → tool overgeslagen; prefill zet het veld op `ontbrekend` en validatie blokkeert.
  6. Per transactie: `prefill.bouw` + `validate.valideer`; events `prefill` en `validatie` per transactie (service + status; veldwaarden alléén in het run-artefact).
  7. Status: geweigerd → `"geweigerd"`; escalatie → `"escalatie"`; anders ergste transactie-status (`blokkade` > `gereed-met-waarschuwing` > `gereed`).
  8. Stap `h3-conceptbeoordeling` (actor `mens`, consent `gevraagd` → `gegeven`) met de concept-samenvatting in `dataUsed` (per transactie: titel + waarschuwingen/blokkades); `h3: {"verdict": "gegeven", "correcties": {}}` (F2: altijd gegeven; blokkade-correctiepad staat in de bevindingen).
  - Persona-uitbreiding: alle persona's krijgen `"gebruikGegevens": "gegeven"` behalve `ellen: "geweigerd"`; nieuwe persona's `ellen` (adres Sint-Pietersplein, intent ondernemer/herstelwerken, edge `weigert-gegevensgebruik`) en `dirk` (adres Korenmarkt, Euro 4, edge `validatieblokkade`).
  - Golden: g1 sanne → `status: "gereed"`; g2 ahmed → `"gereed-met-waarschuwing"`; g3 maria → `"gereed"`; g4 fatima → `"gereed-met-waarschuwing"`; g5 jeroen → `"gereed"`; g6 escalatie → `"escalatie"`; nieuw g7 ellen → `"geweigerd"`; nieuw g8 dirk → `"blokkade"`. Alle golden-regels krijgen een `status`-veld in `expect`.

- [ ] **Step 1: Breid personas en golden uit**

`poc-gent/fixtures/personas.json` — voeg aan élke bestaande persona `"gebruikGegevens": "gegeven"` toe en voeg twee persona's toe:

```json
    {"id": "ellen", "label": {"nl": "Ellen — weigert het gebruik van haar gegevens"}, "edge": "weigert-gegevensgebruik",
     "situatieschets": "Ik ben ondernemer en moet werken aan het Sint-Pietersplein, maar ik wil mijn gegevens niet delen.",
     "intentSlots": {"applicantType": "ondernemer", "address": "Sint-Pietersplein 1, Gent", "activity": "herstelwerken uitvoeren"},
     "antwoorden": {}, "corrections": {}, "gebruikGegevens": "geweigerd"},
    {"id": "dirk", "label": {"nl": "Dirk — oud dieselvoertuig (Euro 4), verwacht blokkade"}, "edge": "validatieblokkade",
     "situatieschets": "Ik kom met mijn oude bestelwagen werken aan de Korenmarkt.",
     "intentSlots": {"applicantType": "ondernemer", "address": "Korenmarkt 1, Gent", "activity": "herstelwerken uitvoeren"},
     "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven"}
```

`poc-gent/packages/gent-mobiliteit-ondernemer/golden/scenarios.jsonl` — voeg `"status"` toe aan élke bestaande expect (waarden als hierboven) en voeg toe:

```jsonl
{"scenarioId": "g7-ellen-weigert-gegevensgebruik", "persona": "ellen", "expect": {"outcome": "paden", "transactions": ["ontheffing-lez"], "info": [], "status": "geweigerd"}}
{"scenarioId": "g8-dirk-euro4-blokkade", "persona": "dirk", "expect": {"outcome": "paden", "transactions": ["ontheffing-lez", "ontheffing-autovrij"], "info": ["info-lez"], "status": "blokkade"}}
```

- [ ] **Step 2: Schrijf de falende pipeline-tests**

Voeg toe aan `poc-gent/tests/test_pipeline.py`:

```python
def test_sanne_doorloopt_tot_h3_gereed_met_authentieke_prefill():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "gereed"
    assert run["transaction"]["auth"] == {"authenticatie": "uitgevoerd", "toestemming": "gegeven", "mandaten": []}
    kenteken = [v for v in run["transaction"]["prefill"]["transacties"][0]["velden"] if v["veld"] == "kenteken"][0]
    assert kenteken["label"] == "authentiek"
    assert kenteken["bron"].startswith("magda:kenteken")
    assert run["transaction"]["h3"]["verdict"] == "gegeven"
    assert events_mod.verify_chain(log) is True


def test_ellen_weigering_stopt_netjes_zonder_prefill():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "ellen")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "geweigerd"
    assert run["transaction"]["prefill"]["transacties"] == []
    assert run["transaction"]["h3"]["verdict"] == "n.v.t."
    consent = [s for s in run["steps"] if s["stepId"] == "h2-gegevensgebruik"][0]["consent"]
    assert consent == "geweigerd"


def test_dirk_euro4_levert_blokkade_met_correctiepad():
    run, _log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "dirk")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "blokkade"
    bevindingen = run["transaction"]["validatie"]["transacties"][0]["bevindingen"]
    assert bevindingen[0]["id"] == "V1-euroklasse"
    assert "Vervang" in bevindingen[0]["melding"]


def test_bron_raadpleging_logt_sleutels_zonder_waarden():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    raadplegingen = [e for e in log if e["kind"] == "bron_raadpleging"]
    assert raadplegingen and all(set(r["payload"]["sleutels"]) <= {"kenteken", "euroklasse", "brandstof"} for r in raadplegingen)
    assert all("waarde" not in json.dumps(r) or "sleutels" in r for r in raadplegingen)


def test_maria_zonder_transacties_slaat_auth_over():
    run, _log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "maria")
    runs.validate(run, POC_ROOT)
    assert run["transaction"]["status"] == "gereed"
    assert run["transaction"]["auth"]["authenticatie"] == "niet-uitgevoerd"
    assert run["transaction"]["auth"]["toestemming"] == "n.v.t."
```

(Voeg bovenaan het testbestand `import json` toe als die ontbreekt.)

- [ ] **Step 3: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_pipeline.py -q`
Expected: FAIL — status/auth/prefill ontbreken in het huidige run-artefact (`KeyError: 'status'`) en de nieuwe persona's bestaan nog niet; dat is het RED-bewijs voor de fase-2-uitbreiding.

- [ ] **Step 4: Breid `pipeline.run_replay` uit (fase-2)**

Voeg imports toe aan `poc-gent/core/pipeline.py`:

```python
from adapters import acm_idm_mock, magda_mock
from core import prefill, validate
```

En implementeer na de bestaande routing/fase-1 en vóór het samenstellen van `run` de fase-2 (vervang de huidige `"transaction"`-opbouw; de escalatie-tak en de stappenlijst worden aangevuld):

```python
    transacties = routing["paths"]["transactions"]
    vereist_auth = [sv for sv in transacties if pkg.manifest["services"][sv].get("vereistAuth")]
    auth_blok = {"authenticatie": "niet-uitgevoerd", "toestemming": "n.v.t.", "mandaten": []}
    prefill_blok = {"transacties": []}
    validatie_blok = {"transacties": []}
    status = "gereed"
    h3_blok = {"verdict": "n.v.t.", "correcties": {}}

    if routing["outcome"] == "escalatie":
        status = "escalatie"
    elif vereist_auth:
        uitleg_h2 = gates.h2_uitleg(pkg.manifest, vereist_auth)
        events_mod.emit(events, "gate_request", {"gate": "H2", "uitleg": uitleg_h2})
        toestemming = persona.get("gebruikGegevens", "gegeven")
        if toestemming == "geweigerd":
            status = "geweigerd"
            auth_blok["toestemming"] = "geweigerd"
            events_mod.emit(events, "gate_verdict", {"gate": "H2", "verdict": "geweigerd"})
            steps.append({"stepId": "h2-gegevensgebruik", "title": "Je beslist of we je gegevens mogen gebruiken",
                          "actor": "mens", "genAiTestPoint": "—",
                          "dataUsed": [b["tool"] + " — " + b["purpose"] for b in uitleg_h2["bronnen"]],
                          "consent": "geweigerd", "handover": None, "kpiEvents": [],
                          "prov": {"sources": ["H2-weigering door gebruiker"]}})
        else:
            identiteit = acm_idm_mock.authenticate(poc_root, persona_id)
            besluit = gates.decide_h2(pkg.manifest, ctx, identiteit, vereist_auth)
            steps.append({"stepId": "h2-gegevensgebruik", "title": "Je geeft toestemming om je gegevens op te halen",
                          "actor": "mens", "genAiTestPoint": "—",
                          "dataUsed": [b["tool"] + " — " + b["purpose"] for b in uitleg_h2["bronnen"]],
                          "consent": "gegeven", "handover": None, "kpiEvents": [],
                          "prov": {"sources": ["H2-toestemming door gebruiker"]}})
            steps.append({"stepId": "acm-authenticatie", "title": "Je bevestigt wie je bent (ACM/IDM)",
                          "actor": "partij", "genAiTestPoint": "—",
                          "dataUsed": [identiteit["pseudoniem"]], "consent": "n.v.t.", "handover": None,
                          "kpiEvents": [], "prov": {"sources": ["ACM/IDM (mock v1)"]}})
            events_mod.emit(events, "gate_verdict", {"gate": "H2", "verdict": "gegeven"})
            auth_blok = {"authenticatie": "uitgevoerd", "toestemming": "gegeven", "mandaten": identiteit["mandaten"]}
            if not besluit["doorgang"]:
                status = "blokkade"
                steps.append({"stepId": "h2-mandaatblokkade", "title": "Een medewerker controleert het mandaat",
                              "actor": "mens", "genAiTestPoint": "G5", "dataUsed": [besluit["reden"]],
                              "consent": "gevraagd", "handover": {"reason": besluit["reden"], "to": "Gentinfo"},
                              "kpiEvents": [], "prov": {"sources": []}})
                events_mod.emit(events, "handover", {"gate": "H2", "naar": "Gentinfo", "reden": besluit["reden"]})
            else:
                records: dict = {}
                for bron in uitleg_h2["bronnen"]:
                    try:
                        records[bron["tool"]] = magda_mock.raadpleeg(pkg.manifest, bron["tool"], bron["purpose"],
                                                                    poc_root, persona_id)
                    except KeyError:
                        continue
                    events_mod.emit(events, "bron_raadpleging",
                                    {"tool": bron["tool"], "purpose": bron["purpose"],
                                     "sleutels": sorted(records[bron["tool"]].keys())})
                ergste = {"gereed": 0, "gereed-met-waarschuwing": 1, "blokkade": 2}
                for service_id in transacties:
                    formulier = prefill.bouw(pkg.manifest, service_id, ctx, herkomst, records)
                    uitslag = validate.valideer(pkg.manifest, service_id, formulier)
                    prefill_blok["transacties"].append(formulier)
                    validatie_blok["transacties"].append(uitslag)
                    events_mod.emit(events, "prefill", {"service": service_id, "ontbrekend": formulier["ontbrekend"]})
                    events_mod.emit(events, "validatie", {"service": service_id, "status": uitslag["status"]})
                status = max((u["status"] for u in validatie_blok["transacties"]),
                             key=lambda s: ergste[s], default="gereed")
                h3_blok = {"verdict": "gegeven", "correcties": {}}
                steps.append({"stepId": "h3-conceptbeoordeling", "title": "Je beoordeelt het concept van je aanvraag",
                              "actor": "mens", "genAiTestPoint": "—",
                              "dataUsed": [f"{pkg.manifest['services'][u['service']]['titel']} — {u['status']}"
                                           for u in validatie_blok["transacties"]],
                              "consent": "gegeven", "handover": None, "kpiEvents": [],
                              "prov": {"sources": ["H3-beoordeling door gebruiker"]}})
                events_mod.emit(events, "gate_request", {"gate": "H3", "concept": [
                    {"service": u["service"], "status": u["status"]} for u in validatie_blok["transacties"]]})
                events_mod.emit(events, "gate_verdict", {"gate": "H3", "verdict": "gegeven", "correcties": {}})
```

En vervang in de `run`-opbouw: `"schemaVersion": "1.0"` → `"1.1"`, en het `transaction`-blok door:

```python
        "transaction": {"context": context.summary(pkg.manifest, ctx, herkomst),
                        "routing": routing,
                        "h1": {"verdict": "gegeven", "correcties": corrections},
                        "status": status,
                        "auth": auth_blok,
                        "prefill": prefill_blok,
                        "validatie": validatie_blok,
                        "h3": h3_blok},
```

- [ ] **Step 5: Draai alle tests**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `74 passed` (69 + 5).

- [ ] **Step 6: Commit**

```bash
git add poc-gent/core/pipeline.py poc-gent/fixtures/personas.json poc-gent/packages/gent-mobiliteit-ondernemer/golden/scenarios.jsonl poc-gent/tests/test_pipeline.py
git commit -m "feat(poc-gent): pipeline fase-2 — H2, authenticatie, Magda-prefill, validatie, H3"
```

---

### Task 9: eval-status + CLI + README

**Files:**
- Modify: `poc-gent/eval.py`
- Modify: `poc-gent/run.py`
- Modify: `poc-gent/README.md`
- Test: `poc-gent/tests/test_eval.py`

**Interfaces:**
- Consumes: golden `expect.status` (taak 8); run `transaction.status`.
- Produces: `eval.evaluate` vergelijkt naast outcome/paths/info óók `status`; de FAAL-regel print de verwachte status bij mismatch; `run.py` drukt na de routing-samenvatting de status en (indiet aanwezig) de bevindingen met meldingen; README beschrijft F2.

- [ ] **Step 1: Breid eval.py uit**

Vervang in `poc-gent/eval.py` de vergelijking:

```python
        ok = (routing["outcome"] == expect["outcome"]
              and routing["paths"]["transactions"] == expect["transactions"]
              and routing["paths"]["info"] == expect["info"])
```

door:

```python
        ok = (routing["outcome"] == expect["outcome"]
              and routing["paths"]["transactions"] == expect["transactions"]
              and routing["paths"]["info"] == expect["info"]
              and run["transaction"]["status"] == expect.get("status", "gereed"))
```

en de printregel door:

```python
        print(f"{'OK  ' if ok else 'FAAL'} {scenario['scenarioId']}: "
              f"{routing['outcome']} {routing['paths']['transactions']} "
              f"[status {run['transaction']['status']}]")
```

- [ ] **Step 2: Breid run.py uit**

Voeg in `poc-gent/run.py` ná het blok `for u in routing["uitleg"]:` toe (vóór de escalatie-regel):

```python
    status = run["transaction"]["status"]
    print(f"status:     {status}")
    for uitslag in run["transaction"]["validatie"]["transacties"]:
        for bevinding in uitslag["bevindingen"]:
            print(f"  {bevinding['ernst']}: {bevinding['melding']}")
    if run["transaction"]["auth"]["toestemming"] == "geweigerd":
        print("  gestopt: je gaf geen toestemming om je gegevens op te halen")
```

- [ ] **Step 3: Update de README**

Vervang in `poc-gent/README.md` de openingsalinea "Fase 1 (intake → context → GIS → routing → H1) …" door:

```markdown
Fase 1 + 2 (intake → context → GIS → routing → H1 → H2-authenticatie →
Magda-prefill → validatie → H3-concept) van het referentiepakket
`gent-mobiliteit-ondernemer`. Ontwerp:
[`docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md`](../docs/superpowers/specs/2026-10-30-piloot-gent-transactionele-assistent-design.md).
```

en voeg onder de bestaande doctrine-bullets toe:

```markdown
- F2 (H2–H3): authenticatie via ACM/IDM-mock, prefill uit de Magda-mock in
  MCP-vorm mét doelbinding, zichtbare herkomstlabels (`authentiek`) per
  formulierveld, deterministische validatie (blokkade/waarschuwing) en de
  H3-conceptbeoordeling; weigering van gegevensgebruik stopt de run netjes.
```

- [ ] **Step 4: Draai alles en smoke**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: `74 passed` (geen nieuwe pytest-tests; de bestaande golden-test dekt de status-uitbreiding).

Run: `python3 eval.py` → acht regels, allemaal OK (g1…g8), `determinisme: OK`, `golden: 8/8 geslaagd`, exit 0.

Run: `python3 run.py --persona dirk | head -8` → `uitkomst: paden`, beide transacties, `status: blokkade`, en de Euro 4-blokkademelding.

Run: `python3 run.py --persona ellen | head -6` → `status: geweigerd` en de stopmelding.

- [ ] **Step 5: Commit**

```bash
git add poc-gent/eval.py poc-gent/run.py poc-gent/README.md
git commit -m "feat(poc-gent): status in eval en CLI; README F2"
```

---

## Zelfcheck na afronding (executeur)

1. `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` → `74 passed`.
2. `python3 eval.py` → `golden: 8/8 geslaagd`, `determinisme: OK`, exit 0.
3. `python3 run.py --persona sanne | head -6` → `status: gereed`, `transactie: ontheffing-lez`, `ontheffing-autovrij`.
4. `python3 run.py --persona ellen | head -6` → `status: geweigerd`.
5. `python3 run.py --persona dirk | head -8` → `status: blokkade` + V1-melding.
