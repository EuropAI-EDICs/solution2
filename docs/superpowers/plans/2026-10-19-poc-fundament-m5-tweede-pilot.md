# PoC-fundament M5 Implementatieplan (tweede pilot NSPD-tracks, golden-per-fase, V-tool-suite, afronding)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Het fundament aanmelden met een tweede pilot: **NSPD-tracks** krijgt een fase-manifest (agent–fase–tool matrix) afgeleid uit zijn eigen corpus- en bronregisters, bewezen via conformance — plus de restanten uit de M1–M4-reviews: golden-per-fase, de benoemde V-tool-suite, de sys.path-bridge als gedocumenteerd patroon en de MINIGIM-fase-2-haken herdok naar het modelregister.

**Architecture:** NSPD's pipeline (intake → normanalyse → formalisering → geodoorrekening → synthese) wordt op de vijf fase-archetypen gemapt; de generator leidt 82 taken af uit de 26 corpus-paren (land×track) plus harnas-taken, zonder de NSPD-engine aan te raken (engines blijven authoritatief, spec §7). Golden-per-fase pint per fase de delivered/manual/not-delivered-tellingen van de offline fixture-run. De fase-2-haken (GREX, IFC-export) worden modelregister-entries met `status: "fase-2-haak"` — bestaandbewijs geldt alleen voor `status: "actief"`.

**Tech Stack:** Python (stdlib + jsonschema), unittest (poc-fundament, poc-minigim) en pytest (poc-nspd eigen venv, deep-agents).

**Spec:** `docs/superpowers/specs/2026-10-18-poc-fundament-minigim-harnas-design.md` §11 **M5**; pilot-keuze = beslispunt 5 (gebruiker: **NSPD-tracks**). Exit: de tweede PoC is volgens §1-succescriterium aanmeldbaar — manifest + register-invoer + fixtures, engine onaangetast.

## Global Constraints

- **Engine onaangetast:** `poc-nspd/run.py`, `pipeline/`, `corpus/*` (inhoud), `data/sources.json` worden alleen gelezen; geen gedragswijziging in NSPD. Golden-tests van NSPD (`pytest -m golden`) horen buiten de standaard-suite en worden niet aangeraakt.
- **Dependency-richting:** `poc-fundament` importeert nooit deep-agents/poc/nldt; `deep-agents/fase_slotgate.py` blijft de enige slotgate-implementatie; NSPD-tests importeren uitsluitend `poc-fundament` (via de nieuwe brug-conventie), nooit deep-agents.
- **Sys.path-brug-conventie (M5-verplicht punt):** consumenten zonder een package-bootstrap voegen het fundament toe met `sys.path.append(str(REPO_ROOT / "poc-fundament"))` — **append, nooit insert(0)** (insert schaduwt lokale `tests`-packages onder discovery; M2-les).
- **Alle vier de suites groen na elke taak:** poc-fundament (`../nldt/.venv/bin/python -m unittest discover -s tests -q`), poc-minigim (idem), poc-nspd (`.venv/bin/python -m pytest -q` — standaard-suite, geen golden/llm), deep-agents (`PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q`).
- **Golden-veilig:** de minigim-golden-set groeit alleen met `fase-samenvatting.json` (afgeleid, deterministisch, via de bestaande capture); `report.html`/`prov.json` blijven buiten de set.
- **Gebruikers-werkboom:** deep-agents/README.md, deep-agents/laya_router.py, deep-agents/laya_train/, poc-nspd/scenario-runs/*, poc-nspd/viewer nooit stagen; nooit `git add -A`.
- Commit per taak, Nederlands conventioneel, direct op `main`.

## Bestandskaart

```
deep-agents/
  fase_slotgate.py               AANGEPAST — ROLE_ALIASES += normspecialist, formalizer;
                                 journal-gate-fase uit het manifest; except (OSError, ValueError)
  tests/test_fase_slotgate.py    AANGEPAST — alias-test + wiring-spy-test
poc-nspd/
  fase-manifest.json             NIEUW — gegenereerd (82 taken)
  tools/gen_fase_manifest.py     NIEUW — generator (corpus-paren → fasen)
  tools/render_matrix.py         NIEUW — matrix → fase-matrix.md op verzoek
  tests/test_fase_manifest_conformance.py   NIEUW — conformance + transport-bewijs
  README.md                      AANGEPAST — manifest-sectie
poc-fundament/
  fundament/models.py            AANGEPAST — status-veld-tolerantie zit in schema; docstring
  schemas/modelregister.schema.json  AANGEPAST — status: actief|fase-2-haak
  tests/test_models.py           AANGEPAST — fase-2-haak-validatie
  fundament/canon? nee           —
poc-minigim/
  minigim/canon.py               AANGEPAST — + fase_samenvatting(manifest, records)
  tools/capture_golden.py        AANGEPAST — schrijft golden/fase-samenvatting.json
  tests/test_golden.py           AANGEPAST — vergelijkt fase-samenvatting
  tests/test_modelregister.py    AANGEPAST — drempel == 6; fase-2-haak-exemptie
  modelregister.json             AANGEPAST — + grex-financien, ifc-export (fase-2-haak)
  tests/test_vtool?              NIEUW in poc-fundament (zie hieronder)
poc-fundament/tests/test_vtool.py  NIEUW — benoemde V-tool-suite (index + contracten)
poc-fundament/README.md          AANGEPAST — brug-conventie + matrix-tabel
docs/MINIGIM.md                  AANGEPAST — fase-2-haken → modelregister-herdok
```

---

### Task 1: deep-agents hardening — aliassen voor NSPD-rollen, wiring-spy, journal-generalisatie

**Files:**
- Modify: `deep-agents/fase_slotgate.py` (aliassen, gate-fase-id, except-clausule)
- Modify: `deep-agents/tests/test_fase_slotgate.py` (3 aanvullingen)

**Interfaces:**
- Produces: `ROLE_ALIASES` met `normspecialist` en `formalizer` (nodig voor taak 2's rolcheck-uitgangspunt); `journal_fases_en_gate` met gate-fase = laatste manifest-fase en except `(OSError, ValueError)`; een spy-test die faalt als de wiring uit `poc_subagents` wordt verwijderd.

- [ ] **Step 1: Schrijf de failing tests** — voeg toe aan `deep-agents/tests/test_fase_slotgate.py`:

```python
def test_nspd_rollen_resolven_via_aliassen():
    manifest = {"poc": "nspd", "methodiek": "m", "phases": [
        {"id": "F1-normanalyse", "title": "N", "agent": {"role": "normspecialist"},
         "tasks": [{"id": "t1", "binding": "auto",
                    "tool": {"class": "retrieval", "ref": "r"}}]},
        {"id": "F2-formalisering", "title": "F", "agent": {"role": "formalizer"},
         "tasks": [{"id": "t2", "binding": "auto",
                    "tool": {"class": "computation", "ref": "r"}}]},
    ]}
    out = fs.resolve_agent_phases(manifest)
    assert out["normspecialist"] == ["F1-normanalyse"]
    assert out["formalizer"] == ["F2-formalisering"]


def test_poc_subagents_roept_de_slotgate_aan(monkeypatch):
    """De wiring-zelf is getest: als iemand apply_slotgate uit poc_subagents
    verwijdert, faalt deze test (M4-eindreview, restant 4)."""
    import pocs

    aangeroepen = {}
    origineel = pocs.apply_slotgate

    def spy(specs, manifest, poc_agent_names):
        aangeroepen["n"] = aangeroepen.get("n", 0) + 1
        aangeroepen["poc"] = tuple(sorted(poc_agent_names))
        return origineel(specs, manifest, poc_agent_names)

    monkeypatch.setattr(pocs, "apply_slotgate", spy)
    pocs.poc_subagents(mcp_tools=None)
    assert aangeroepen.get("n") == 1
    assert "minigim" in aangeroepen["poc"]


def test_journal_gate_fase_uit_het_manifest(monkeypatch, tmp_path):
    """De gate-journal-regel gebruikt de laatste manifest-fase, geen hardcode."""
    manifest = fs.load_manifest("minigim")
    assert manifest["phases"][-1]["id"] == "F4-synthese"  # zelfde waarde, nu afgeleid
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    (tmp_path / "run_summary.json").write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")
    fs.journal_fases_en_gate("minigim", tmp_path)
    gates = [e for e in events if e[0] == "gate"]
    assert gates[0][3]["fase"] == manifest["phases"][-1]["id"]


def test_journal_corrupt_json_is_stil(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    (tmp_path / "run_summary.json").write_bytes(b"\xff\xfe\x00invalid")
    fs.journal_fases_en_gate("minigim", tmp_path)  # UnicodeDecodeError ⊂ ValueError
    assert events == []
```

- [ ] **Step 2: Run — verwacht FAIL op precies twee nieuwe tests.** `test_nspd_rollen_resolven_via_aliassen` faalt met `ValueError` (de aliassen bestaan nog niet) en `test_journal_corrupt_json_is_stil` faalt omdat `UnicodeDecodeError` de except-clausule ontwijkt. De spy-test en de gate-fase-test passeren al (de wiring en de hardcoded waarde bestaan) — dat is correct, zij bewaken gedrag dat er al is.

Run: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_fase_slotgate.py -q`

- [ ] **Step 3: Implementeer** — drie wijzigingen in `deep-agents/fase_slotgate.py`:
  1. `ROLE_ALIASES` krijgt twee regels na `"minigim-specialist": "minigim",`:

```python
    "normspecialist": "normspecialist",
    "formalizer": "formalizer",
```

  2. In `journal_fases_en_gate`: vervang `except (OSError, json.JSONDecodeError):` door `except (OSError, ValueError):  # incl. JSONDecodeError/UnicodeDecodeError` en vervang de hardcoded gate-regel `fase="F4-synthese"` door:

```python
    laatste_fase = manifest["phases"][-1]["id"]
    journal.append("gate", poc,
                   f"verdict: {verdict} (V0–V3 deterministisch; V4 pending)",
                   fase=laatste_fase, verdict=verdict)
```

- [ ] **Step 4: Run — verwacht PASS + volledige deep-agents-suite groen**

Run: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_fase_slotgate.py tests -q` (eerst gefocust, dan de hele suite; 2 pre-existing skips)

- [ ] **Step 5: Commit**

```bash
git add deep-agents/fase_slotgate.py deep-agents/tests/test_fase_slotgate.py
git commit -m "feat(deep-agents): nspd-rollen in de slotgate-aliassen + wiring-spy + journal-generalisatie (M5)"
```

---

### Task 2: NSPD fase-manifest — de tweede pilot

**Files:**
- Create: `poc-nspd/tools/gen_fase_manifest.py`, `poc-nspd/fase-manifest.json`, `poc-nspd/tests/test_fase_manifest_conformance.py`, `poc-nspd/tools/render_matrix.py`
- Modify: `poc-nspd/README.md` (korte manifest-sectie bij „Architectuur")

**Interfaces:**
- Consumes: `fundament.manifest.load_manifest`, `fundament.matrix.render_matrix` (taak-conventie: `sys.path.append(str(REPO_ROOT / "poc-fundament"))` — de M5-brug-conventie uit Global Constraints).
- Produces: `poc-nspd/fase-manifest.json` — 82 taken: F0 1, F1 26 (normcards per land×track), F2 26 (formal-rules), F3 26 (zones per track×land), F4 3. Fasen-rollen: `intake`, `normspecialist`, `formalizer`, `geospecialist`, `critic + explainer` (allemaal aliassen na taak 1).

- [ ] **Step 1: Generator** — `poc-nspd/tools/gen_fase_manifest.py` (volledig):

```python
#!/usr/bin/env python3
"""Genereert poc-nspd/fase-manifest.json uit NSPD's eigen registers.

De matrix is declaratief: het corpus (normcards/formal-rules per land×track)
is leidend; de generator knoopt het aan de vijf fase-archetypen en raakt de
engine niet aan. Deterministisch; elke run schrijft dezelfde bytes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT.parent / "poc-fundament"))  # brug-conventie: append, nooit insert


def _paren(prefix: str) -> list[str]:
    """Gesorteerde '<land>-<track>'-paren uit corpus/<prefix>-<land>-<track>.json
    (rejected-varianten vallen buiten het patroon)."""
    return sorted(p.stem[len(prefix) + 1:]
                  for p in (ROOT / "corpus").glob(f"{prefix}-*.json")
                  if "rejected" not in p.name)


def _track_land(paar: str) -> str:
    land, track = paar.split("-", 1)
    return f"{track}-{land}"


def build() -> dict:
    norm = _paren("normcards")
    rules = _paren("formal-rules")
    if norm != rules:
        raise SystemExit(f"corpus-asymmetrie normcards/formal-rules: {set(norm) ^ set(rules)}")
    f1 = [{"id": f"normcards-{paar}", "from": "register:nspd-corpus", "binding": "auto",
           "tool": {"class": "retrieval", "ref": f"corpus:normcards-{paar}",
                    "transport": "in-process", "derive": ["cite-or-abstain"]}}
          for paar in norm]
    f2 = [{"id": f"formal-rules-{paar}", "from": "register:nspd-corpus", "binding": "auto",
           "tool": {"class": "computation", "ref": f"corpus:formal-rules-{paar}",
                    "transport": "in-process", "derive": ["v2b-jurisdictie-gate"]}}
          for paar in rules]
    f3 = [{"id": f"zones-{_track_land(paar)}", "from": "register:nspd-bronnen", "binding": "auto",
           "tool": {"class": "computation", "ref": "run:nspd-zone-engine",
                    "transport": "in-process", "derive": ["zone-algebra", "fr-aoi-01"]}}
          for paar in rules]
    return {
        "poc": "nspd-tracks",
        "methodiek": "nspd-tracks-v2.0",
        "aoi": {"schema": "geojson", "crs": "EPSG:28992"},
        "phases": [
            {"id": "F0-intake", "title": "Intake/scoping (use-case + AOI)",
             "agent": {"role": "intake"},
             "tasks": [{"id": "use-case-aoi", "from": "use-cases:make_aoi", "binding": "auto",
                        "tool": {"class": "validation", "ref": "use-cases:make_aoi",
                                 "transport": "in-process"}}],
             "gate": {"validate": ["V0"]}},
            {"id": "F1-normanalyse", "title": "Normanalyse (cite-or-abstain)",
             "agent": {"role": "normspecialist"}, "tasks": f1,
             "gate": {"validate": ["V0", "V2"], "onFail": "cite-or-abstain"}},
            {"id": "F2-formalisering", "title": "Formalisering (FormalRules, V2b-gate)",
             "agent": {"role": "formalizer"}, "tasks": f2,
             "gate": {"validate": ["V2"], "onFail": "formal-rule geweigerd (ledger)"}},
            {"id": "F3-geodoorrekening", "title": "Geodoorrekening (zone-algebra, cache-first)",
             "agent": {"role": "geospecialist"}, "tasks": f3,
             "gate": {"validate": ["V1", "V3"]}},
            {"id": "F4-synthese", "title": "Synthese & rapport (xborder-merge, Leia)",
             "agent": {"role": "critic + explainer"},
             "tasks": [
                 {"id": "v0-v3-verdict", "from": "run-input", "binding": "auto",
                  "tool": {"class": "validation", "ref": "fundament:validate",
                           "transport": "in-process"}},
                 {"id": "xborder-merge", "from": "pipeline:xborder", "binding": "auto",
                  "tool": {"class": "computation", "ref": "pipeline:xborder",
                           "transport": "in-process"}},
                 {"id": "rapport", "from": "run-input", "binding": "auto",
                  "tool": {"class": "report", "ref": "nspd:report", "transport": "in-process"}}],
             "gate": {"validate": ["V0", "V1", "V2", "V3"], "hitl": "v4 (mens) pending"}},
        ],
    }


def main() -> None:
    manifest = build()
    out = ROOT / "fase-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(len(p.get("tasks") or []) for p in manifest["phases"])
    print(f"fase-manifest: {len(manifest['phases'])} fasen, {n} taken → {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Conformance-tests** — `poc-nspd/tests/test_fase_manifest_conformance.py` (volledig):

```python
"""NSPD fase-manifest: conformance tegen het fundament en de eigen registers.

De tweede pilot bewijst het §1-succescriterium: alleen manifest + register-
verwijzingen + tests, engine onaangetast. Offline (geen netwerk, geen engine-run).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.append(str(REPO / "poc-fundament"))  # brug-conventie: append, nooit insert

from fundament.manifest import load_manifest  # noqa: E402

BEKENDE_ROLLEN = {"intake", "normspecialist", "formalizer", "geospecialist",
                  "critic", "explainer"}


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(ROOT / "fase-manifest.json")


def _tasks(manifest, fase_prefix):
    for ph in manifest["phases"]:
        if ph["id"].startswith(fase_prefix):
            return ph.get("tasks") or []
    return []


def test_manifest_valideert_tegen_het_fundamentschema(manifest):
    assert manifest["poc"] == "nspd-tracks"
    assert [p["id"] for p in manifest["phases"]] == [
        "F0-intake", "F1-normanalyse", "F2-formalisering",
        "F3-geodoorrekening", "F4-synthese"]


def test_rollen_zijn_bekende_deep_agents_agenten(manifest):
    for ph in manifest["phases"]:
        for rol in str(ph["agent"]["role"]).lower().split("+"):
            assert rol.strip() in BEKENDE_ROLLEN, ph["id"]


def test_corpus_taken_komen_overeen_met_de_werkelijke_bestanden(manifest):
    norm_bestanden = sorted(p.stem[len("normcards-"):]
                            for p in (ROOT / "corpus").glob("normcards-*-*.json")
                            if "rejected" not in p.name)
    f1_ids = {t["id"][len("normcards-"):] for t in _tasks(manifest, "F1-")}
    assert f1_ids == set(norm_bestanden)
    rules_bestanden = sorted(p.stem[len("formal-rules-"):]
                             for p in (ROOT / "corpus").glob("formal-rules-*.json"))
    f2_ids = {t["id"][len("formal-rules-"):] for t in _tasks(manifest, "F2-")}
    assert f2_ids == set(rules_bestanden)


def test_corpus_refs_resolven_naar_bestaande_bestanden(manifest):
    for t in _tasks(manifest, "F1-") + _tasks(manifest, "F2-"):
        ref = t["tool"]["ref"]
        assert ref.startswith("corpus:"), ref
        assert (ROOT / "corpus" / (ref[len("corpus:"):] + ".json")).is_file(), ref


def test_zone_taken_dekken_alle_corpus_paren(manifest):
    paren = sorted(p.stem[len("normcards-"):]
                   for p in (ROOT / "corpus").glob("normcards-*-*.json")
                   if "rejected" not in p.name)
    verwacht = {f"zones-{p.split('-', 1)[1]}-{p.split('-', 1)[0]}" for p in paren}
    assert {t["id"] for t in _tasks(manifest, "F3-")} == verwacht


def test_elke_track_heeft_gepinde_bronnen_in_het_bronregister(manifest):
    bronnen = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    tracks_in_register = {t for b in bronnen["sources"] for t in (b.get("tracks") or [])}
    for t in _tasks(manifest, "F3-"):
        track = t["id"][len("zones-"):].rsplit("-", 1)[0]
        assert track in tracks_in_register, track


def test_matrix_render_is_deterministisch(manifest):
    from fundament.matrix import render_matrix
    twee = {render_matrix(manifest), render_matrix(manifest)}
    assert len(twee) == 1
    md = twee.pop()
    for fase in ("F0-intake", "F1-normanalyse", "F2-formalisering",
                 "F3-geodoorrekening", "F4-synthese"):
        assert fase in md
```

**Correctie bij implementatie:** in `test_corpus_refs_resolven_naar_bestaande_bestanden` staat hierboven een verdwaald dubbel expressie-fragment — de correcte assertie is exact:

```python
        assert (ROOT / "corpus" / (ref[len("corpus:"):] + ".json")).is_file(), ref
```

- [ ] **Step 3: Render-tool** — `poc-nspd/tools/render_matrix.py` (volledig):

```python
#!/usr/bin/env python3
"""Schrijft de agent–fase–tool matrix van NSPD als fase-matrix.md (op verzoek).

De engine wordt niet aangeraakt; dit is de leesbare vorm van het manifest.
    cd poc-nspd && .venv/bin/python tools/render_matrix.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT.parent / "poc-fundament"))  # brug-conventie: append, nooit insert

from fundament.manifest import load_manifest  # noqa: E402
from fundament.matrix import render_matrix  # noqa: E402


def main() -> None:
    manifest = load_manifest(ROOT / "fase-manifest.json")
    out = ROOT / "fase-matrix.md"
    out.write_text(render_matrix(manifest), encoding="utf-8")
    print(f"matrix → {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Genereer + test + determinisme**

Run: `cd poc-nspd && .venv/bin/python tools/gen_fase_manifest.py && .venv/bin/python -m pytest tests/test_fase_manifest_conformance.py -q && .venv/bin/python tools/render_matrix.py`
Expected: `5 fasen, 82 taken`; conformance 7 passed; matrix weggeschreven. Determinisme: twee generaties → identieke sha256. Handmatige steekproef: 3 willekeurige F1/F2-taken openen en vergelijken met de corpus-bestandsnamen.

- [ ] **Step 5: README-sectie** — in `poc-nspd/README.md`, direct boven `## Architectuur`, toevoegen:

```markdown
## Fase-manifest (MiniGIM-harnas, tweede pilot)

`fase-manifest.json` (82 taken, 5 fasen) verklaart NSPD's methodiek in de
toolbox-conventie: per fase agent, tools (retrieval/computation) en gates —
afgeleid uit het corpus (26 land×track-paren) via
`tools/gen_fase_manifest.py`, geconformeerd tegen het fundament
(`tests/test_fase_manifest_conformance.py`). Leesbare matrix:
`tools/render_matrix.py` → `fase-matrix.md`. De engine (hierna) is onaangetast.
```

- [ ] **Step 6: Alle suites groen + commit**

```bash
(cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
(cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
(cd poc-nspd && .venv/bin/python -m pytest -q)
(cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q)
git add poc-nspd/fase-manifest.json poc-nspd/tools/gen_fase_manifest.py poc-nspd/tools/render_matrix.py poc-nspd/tests/test_fase_manifest_conformance.py poc-nspd/README.md
git commit -m "feat(poc-nspd): fase-manifest (tweede pilot op het MiniGIM-harnas) + conformance + matrix-render (M5)"
```

---

### Task 3: Golden-per-fase, V-tool-suite, modelregister-herdok, brug-docs

**Files:**
- Modify: `poc-minigim/minigim/canon.py` (+ `fase_samenvatting`), `poc-minigim/tools/capture_golden.py` (+ schrijfstap), `poc-minigim/tests/test_golden.py` (+ vergelijking), `poc-minigim/tests/test_modelregister.py` (drempel == 6 + fase-2-haak-exemptie)
- Modify: `poc-fundament/schemas/modelregister.schema.json` (+ `status`), `poc-minigim/modelregister.json` (+ 2 fase-2-haak-entries)
- Create: `poc-fundament/tests/test_vtool.py`
- Modify: `poc-fundament/README.md` (brug-conventie + matrix-tabel), `docs/MINIGIM.md` (fase-2-herdok)

**Interfaces:**
- Produces: `minigim.canon.fase_samenvatting(manifest, records) -> list[dict]` (deterministisch; per fase taken/delivered/manualAction/notDelivered/nvt); modelregister-entries met `status: "fase-2-haak"` zijn vrijgesteld van transport-bestaanbewijs (alleen `status: "actief"` — de default — wordt bewezen).

- [ ] **Step 1: `fase_samenvatting` in `poc-minigim/minigim/canon.py`** — onder `canon` (en pas de module-docstring- tweede alinea aan: "Ook thuis hier: fase_samenvatting, de per-fase kant van het bewijs."):

```python
def fase_samenvatting(manifest: dict, records: list[dict]) -> list[dict]:
    """Per manifest-fase: taken en deliveredStatus-tellingen (deterministisch).

    Bewijs-instrument voor golden-per-fase: geen tijden, geen volgorde-afhankelijkheid
    (tellingen), join op lijstItemId.
    """
    from collections import Counter

    fase_van = {t["id"]: ph["id"]
                for ph in manifest["phases"] for t in (ph.get("tasks") or [])}
    uit = []
    for ph in manifest["phases"]:
        recs = [r for r in records if fase_van.get(r["lijstItemId"]) == ph["id"]]
        c = Counter(r["deliveredStatus"] for r in recs)
        uit.append({
            "fase": ph["id"], "taken": len(recs),
            "delivered": c.get("delivered", 0),
            "manualAction": c.get("manual-action", 0),
            "notDelivered": c.get("not-delivered", 0),
            "nvt": c.get("nvt", 0),
        })
    return uit
```

- [ ] **Step 2: Capture schrijft de fase-golden.** In `poc-minigim/tools/capture_golden.py`:
  1. Bij de imports: `from minigim.canon import ARTIFACTS, canon, fase_samenvatting` (vervang de bestaande canon-import) en `from fundament.manifest import load_manifest`.
  2. In `main()`, na de ARTIFACTS-lus en vóór de lagen-lus:

```python
        manifest = load_manifest(ROOT / "fase-manifest.json")
        items = json.loads((run_dir / "omgevingsanalyse.json").read_text(encoding="utf-8"))["items"]
        (GOLDEN / "fase-samenvatting.json").write_text(
            json.dumps(fase_samenvatting(manifest, items), ensure_ascii=False, indent=1,
                       sort_keys=True) + "\n", encoding="utf-8")
```

  3. De opschonings-lus (`for old in GOLDEN.iterdir(): old.unlink()`) blijft — de nieuwe file wordt bij elke capture vers aangemaakt.
  4. Draai de capture opnieuw en commit de nieuwe golden mee (step 5).

- [ ] **Step 3: `test_golden.py` vergelijkt de fase-samenvatting.** Voeg in `TestGoldenReproductie.test_offline_run_is_canonisch_identiek`, ná de artefacten-vergelijking, toe:

```python
        from minigim.canon import fase_samenvatting
        from fundament.manifest import load_manifest

        manifest = load_manifest(ROOT / "fase-manifest.json")
        docs = json.loads((canon_dir / "omgevingsanalyse.json").read_text(encoding="utf-8"))
        sam = fase_samenvatting(manifest, docs["items"])
        verwacht = json.loads((GOLDEN / "fase-samenvatting.json").read_text(encoding="utf-8"))
        self.assertEqual(sam, verwacht, "fase-samenvatting wijkt af")
```

(`json` is na de M4-sloop weg uit de imports van test_golden.py — voeg `import json` bovenin weer toe.)

- [ ] **Step 4: Modelregister fase-2-haken.**
  1. `poc-fundament/schemas/modelregister.schema.json`: in `$defs.model.properties` toevoegen `"status": {"enum": ["actief", "fase-2-haak"]}` (niet in `required` — afwezig = actief; zet `"status"` ook letterlijk in `properties`, na `"prov"`).
  2. `poc-minigim/modelregister.json`: twee nieuwe entries in `models` (na `minigim-proxy-derivaties`):

```json
  {
   "id": "grex-financien",
   "title": "GREX financi\u00eble doorrekening per gebiedsdeel (MiniGIM fase 2)",
   "class": "computation",
   "status": "fase-2-haak",
   "riskLevel": "medium",
   "version": "fase-2",
   "prov": {"note": "fase-2-haak uit docs/MINIGIM.md: join op ilsNodeId; transportintentie a2a (Agent Card) zodra GREX ontsloten is \u2014 nog geen bestaandbewijs, vandaar status"},
   "transports": [{"type": "a2a", "catalogRef": "fase-2-haak: GREX-tabellen (niet ontsloten)", "agentId": "grex"}]
  },
  {
   "id": "ifc-export",
   "title": "IFC-export van de ILS-draft (IfcOpenShell, spatial structure per nodePath)",
   "class": "computation",
   "status": "fase-2-haak",
   "riskLevel": "low",
   "version": "fase-2",
   "prov": {"note": "fase-2-haak: ils-draft.features.28992.geojson draagt ilsNodeId/ifcExportAs/epsetMinigim; transportintentie in-process (tool) \u2014 nog niet ge\u00efmplementeerd"},
   "transports": [{"type": "in-process", "ref": "haak:minigim/ils.py#write", "note": "intentie, nog niet gebouwd"}]
  }
```

  3. `poc-minigim/tests/test_modelregister.py`: verhoog de manifest-drempel `assertGreaterEqual(gevonden, 3)` naar `assertEqual(gevonden, 6)` (de generator emitteert er exact 6), en voeg twee testmethoden toe:

```python
    def test_fase2haak_entries_zijn_gemarkeerd_en_vrijgesteld(self):
        for m in self.reg["models"]:
            if m.get("status") == "fase-2-haak":
                self.assertIn("fase-2", m["prov"]["note"], m["id"])
        haak_ids = {m["id"] for m in self.reg["models"] if m.get("status") == "fase-2-haak"}
        self.assertEqual(haak_ids, {"grex-financien", "ifc-export"})

    def test_actieve_entries_blijven_bewezen(self):
        actief = [m for m in self.reg["models"] if m.get("status", "actief") == "actief"]
        self.assertIn("minigim-gebiedscheck-run", [m["id"] for m in actief])
```

  Verwachte tellingen na deze taak: test_modelregister 6 passed (3 bestaande + manifest-refs + 2 nieuwe), conformance ongewijzigd 6, test_golden uitgebreid, test_vtool 5, test_models 6 (basis), test_fase_slotgate 16 (12 + 4 nieuwe). Het bestaande transport-bewijs (`test_processes_transport…`/`test_a2a_transport…`) itereert over het gebiedscheck-model en raakt de fase-2-haak-entries dus niet — die zijn door hun `status` bewust vrijgesteld.

- [ ] **Step 5: V-tool-suite** — `poc-fundament/tests/test_vtool.py` (volledig). Dit is de benoemde assemblage van de bestaande contracten (spec §9, V-tool): V0 schema's, retrieval-contract, computation-replay-contract, binding-contract; de slotgate-contracten wonen bewust in deep-agents (dependency-richting) en worden hier alleen gerefereerd.

```python
"""V-tool-suite (M5): de contracten van het harnas als één benoemde suite.

Assemblage van de bestaande bewijzen, per contract-familie (spec §9):
  V0      — fase-manifest en modelregister van beide pilot-PoC's zijn schema-geldig
  retrieval — een falende fetch degradeert naar not-delivered mét manifest-velden in de prov
  computation — derivaties zijn in-run replay-identiek (byte-vergelijking op canon)
  binding — auto⇒tool en manual⇒pointer worden door het schema afgedwongen
Slotgate-contracten: zie deep-agents/tests/test_fase_slotgate.py (dependency-richting:
dit package importeert deep-agents niet).

Offline; hergebruikt de mini-registry/fixtures van de executor-tests.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.manifest import load_manifest  # noqa: E402
from fundament.models import load_model_registry  # noqa: E402

import mini_registry  # noqa: E402
from fundament.executor import BindingExecutor  # noqa: E402
from fundament.ops import DEFAULT_OPS  # noqa: E402

from tests import fixtures  # noqa: E402

REPO = ROOT.parent
PILOTS = {"minigim": REPO / "poc-minigim", "nspd": REPO / "poc-nspd"}


class TestV0Schemas(unittest.TestCase):
    def test_beide_pilot_manifesten_zijn_schema_geldig(self):
        for poc, home in PILOTS.items():
            m = load_manifest(home / "fase-manifest.json")
            self.assertEqual(m["poc"], {"minigim": "minigim-gebiedscheck",
                                        "nspd": "nspd-tracks"}[poc], poc)

    def test_modelregister_is_schema_geldig(self):
        reg = load_model_registry(PILOTS["minigim"] / "modelregister.json")
        ids = [m["id"] for m in reg["models"]]
        self.assertEqual(len(ids), len(set(ids)))


class TestRetrievalContract(unittest.TestCase):
    def test_falende_fetch_degradeert_met_prov_en_vlaggen(self):
        reg = mini_registry.build()
        real = fixtures.fake_fetch_layer_factory()

        def failing(source, bbox=None, refresh=False, cbs_filter=None):
            if source["id"] == "pdok-nwb-wegen":
                raise RuntimeError("server onbereikbaar")
            return real(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter)

        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=failing,
                                 ops=DEFAULT_OPS)
            recs = ex.run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.clip")
        self.assertEqual(rec["deliveredStatus"], "not-delivered")
        self.assertIn("server onbereikbaar", " ".join(rec["notes"]))
        self.assertIn("hoog-prioriteit niet automatisch geleverd", rec["riskFlags"])
        self.assertIsNone(rec["prov"])


class TestComputationContract(unittest.TestCase):
    def test_derivatie_replay_is_identiek(self):
        reg = mini_registry.build()
        fn = fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=fn,
                                 ops=DEFAULT_OPS)
            first = ex.run()
            again = ex._execute(reg.item("t.clip"), reg.binding("t.clip"))
        base = next(r for r in first if r["lijstItemId"] == "t.clip")
        self.assertEqual(json.dumps(again["values"], sort_keys=True),
                         json.dumps(base["values"], sort_keys=True))


class TestBindingContract(unittest.TestCase):
    def test_auto_heeft_tool_en_manual_heeft_pointer_in_beide_manifesten(self):
        for home in PILOTS.values():
            m = load_manifest(home / "fase-manifest.json")
            for ph in m["phases"]:
                for t in (ph.get("tasks") or []):
                    if t["binding"] in ("auto", "partial"):
                        self.assertIn("tool", t, t["id"])
                    elif t["binding"] == "manual":
                        self.assertIn("manualPointer", t, t["id"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Docs.**
  1. `poc-fundament/README.md`: onder „Regels" toevoegen:

```markdown
- **Import-brug:** consumenten zonder package-bootstrap voegen het fundament toe met
  `sys.path.append(str(REPO_ROOT / "poc-fundament"))` — append, nooit insert(0)
  (insert schaduwt lokale `tests`-packages onder unittest-discovery; M2-les).
  Zie `poc-nspd/tools/gen_fase_manifest.py` als voorbeeld.
```

  en onder de module-tabel een kop `## Matrix van de eerste pilot (minigim)` met de gerenderde tabel. Render hem vanuit de repo-root met de brug-conventie en plak de uitvoer in de README:

```bash
python3 -c "import sys; sys.path.append('poc-fundament'); from fundament.manifest import load_manifest; from fundament.matrix import render_matrix; print(render_matrix(load_manifest('poc-minigim/fase-manifest.json')), end='')"
```
  2. `docs/MINIGIM.md`: in de „Fase-2-haken"-sectie boven de tabel toevoegen:

```markdown
De GREX- en IFC-export-haken zijn sinds M4/M5 modelregister-entries met
`status: "fase-2-haak"` (`poc-minigim/modelregister.json`) — geregistreerd als
intentie, bewust zonder transport-bestaanbewijs; de bron-haken (BRK-eigendom,
AHN/3D, bestemmingsplan/RO-online) horen bij het bronregister en blijven
`manualPointer`s in de Lijst-bindingen.
```

- [ ] **Step 7: Alle vier de suites groen + capture + commit**

```bash
cd poc-minigim && ../nldt/.venv/bin/python tools/capture_golden.py && cd ..
(cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
(cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
(cd poc-nspd && .venv/bin/python -m pytest -q)
(cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q)
git add poc-minigim/minigim/canon.py poc-minigim/tools/capture_golden.py poc-minigim/tests/test_golden.py poc-minigim/tests/test_modelregister.py poc-minigim/modelregister.json poc-fundament/schemas/modelregister.schema.json poc-fundament/tests/test_vtool.py poc-fundament/README.md docs/MINIGIM.md
git commit -m "feat(fundament,poc-minigim): golden-per-fase + V-tool-suite + fase-2-haken in het modelregister + brug-docs (M5 afronding)"
```

---

## Buiten scope van dit plan

- Slotgating voor NSPD in deep-agents (er bestaat nog geen nspd-specialist; de rollen zijn na taak 1 wél alias-klaar).
- riskLevel-high HITL-voorbeeld (wacht op een echt high-model, zie M4).
- Bijdrage van NSPD's scenario-runs aan de matrix (`render_run_matrix`) — de engine-run koppeling volgt als een nspd-specialist er is.
- Overwogen en bewust laten vallen: "n.v.t."-status voor harnas-taken in `render_run_matrix` (cosmetisch; de fase-samenvatting rapporteert wél per fase, inclusief `nvt`-telling).
