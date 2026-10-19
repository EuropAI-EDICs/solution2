# PoC-fundament M3 Implementatieplan (slotgates in deep-agents — het manifest stuurt de wiring)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De deep-agents-wiring wordt afgeleid uit het fase-manifest: per agent exact de tools van zijn fasen (slotgate), en de journal vermeldt fase + gate-verdict per manifest-gedreven run.

**Architecture:** Nieuw `deep-agents/fase_slotgate.py` laadt `poc-minigim/fase-manifest.json`, vertaalt manifest-agentrollen (`intake`, `minigim-specialist`, `geospecialist`, `critic + explainer`) via aliases naar deep-agents-agentnamen, en filtert de subagent-specs uit `pocs.poc_subagents()` op een expliciete tool-pool per agent × tool-klasse. `tools/poc_live.py` journaliseert bij manifest-gedreven runs de fasen en het gate-verdict. Agents die het manifest niet noemt (utrecht, breda, rijnland, normspecialist, formalizer, …) blijven ongewijzigd; zonder manifest is de slotgate een no-op.

**Tech Stack:** Python, deepagents/LangGraph (bestaande wiring), pytest (offline, LLM-vrij).

**Spec:** `docs/superpowers/specs/2026-10-18-poc-fundament-minigim-harnas-design.md` §11 **M3** — exit: slotgate-test (agent buiten zijn fase heeft geen tools); volledige-keten-demo loopt ongewijzigd. M4 (transport-bruggen) en M5 (golden-per-fase, tweede pilot) krijgen eigen plannen.

## Global Constraints

- **Geen regressie:** de volledige deep-agents-suite blijft groen (`cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q`); de volledige-keten-demo-wiring (artifact gates, HITL, laya) verandert niet.
- **Manifest-gedreven PoC's only:** M3 raakt uitsluitend agenten die het minigim-manifest noemt (`intake`, `minigim`, `geospecialist`, `critic`, `explainer`); alle andere agenten have exact dezelfde tools als vóór M3 (getest).
- **Read-only t.o.v. het fundament:** `poc-fundament/` en de PoC-5-runtime worden niet gewijzigd; het manifest wordt alleen gelezen.
- **Gebruikers-werkboom:** `deep-agents/README.md`, `deep-agents/laya_router.py` en `deep-agents/laya_train/` bevatten ongecommit gebruikerswerk — NOOIT stagen of wijzigen. Stage alleen eigen bestanden, nooit `git add -A`.
- **Luid falen:** een onbekende agentrol in het manifest is een `ValueError`, geen stil falen.
- **Offline, LLM-vrij tests** (de llm-marker-suite wordt niet aangeraakt).
- Commit per taak, Nederlands conventioneel (`feat(deep-agents): …`), direct op `main` (repo-conventie).

## Bestandskaart

```
deep-agents/
  fase_slotgate.py              NIEUW — loader, rol-aliassen, tool-pool, apply_slotgate, journal-helper
  pocs.py                       AANGEPAST — poc_subagents() past apply_slotgate toe (2 regels + import)
  tools/poc_live.py             AANGEPAST — na geslaagde run: journal_fases_en_gate() (4 regels)
  tests/test_fase_slotgate.py   NIEUW — slotgate-tests (offline)
```

---

### Task 1: `fase_slotgate.py` — manifest → agent-toolsets

**Files:**
- Create: `deep-agents/fase_slotgate.py`
- Test: `deep-agents/tests/test_fase_slotgate.py` (de module-tests; de wiring-tests komen in taak 2)

**Interfaces:**
- Produces (taak 2 hangt hieraan):
  - `load_manifest(poc: str = "minigim") -> dict | None` — None als er geen manifest is.
  - `resolve_agent_phases(manifest: dict) -> dict[str, list[str]]` — agent-naam → fase-ids; onbekende rol → `ValueError`.
  - `apply_slotgate(specs: list[dict], manifest: dict, poc_agent_names: set[str]) -> list[dict]` — nieuwe specs-lijst (mutatie-vervrij), manifest-agenten gefilterd op fase ∪ catalog-discovery.
  - `journal_fases_en_gate(poc: str, run_dir: Path) -> None` — journal `fase`-regels per manifest-fase + één `gate`-regel met het verdict; no-op zonder manifest of zonder leesbare `run_summary.json`.
- Het filter is vandaag een **no-op met dezelfde uitkomst** als de huidige handmatige wiring (de pool is opgesteld gelijk aan de bestaande ROLE_AGENTS-tools); het verschil is dat de wiring nu manifest-afgeleid en getest is.

- [ ] **Step 1: Schrijf de failing tests** — `deep-agents/tests/test_fase_slotgate.py` (volledig):

```python
"""Slotgate-tests (M3): het manifest stuurt de wiring — agenten buiten hun
fase hebben geen tools. Offline, LLM-vrij (pytest, standaardsuite)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import fase_slotgate as fs


class FakeTool:
    def __init__(self, name: str):
        self.name = name


def _names(tools) -> set[str]:
    return {getattr(t, "name", getattr(t, "__name__", "")) for t in tools}


def test_manifest_bestaat_en_dekt_vijf_fasen():
    manifest = fs.load_manifest("minigim")
    assert manifest is not None
    assert [p["id"] for p in manifest["phases"]] == [
        "F0-intake", "F1-omgevingsanalyse", "F2-gebiedsindeling",
        "F3-doorrekening", "F4-synthese"]


def test_resolve_agent_phases_rol_splits_en_aliassen():
    manifest = fs.load_manifest("minigim")
    out = fs.resolve_agent_phases(manifest)
    assert out["minigim"] == ["F1-omgevingsanalyse", "F3-doorrekening"]
    assert out["intake"] == ["F0-intake"]
    assert out["geospecialist"] == ["F2-gebiedsindeling"]
    assert out["critic"] == ["F4-synthese"] and out["explainer"] == ["F4-synthese"]


def test_onbekende_rol_faalt_luid():
    manifest = {"poc": "x", "methodiek": "m", "phases": [
        {"id": "F1-x", "title": "X", "agent": {"role": "tovenaar"},
         "tasks": [{"id": "t", "binding": "auto",
                    "tool": {"class": "retrieval", "ref": "r"}}]}]}
    with pytest.raises(ValueError):
        fs.resolve_agent_phases(manifest)


def test_apply_slotgate_stript_tool_buiten_de_fase():
    """De kern van het bewijs: een tool die niet in de fase-pool van de agent
    zit wordt gestript — de wiring kan niet stilletjes afdwalen van het manifest."""
    manifest = fs.load_manifest("minigim")
    specs = [
        {"name": "intake", "description": "d", "system_prompt": "p", "model": None,
         "tools": [FakeTool("request_template"), FakeTool("run_minigim_live")]},
        {"name": "utrecht", "description": "d", "system_prompt": "p", "model": None,
         "tools": [FakeTool("run_minigim_live"), FakeTool("run_world_scene")]},
    ]
    out = {s["name"]: s for s in fs.apply_slotgate(specs, manifest, poc_agent_names={"minigim"})}
    intake = _names(out["intake"]["tools"])
    assert "run_minigim_live" not in intake          # buiten intakes fase → gestript
    assert "request_template" in intake              # fase-tool blijft
    utrecht = _names(out["utrecht"]["tools"])        # niet in het manifest → onaangetast
    assert "run_minigim_live" in utrecht and "run_world_scene" in utrecht


def test_catalog_discovery_blijft_binnen_poc_agenten():
    manifest = fs.load_manifest("minigim")
    specs = [{"name": "minigim", "description": "d", "system_prompt": "p", "model": None,
              "tools": [FakeTool("list_recipes"), FakeTool("run_minigim_live"),
                        FakeTool("submit_request")]}]
    out = {s["name"]: s for s in fs.apply_slotgate(specs, manifest, poc_agent_names={"minigim"})}
    minigim = _names(out["minigim"]["tools"])
    assert {"list_recipes", "run_minigim_live"} <= minigim   # catalog + fase-tool
    assert "submit_request" not in minigim                    # F0-gate is niet voor minigim


def test_journal_fases_en_gate(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    (tmp_path / "run_summary.json").write_text(
        json.dumps({"verdict": "pass", "label": "pilot"}), encoding="utf-8")
    fs.journal_fases_en_gate("minigim", tmp_path)
    fases = [e[3]["fase"] for e in events if e[0] == "fase"]
    assert fases == ["F0-intake", "F1-omgevingsanalyse", "F2-gebiedsindeling",
                     "F3-doorrekening", "F4-synthese"]
    gates = [e for e in events if e[0] == "gate"]
    assert len(gates) == 1 and gates[0][3]["verdict"] == "pass"


def test_journal_zonder_manifest_is_stil(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    monkeypatch.setitem(fs.MANIFEST_PATHS, "minigim", Path("/niet/bestaand.json"))
    fs.journal_fases_en_gate("minigim", tmp_path)
    assert events == []


def test_journal_zonder_run_summary_is_stil(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    fs.journal_fases_en_gate("minigim", tmp_path)  # geen run_summary.json
    assert events == []
```

- [ ] **Step 2: Run — verwacht FAIL**

Run: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_fase_slotgate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fase_slotgate'`

- [ ] **Step 3: Implementeer `deep-agents/fase_slotgate.py`** (volledig):

```python
"""Slotgates: het fase-manifest stuurt welke agent welke tools krijgt (M3).

Het fundament-manifest (poc-minigim/fase-manifest.json) declareert per fase
een agent-rol en taken met tool-klasse (retrieval/computation/validation/
report). Deze module vertaalt dat naar de deep-agents-wiring: per agent een
expliciete, manifest-afgeleide toolset (apply_slotgate). Agents die het
manifest niet noemt blijven ongewijzigd; zonder manifest is de slotgate een
no-op — de wiring kan dus niet stilletjes afwijken van de methodiek.

Klassen die een agent niet in zijn pool heeft tellen niet voor díe agent
(rol-splits zoals 'critic + explainer' delen een fase; ieder neemt zijn
eigen deel). Een onbekende ROL faalt daarentegen luid (ValueError).
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

import journal  # noqa: E402  (deep-agents-root staat op sys.path)

# manifest-gedreven PoC's (M3: alleen minigim; M5 volgt bij de tweede pilot)
MANIFEST_PATHS = {
    "minigim": REPO_ROOT / "poc-minigim" / "fase-manifest.json",
}

# manifest-agentrol (genormaliseerd, '+'-gesplitst) → deep-agents agent-naam
ROLE_ALIASES = {
    "intake": "intake",
    "minigim-specialist": "minigim",
    "geospecialist": "geospecialist",
    "critic": "critic",
    "explainer": "explainer",
}

# catalog-discovery (MCP-namen óf wrapper-namen) mag bij alle PoC-agenten —
# leesontdekking van recepten/records is fase-overstijgend en read-only
CATALOG_DISCOVERY = {"search_records", "get_record", "list_recipes", "get_recipe"}


def _tool_name(t) -> str:
    return getattr(t, "name", getattr(t, "__name__", ""))


def load_manifest(poc: str = "minigim") -> dict | None:
    """Manifest van een PoC, of None als er geen is (slotgate = no-op)."""
    path = MANIFEST_PATHS.get(poc)
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_agent_phases(manifest: dict) -> dict[str, list[str]]:
    """agent-naam → fase-ids, via ROLE_ALIASES; onbekende rol = luide faal."""
    out: dict[str, list[str]] = {}
    for ph in manifest["phases"]:
        for rol in str(ph["agent"]["role"]).lower().split("+"):
            alias = ROLE_ALIASES.get(rol.strip())
            if alias is None:
                raise ValueError(
                    f"onbekende manifest-agentrol {ph['agent']['role']!r} in {ph['id']}"
                )
            out.setdefault(alias, []).append(ph["id"])
    return out


def _pool() -> dict[str, dict[str, list]]:
    """tool-klasse → concrete deep-agents tools, per agent.

    Traag geïmporteerd (bij apply_slotgate) om import-cirkels met pocs.py
    te vermijden. De pool is vandaag gelijk aan de bestaande ROLE_AGENTS-
    tools: M3 maakt de wiring manifest-afgeleid, hij verandert haar niet.
    """
    from tools.explain import crosscheck_formal_rule, get_provenance
    from tools.geo import compare_layers, inspect_geo_layer
    from tools.intake import request_template, submit_request, validate_request
    from tools.poc_live import run_minigim_live
    from tools.validate import validate_world_scene

    return {
        "intake": {"validation": [request_template, validate_request, submit_request]},
        # minigim haalt retrieval via de catalog-discovery; computation is de run
        "minigim": {"computation": [run_minigim_live]},
        "geospecialist": {"computation": [inspect_geo_layer, compare_layers]},
        "critic": {"validation": [validate_world_scene]},
        "explainer": {"report": [get_provenance, crosscheck_formal_rule]},
    }


def apply_slotgate(specs: list[dict], manifest: dict, poc_agent_names: set[str]) -> list[dict]:
    """Filter per manifest-agent de tools tot fase ∪ (PoC-agenten: catalog).

    Geeft een nieuwe specs-lijst terug (de invoer wordt niet gemuteerd);
    agenten die het manifest niet noemt gaan ongewijzigd door.
    """
    pool = _pool()
    phases_by_agent = resolve_agent_phases(manifest)
    classes_by_phase = {
        ph["id"]: {(t.get("tool") or {}).get("class")
                   for t in (ph.get("tasks") or []) if t.get("tool")}
        for ph in manifest["phases"]
    }
    allowed: dict[str, set[str]] = {}
    for agent_name, fase_ids in phases_by_agent.items():
        names: set[str] = set()
        if agent_name in poc_agent_names:
            names |= CATALOG_DISCOVERY
        for cls in set().union(*(classes_by_phase[f] for f in fase_ids)):
            for tool in pool.get(agent_name, {}).get(cls) or []:
                names.add(_tool_name(tool))
        allowed[agent_name] = names

    out: list[dict] = []
    for spec in specs:
        name = spec["name"]
        if name not in allowed:
            out.append(spec)
            continue
        out.append({**spec, "tools": [t for t in spec["tools"]
                                      if _tool_name(t) in allowed[name]]})
    return out


def journal_fases_en_gate(poc: str, run_dir: Path) -> None:
    """Journaliseer de manifest-fasen + het gate-verdict van een run (M3).

    Alleen bij manifest-gedreven PoC's; een PoC zonder manifest (of een run
    zonder leesbare run_summary.json) journaalt niets extra — achterwaarts
    compatibel met de bestaande live-panel-tools.
    """
    manifest = load_manifest(poc)
    if manifest is None:
        return
    try:
        summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    verdict = summary.get("verdict", "onbekend")
    for ph in manifest["phases"]:
        journal.append("fase", poc,
                       f"{ph['id']}: {ph['title']} — agent {ph['agent']['role']}",
                       fase=ph["id"])
    journal.append("gate", poc,
                   f"verdict: {verdict} (V0–V3 deterministisch; V4 pending)",
                   fase="F4-synthese", verdict=verdict)
```

Let op: `import journal` bovenin — dat werkt omdat pytest vanaf `deep-agents/` draait (rootdir staat op sys.path, zelfde mechanisme als `import journal` in `tools/poc_live.py`). `journal` importeert niets uit deep-agents modules → geen cirkel.

- [ ] **Step 4: Run — verwacht PASS**

Run: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_fase_slotgate.py -q`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add deep-agents/fase_slotgate.py deep-agents/tests/test_fase_slotgate.py
git commit -m "feat(deep-agents): fase_slotgate — manifest-afgeleide agent-toolsets + fase/gate-journalhelper (M3)"
```

---

### Task 2: Wiring — `poc_subagents` past de slotgate toe; live-run journaliseert fase + gate

**Files:**
- Modify: `deep-agents/pocs.py` (import + 4 regels in `poc_subagents`)
- Modify: `deep-agents/tools/poc_live.py` (4 regels in `run_poc_live`)
- Test: uitbreiding `deep-agents/tests/test_fase_slotgate.py` (wiring-tests) + één testgeval in `deep-agents/tests/test_poc_live.py`

**Interfaces:**
- Consumes: `fase_slotgate.{load_manifest, apply_slotgate}` (taak 1).
- Gedrag: `poc_subagents(mcp_tools=None)` levert vandaag exact dezelfde toolsets als vóór M3 (de pool is daarop ingericht); het verschil is afdwingbaar — een toekomstige tool die niet in het manifest-past wordt gestript, en een manifestwijziging verandert de wiring.
- `run_poc_live` journalt ná de bestaande `tool_result`-regel de fase/gate-regels voor manifest-gedreven PoC's (rijnland/eindhoven: no-op).

- [ ] **Step 1: Schrijf de failing wiring-tests** — voeg toe aan `deep-agents/tests/test_fase_slotgate.py`:

```python
# ---- wiring (taak 2): poc_subagents past de slotgate toe ----

from pocs import poc_subagents  # noqa: E402


def test_poc_subagents_minigim_heeft_fase_en_catalog_tools():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=None)}
    minigim = _names(specs["minigim"]["tools"])
    assert {"list_recipes", "get_recipe", "run_minigim_live"} <= minigim
    assert "submit_request" not in minigim and "validate_world_scene" not in minigim


def test_poc_subagents_agent_buiten_zijn_fase_heeft_geen_tools():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=None)}
    assert "run_minigim_live" not in _names(specs["intake"]["tools"])
    assert "run_minigim_live" not in _names(specs["geospecialist"]["tools"])
    assert _names(specs["critic"]["tools"]) == {"validate_world_scene"}
    assert _names(specs["explainer"]["tools"]) == {"get_provenance", "crosscheck_formal_rule"}


def test_poc_subagents_agenten_buiten_manifest_ongewijzigd():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=None)}
    assert "run_world_scene" in _names(specs["utrecht"]["tools"])
    assert "run_breda_scan" in _names(specs["breda"]["tools"])
    assert _names(specs["normspecialist"]["tools"]) == {"search_norms", "submit_norm_cards"}


def test_poc_subagents_mcp_catalog_komt_door_de_slotgate():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=[
        FakeTool("search_records"), FakeTool("get_record"), FakeTool("run_opportunity_map")])}
    minigim = _names(specs["minigim"]["tools"])
    assert {"search_records", "get_record", "run_minigim_live"} <= minigim
    assert "list_recipes" not in minigim
```

En voeg aan `deep-agents/tests/test_poc_live.py` (binnen het bestand, op module-niveau na de bestaande tests) toe:

```python
def test_minigim_live_journaliseert_fase_en_gate(live_env):
    from tools import poc_live as pl

    live_env["monkeypatch"].setattr(
        pl.subprocess, "run",
        live_env["fake_engine"]({
            "20260101T000000Z-minigim-gebiedscheck/report.html": "<html>r</html>",
            "20260101T000000Z-minigim-gebiedscheck/run_summary.json": json.dumps(
                {"verdict": "pass", "label": "pilot"}),
        }))
    out = pl.run_minigim_live()
    assert out["poc"] == "minigim"
    events = live_env["events"]
    fases = [e[3]["fase"] for e in events if e[0] == "fase"]
    assert fases == ["F0-intake", "F1-omgevingsanalyse", "F2-gebiedsindeling",
                     "F3-doorrekening", "F4-synthese"]
    gates = [e for e in events if e[0] == "gate"]
    assert len(gates) == 1 and gates[0][3]["verdict"] == "pass"
    # de bestaande tool_result-regel met de viz-referentie blijft bestaan
    assert any(e[0] == "tool_result" and e[3].get("viz") for e in events)
```

- [ ] **Step 2: Run — verwacht FAIL op precies één test.** De vier wiring-tests zijn regresie-bewakers: zonder wiring zijn hun `not in`-asserties al waar (de agenten hebben die tools vandaag nooit tegelijk gehad), dus die zijn al groen vóór implementatie — correct, want M3 verandert de uitkomst niet, hij maakt haar manifest-afgeleid. Het enige falende geval vóór implementatie is de journal-test: `test_minigim_live_journaliseert_fase_en_gate` (nog geen fase/gate-events).

Run: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_fase_slotgate.py tests/test_poc_live.py -q`
Expected: 1 failed (`test_minigim_live_journaliseert_fase_en_gate`), rest passed

- [ ] **Step 3: Implementeer de wiring.**

In `deep-agents/pocs.py`:

1. Bij de imports (na `from tools.validate import validate_world_scene`):

```python
from fase_slotgate import apply_slotgate, load_manifest  # noqa: E402
```

2. In `poc_subagents`, vervang de laatste regel (`return poc_specs + role_specs`) door:

```python
    specs = poc_specs + role_specs
    # M3 slotgate: het fase-manifest stuurt de toolsets van de agenten die
    # het noemt; zonder manifest (andere PoC's) ongewijzigd.
    manifest = load_manifest()
    if manifest is not None:
        specs = apply_slotgate(specs, manifest,
                               poc_agent_names={s["name"] for s in POC_AGENTS})
    return specs
```

In `deep-agents/tools/poc_live.py`:

1. Bij de imports (na `import journal`):

```python
from fase_slotgate import journal_fases_en_gate  # noqa: E402
```

2. In `run_poc_live`, direct ná het bestaande `journal.append("tool_result", …)`-blok en vóór `return { … }`:

```python
    # M3: manifest-fasen + gate-verdict journaal (no-op voor PoC's zonder manifest)
    run_dirs = sorted(work.glob("*/run_summary.json"))
    if run_dirs:
        journal_fases_en_gate(poc, run_dirs[-1].parent)
```

- [ ] **Step 4: Run beide testbestanden + de volledige deep-agents-suite — verwacht allemaal groen**

Run: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_fase_slotgate.py tests/test_poc_live.py tests/test_agent_wiring.py -q` → expected: alle passed; daarna de volledige suite `… -m pytest tests -q` → expected: alles groen (skips alleen waar die al waren, bv. llm-marker zonder endpoint).

- [ ] **Step 5: Commit**

```bash
git add deep-agents/pocs.py deep-agents/tools/poc_live.py deep-agents/tests/test_fase_slotgate.py deep-agents/tests/test_poc_live.py
git commit -m "feat(deep-agents): slotgate in poc_subagents + fase/gate-journal bij live-runs (M3)"
```

---

## Buiten scope van dit plan

- **M4**: computation-tool → nldt-processId en A2A Agent Card; riskLevel-tiering (HITL-voorbeeld).
- **M5**: golden-per-fase, tweede pilot-PoC op het fundament, V-tool-suite-uitbreiding.
- Laya-routing naar fase-agent (blijft zoals hij is; de slotgate beperkt tools, niet de routing).
- README-updates in `deep-agents/` (bevat ongecommit gebruikerswerk — pas op na die commit).
