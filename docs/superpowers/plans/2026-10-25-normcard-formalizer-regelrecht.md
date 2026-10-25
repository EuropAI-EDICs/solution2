# NormCard & Norm Formalizer → RegelRecht NDD v0.8.11 — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Herijk NormCards en de Norm Formalizer zodat RegelRecht-`execution` (NDD schema v0.8.11) de source of truth is, zone-velden dual-write via deterministische projectie blijven werken, en full_export/demo/deep-agents synchroon lopen met `NederlandseDigitaleDienst/regelrecht`.

**Architecture:** Pin v0.8.11 lokaal + sync-gate. NormCard krijgt RR-artikelfiguren (`number`/`text`/`url`). Formalizer-templates author’t `execution` + `zoneBinding`; `zone_projector` vult `zoneSelector`/`conditions`/…. full_export leest `execution` rechtstreeks (geen FormalRule→MR-omweg). Spec: `docs/superpowers/specs/2026-10-25-normcard-formalizer-regelrecht-design.md`.

**Tech Stack:** Python 3 (`nldt/.venv` of `poc` test-venv), `jsonschema`, `pyyaml`, unittest; bestaande zone-engine ongewijzigd als consumer van geprojecteerde velden.

## Global Constraints

- Upstream: `https://github.com/NederlandseDigitaleDienst/regelrecht` — pin **v0.8.11** (niet `schema/latest` in runtime).
- `execution` = SoT; zone-velden alleen via `zone_projector`; nooit handmatig authoren in templates na cutover.
- Dual-write blijft in FormalRule-JSON tot consumers cutoveren; equivalentie-gate is hard.
- Python via `nldt/.venv/bin/python` waar mogelijk; poc-tests: `cd poc && ../nldt/.venv/bin/python -m unittest …` of project-conventie.
- Commits: `feat(poc): …` / `feat(nldt): …` / `feat(deep-agents): …` / `test(…): …` / `docs(…): …`.
- Geen upstream PR naar NDD-corpus; geen live Rust-engine in PoC-pipeline.
- poc-nspd schemas buiten scope (bewust afwijkend); wel `poc/schemas` én spiegel `nldt/schemas/poc/` byte-gelijk houden.
- MinBZK-URLs verdwijnen uit actieve paden.

---

## File map

| Path | Responsibility |
|---|---|
| `nldt/simulation/regelrecht/schema/regelrecht-v0.8.11.schema.json` | vastgepinde NDD-schema-kopie |
| `nldt/simulation/regelrecht/schema/README.md` | pin-metadata + sha256 |
| `nldt/simulation/regelrecht/schema/pin.json` | `{version, sourceUrl, sha256, pinnedAt}` |
| `nldt/simulation/regelrecht/sync_regelrecht_schema.py` | download/compare/update pin |
| `poc/pipeline/zone_projector.py` | execution+zoneBinding → zoneSelector/conditions/… |
| `poc/pipeline/rr_ops.py` | RR↔PoC operator maps (enums uit pin) |
| `poc/schemas/norm-card.schema.json` | RR-artikelkern + PoC-velden |
| `poc/schemas/formal-rule.schema.json` | execution SoT + dual-write zone |
| `nldt/schemas/poc/*.schema.json` | spiegel van poc/schemas |
| `poc/pipeline/contracts.py` | NormCard/FormalRule dataclasses |
| `poc/pipeline/agents.py` | NormAnalyst number/text/url; NormFormalizer execution-path |
| `poc/tracks/_templates/*.json` | execution + zoneBinding i.p.v. zone/conditions |
| `poc/corpus/normcards-*.json`, `formalrules-*.json` | regeneratie via `python -m pipeline.agents` |
| `nldt/simulation/regelrecht/full_export/formalize_to_rr.py` | lees `rule["execution"]` (+ endpoint metadata) |
| `nldt/simulation/regelrecht/full_export/write_instrument_yaml.py` | `$schema` → v0.8.11 |
| `docs/examples/regelrecht/*.yaml` | `$schema`-URL NDD v0.8.11 |
| `deep-agents/prompts/roles/{normspecialist,formalizer}.md` | RR-contracten |
| `deep-agents/tools/{norms,formalize}.py` | schema-gates + projectie-check |
| `deep-agents/harnessregister.json` | sha’s prompts |
| `docs/POC_REGELRECHT_INTEGRATION.md` e.a. | NDD-links + versie |

---

### Task 1: Schema-pin v0.8.11 + sync-script

**Files:**
- Create: `nldt/simulation/regelrecht/schema/regelrecht-v0.8.11.schema.json`
- Create: `nldt/simulation/regelrecht/schema/pin.json`
- Modify: `nldt/simulation/regelrecht/schema/README.md`
- Create: `nldt/simulation/regelrecht/sync_regelrecht_schema.py`
- Create: `nldt/tests/test_regelrecht_schema_pin.py`
- Modify: `nldt/simulation/regelrecht/build_runs.py` (pad naar v0.8.11)
- Modify: `nldt/simulation/regelrecht/full_export/write_instrument_yaml.py` (SCHEMA_PATH + URL)

**Interfaces:**
- Consumes: NDD raw URL `https://raw.githubusercontent.com/NederlandseDigitaleDienst/regelrecht/main/schema/v0.8.11/schema.json`
- Produces: `pin.json` met `version: "v0.8.11"`, `sha256: str`, `sourceUrl: str`, `pinnedAt: str`; `sync_regelrecht_schema.main(argv) -> int` (0=ok, 1=drift tenzij `--update`)

- [ ] **Step 1: Schrijf falende pin-test**

```python
# nldt/tests/test_regelrecht_schema_pin.py
from __future__ import annotations
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "nldt/simulation/regelrecht/schema"
PIN = SCHEMA_DIR / "pin.json"
SCHEMA = SCHEMA_DIR / "regelrecht-v0.8.11.schema.json"

class SchemaPinTests(unittest.TestCase):
    def test_pin_matches_local_bytes(self):
        pin = json.loads(PIN.read_text(encoding="utf-8"))
        self.assertEqual(pin["version"], "v0.8.11")
        digest = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
        self.assertEqual(pin["sha256"], digest)
        self.assertIn("NederlandseDigitaleDienst/regelrecht", pin["sourceUrl"])
        self.assertIn("v0.8.11", pin["sourceUrl"])

    def test_schema_title_is_v0811(self):
        doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertIn("0.8.11", doc.get("title", ""))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test — expect FAIL (bestand ontbreekt)**

Run: `nldt/.venv/bin/python -m unittest nldt.tests.test_regelrecht_schema_pin -v`  
Expected: FAIL / FileNotFoundError op `pin.json` of schema

- [ ] **Step 3: Download pin + sync-script**

```bash
curl -fsSL \
  "https://raw.githubusercontent.com/NederlandseDigitaleDienst/regelrecht/main/schema/v0.8.11/schema.json" \
  -o nldt/simulation/regelrecht/schema/regelrecht-v0.8.11.schema.json
python3 - <<'PY'
import hashlib, json, datetime
from pathlib import Path
p = Path("nldt/simulation/regelrecht/schema/regelrecht-v0.8.11.schema.json")
sha = hashlib.sha256(p.read_bytes()).hexdigest()
pin = {
  "version": "v0.8.11",
  "sourceUrl": "https://raw.githubusercontent.com/NederlandseDigitaleDienst/regelrecht/main/schema/v0.8.11/schema.json",
  "sha256": sha,
  "pinnedAt": datetime.date.today().isoformat(),
}
Path("nldt/simulation/regelrecht/schema/pin.json").write_text(
    json.dumps(pin, indent=2) + "\n", encoding="utf-8")
print(sha)
PY
```

Schrijf `sync_regelrecht_schema.py`:

```python
#!/usr/bin/env python3
"""Vergelijk of update de vastgepinde RegelRecht-schema-pin (NDD)."""
from __future__ import annotations
import argparse, hashlib, json, sys, urllib.request
from pathlib import Path

DIR = Path(__file__).resolve().parent / "schema"
PIN_PATH = DIR / "pin.json"
DEFAULT_VERSION = "v0.8.11"

def _url(version: str) -> str:
    return (
        "https://raw.githubusercontent.com/NederlandseDigitaleDienst/regelrecht/"
        f"main/schema/{version}/schema.json"
    )

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=DEFAULT_VERSION)
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--allow-drift", action="store_true")
    args = ap.parse_args(argv)
    url = _url(args.version)
    with urllib.request.urlopen(url, timeout=60) as resp:
        remote = resp.read()
    remote_sha = hashlib.sha256(remote).hexdigest()
    local_path = DIR / f"regelrecht-{args.version}.schema.json"
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8")) if PIN_PATH.exists() else {}
    if args.update:
        local_path.write_bytes(remote)
        pin = {
            "version": args.version,
            "sourceUrl": url,
            "sha256": remote_sha,
            "pinnedAt": __import__("datetime").date.today().isoformat(),
        }
        PIN_PATH.write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8")
        print(f"updated pin {args.version} sha256={remote_sha}")
        return 0
    local_sha = hashlib.sha256(local_path.read_bytes()).hexdigest()
    if local_sha != pin.get("sha256") or remote_sha != pin.get("sha256"):
        print(f"DRIFT local={local_sha} pin={pin.get('sha256')} remote={remote_sha}", file=sys.stderr)
        return 0 if args.allow_drift else 1
    print("ok", pin["version"], pin["sha256"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

Update README:

```markdown
# Vastgepinde schema's

`regelrecht-v0.8.11.schema.json` — byte-identieke kopie van
https://raw.githubusercontent.com/NederlandseDigitaleDienst/regelrecht/main/schema/v0.8.11/schema.json
(EUPL-1.2, Nederlandse Digitale Dienst). Metadata: `pin.json`.

Sync: `nldt/.venv/bin/python nldt/simulation/regelrecht/sync_regelrecht_schema.py`
Update pin: `… sync_regelrecht_schema.py --update`.

Historisch: `regelrecht-v0.7.1.schema.json` (MinBZK-tijdperk) mag blijven tot alle
consumers zijn omgezet; nieuwe builds gebruiken alleen v0.8.11.
```

In `build_runs.py` en `write_instrument_yaml.py`: vervang pad/`$schema`-URL door v0.8.11 + NDD host.

- [ ] **Step 4: Run pin-test — expect PASS**

Run: `nldt/.venv/bin/python -m unittest nldt.tests.test_regelrecht_schema_pin -v`  
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/regelrecht/schema/ nldt/simulation/regelrecht/sync_regelrecht_schema.py \
  nldt/tests/test_regelrecht_schema_pin.py nldt/simulation/regelrecht/build_runs.py \
  nldt/simulation/regelrecht/full_export/write_instrument_yaml.py
git commit -m "$(cat <<'EOF'
feat(nldt): pin RegelRecht schema v0.8.11 from NDD upstream

Replace MinBZK v0.7.1 runtime pin with NederlandseDigitaleDienst/regelrecht
v0.8.11 plus sha256 drift gate.
EOF
)"
```

---

### Task 2: `rr_ops` + `zone_projector` (TDD)

**Files:**
- Create: `poc/pipeline/rr_ops.py`
- Create: `poc/pipeline/zone_projector.py`
- Create: `poc/tests/test_zone_projector.py`

**Interfaces:**
- Consumes: FormalRule-`execution` dict + `zoneBinding` dict
- Produces:
  - `RR_TO_POC_OP: dict[str,str]` (`LESS_THAN_OR_EQUAL`→`<=`, …)
  - `POC_TO_RR_OP: dict[str,str]` (inverse)
  - `project_zone(execution: dict, zone_binding: dict | None, *, zone_semantics: str, rule_type: str) -> dict`  
    returns `{"zoneSelector": dict|None, "conditions": list, "zoneSemantics": str, "ruleType": str}`  
  - Raises `ProjectionError` bij onbekende operatie of geo-input zonder binding

- [ ] **Step 1: Falende tests (golden art. 5.3)**

```python
# poc/tests/test_zone_projector.py
from __future__ import annotations
import unittest
from pipeline.zone_projector import ProjectionError, project_zone

EXEC_53 = {
    "produces": {"legal_character": "TOETS"},
    "parameters": [
        {"name": "ashoogte_m", "type": "number", "description": "As m"},
        {"name": "op_of_in_aansluiting_op_bestaand_bouwperceel", "type": "boolean", "description": "bouwperceel"},
    ],
    "input": [
        {
            "name": "in_gebied_kleine_windturbine",
            "type": "boolean",
            "description": "Geo-feit",
            "source": {"description": "buiten wet-YAML"},
        }
    ],
    "output": [{"name": "toegestaan_kleine_windturbine", "type": "boolean", "description": "uitkomst"}],
    "actions": [{
        "output": "toegestaan_kleine_windturbine",
        "value": {
            "operation": "AND",
            "conditions": [
                {"operation": "LESS_THAN_OR_EQUAL", "subject": "$ashoogte_m", "value": 20},
                {"operation": "EQUALS", "subject": "$op_of_in_aansluiting_op_bestaand_bouwperceel", "value": True},
                {"operation": "EQUALS", "subject": "$in_gebied_kleine_windturbine", "value": True},
            ],
        },
    }],
}

BINDING_53 = {
    "inputs": {
        "in_gebied_kleine_windturbine": {
            "zoneIds": ["gebied_kleine_windturbine"],
            "selection": "within",
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822",
            "caveat": "GIO uit Bijlage II CVDR704250",
        }
    }
}

class ZoneProjectorTests(unittest.TestCase):
    def test_art53_projects_zone_and_conditions(self):
        out = project_zone(EXEC_53, BINDING_53, zone_semantics="inclusion", rule_type="zone_inclusion")
        self.assertEqual(out["zoneSelector"]["zoneIds"], ["gebied_kleine_windturbine"])
        self.assertEqual(out["zoneSelector"]["selection"], "within")
        params = {c["parameter"]: c for c in out["conditions"]}
        self.assertEqual(params["ashoogte_m"]["operator"], "<=")
        self.assertEqual(params["ashoogte_m"]["value"], 20)
        self.assertEqual(params["op_of_in_aansluiting_op_bestaand_bouwperceel"]["value"], True)
        self.assertNotIn("in_gebied_kleine_windturbine", params)  # geo zit in zoneSelector

    def test_missing_binding_raises(self):
        with self.assertRaises(ProjectionError):
            project_zone(EXEC_53, None, zone_semantics="inclusion", rule_type="zone_inclusion")

    def test_unknown_operation_raises(self):
        bad = {"actions": [{"output": "x", "value": {"operation": "NOT_A_REAL_OP", "subject": "$a", "value": 1}}],
               "parameters": [{"name": "a", "type": "number"}], "input": [], "output": [{"name": "x", "type": "boolean"}]}
        with self.assertRaises(ProjectionError):
            project_zone(bad, {}, zone_semantics="none", rule_type="procedural_condition")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — expect FAIL (import error)**

Run: `cd poc && ../nldt/.venv/bin/python -m unittest tests.test_zone_projector -v`  
Expected: ModuleNotFoundError / FAIL

- [ ] **Step 3: Implementeer `rr_ops.py` + `zone_projector.py`**

```python
# poc/pipeline/rr_ops.py
"""Operator maps between RegelRecht execution ops and PoC FormalRule conditions."""
from __future__ import annotations

RR_TO_POC_OP = {
    "LESS_THAN_OR_EQUAL": "<=",
    "GREATER_THAN_OR_EQUAL": ">=",
    "LESS_THAN": "<",
    "GREATER_THAN": ">",
    "EQUALS": "==",
    "NOT_EQUALS": "!=",
}
POC_TO_RR_OP = {v: k for k, v in RR_TO_POC_OP.items()}
```

```python
# poc/pipeline/zone_projector.py
"""Project RegelRecht execution (+ zoneBinding) into PoC zoneSelector/conditions."""
from __future__ import annotations
from typing import Any
from pipeline.rr_ops import RR_TO_POC_OP

class ProjectionError(ValueError):
    pass

def _walk_conditions(node: Any) -> list[dict]:
    if not isinstance(node, dict):
        return []
    op = node.get("operation")
    if op == "AND":
        out: list[dict] = []
        for c in node.get("conditions") or []:
            out.extend(_walk_conditions(c))
        return out
    if op in RR_TO_POC_OP:
        subject = str(node.get("subject") or "")
        if not subject.startswith("$"):
            raise ProjectionError(f"subject must be $ref, got {subject!r}")
        return [{"parameter": subject[1:], "operator": RR_TO_POC_OP[op], "value": node.get("value")}]
    if op:
        raise ProjectionError(f"unsupported operation {op!r}")
    return []

def project_zone(
    execution: dict,
    zone_binding: dict | None,
    *,
    zone_semantics: str,
    rule_type: str,
) -> dict:
    actions = execution.get("actions") or []
    if not actions:
        raise ProjectionError("execution.actions empty")
    leafs: list[dict] = []
    for act in actions:
        leafs.extend(_walk_conditions(act.get("value") or act))

    geo_names = {i["name"] for i in (execution.get("input") or []) if i.get("type") == "boolean"}
    binding_inputs = (zone_binding or {}).get("inputs") or {}
    for name in geo_names:
        if name not in binding_inputs:
            raise ProjectionError(f"geo input {name!r} missing from zoneBinding.inputs")

    conditions = []
    for leaf in leafs:
        if leaf["parameter"] in geo_names:
            continue  # encoded in zoneSelector
        conditions.append(leaf)

    zone_selector = None
    if geo_names:
        # one primary geo input for v1 (AND of equals-true already filtered)
        primary = sorted(geo_names)[0]
        zb = binding_inputs[primary]
        zone_selector = {
            "zoneIds": list(zb["zoneIds"]),
            "selection": zb.get("selection", "within"),
            "geometrySource": zb["geometrySource"],
        }
        for k in ("gioJoinId", "bufferDistanceM", "derivedFrom", "caveat"):
            if zb.get(k) is not None:
                zone_selector[k] = zb[k]

    return {
        "zoneSelector": zone_selector,
        "conditions": conditions,
        "zoneSemantics": zone_semantics,
        "ruleType": rule_type,
    }
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd poc && ../nldt/.venv/bin/python -m unittest tests.test_zone_projector -v`  
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add poc/pipeline/rr_ops.py poc/pipeline/zone_projector.py poc/tests/test_zone_projector.py
git commit -m "$(cat <<'EOF'
feat(poc): add RegelRecht execution→zone projector

Deterministic dual-write helper so FormalRule.execution stays source of truth
while zone-engine consumers keep zoneSelector/conditions.
EOF
)"
```

---

### Task 3: Schemas + contracts (NormCard artikelkern, FormalRule execution)

**Files:**
- Modify: `poc/schemas/norm-card.schema.json`
- Modify: `poc/schemas/formal-rule.schema.json`
- Modify: `nldt/schemas/poc/norm-card.schema.json` (kopieer byte-gelijk)
- Modify: `nldt/schemas/poc/formal-rule.schema.json` (kopieer byte-gelijk)
- Modify: `poc/pipeline/contracts.py`
- Modify: `poc/tests/test_contracts.py` (assertions op nieuwe velden)

**Interfaces:**
- NormCard required += `number`, `text`, `url` (RR-artikelkern); behoud `source` cite-blok
- FormalRule: bij `status=formalized` required += `execution`; optional `zoneBinding`; `zoneSelector`/`conditions` blijven required via allOf formalized (dual-write)
- `execution` additionalProperties: valideer structureel in PoC-schema (parameters/input/output/actions aanwezig); diepere op-enums via projector/tests + optioneel jsonschema $ref naar pin later

- [ ] **Step 1: Pas schemas aan**

In `norm-card.schema.json` `required` uitbreiden met `"number", "text", "url"`:

```json
"number": { "type": "string", "minLength": 1, "description": "Artikelnummer zoals in de wet (RegelRecht articles[].number)" },
"text": { "type": "string", "minLength": 20, "description": "Verbatim artikeltekst / quote (RegelRecht articles[].text)" },
"url": { "type": "string", "pattern": "^https?://\\S+$", "description": "Artikel- of instrument-URI (RegelRecht articles[].url)" }
```

In `formal-rule.schema.json` properties toevoegen:

```json
"execution": {
  "type": "object",
  "additionalProperties": true,
  "required": ["output", "actions"],
  "properties": {
    "produces": { "type": "object" },
    "parameters": { "type": "array" },
    "input": { "type": "array" },
    "output": { "type": "array", "minItems": 1 },
    "actions": { "type": "array", "minItems": 1 }
  }
},
"zoneBinding": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "inputs": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["zoneIds", "geometrySource"],
        "properties": {
          "zoneIds": { "type": "array", "minItems": 1, "items": { "type": "string" } },
          "selection": { "enum": ["within", "outside"] },
          "geometrySource": { "type": "string" },
          "gioJoinId": { "type": "string" },
          "bufferDistanceM": { "type": "number" },
          "derivedFrom": { "type": "string" },
          "caveat": { "type": "string" }
        }
      }
    }
  }
}
```

AllOf formalized: `required` uitbreiden met `"execution"` (naast bestaande zoneSelector/conditions).

Spiegel naar `nldt/schemas/poc/`.

- [ ] **Step 2: Update dataclasses**

```python
# contracts.py — NormCard fields toevoegen
number: str
text: str
url: str

# FormalRule
execution: Optional[Dict[str, Any]] = None
zoneBinding: Optional[Dict[str, Any]] = None
```

Zorg dat `to_dict`/`from_dict` dict-velden doorgeven (`execution`/`zoneBinding` als plain dict, niet nested dataclass).

- [ ] **Step 3: NormAnalyst vult number/text/url**

In `_to_card`:

```python
import re
_ART_NUM = re.compile(r"(\d+(?:\.\d+)*)")

def _article_number(article: str) -> str:
    m = _ART_NUM.search(article or "")
    return m.group(1) if m else (article or "").strip()

# in card_payload:
"number": _article_number(ev.get("article", "")),
"text": ev.get("quote_nl"),
"url": ev.get("url") or src.get("url"),
```

- [ ] **Step 4: Run contract-tests (nog rood tot corpus-regeneratie — tijdelijk skip of verwacht fail)**

Run: `cd poc && ../nldt/.venv/bin/python -m unittest tests.test_contracts.NormCardCorpusTests -v`  
Expected: FAIL op ontbrekende number/text/url in corpus — dat is input voor Task 5–6.

- [ ] **Step 5: Commit schemas + contracts + analyst (nog zonder volle corpus-regen)**

```bash
git add poc/schemas/nldt/schemas/poc/ poc/pipeline/contracts.py poc/pipeline/agents.py
# note: nldt/schemas/poc paths
git add poc/schemas nldt/schemas/poc poc/pipeline/contracts.py poc/pipeline/agents.py
git commit -m "$(cat <<'EOF'
feat(poc): align NormCard/FormalRule schemas with RegelRecht article+execution

NormCards carry number/text/url; formalized FormalRules require execution as SoT
with zoneBinding for dual-write projection.
EOF
)"
```

---

### Task 4: NormFormalizer execution-path + W-03 template

**Files:**
- Modify: `poc/pipeline/agents.py` (`NormFormalizer`, `_base_rule`)
- Modify: `poc/tracks/_templates/wind.json` (W-03 e.a. formalized kinds)
- Create: `poc/tests/test_formalizer_execution.py`

**Interfaces:**
- Template kind `inclusion|exclusion|…` bij formalized: velden `execution`, `zoneBinding`, `zone_semantics`/`rule_type`/`executable_ref`/`rationale` (geen handmatige `zone`/`conditions`)
- `_formalize_card`: na template-hit → `project_zone` → `_base_rule(..., execution=..., zoneBinding=..., zone_selector=..., conditions=...)`
- Equivalentie: opnieuw `project_zone` en vergelijk met opgeslagen zone (assert in formalizer `_check_integrity`)

- [ ] **Step 1: Falende test W-03 execution roundtrip**

```python
# poc/tests/test_formalizer_execution.py
from __future__ import annotations
import unittest
from pipeline.agents import NormAnalyst, NormFormalizer
from pipeline.zone_projector import project_zone
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "corpus"

class FormalizerExecutionTests(unittest.TestCase):
    def test_w03_execution_is_sot_and_projects(self):
        cards = NormAnalyst().read(CORPUS / "evidence-wind.json")
        by_id = {c.id: c for c in cards}
        self.assertIn("NC-W-03", by_id)
        rules = NormFormalizer().formalize([by_id["NC-W-03"]])
        rule = rules[0].to_dict()
        self.assertEqual(rule["status"], "formalized")
        self.assertIn("execution", rule)
        self.assertIn("zoneBinding", rule)
        projected = project_zone(
            rule["execution"], rule["zoneBinding"],
            zone_semantics=rule["zoneSemantics"], rule_type=rule["ruleType"],
        )
        self.assertEqual(projected["zoneSelector"], rule["zoneSelector"])
        self.assertEqual(projected["conditions"], rule["conditions"])
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Herschrijf W-03 template + formalizer-pad**

W-03 in `wind.json`:

```json
"W-03": {
  "kind": "inclusion",
  "rule_type": "zone_inclusion",
  "zone_semantics": "inclusion",
  "executable_ref": "engine.zone.within@poc-v1",
  "extra_tags": ["inclusion_zone_gebied_kleine_windturbine", "ashoogte_le_20m", "on_or_adjacent_to_existing_building_plot"],
  "rationale": "Art. 5.3 lid 1 — execution SoT (RegelRecht); zone dual-write via projector.",
  "execution": {
    "produces": {"legal_character": "TOETS"},
    "parameters": [
      {"name": "ashoogte_m", "type": "number", "description": "As van de voorgestelde windturbine, in meters."},
      {"name": "op_of_in_aansluiting_op_bestaand_bouwperceel", "type": "boolean", "description": "Op of in aansluiting op bestaand bouwperceel."}
    ],
    "input": [
      {"name": "in_gebied_kleine_windturbine", "type": "boolean", "description": "Geo-feit: binnen Gebied kleine windturbine.",
       "source": {"description": "Buiten wet-YAML; zone-engine / GIO."}}
    ],
    "output": [
      {"name": "toegestaan_kleine_windturbine", "type": "boolean", "description": "Of omgevingsplan hier mag toestaan."}
    ],
    "actions": [{
      "output": "toegestaan_kleine_windturbine",
      "value": {
        "operation": "AND",
        "conditions": [
          {"operation": "LESS_THAN_OR_EQUAL", "subject": "$ashoogte_m", "value": 20},
          {"operation": "EQUALS", "subject": "$op_of_in_aansluiting_op_bestaand_bouwperceel", "value": true},
          {"operation": "EQUALS", "subject": "$in_gebied_kleine_windturbine", "value": true}
        ]
      }
    }]
  },
  "zoneBinding": {
    "inputs": {
      "in_gebied_kleine_windturbine": {
        "zoneIds": ["gebied_kleine_windturbine"],
        "selection": "within",
        "geometrySource": "provincial_gio",
        "gioJoinId": "/join/id/regdata/pv26/2025/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822",
        "caveat": "GIO-versie uit Bijlage II CVDR704250 (geldend 13-10-2025)"
      }
    }
  }
}
```

In `NormFormalizer` voor kinds inclusion/exclusion/attention/conditional/compensation: lees `spec["execution"]` + `spec.get("zoneBinding")`, roep `project_zone` aan, geef resultaat + execution door aan `_base_rule`. Verwijder gebruik van `spec["zone"]` / `spec["conditions"]` voor die kinds.

Breid `_base_rule` uit met `execution=` / `zoneBinding=` kwargs.

LLM-pad (`_llm_rule`): tijdelijk behouden via oude zone-proposal **of** markeer S2 als ambiguous tot aparte follow-up — in deze taak: als llm_hook een zone-proposal geeft zonder execution → status ambiguous met reason `llm proposal lacks execution (RegelRecht SoT)`.

- [ ] **Step 4: Run test_formalizer_execution — expect PASS** (na corpus-card met number/text/url via analyst; evidence-pad leest live)

- [ ] **Step 5: Commit**

```bash
git add poc/pipeline/agents.py poc/tracks/_templates/wind.json poc/tests/test_formalizer_execution.py
git commit -m "$(cat <<'EOF'
feat(poc): NormFormalizer authors RegelRecht execution for wind W-03

Templates carry execution+zoneBinding; projector fills dual-write zone fields.
EOF
)"
```

---

### Task 5: Lift overige formalized templates + corpus regeneratie

**Files:**
- Create: `poc/pipeline/lift_templates_to_execution.py` (eenmalige/herhaalbare helper)
- Modify: `poc/tracks/_templates/*.json` (alle formalized kinds)
- Regenerate: `poc/corpus/normcards-*.json`, `poc/corpus/formalrules-*.json`
- Modify: tests die exacte corpus-bytes verwachten (`tests/test_track_config.py`, track-run tests)

**Interfaces:**
- `lift_template(spec: dict) -> dict`: als spec al `execution` heeft → return; anders bouw execution uit oude `zone`+`conditions` (logica spiegel van oude `formal_rule_to_machine_readable`) + zoneBinding uit zone
- CLI: `python -m pipeline.lift_templates_to_execution --write` herschrijft alle `_templates/*.json`

- [ ] **Step 1: Implementeer lift-helper** (volledige OP_MAP uit Task 2 `POC_TO_RR_OP`; geo-inputnaam `in_{zoneId}`; parameters uit conditions)

- [ ] **Step 2: Run lift --write op alle tracks**

Run: `cd poc && ../nldt/.venv/bin/python -m pipeline.lift_templates_to_execution --write`  
Expected: elk formalized template heeft `execution` + `zoneBinding`; ambiguous/reject ongewijzigd in kind

- [ ] **Step 3: Regenereer corpus**

Run: `cd poc && ../nldt/.venv/bin/python -m pipeline.agents`  
Expected: alle normcards/formalrules herschreven; formalized rules bevatten execution

- [ ] **Step 4: Fix/update byte-gates en unittest-suites**

Run: `cd poc && ../nldt/.venv/bin/python -m unittest tests.test_contracts tests.test_track_config tests.test_zone_projector tests.test_formalizer_execution -v`  
Expected: OK (pas expected counts/bytes aan waar nodig — geen semantiek wijzigen)

- [ ] **Step 5: Commit**

```bash
git add poc/tracks/_templates poc/corpus poc/pipeline/lift_templates_to_execution.py poc/tests
git commit -m "$(cat <<'EOF'
feat(poc): lift all Formalizer templates to RegelRecht execution SoT

Regenerate Utrecht normcard/formalrule corpora with dual-write zone projection.
EOF
)"
```

---

### Task 6: full_export + examples + demo op execution + v0.8.11

**Files:**
- Modify: `nldt/simulation/regelrecht/full_export/formalize_to_rr.py`
- Modify: `docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml` (`$schema` URL)
- Modify: `docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml`
- Rebuild: `nldt/simulation/regelrecht/full_export/out/*` via `build_all.py`
- Modify: demo template strings v0.7.1 → v0.8.11
- Modify: `nldt/tests/test_simulation_regelrecht.py`, `test_simulation_regelrecht_full.py`

**Interfaces:**
- `formal_rule_to_machine_readable(rule, article)`: als `rule.get("execution")`: return `{endpoint, competent_authority, execution: rule["execution"]}` (endpoint uit template metadata of `art_{number}`; competent_authority default CATEGORY); **geen** conditions→actions mapping meer voor SoT-pad
- Smoke FR-W-03: mag nog smoke-YAML laden **zolang** execution in rule ≡ smoke execution (assert); liever rule.execution gebruiken en smoke YAML synchroon houden

- [ ] **Step 1: Pas `formal_rule_to_machine_readable` aan**

```python
def formal_rule_to_machine_readable(rule: dict, article: Article) -> dict:
    if rule.get("status") != "formalized":
        raise ValueError(f"rule {rule.get('id')} is not formalized")
    execution = rule.get("execution")
    if not execution:
        raise ValueError(f"rule {rule.get('id')} missing execution (RegelRecht SoT)")
    endpoint = (rule.get("rrEndpoint")
                or f"art_{article['number'].replace('.', '_')}")
    return {
        "endpoint": endpoint,
        "competent_authority": rule.get("competentAuthority")
            or {"name": "Bevoegd gezag", "type": "CATEGORY"},
        "execution": execution,
    }
```

Optioneel: templates mogen `rrEndpoint` / `competentAuthority` meedragen; W-03 endpoint `kleine_windturbine_bestaand_bouwperceel` via template-veld zetten zodat golden demo gelijk blijft.

- [ ] **Step 2: Bump example YAML `$schema` naar NDD v0.8.11; valideer**

```bash
nldt/.venv/bin/python - <<'PY'
import json, yaml, pathlib
from jsonschema import Draft7Validator
schema = json.loads(pathlib.Path("nldt/simulation/regelrecht/schema/regelrecht-v0.8.11.schema.json").read_text())
v = Draft7Validator(schema)
for p in pathlib.Path("docs/examples/regelrecht").glob("*.yaml"):
    doc = yaml.safe_load(p.read_text())
    errs = sorted(v.iter_errors(doc), key=str)
    print(p.name, "OK" if not errs else errs[0].message)
PY
```

Expected: OK (pas YAML aan bij v0.8.11 breaking changes)

- [ ] **Step 3: Rebuild full export + runs**

```bash
nldt/.venv/bin/python nldt/simulation/regelrecht/full_export/build_all.py --stamp 2026-10-25T12:00:00Z
# + build_runs indien nodig voor demo
```

- [ ] **Step 4: Tests**

Run: `nldt/.venv/bin/python -m unittest nldt.tests.test_simulation_regelrecht nldt.tests.test_simulation_regelrecht_full -v`  
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/regelrecht docs/examples/regelrecht nldt/tests
git commit -m "$(cat <<'EOF'
feat(nldt): full_export reads FormalRule.execution under RegelRecht v0.8.11

Drop reverse FormalRule→actions mapping as SoT path; sync examples and demo.
EOF
)"
```

---

### Task 7: deep-agents prompts/tools + harnessregister

**Files:**
- Modify: `deep-agents/prompts/roles/normspecialist.md`
- Modify: `deep-agents/prompts/roles/formalizer.md`
- Modify: `deep-agents/tools/formalize.py`
- Modify: `deep-agents/tools/norms.py` (toon number/text in search hits)
- Modify: `deep-agents/harnessregister.json` (sha256 van gewijzigde prompts)
- Modify/extend: `deep-agents/tests/test_harnessregister.py` indien nodig

**Interfaces:**
- `validate_formal_rule`: na jsonschema-pass, als status formalized → `project_zone` en vergelijk; fail met errors als mismatch of ontbrekende execution
- Prompts: verbied handmatige zoneSelector; verplicht execution + zoneBinding

- [ ] **Step 1: Update formalizer.md** (kernregels)

```markdown
Draft FormalRule with RegelRecht `execution` as source of truth (parameters/input/output/actions).
Provide `zoneBinding` for geo inputs. Do NOT hand-author zoneSelector/conditions —
the schema gate projects them. Calibrate on rejected corpus rules.
```

- [ ] **Step 2: Gate in `validate_formal_rule`**

```python
from pipeline.zone_projector import ProjectionError, project_zone  # via sys.path naar poc

# after schema validate, if rule.get("status") == "formalized":
try:
    proj = project_zone(rule["execution"], rule.get("zoneBinding"),
                        zone_semantics=rule["zoneSemantics"], rule_type=rule["ruleType"])
except (ProjectionError, KeyError) as exc:
    return {"passed": False, "errors": [str(exc)], "ruleId": rule.get("id")}
if proj["zoneSelector"] != rule.get("zoneSelector") or proj["conditions"] != rule.get("conditions"):
    return {"passed": False, "errors": ["zone fields must equal zone_projector(execution)"], "ruleId": rule.get("id")}
```

(Zorg dat deep-agents `poc` op `sys.path` heeft — zelfde patroon als andere poc-imports in die package.)

- [ ] **Step 3: Update harnessregister sha’s**

```bash
cd deep-agents && python3 - <<'PY'
import hashlib, json, pathlib
reg = json.loads(pathlib.Path("harnessregister.json").read_text())
for h in reg["harnesses"]:
    art = h.get("artifact") or {}
    if art.get("kind") == "promptFile" and art.get("path", "").endswith(("formalizer.md", "normspecialist.md")):
        data = pathlib.Path(art["path"]).read_bytes()
        art["sha256"] = hashlib.sha256(data).hexdigest()
pathlib.Path("harnessregister.json").write_text(json.dumps(reg, indent=2) + "\n")
PY
```

- [ ] **Step 4: Run offline tests**

Run: `cd deep-agents && ../nldt/.venv/bin/python -m unittest tests.test_harnessregister -v` (+ eventuele formalize-tests)  
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add deep-agents/prompts/roles/formalizer.md deep-agents/prompts/roles/normspecialist.md \
  deep-agents/tools deep-agents/harnessregister.json
git commit -m "$(cat <<'EOF'
feat(deep-agents): formalizer/normspecialist follow RegelRecht execution SoT

Schema gate projects zone fields; harnessregister pin hashes updated.
EOF
)"
```

---

### Task 8: Docs-sync (MinBZK → NDD) + acceptatiegate

**Files:**
- Modify: `docs/POC_REGELRECHT_INTEGRATION.md`
- Modify: `nldt/simulation/README.md`, `docs/superpowers/specs/2026-10-14-regelrecht-full-instrument-export-design.md` (pointer/versie-noot)
- Modify: overige actieve refs gevonden via ripgrep `MinBZK/regelrecht` in docs/nldt (niet per se historische plans herschrijven — wel actieve README’s)

- [ ] **Step 1: rg en vervang actieve links**

```bash
rg -n 'MinBZK/regelrecht|v0\.7\.1' docs/POC_REGELRECHT_INTEGRATION.md nldt/simulation/README.md \
  nldt/simulation/regelrecht/schema/README.md docs/examples/regelrecht || true
```

Update integratiedoc: upstream NDD, schema v0.8.11, NormCard/FormalRule dual-write korte paragraaf + link naar 2026-10-25-spec.

- [ ] **Step 2: Acceptatiechecklist runnen**

```bash
# pin
nldt/.venv/bin/python -m unittest nldt.tests.test_regelrecht_schema_pin -v
# projector + formalizer
cd poc && ../nldt/.venv/bin/python -m unittest tests.test_zone_projector tests.test_formalizer_execution tests.test_contracts tests.test_track_config -v
# regelrecht simulation
cd .. && nldt/.venv/bin/python -m unittest nldt.tests.test_simulation_regelrecht nldt.tests.test_simulation_regelrecht_full -v
# deep-agents
cd deep-agents && ../nldt/.venv/bin/python -m unittest tests.test_harnessregister -v
# geen MinBZK in actieve schema-URLs
rg -n 'MinBZK/regelrecht' docs/examples/regelrecht nldt/simulation/regelrecht/full_export/out/*.yaml || echo 'clean'
```

Expected: alle OK; example/export YAML wijzen naar NDD v0.8.11.

- [ ] **Step 3: Commit docs**

```bash
git add docs/POC_REGELRECHT_INTEGRATION.md nldt/simulation/README.md docs/superpowers/specs/
git commit -m "$(cat <<'EOF'
docs: point RegelRecht integration at NDD v0.8.11 and NormCard herijking

EOF
)"
```

---

## Spec coverage (self-review)

| Spec-eis | Task |
|---|---|
| Pin NDD v0.8.11 + sha sync | Task 1 |
| NormCard ≈ RR artikel (number/text/url) | Task 3–5 |
| FormalRule execution SoT + dual-write zone | Task 2–5 |
| zone_projector + hard fail | Task 2, 4 |
| full_export leest execution; demo/examples v0.8.11 | Task 6 |
| deep-agents prompts/tools/register | Task 7 |
| Docs MinBZK→NDD; acceptatiegates | Task 8 |
| Geen upstream corpus-PR / geen Rust in pipeline | Global Constraints |
| poc-nspd buiten scope | Global Constraints |

Geen TBD’s in taken; W-03 golden expliciet; overige templates via lift-helper i.p.v. “similar to”.
