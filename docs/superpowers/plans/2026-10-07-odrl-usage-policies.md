# ODRL usage policies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Executiestatus (2026-10-07):** alle 4 taken uitgevoerd — T1–T3 subagent-driven met review
> (spec ✅, geen Critical/Important), T4 inline door de controller (live-publicatiegolf 15/15:
> 13 open policy-open, 1 internal policy-internal, 1 restricted policy-restricted HITL-approved;
> nldt/26 met de fase × databron × acteur-matrix en de werkelijke JSON's; nldt/13-koppeling).
> Suites: nldt 401 passed, poc 304/1. Gepusht (`91cd0cd`). Eindreview-triage (kan-later):
> geen caching in load_policies; `odrl:spatial isA` met custom terms is niet-canoniek ODRL
> (documentair tot de wallet-binding); permissief policy-schema; KeyError-hardening bij
> onbekende accessClass in het http-pad; body bevat asset-tekst bij policy-≥400.

**Goal:** ODRL-beleid machinaal leesbaar: drie vaste Policy-Definitions als beleidsartefact, geëmbed in offers en meegeleverd in EDC-manifests/http-registratie, gedemonstreerd met een live-publicatiegolf over het Utrechtse planproces (15 offers) en de fase × databron × acteur-matrix als `nldt/26`.

**Architecture:** Policy-bibliotheek (JSON + schema + pure lader) als enige bron van beleidsinhoud; `build_odrl_offer` embedt permission/prohibition uit de bibliotheek; de connector levert Policy-Definitions mee (manifest compleet, http POST vóór asset, mock krijgt policyId). Geen enforcement-runtime, geen wijziging aan deny-lijst/HITL-gate.

**Tech Stack:** stdlib + bestaande `services.common.schema.validate_instance`; geen nieuwe dependencies.

**Spec:** [`docs/superpowers/specs/2026-10-07-odrl-usage-policies-design.md`](../specs/2026-10-07-odrl-usage-policies-design.md)

## Global Constraints

- Beleidsregel (gebruikersbesluit): open = use+distribute zonder constraints (CC0); internal = use+distribute binnen `nldt-participant`, distribute aan `external-party` verboden; restricted = use only, distribute altijd verboden.
- `nldt/data/**` is gitignored — beleid woont in `nldt/schemas/dataspace-policies.json` (in git); gegenereerde offers/manifests blijven buiten git; het doc `nldt/26` bevat de werkelijke JSON's.
- Enforcement is buiten scope (EDC wanneer live); de bestaande HITL-gate en `lake-deny.json` blijven onaangetast.
- ODRL 2.2 JSON-LD-vorm: context `https://www.w3.org/ns/odrl.jsonld`, `@type: odrl:Set`, `odrl:permission`/`odrl:prohibition` met `odrl:action`/`odrl:constraint`/`odrl:leftOperand`/`odrl:operator`/`odrl:rightOperand`.
- Terugwaarts compatibel: `publish_dataset`-returnvorm ongewijzigd; bestaande offers (zonder `prohibition`) blijven geldig tegen het uitgebreide offer-schema; bestaande tests (`test_phase6_dataspace.py`) blijven groen.
- Let op de parallelle HITL-sessie: dit plan raakt `publish.py`, `dataspace_connector.py` en nieuwe bestanden — raak `deep-agents/` en `services/memory/observations.py` niet aan.
- Testinterpreter: `cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q`; commit-stijl Nederlands.

---

### Task 1: Policy-bibliotheek (`dataspace-policies.json`, schema, lader)

**Files:**
- Create: `nldt/schemas/dataspace-policies.json`
- Create: `nldt/schemas/dataspace-policy.schema.json`
- Create: `nldt/services/adapters/odrl_policies.py`
- Test: `nldt/tests/test_odrl_policies.py`

**Interfaces:**
- Produces (Tasks 2–3 consumeren): `load_policies() -> dict` (alle policies, schema-gevalideerd), `policy_for(access_class: str) -> dict` (KeyError bij onbekende klasse), `policy_ids_referenced_by(offer: dict) -> list[str]`.

- [ ] **Step 1: De drie policies** (`nldt/schemas/dataspace-policies.json`):

```json
{
  "@context": "https://www.w3.org/ns/odrl.jsonld",
  "vocabularies": {
    "nldt-participant": "Deelnemer aan de nLDT data space (provincies, gemeenten, waterschappen, omgevingsdiensten met actieve deelname-overeenkomst).",
    "external-party": "Elke partij buiten de nLDT-deelnemerskring."
  },
  "policies": [
    {
      "@id": "policy-open",
      "@type": "odrl:Set",
      "odrl:uid": "http://nldt.example/policy/open",
      "odrl:permission": [
        { "odrl:action": ["odrl:use", "odrl:distribute"] }
      ]
    },
    {
      "@id": "policy-internal",
      "@type": "odrl:Set",
      "odrl:uid": "http://nldt.example/policy/internal",
      "odrl:permission": [
        {
          "odrl:action": ["odrl:use", "odrl:distribute"],
          "odrl:constraint": [{
            "odrl:leftOperand": "odrl:spatial",
            "odrl:operator": "odrl:isA",
            "odrl:rightOperand": "nldt-participant"
          }]
        }
      ],
      "odrl:prohibition": [
        {
          "odrl:action": ["odrl:distribute"],
          "odrl:constraint": [{
            "odrl:leftOperand": "odrl:spatial",
            "odrl:operator": "odrl:isA",
            "odrl:rightOperand": "external-party"
          }]
        }
      ]
    },
    {
      "@id": "policy-restricted",
      "@type": "odrl:Set",
      "odrl:uid": "http://nldt.example/policy/restricted",
      "odrl:permission": [
        { "odrl:action": ["odrl:use"] }
      ],
      "odrl:prohibition": [
        { "odrl:action": ["odrl:distribute"] }
      ]
    }
  ]
}
```

- [ ] **Step 2: Policy-schema** (`nldt/schemas/dataspace-policy.schema.json`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://nldt.example/schemas/dataspace-policy.schema.json",
  "title": "ODRL Set policy (nLDT usage policies)",
  "type": "object",
  "required": ["@id", "@type", "odrl:permission"],
  "additionalProperties": true,
  "properties": {
    "@id": { "enum": ["policy-open", "policy-internal", "policy-restricted"] },
    "@type": { "const": "odrl:Set" },
    "odrl:uid": { "type": "string" },
    "odrl:permission": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/rule" }
    },
    "odrl:prohibition": {
      "type": "array",
      "items": { "$ref": "#/$defs/rule" }
    }
  },
  "$defs": {
    "rule": {
      "type": "object",
      "required": ["odrl:action"],
      "additionalProperties": true,
      "properties": {
        "odrl:action": { "type": "array", "minItems": 1 },
        "odrl:constraint": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["odrl:leftOperand", "odrl:operator", "odrl:rightOperand"],
            "additionalProperties": true
          }
        }
      }
    }
  }
}
```

- [ ] **Step 3: Falende tests** (`nldt/tests/test_odrl_policies.py`):

```python
from __future__ import annotations

import pytest

from services.adapters import odrl_policies


def test_load_policies_validates_all_three() -> None:
    policies = odrl_policies.load_policies()
    assert set(policies) == {"policy-open", "policy-internal", "policy-restricted"}


def test_policy_for_maps_access_class() -> None:
    assert odrl_policies.policy_for("open")["@id"] == "policy-open"
    assert odrl_policies.policy_for("internal")["@id"] == "policy-internal"
    assert odrl_policies.policy_for("restricted")["@id"] == "policy-restricted"


def test_policy_for_unknown_class_raises() -> None:
    with pytest.raises(KeyError):
        odrl_policies.policy_for("geheim")


def test_internal_has_distribute_prohibition_for_external() -> None:
    policy = odrl_policies.policy_for("internal")
    prohibition = policy["odrl:prohibition"][0]
    constraint = prohibition["odrl:constraint"][0]
    assert "odrl:distribute" in prohibition["odrl:action"]
    assert constraint["odrl:rightOperand"] == "external-party"


def test_restricted_permits_use_only() -> None:
    policy = odrl_policies.policy_for("restricted")
    assert policy["odrl:permission"][0]["odrl:action"] == ["odrl:use"]
    assert "odrl:distribute" in policy["odrl:prohibition"][0]["odrl:action"]


def test_policy_ids_referenced_by_offer() -> None:
    offer = {"accessClass": "internal", "permission": [], "prohibition": []}
    assert odrl_policies.policy_ids_referenced_by(offer) == ["policy-internal"]
```

- [ ] **Step 4: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_odrl_policies.py -q` → ModuleNotFoundError.

- [ ] **Step 5: Implementeer `nldt/services/adapters/odrl_policies.py`**:

```python
"""ODRL usage-policy-bibliotheek (dataspacebeleidsobjecten).

De drie vaste policies leven in nldt/schemas/dataspace-policies.json (in git —
beleid is contract). Pure lader; enforcement is een EDC-verantwoordelijkheid
zodra live — deze laag levert de beleidsobjecten.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.common.schema import validate_instance

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"
POLICIES_PATH = SCHEMAS_DIR / "dataspace-policies.json"
POLICY_SCHEMA = "dataspace-policy.schema.json"

CLASS_TO_POLICY = {
    "open": "policy-open",
    "internal": "policy-internal",
    "restricted": "policy-restricted",
}


def load_policies() -> dict[str, Any]:
    data = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
    policies = {p["@id"]: p for p in data["policies"]}
    for policy in policies.values():
        validate_instance(policy, POLICY_SCHEMA)
    return policies


def policy_for(access_class: str) -> dict[str, Any]:
    policies = load_policies()
    policy_id = CLASS_TO_POLICY.get(access_class)
    if policy_id is None:
        raise KeyError(f"onbekende accessClass: {access_class}")
    return policies[policy_id]


def policy_ids_referenced_by(offer: dict[str, Any]) -> list[str]:
    policy_id = CLASS_TO_POLICY.get(str(offer.get("accessClass")), "")
    return [policy_id] if policy_id else []

```


- [ ] **Step 6: Draai, verwacht PASS** — `.venv/bin/python -m pytest tests/test_odrl_policies.py -q` → `6 passed`.

- [ ] **Step 7: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/schemas/dataspace-policies.json nldt/schemas/dataspace-policy.schema.json nldt/services/adapters/odrl_policies.py nldt/tests/test_odrl_policies.py
git commit -m "feat(nldt): ODRL policy-bibliotheek — drie vaste usage-policies (open/internal/restricted) met schema en lader"
```

### Task 2: `build_odrl_offer` embedt echt beleid + offer-schema uitbreiden

**Files:**
- Modify: `nldt/services/lake/publish.py` (`build_odrl_offer`, regel ~52)
- Modify: `nldt/schemas/dataspace-offer.schema.json` (`prohibition` erbij)
- Test: `nldt/tests/test_odrl_policies.py` (uitbreiding)

**Interfaces:**
- Consumes: Task 1 (`policy_for`).
- Produces: offers met echte `odrl:permission`/`odrl:prohibition`-arrays (ingebette policy-regels); retourvorm van `publish_dataset` ongewijzigd.

- [ ] **Step 1: Falende tests** (append aan `nldt/tests/test_odrl_policies.py`):

```python
def test_build_odrl_offer_embeds_policy(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    from services.lake.publish import build_odrl_offer

    offer = build_odrl_offer(
        dataset_id="utrecht-test", lake_uri="lake://nldt-poc-lake/gold/utrecht/test.json",
        access_class="internal", license_="CC-BY-4.0",
    )
    assert offer["permission"][0]["odrl:action"] == ["odrl:use", "odrl:distribute"]
    assert offer["prohibition"][0]["odrl:action"] == ["odrl:distribute"]
    assert offer["license"] == "CC-BY-4.0"


def test_build_odrl_offer_open_has_no_prohibition() -> None:
    from services.lake.publish import build_odrl_offer

    offer = build_odrl_offer(
        dataset_id="utrecht-open", lake_uri="lake://nldt-poc-lake/gold/utrecht/open.json",
        access_class="open",
    )
    assert offer["permission"][0]["odrl:action"] == ["odrl:use", "odrl:distribute"]
    assert "prohibition" not in offer
```

- [ ] **Step 2: Draai, verwacht FAIL** — pseudo-ODRL-constraint in plaats van echte arrays.

- [ ] **Step 3: Implementeer** — vervang in `publish.py` de body van `build_odrl_offer`:

```python
def build_odrl_offer(
    *,
    dataset_id: str,
    lake_uri: str,
    access_class: str,
    license_: str | None = None,
) -> dict[str, Any]:
    """ODRL-offer met ingebette usage-policy uit de policy-bibliotheek."""
    from services.adapters.odrl_policies import policy_for

    offer_id = f"offer-{uuid.uuid4().hex[:10]}"
    policy = policy_for(access_class)
    offer: dict[str, Any] = {
        "@type": "Offer",
        "uid": offer_id,
        "datasetId": dataset_id,
        "lakeUri": lake_uri,
        "accessClass": access_class,
        "license": license_ or "unknown",
        "permission": policy.get("odrl:permission", []),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "draft" if access_class == "restricted" else "published",
    }
    if policy.get("odrl:prohibition"):
        offer["prohibition"] = policy["odrl:prohibition"]
    return offer
```

En in `dataspace-offer.schema.json`: voeg toe onder `properties` (naast het bestaande `permission`):

```json
    "prohibition": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["odrl:action"],
        "properties": {
          "odrl:action": { "type": "array" },
          "odrl:constraint": { "type": "array" }
        }
      }
    }
```

Let op: het bestaande `permission`-item-schema (met `action`/`constraint` in snake-case) is te smal voor de nieuwe `odrl:`-vorm — vervang ook het `permission`-items-blok door dezelfde open vorm (`additionalProperties: true`, alleen `odrl:action` vereist, oude `action`-vorm blijft toegestaan door er géén `additionalProperties: false` te zetten):

```json
    "permission": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true,
        "anyOf": [
          { "required": ["action"] },
          { "required": ["odrl:action"] }
        ]
      }
    }
```

- [ ] **Step 4: Draai** — `.venv/bin/python -m pytest tests/test_odrl_policies.py tests/test_phase6_dataspace.py -q` → alle groen (bestaande publish-tests bewijzen terugwaartse compatibiliteit; als een bestaande test op de oude pseudo-constraint let, rapporteer dat — niet zelf aanpassen zonder melding).

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/lake/publish.py nldt/schemas/dataspace-offer.schema.json nldt/tests/test_odrl_policies.py
git commit -m "feat(nldt): build_odrl_offer embedt echte usage-policy — permission/prohibition uit de bibliotheek"
```

### Task 3: Connector levert Policy-Definitions mee

**Files:**
- Modify: `nldt/services/adapters/dataspace_connector.py` (`write_edc_manifest`, `http_register_offer`, `mock_register_offer`)
- Test: `nldt/tests/test_odrl_policies.py` (uitbreiding)

**Interfaces:**
- Consumes: Task 1 (`policy_for`), bestaande offer-vorm uit Task 2.

- [ ] **Step 1: Falende tests** (append):

```python
def test_edc_manifest_includes_policies(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_DATASPACE_CONNECTOR", "edc-manifest")
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("NLDT_EDC_MANIFEST_DIR", str(tmp_path / "manifests"))
    from services.adapters.dataspace_connector import write_edc_manifest

    result = write_edc_manifest({"uid": "offer-abc", "datasetId": "ds", "lakeUri": "lake://x", "accessClass": "internal"})
    import json as _json

    bundle = _json.loads((tmp_path / "manifests" / "offer-abc.edc.json").read_text(encoding="utf-8"))
    assert bundle["policies"][0]["@id"] == "policy-internal"
    assert bundle["contractDefinition"]["accessPolicyId"] == "policy-internal"
    assert result["policyIds"] == ["policy-internal"]


def test_mock_register_records_policy_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_DATASPACE_CONNECTOR", "mock")
    monkeypatch.setenv("NLDT_DATASPACE_REGISTRY", str(tmp_path / "registry.json"))
    from services.adapters.dataspace_connector import mock_register_offer

    result = mock_register_offer({"uid": "offer-xyz", "datasetId": "ds2", "lakeUri": "lake://y", "accessClass": "open", "status": "published"})
    assert result["policyId"] == "policy-open"
```

- [ ] **Step 2: Draai, verwacht FAIL.**

- [ ] **Step 3: Implementeer** — in `dataspace_connector.py`:

Bovenaan: `from services.adapters.odrl_policies import policy_for, policy_ids_referenced_by  # noqa: E402` (onder de bestaande imports).

In `write_edc_manifest`: na `contract = ...` het bundle-dict uitbreiden:

```python
    policy = policy_for(str(offer.get("accessClass", "internal")))
    bundle = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "participantId": os.environ.get("NLDT_DATASPACE_PARTICIPANT", "nldt-nl-poc"),
        "asset": asset,
        "contractDefinition": contract,
        "policies": [policy],
        "sourceOffer": {"uid": offer.get("uid"), "datasetId": offer.get("datasetId")},
    }
```

en het retour-dict uitbreiden met `"policyIds": policy_ids_referenced_by(offer),`.

In `http_register_offer`: vóór de Asset-POST de Policy-Definition registreren (binnen dezelfde try, direct na `import httpx`):

```python
    policy = policy_for(str(offer.get("accessClass", "internal")))
```

en in de client-blok vóór de asset-POST:

```python
            policy_resp = client.post(f"{base}/v3/policydefinitions", json=policy)
```

met `policy_resp.status_code` in het resultaat (`"policyStatus": policy_resp.status_code`); bij policy-status ≥ 400 → zelfde fallback-pad als de asset-fout (manifest). In het fallback-pad (geen base / except) niets wijzigen behalve dat `write_edc_manifest` nu automatisch policies meelevert.

In `mock_register_offer`: `entry` uitbreiden met `"policyId": policy_ids_referenced_by(offer)[0] if policy_ids_referenced_by(offer) else None,` en het retour-dict met `"policyId": entry["policyId"],`.

- [ ] **Step 4: Draai** — `.venv/bin/python -m pytest tests/test_odrl_policies.py tests/test_phase6_dataspace.py -q` → alle groen; daarna hele suite `.venv/bin/python -m pytest tests -q`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/adapters/dataspace_connector.py nldt/tests/test_odrl_policies.py
git commit -m "feat(nldt): connector levert ODRL Policy-Definitions mee — manifest compleet, http POST policy vóór asset, mock policyId"
```

### Task 4: Worked example — live-publicatiegolf + `nldt/26` + doc-koppeling

**Files:**
- Create: `nldt/26-odrl-usage-policies.md`
- Modify: `nldt/13-data-lake-and-space.md` (korte beleidsnotitie in de accessClass-sectie)

**Interfaces:**
- Consumes: Tasks 1–3 (`publish_dataset`, `sync_local_to_gold`, beleidsinbedding).

Deze taak is een live-taak: de publicatiegolf wordt gedraaid tegen de echte stack (NLDT_LAKE_BACKEND=fs, connector=edc-manifest) en het doc bevat de werkelijke JSON's.

- [ ] **Step 1: Live-golf script draaien** (interactief of als ad-hoc-script; van cwd `nldt` met `PYTHONPATH=.`):

```python
# 13 open offers — per canonieke track de zones.geojson
import json
from pathlib import Path
from services.lake.publish import sync_local_to_gold, publish_dataset
from services.adapters.odrl_policies import policy_ids_referenced_by

CANONICAL = {
    "wind": "20260830T113234Z-wind", "zon": "20260830T142439Z-zon", "bos": "20260830T142446Z-bos",
    "water": "20261004T185116Z-water", "bodem": "20261004T185509Z-bodem",
    "mobiliteit": "20261005T072839Z-mobiliteit", "landschap": "20261005T070621Z-landschap",
    "landbouw": "20261005T094244Z-landbouw", "wonen": "20261005T100258Z-wonen",
    "werken": "20261006T121921Z-werken", "recreatie": "20261006T114934Z-recreatie",
    "biomassa": "20261006T120133Z-biomassa", "energietoets": "20261006T171730Z-energietoets",
}
results = []
for track, run_id in CANONICAL.items():
    zones = Path("../poc/runs") / run_id / "zones.geojson"
    sync = sync_local_to_gold(zones, "utrecht", "run", run_id)
    offer = publish_dataset(lake_key=sync["key"], access_class="open", license_="CC0-1.0")
    results.append({"track": track, "runId": run_id, "status": offer["status"], "uid": offer.get("offer", {}).get("uid")})
print(json.dumps(results, indent=1))
```

Geverifieerd: `sync_local_to_gold(src, poc, run_type, run_id) -> dict` retourneert `{"key", "uri", "sha256", "bytes", "skipped", "dry_run"}` (`services/lake/sync.py::sync_file`) — vandaar `sync["key"]`.

- [ ] **Step 2: Internal + restricted offer** — kies uit wat bestaat: internal = nieuwste scenario-sweep output onder `poc/scenario-runs/` (geen `-authorcmp`-dir); restricted = de world-scene-bundel van de nieuwste `<id>-worldscene`-dir (`world-scene-specs.json`), beide via `sync_local_to_gold` + `publish_dataset(access_class="internal")` resp. `(..., access_class="restricted", force_hitl_approved=True)`. Rapporteer de gekozen run-ids.

- [ ] **Step 3: `nldt/26-odrl-usage-policies.md` schrijven** — structuur (met de werkelijke JSON's uit de golf):

1. Kop: doel, doctrine ("AI proposes · pipeline disposes · human decides" op de share plane), nummer-notitie (voorlopig; function-first-layer krijgt bij landing een ander nummer).
2. Policy-bibliotheek: de drie policies (JSON uit `nldt/schemas/dataspace-policies.json`), vocabulair (`nldt-participant`, `external-party` — documentair tot de wallet-koppeling).
3. **Fase × databron × acteur-matrix** — letterlijk de matrix uit de spec (§3a), inclusief gaten (planMER, PDOK, DSO, energienet) en de `restricted-pending`-notitie.
4. Live-publicatiegolf: batch-tabel van de 15 offers (offer-id, track/bundel, klasse, policy-id, status); drie volledige uitwerkingen (één per klasse): offer-JSON, EDC-manifest (Asset + ContractDefinition + Policy-Definition), ValidationReport.
5. De three-class uitleg: wat een ontvangende EDC afdwingt per klasse; het HITL-moment als planproces-moment (opwaardering ná bestuurlijk overleg = menselijke stap).
6. Notities: enforcement bij de EDC wanneer live; matrix is voorstel per bron zonder code-wijziging aanpasbaar; gaten-kolom voedt de databronnen-mijlpaal.

- [ ] **Step 4: nldt/13-notitie** — in de accessClass-tabel-sectie van `nldt/13-data-lake-and-space.md` onderaan toevoegen:

```markdown
Usage policies zijn sinds oktober 2026 echte ODRL 2.2-sets
([`schemas/dataspace-policies.json`](schemas/dataspace-policies.json), één per
accessClass) en worden geëmbed in offers én meegeleverd in EDC-manifests —
zie [`26-odrl-usage-policies.md`](26-odrl-usage-policies.md) voor de
worked example op het Utrechtse planproces.
```

- [ ] **Step 5: Eindverificatie + commit + push**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q   # verwacht: 401 passed (391 + 6 T1 + 2 T2 + 2 T3)
cd ../poc && ../nldt/.venv/bin/python -m pytest tests -q                          # 304 passed, 1 skipped (raakveld ongewijzigd)
cd .. && git add nldt/26-odrl-usage-policies.md nldt/13-data-lake-and-space.md && git commit -m "docs(nldt): 26-odrl-usage-policies — datastoffering planproces + live-publicatiegolf Utrecht (15 offers)" && git push origin main
```

Bij afwijkende suite-tellers: alles groen is de eis; exacte telling in het rapport benoemen.
