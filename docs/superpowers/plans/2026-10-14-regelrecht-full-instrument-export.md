# RegelRecht volle-instrument export (Utrecht + Eindhoven) — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exporteer de volledige Omgevingsverordening Utrecht (CVDR704250) en het Omgevingsplan Eindhoven (CVDR696400) als RegelRecht v0.7.1-YAML, formaliseer elk artikel deterministisch waar templates dat toelaten, en breid `regelrecht-demo.html` uit met instrument-browser, coverage en live engine alleen bij `machine_readable`.

**Architecture:** Pipeline `ArticleSplitter → EvidenceAligner → FormalizerPass → RegelRechtWriter → DemoBuilder` onder `nldt/simulation/regelrecht/full_export/`. Eén YAML per instrument. Geo blijft externe input. Bestaande 16 golden cases blijven; plus max 20 formalized demoCases per PoC. Spec: `docs/superpowers/specs/2026-10-14-regelrecht-full-instrument-export-design.md`.

**Tech Stack:** Python 3 (`nldt/.venv`: stdlib + `pyyaml` + `jsonschema`), hergebruik `poc-bp2op/pipeline/parsers.tokenize` / artikel-ankerlogica, bestaande `reference_engine.py` + `mini-engine.js`, plain HTML/CSS demo.

## Global Constraints

- Python via `nldt/.venv/bin/python`; geen netwerk in default-build.
- RegelRecht-schema vastgepind: `nldt/simulation/regelrecht/schema/regelrecht-v0.7.1.schema.json`.
- `poc/` en `poc-bp2op/` alleen-lezen; HTML-bronnen vastgepind (geen live DSO).
- Geen LLM in FormalizerPass; cite-or-abstain zonder template → `ambiguous`.
- UI-demo NL, single-file `file://`, geen fetch.
- Invocatie als script (geen `python -m nldt…` — `nldt` heeft geen package-`__init__`): `nldt/.venv/bin/python nldt/simulation/regelrecht/full_export/build_all.py --stamp <ISO>`.
- Commits: `feat(nldt): …` / `test(nldt): …` / `docs(nldt): …`.
- Bestaande smoke-fixtures `docs/examples/regelrecht/*` niet verwijderen.

---

## File map

| Path | Responsibility |
|---|---|
| `nldt/simulation/regelrecht/full_export/__init__.py` | leeg / versie-string |
| `nldt/simulation/regelrecht/full_export/paths.py` | ROOT, HTML-paden, corpus-paden, OUT-dir |
| `nldt/simulation/regelrecht/full_export/split_cvdr_html.py` | ArticleSplitter |
| `nldt/simulation/regelrecht/full_export/align_evidence.py` | EvidenceAligner |
| `nldt/simulation/regelrecht/full_export/formalize_to_rr.py` | FormalizerPass + FormalRule→actions |
| `nldt/simulation/regelrecht/full_export/write_instrument_yaml.py` | YAML + schema-gate |
| `nldt/simulation/regelrecht/full_export/build_full_demo.py` | demo/template vullen |
| `nldt/simulation/regelrecht/full_export/build_all.py` | CLI-orkestratie `--stamp` |
| `nldt/simulation/regelrecht/full_export/formalization-report.schema.json` | report-contract |
| `nldt/simulation/regelrecht/full_export/out/*` | gegenereerde YAML/JSON (committed na eerste succesvolle build) |
| `nldt/tests/test_simulation_regelrecht_full.py` | nieuwe testsuite |
| `nldt/simulation/regelrecht/regelrecht-demo.template.html` | artikelkiezer + coverage |
| `nldt/simulation/poc-utrecht.html`, `poc-eindhoven.html`, `index.html`, `README.md` | teaser/docs |
| `docs/POC_REGELRECHT_INTEGRATION.md` | pointer naar deze spec |

---

### Task 1: ArticleSplitter + `articles.json`

**Files:**
- Create: `nldt/simulation/regelrecht/full_export/__init__.py`
- Create: `nldt/simulation/regelrecht/full_export/paths.py`
- Create: `nldt/simulation/regelrecht/full_export/split_cvdr_html.py`
- Create: `nldt/tests/test_simulation_regelrecht_full.py`
- Test: `nldt/tests/test_simulation_regelrecht_full.py`

**Interfaces:**
- Consumes: vastgepinde HTML via `paths.HTML_UTRECHT` / `paths.HTML_EINDHOVEN`; hergebruikt tokenizer-logica gelijk aan `poc-bp2op.pipeline.parsers` (`tokenize`, `_ART_ANCHOR_RE`).
- Produces:
  - `Article = TypedDict` met keys `number: str`, `text: str`, `url: str`, `title: str`, `containers: list[dict]` (`kind` ∈ `hoofdstuk|afdeling|paragraaf`, `label: str`)
  - `split_instrument(poc: Literal["utrecht","eindhoven"]) -> list[Article]`
  - `write_articles_json(poc, articles, out_path) -> None` schrijft `{"poc","cvdr","sourceHtml","sourceSha256","articles":[…]}`

- [ ] **Step 1: Schrijf falende tests**

```python
# nldt/tests/test_simulation_regelrecht_full.py
"""Tests volle RegelRecht-instrument-export (spec 2026-10-14)."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FULL = ROOT / "nldt" / "simulation" / "regelrecht" / "full_export"
sys.path.insert(0, str(FULL))

from split_cvdr_html import split_instrument, write_articles_json  # noqa: E402
import paths  # noqa: E402


class TestArticleSplitter(unittest.TestCase):
    def test_utrecht_contains_art_5_3(self):
        arts = split_instrument("utrecht")
        by_num = {a["number"]: a for a in arts}
        self.assertIn("5.3", by_num)
        self.assertIn("kleine windturbine", by_num["5.3"]["text"].lower())
        self.assertGreater(len(arts), 100)

    def test_eindhoven_contains_art_10_2_and_22_1(self):
        arts = split_instrument("eindhoven")
        nums = {a["number"] for a in arts}
        self.assertIn("10.2", nums)
        self.assertIn("22.1", nums)
        self.assertGreater(len(arts), 500)

    def test_articles_json_roundtrip_sha(self):
        arts = split_instrument("utrecht")[:3]
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "u.json"
            write_articles_json("utrecht", arts, out)
            data = json.loads(out.read_text())
            self.assertEqual(data["poc"], "utrecht")
            self.assertEqual(data["sourceSha256"], hashlib.sha256(paths.HTML_UTRECHT.read_bytes()).hexdigest())
            self.assertEqual(len(data["articles"]), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Draai test — moet falen**

Run: `cd /Users/marc/Projecten/ldttoolbox && nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht_full.py -v`
Expected: `ModuleNotFoundError: No module named 'split_cvdr_html'`

- [ ] **Step 3: Implementeer `paths.py` + splitter**

```python
# nldt/simulation/regelrecht/full_export/paths.py
from __future__ import annotations
import pathlib

DIR = pathlib.Path(__file__).resolve().parent
ROOT = DIR.parents[3]  # repo root (nldt/simulation/regelrecht/full_export → 4 up)
OUT = DIR / "out"
HTML_UTRECHT = ROOT / "docs/research/sources/cvdr704250-omgevingsverordening-geldend-2025-10-13.html"
HTML_EINDHOVEN = ROOT / "poc-bp2op/corpus/eindhoven/omgevingsplan-eindhoven-cvdr696400-geldend-2026-06-29.html"

INSTRUMENTS = {
    "utrecht": {
        "cvdr": "CVDR704250",
        "versie": 8,
        "html": HTML_UTRECHT,
        "title": "Omgevingsverordening provincie Utrecht",
        "regulatory_layer": "PROVINCIALE_VERORDENING",
        "organisation": "Provincie Utrecht",
        "provincie_code": "PV26",
        "url": "https://lokaleregelgeving.overheid.nl/CVDR704250",
        "valid_from": "2025-10-13",
        "publication_date": "2025-10-13",
    },
    "eindhoven": {
        "cvdr": "CVDR696400",
        "versie": 4,
        "html": HTML_EINDHOVEN,
        "title": "Omgevingsplan gemeente Eindhoven",
        "regulatory_layer": "GEMEENTELIJKE_VERORDENING",
        "organisation": "Gemeente Eindhoven",
        "gemeente_code": "GM0772",
        "url": "https://lokaleregelgeving.overheid.nl/CVDR696400",
        "valid_from": "2026-06-29",
        "publication_date": "2026-06-29",
    },
}
```

In `split_cvdr_html.py`: kopieer `tokenize`, `_ART_ANCHOR_RE`, `_text`, `_hoofdstuk_titel` byte-dicht uit `poc-bp2op/pipeline/parsers.py` (geen runtime-import van `poc-bp2op` — vermijdt package-`__version__`-koppeling). Bouw artikelen zoals `parse_doelregeling`, maar output `Article` i.p.v. DoelRegel. Anker-URL: `{base}/{versie}#{aid}`. Sla `[Gereserveerd]`/`[Vervallen]`-only buffers over of behoud kopregel (zelfde als parser). Dedup op `number`: bij duplicate ankers behoud eerste niet-lege `text`.

`write_articles_json` schrijft UTF-8 JSON met `indent=2` + trailing newline.

- [ ] **Step 4: Draai tests — moeten slagen**

Run: `nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht_full.py -v`
Expected: 3 OK (of meer als alleen deze class).

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/regelrecht/full_export/ nldt/tests/test_simulation_regelrecht_full.py
git commit -m "$(cat <<'EOF'
feat(nldt): ArticleSplitter voor RegelRecht volle-instrument export

EOF
)"
```

---

### Task 2: EvidenceAligner

**Files:**
- Create: `nldt/simulation/regelrecht/full_export/align_evidence.py`
- Modify: `nldt/tests/test_simulation_regelrecht_full.py`
- Modify: `nldt/simulation/regelrecht/full_export/paths.py` (corpus-paden)

**Interfaces:**
- Consumes: `list[Article]`; Utrecht NormCards+FormalRules uit alle tracks; Eindhoven `bronregels.json` / `doelregels.json` / `omzettabel.json` / `kennisbank.json` (canonieke run `20260830-124515-eindhoven`).
- Produces:
  - `Alignment = TypedDict` met `articleNumber`, `normCards: list[dict]`, `formalRules: list[dict]`, `bronRegels: list[dict]`, `doelRegels: list[dict]`, `omzetRows: list[dict]`
  - `align(poc, articles) -> tuple[dict[str, Alignment], list[dict]]`  
    tweede return = `orphanedFormalRules` / orphaned evidence (`id`, `articleHint`, `reason`)
  - Artikelnummer-normalisatie: `"art. 5.3, eerste lid"` / `"Artikel 5.3"` / `"5.3"` → canonieke `"5.3"` via regex `(\d+\.\d+[a-z]?)`

Utrecht evidence-paden (vast in `paths.py`):

```python
UTRECHT_NORMCARD_RUNS = [
    ("wind", ROOT / "poc/runs/20260830T113234Z-wind/normcards.json"),
    ("zon", ROOT / "poc/runs/20260830T142439Z-zon/normcards.json"),
    ("bos", ROOT / "poc/runs/20260830T142446Z-bos/normcards.json"),
    ("water", ROOT / "poc/runs/20261004T185116Z-water/normcards.json"),
    ("bodem", ROOT / "poc/runs/20261004T185509Z-bodem/normcards.json"),
    ("landschap", ROOT / "poc/runs/20261005T070621Z-landschap/normcards.json"),
    ("mobiliteit", ROOT / "poc/runs/20261005T072839Z-mobiliteit/normcards.json"),
    ("landbouw", ROOT / "poc/runs/20261005T094244Z-landbouw/normcards.json"),
    ("wonen", ROOT / "poc/runs/20261005T100258Z-wonen/normcards.json"),
    ("recreatie", ROOT / "poc/runs/20261006T114934Z-recreatie/normcards.json"),
    ("biomassa", ROOT / "poc/runs/20261006T120133Z-biomassa/normcards.json"),
    ("werken", ROOT / "poc/runs/20261006T121921Z-werken/normcards.json"),
    ("energietoets", ROOT / "poc/runs/20261006T171730Z-energietoets/normcards.json"),
]
# FormalRules: corpus wind/zon/bos + per-run formalrules.json waar aanwezig
```

- [ ] **Step 1: Falende tests**

```python
class TestEvidenceAligner(unittest.TestCase):
    def test_utrecht_5_3_links_nc_w_03_and_fr_w_03(self):
        from align_evidence import align
        arts = split_instrument("utrecht")
        by_num, orphans = align("utrecht", arts)
        a = by_num["5.3"]
        nc_ids = {c["id"] for c in a["normCards"]}
        fr_ids = {r["id"] for r in a["formalRules"]}
        self.assertIn("NC-W-03", nc_ids)
        self.assertIn("FR-W-03", fr_ids)

    def test_eindhoven_10_2_links_doelregel(self):
        from align_evidence import align
        arts = split_instrument("eindhoven")
        by_num, _ = align("eindhoven", arts)
        self.assertTrue(any(d.get("locator", {}).get("artikel") == "10.2"
                            for d in by_num["10.2"]["doelRegels"]))

    def test_normalize_article_ref(self):
        from align_evidence import normalize_article_ref
        self.assertEqual(normalize_article_ref("art. 5.3, eerste lid"), "5.3")
        self.assertEqual(normalize_article_ref("Artikel 22.1"), "22.1")
        self.assertIsNone(normalize_article_ref("par. Duurzame energie"))
```

- [ ] **Step 2: Draai — moet falen** (`ModuleNotFoundError: align_evidence`)

- [ ] **Step 3: Implementeer aligner**

Matchregels:
1. NormCard: `normalize_article_ref(card["source"]["article"])`; skip `None` (toelichting/visie-paragrafen) → orphan met reason `non_article_locator`.
2. FormalRule: via `normCardId` → card → article; als card orphan is, FormalRule orphan.
3. Eindhoven bron/doel: `locator["artikel"]`.
4. Omzetrij: via `bronRegelId`/`suggesties[].doelRegelId` (of canonieke velden in omzettabel) koppelen aan beide artikelnummers.
5. Verbatim soft-check (niet hard-fail): als NormCard-quote (whitespace-genorm) niet in `article["text"]`, zet `alignmentNote: "quote_not_in_article_text"` op de card-entry in Alignment ( Critic V2 hard-gate volgt in writer-tests alleen voor formalized).

- [ ] **Step 4: Tests groen**

- [ ] **Step 5: Commit** `feat(nldt): EvidenceAligner voor RegelRecht full export`

---

### Task 3: FormalizerPass + report-schema

**Files:**
- Create: `nldt/simulation/regelrecht/full_export/formalize_to_rr.py`
- Create: `nldt/simulation/regelrecht/full_export/formalization-report.schema.json`
- Modify: `nldt/tests/test_simulation_regelrecht_full.py`

**Interfaces:**
- Consumes: `articles`, `alignments`, bestaande FormalRules.
- Produces:
  - `formalize(poc, articles, alignments) -> tuple[dict[str, ArticleFormalization], dict]`
  - `ArticleFormalization`: `{number, status, reason, machineReadable|None, normCardId?, formalRuleId?, source}`
  - `status ∈ formalized|ambiguous|rejected|unmatched`
  - Report-dict: `{schemaVersion:"1", poc, generatedAt, sourceSha256, counts:{…}, articles:[…], orphanedFormalRules:[…]}`
  - `formal_rule_to_machine_readable(rule: dict, article: Article) -> dict` — pure mapping

**Mapping (exact):**

```python
OP_MAP = {
    "<=": "LESS_THAN_OR_EQUAL",
    ">=": "GREATER_THAN_OR_EQUAL",
    "==": "EQUALS",
    "!=": "NOT_EQUALS",
    "<": "LESS_THAN",
    ">": "GREATER_THAN",
}

def formal_rule_to_machine_readable(rule, article):
    # alleen status == "formalized"
    params = []
    conditions_ops = []
    for c in rule.get("conditions") or []:
        pname = c["parameter"]
        params.append({"name": pname, "type": "number" if isinstance(c.get("value"), (int, float)) and c["operator"] != "==" else _infer_type(c["value"]), "description": pname})
        conditions_ops.append({
            "operation": OP_MAP[c["operator"]],
            "subject": f"${pname}",
            "value": True if c.get("value") == "existing_building_plot" else c["value"],
            # special-case known enum→bool from art 5.3 smoke fixture:
            # location==existing_building_plot → parameter op_of_in_aansluiting_op_bestaand_bouwperceel
        })
    inputs = []
    zs = rule.get("zoneSelector") or {}
    zone_ids = zs.get("zoneIds") or []
    for zid in zone_ids:
        iname = f"in_{zid}"
        inputs.append({
            "name": iname,
            "type": "boolean",
            "description": f"Geo-feit: locatie binnen zone {zid}",
            "source": {"description": f"Buiten wet-YAML; GIO/zone-engine. joinId={zs.get('gioJoinId','')}"},
        })
        if rule.get("zoneSemantics") == "exclusion":
            conditions_ops.append({"operation": "EQUALS", "subject": f"${iname}", "value": False})
        else:
            conditions_ops.append({"operation": "EQUALS", "subject": f"${iname}", "value": True})
    out_name = f"result_{article['number'].replace('.', '_')}"
    value = conditions_ops[0] if len(conditions_ops) == 1 else {"operation": "AND", "conditions": conditions_ops}
    if not conditions_ops:
        # zone-only formalized marker: single zone input equals True
        if inputs:
            value = {"operation": "EQUALS", "subject": f"${inputs[0]['name']}", "value": True}
        else:
            raise ValueError("formalized rule without conditions or zone")
    return {
        "endpoint": f"art_{article['number'].replace('.', '_')}",
        "competent_authority": {"name": "Bevoegd gezag", "type": "CATEGORY"},
        "execution": {
            "produces": {"legal_character": "TOETS"},
            "parameters": params,
            "input": inputs,
            "output": [{"name": out_name, "type": "boolean", "description": f"Uitkomst artikel {article['number']}"}],
            "actions": [{"output": out_name, "value": value}],
        },
    }
```

Special-case **smoke-compatibiliteit art. 5.3**: als `formalRuleId == "FR-W-03"`, gebruik de bestaande `machine_readable` uit `docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml` (byte-gelijke execution) i.p.v. generieke mapping — zodat de 16 golden cases blijven werken.

Special-case **art. 10.2 / OT-001**: hergebruik `machine_readable` uit `docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml` voor nummer `10.2`.

Statuslogica per artikel:
1. Als ≥1 FormalRule `formalized` → `formalized` (kies laagste id stabiel).
2. Elif ≥1 FormalRule `ambiguous` → `ambiguous`.
3. Elif ≥1 FormalRule `rejected` en geen andere → `rejected`.
4. Elif alleen NormCards zonder FR → probeer **template registry** (minimaal: lege registry in v1 behalve smoke special-cases) → anders `unmatched`→ behandel als `ambiguous` met reason `no_template`.
5. Geen evidence → `unmatched` → `ambiguous` / text-only.

Report-schema (`formalization-report.schema.json`): draft 2020-12, required fields zoals Interfaces; `additionalProperties: false` op top-level.

- [ ] **Step 1: Tests**

```python
class TestFormalizer(unittest.TestCase):
    def test_fr_w_03_produces_machine_readable(self):
        from align_evidence import align
        from formalize_to_rr import formalize
        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        by_num, report = formalize("utrecht", arts, al, orphans)
        self.assertEqual(by_num["5.3"]["status"], "formalized")
        self.assertIsNotNone(by_num["5.3"]["machineReadable"])
        self.assertIn("toegestaan_kleine_windturbine",
                      str(by_num["5.3"]["machineReadable"]))

    def test_ambiguous_has_no_mr(self):
        from align_evidence import align
        from formalize_to_rr import formalize
        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        by_num, report = formalize("utrecht", arts, al, orphans)
        # FR-W-04 is ambiguous on 5.3 lid 2 — article 5.3 may still be formalized via FR-W-03;
        # pick a known ambiguous-only article if present, else assert counts
        self.assertGreaterEqual(report["counts"]["ambiguous"] + report["counts"]["unmatched"], 1)

    def test_report_counts_sum_to_articles(self):
        from align_evidence import align
        from formalize_to_rr import formalize
        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        _, report = formalize("utrecht", arts, al, orphans)
        c = report["counts"]
        self.assertEqual(sum(c[k] for k in ("formalized", "ambiguous", "rejected", "unmatched")), len(arts))
```

- [ ] **Step 2–4:** implementeer, schema schrijven, tests groen, commit `feat(nldt): FormalizerPass FormalRule→RegelRecht machine_readable`

---

### Task 4: RegelRechtWriter

**Files:**
- Create: `nldt/simulation/regelrecht/full_export/write_instrument_yaml.py`
- Modify: `nldt/tests/test_simulation_regelrecht_full.py`

**Interfaces:**
- `write_instrument_yaml(poc, articles, formalizations, stamp: str) -> pathlib.Path`  
  schrijft `out/{poc}-cvdr{id}.yaml` en valideert tegen v0.7.1; bij errors `SystemExit` met eerste 5 pad+message.
- Document-shape:

```yaml
$schema: https://raw.githubusercontent.com/MinBZK/regelrecht/refs/heads/main/schema/v0.7.1/schema.json
$id: <slug>
name: <title>
regulatory_layer: …
publication_date: …
valid_from: …
cvdr_id: …          # additionalProperties; bewust meenemen
organisation: …
url: …
articles:
  - number: "1.1"
    text: |
      …
    url: …
    # machine_readable: alleen als status==formalized
```

Voor Utrecht: `provincie_code: PV26`. Voor Eindhoven: `gemeente_code: GM0772` (CBS; verifieer tegen schema enum/pattern — als schema het veld eist of toestaat via additionalProperties: meenemen; als pattern faalt: weglaten en note in report `metaNote`).

- [ ] **Step 1: Tests**

```python
class TestWriter(unittest.TestCase):
    def test_yaml_schema_valid_and_53_has_mr(self):
        import yaml
        from jsonschema import Draft202012Validator
        from align_evidence import align
        from formalize_to_rr import formalize
        from write_instrument_yaml import write_instrument_yaml
        arts = split_instrument("utrecht")
        al, orphans = align("utrecht", arts)
        form, report = formalize("utrecht", arts, al, orphans)
        path = write_instrument_yaml("utrecht", arts, form, stamp="2026-10-14T00:00:00Z")
        doc = yaml.safe_load(path.read_text())
        schema = json.loads((ROOT / "nldt/simulation/regelrecht/schema/regelrecht-v0.7.1.schema.json").read_text())
        Draft202012Validator(schema).validate(doc)
        art53 = next(a for a in doc["articles"] if a["number"] == "5.3")
        self.assertIn("machine_readable", art53)
        ambiguous_nums = {r["number"] for r in report["articles"] if r["status"] == "ambiguous"}
        for a in doc["articles"]:
            if a["number"] in ambiguous_nums:
                self.assertNotIn("machine_readable", a)
```

- [ ] **Step 2–4:** implementeer (PyYAML `safe_dump` met `allow_unicode=True`, `sort_keys=False`), schrijf ook `out/{poc}-formalization-report.json` gevalideerd tegen report-schema, tests groen, commit `feat(nldt): RegelRechtWriter volle instrument-YAML`

---

### Task 5: DemoBuilder + template UI

**Files:**
- Create: `nldt/simulation/regelrecht/full_export/build_full_demo.py`
- Modify: `nldt/simulation/regelrecht/regelrecht-demo.template.html`
- Modify: `nldt/simulation/regelrecht/build_runs.py` (optioneel: aanroep full-export artefacts voor coverage teaser) — **liever niet**; full demo bouwt eigen inline JSON.
- Modify: `nldt/tests/test_simulation_regelrecht_full.py`
- Modify: `nldt/tests/test_simulation_regelrecht.py` alleen als bestaande assertions op teasertekst breken

**Interfaces:**
- `build_demo(stamp: str) -> None`  
  - Leest beide instrument-YAML's + reports + bestaande run-JSON's (`utrecht-wind-art5.3.json`, `eindhoven-bp2op-art10.2.json`) voor de 16 golden cases.  
  - Bouwt `instrumentIndex` per PoC: `[{number, status, hasMachineReadable, title}]`.  
  - Cap demoCases: bestaande 16 + tot 20 formalized artikelen per PoC (sorteer op number, skip 5.3/10.2 duplicaten); cases via `reference_engine.evaluate` met synthetische inputs (parameters=0/False, zone inputs True) — alleen artikelen waarvan alle operanden booleans/numbers zonder open enums. Skip als evaluate faalt → niet in cap.  
  - Vult placeholders in template: `__RUN_UTRECHT__`, `__RUN_EINDHOVEN__` (bestaand), plus `__INDEX_UTRECHT__`, `__INDEX_EINDHOVEN__`, `__REPORT_UTRECHT__`, `__REPORT_EINDHOVEN__`.  
  - Schrijft `nldt/simulation/regelrecht-demo.html`.

**Template-UI (minimaal):**
1. Coverage-strip: `formalized N · ambiguous N · unmatched N · rejected N`.
2. `<input id="article-search">` + `<select id="article-select">` gevuld uit index.
3. Bij selectie: toon quote/text-snippet, MR-JSON of “text-only: {reason}”, lab enable/disable.
4. Selftest-badge: `16+K/16+K` waarbij K = aantal cap-cases; basis 16 blijft hard fail bij afwijking.

- [ ] **Step 1: Tests**

```python
class TestDemoBuild(unittest.TestCase):
    def test_demo_contains_index_and_coverage(self):
        from build_full_demo import build_demo
        # presuppose out/ yaml+report exist from writer tests or call pipeline helpers
        build_demo(stamp="2026-10-14T00:00:00Z")
        html = (ROOT / "nldt/simulation/regelrecht-demo.html").read_text()
        self.assertIn("__INDEX_UTRECHT__".replace("__", "") or "application/json", html)
        self.assertIn("article-select", html)
        self.assertIn("formalized", html.lower())
```

Concrete assertion: placeholders moeten **vervangen** zijn — dus `self.assertNotIn("__INDEX_UTRECHT__", html)` en `self.assertIn('"number": "5.3"', html)`.

- [ ] **Step 2–4:** template aanpassen, builder, tests, commit `feat(nldt): RegelRecht-demo instrument-browser + coverage`

---

### Task 6: `build_all` + docs + hub-teasers

**Files:**
- Create: `nldt/simulation/regelrecht/full_export/build_all.py`
- Modify: `nldt/simulation/README.md`
- Modify: `docs/POC_REGELRECHT_INTEGRATION.md` (korte sectie + link naar spec)
- Modify: `nldt/simulation/poc-utrecht.html`, `poc-eindhoven.html`, `index.html` (teaser: coverage i.p.v. enkel art. 5.3/10.2)
- Modify: `nldt/tests/test_simulation_regelrecht_full.py` (end-to-end + idempotentie)
- Modify: `nldt/tests/test_simulation_regelrecht.py` (hub-link assertions blijven groen)

**Interfaces:**
- CLI:

```bash
nldt/.venv/bin/python nldt/simulation/regelrecht/full_export/build_all.py --stamp 2026-10-14T00:00:00Z
```

Stappen in volgorde: split → write `*-articles.json` → align → formalize → write YAML+report → `build_demo`. Exit ≠ 0 bij schema-fail.

- [ ] **Step 1: E2E-test**

```python
class TestBuildAll(unittest.TestCase):
    def test_idempotent_stamp(self):
        import subprocess, filecmp
        cmd = [str(ROOT / "nldt/.venv/bin/python"),
               str(FULL / "build_all.py"), "--stamp", "2026-10-14T12:00:00Z"]
        subprocess.check_call(cmd, cwd=ROOT)
        u1 = (FULL / "out/utrecht-cvdr704250.yaml").read_bytes()
        subprocess.check_call(cmd, cwd=ROOT)
        u2 = (FULL / "out/utrecht-cvdr704250.yaml").read_bytes()
        self.assertEqual(u1, u2)

    def test_smoke_articles_still_in_legacy_runs(self):
        # bestaande generator blijft werken
        import subprocess
        subprocess.check_call([
            str(ROOT / "nldt/.venv/bin/python"),
            str(ROOT / "nldt/simulation/regelrecht/build_runs.py"),
            "--stamp", "2026-10-14T12:00:00Z",
        ], cwd=ROOT)
```

- [ ] **Step 2: Implementeer `build_all.py`**

```python
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", required=True)
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    for poc in ("utrecht", "eindhoven"):
        arts = split_instrument(poc)
        write_articles_json(poc, arts, OUT / f"{poc}-articles.json")
        al, orphans = align(poc, arts)
        form, report = formalize(poc, arts, al, orphans, stamp=args.stamp)
        write_instrument_yaml(poc, arts, form, stamp=args.stamp)
        (OUT / f"{poc}-formalization-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    build_demo(stamp=args.stamp)
```

- [ ] **Step 3: Docs + teasers** — README sectie “Volle-instrument export”; POC_REGELRECHT_INTEGRATION: “Fase 1 volledig” pointer; teasers noemen “alle artikelen · coverage”.

- [ ] **Step 4: Draai volledige suites**

```bash
nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht_full.py -v
nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v
```

Expected: ALL OK.

- [ ] **Step 5: Commit gegenereerde `out/*` + demo + docs**

```bash
git add nldt/simulation/regelrecht/full_export/ nldt/simulation/regelrecht-demo.html \
  nldt/simulation/poc-utrecht.html nldt/simulation/poc-eindhoven.html \
  nldt/simulation/index.html nldt/simulation/README.md \
  docs/POC_REGELRECHT_INTEGRATION.md nldt/tests/test_simulation_regelrecht_full.py
git commit -m "$(cat <<'EOF'
feat(nldt): volle RegelRecht-export Utrecht/Eindhoven + demo-browser

EOF
)"
```

---

## Spec coverage checklist

| Spec-eis | Task |
|---|---|
| ArticleSplitter HTML → articles | 1 |
| EvidenceAligner + orphans | 2 |
| FormalizerPass + mapping + abstention | 3 |
| 1 YAML/instrument + schema v0.7.1 | 4 |
| formalization-report.json | 3–4 |
| Geo externe input | 3 (mapping) |
| Eindhoven conversielinks in report niet BWBR refs | 3 (omzet in report articles meta) |
| Demo kiezer + coverage + lab-gate | 5 |
| 16 golden + cap 20 | 5 |
| build_all --stamp idempotent | 6 |
| Tests V2 verbatim formalized / counts | 3–4, 6 |
| README + POC_REGELRECHT_INTEGRATION pointer | 6 |
| Smoke fixtures behouden | 6 (legacy build_runs) |
| Geen LLM / geen live DSO | Global + 3 |

## Uitvoeringshand-off

Na goedkeuring van dit plan: kies subagent-driven of inline execution.
