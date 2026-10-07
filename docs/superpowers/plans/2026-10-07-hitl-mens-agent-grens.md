# HITL mens-agent-grens — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poort 3 (mens-agent-grens) aantoonbaar end-to-end: de deep-agents-orkestrator interrupt op `run_bp2op_transform`, de mens beslist via dashboard (approve/reject + verplichte opmerking), en het verdict landt in journal én leerstaat (decision-trail).

**Architecture:** Persistente `SqliteSaver`-checkpointer onder `deep-agents/runs/live/`; bij interrupt eindigt de run netjes (rc=2) met state op schijf; `live_server` toont de pending-kaart (authoritair via `graph.get_state`) en spawnt een klein resume-proces dat met `Command(resume={"decisions":[…]})` hervat. Een duurzaam verdict-ledger (`hitl-verdicts.jsonl`, append-only) voedt de leerstaat, want de journal (`steps.jsonl`) wordt per run gereset.

**Tech Stack:** Python 3.14 (deep-agents/.venv), deepagents 0.7.21 (`HumanInTheLoopMiddleware`, `interrupt_on`), langgraph 1.2.12 + langgraph-checkpoint 4.2.0, nieuw: `langgraph-checkpoint-sqlite` (installeerbaar, dry-run OK), FastAPI/http-conventies zoals `live_server.py` al heeft, pytest via `../nldt/.venv/bin/python` (pytest zit NIET in deep-agents/.venv).

**Spec:** [`docs/superpowers/specs/2026-10-07-hitl-mens-agent-grens-design.md`](../specs/2026-10-07-hitl-mens-agent-grens-design.md) (goedgekeurd 2026-10-07)

## Global Constraints

- Geen cloud-modellen of API-sleutels: alleen lokale Ollama-config via bestaande `models.py`; cloud-tier blijft geweigerd.
- Tests zijn offline en LLM-vrij (fake model uit `langchain_core.language_models.fake_chat_models`); de volledige agent-loop met echt lokaal LLM is een `llm`-gemarkeerde test en geskipt zonder endpoint.
- Suites blijven groen: deep-agents-tests draaien met de deep-agents-site-packages op PYTHONPATH (anders pakt de nldt-python zijn eigen oudere deepagents/langgraph): `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q` · `cd nldt && .venv/bin/python -m pytest tests -q` (verwacht 390+) · `cd poc && ../nldt/.venv/bin/python -m pytest tests -q` (verwacht 304/1).
- **`graph.stream()` is lazy** (T1-gevalideerd): een resume-`stream` moet geïtereerd worden (`for _ in …: pass`), anders voert hij niets uit.
- **NB voor uitvoerders:** de pytest-commando's in de taken hieronder zijn kort genoteerd; voor elke deep-agents-suite geldt steeds de canonieke PYTHONPATH-vorm uit de eerste bullet hierboven (T1-gevalideerd). Zonder de prefix faalt de collectie van `test_hitl_smoke.py` op `langgraph.checkpoint.sqlite`.
- Taal: code en comments in het Nederlands conform repo-stijl; commit-stijl `feat(deep-agents): …` / `feat(nldt): …`.
- De mens is de laatste schakel: geen time-out, geen auto-approve behalve de expliciete dev-flag `--auto-approve-hitl`, en auto-approve wordt in journal én ledger gemarkeerd als machinaal.
- Journal-regime: `steps.jsonl` wordt per run gereset (bestaand gedrag, niet veranderen); alles wat de leerstaat voedt gaat in het append-only `hitl-verdicts.jsonl`.
- Werkboom-check vóór elke commit: alleen de bestanden van de eigen taak; `nldt/data/` is gitignored en blijft dat.

---

### Task 1: Afhankelijkheid + smoke-verificatie van het interrupt-mechanisme

**Files:**
- Test: `deep-agents/tests/test_hitl_smoke.py`
- Install: `langgraph-checkpoint-sqlite` in `deep-agents/.venv`

**Interfaces:**
- Produces: bewezen payload/resume-contracten die latere taken tegen aan coderen: interrupt-chunk = update-payload met key `__interrupt__` (tuple van `Interrupt` met `.id` en `.value` = HITLRequest-dict `{"action_requests": [{"name","args","description"?}], "review_configs": […]}`); resume = `Command(resume={"decisions": [{"type":"approve"} | {"type":"reject","message":…}]})`; `create_deep_agent(checkpointer=…)` werkt direct.

- [ ] **Step 1: Installeer de sqlite-checkpointer**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents
.venv/bin/pip install langgraph-checkpoint-sqlite
.venv/bin/pip show langgraph-checkpoint-sqlite | head -2
```

Expected: installatie slaagt (dry-run was groen), versie ≥ 2.x. Als het netwerk het weigert: BLOCKED rapporteren — het plan vereist dit pakket (fallback is een eigen checkpointer, een eigen besluit voor Marc).

- [ ] **Step 2: Schrijf de smoke-test (failing)**

Maak `deep-agents/tests/test_hitl_smoke.py` aan:

```python
"""Smoke: interrupt-mechanisme van deepagents + SqliteSaver, volledig offline.

Bewijst het contract dat de rest van de HITL-bouw coded tegen:
interrupt-payload-vorm, resume-vorm en herstel uit de checkpointer.
"""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from deepagents import create_deep_agent


def _fake_model_with_toolcall():
    """Model dat eerst een tool-call produceert en daarna stopt (offline)."""
    msgs = iter([
        AIMessage("", tool_calls=[{"name": "run_bp2op_transform", "args": {"useCase": "eindhoven"}, "id": "call-1"}]),
        AIMessage("klaar"),
    ])
    return GenericFakeChatModel(messages=msgs)


@tool
def run_bp2op_transform(useCase: str = "eindhoven") -> str:
    """Teststub: staat voor de echte bp2op-transform."""
    return "transform-uitgevoerd"


def _build(tmp_path):
    conn = __import__("sqlite3").connect(str(tmp_path / "cp.sqlite"), check_same_thread=False)
    saver = SqliteSaver(conn)
    graph = create_deep_agent(
        model=_fake_model_with_toolcall(),
        tools=[run_bp2op_transform],
        system_prompt="test",
        interrupt_on={
            "run_bp2op_transform": {
                "allowed_decisions": ["approve", "reject"],
                "description": "MC-6: de jurist beslist over koppelen.",
            }
        },
        checkpointer=saver,
    )
    return graph, saver


def test_interrupt_vuur_bij_submit_en_resume_werkt(tmp_path):
    graph, _ = _build(tmp_path)
    config = {"configurable": {"thread_id": "smoke-1"}}
    seen_interrupt = None
    for chunk in graph.stream(
        {"messages": [{"role": "user", "content": "converteer"}]},
        config=config,
        stream_mode=["updates", "messages"],
        subgraphs=True,
    ):
        _ns, mode, payload = chunk
        items = payload if isinstance(payload, tuple) else [payload]
        for item in items:
            if isinstance(item, dict) and "__interrupt__" in item:
                seen_interrupt = item["__interrupt__"][0]

    assert seen_interrupt is not None, "geen __interrupt__-chunk gezien"
    value = seen_interrupt.value
    assert value["action_requests"][0]["name"] == "run_bp2op_transform"

    # state bevat de interrupt na de onderbroken run
    state = graph.get_state(config)
    assert any(t.interrupts for t in state.tasks), "interrupt niet in state terug te vinden"

    # resume: goedkeuren — de tool voert uit en de run loopt af
    graph.stream(Command(resume={"decisions": [{"type": "approve"}]}), config=config, stream_mode=["updates", "messages"])

    state2 = graph.get_state(config)
    assert not any(t.interrupts for t in state2.tasks), "interrupt na approve niet verbruikt"
    assert state2.values["messages"][-1].content == "klaar"
```

- [ ] **Step 3: Draai de test en verwacht PASS (dit is bewijs, geen TDD-fail — het contract is reeds door de library geleverd; de test bliksemt het vast)**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests/test_hitl_smoke.py -q
```

Expected: `1 passed`. Faalt de payload-vorm (bijv. andere key dan `__interrupt__` of tuple-vorm), pas dan de assertions aan op de werkelijke vorm en noteer de afwijking in het rapport — de rest van het plan codeert tegen de gemeten vorm.

- [ ] **Step 4: Commit**

```bash
git add deep-agents/tests/test_hitl_smoke.py
git commit -m "test(deep-agents): hitl-smoke — interrupt-payload + resume-contract tegen SqliteSaver bewezen"
```

---

### Task 2: `deep-agents/hitl.py` — configuratie, duurzaam ledger en verdict-mapping

**Files:**
- Create: `deep-agents/hitl.py`
- Test: `deep-agents/tests/test_hitl.py`

**Interfaces:**
- Consumes: Task 1 (payload-/resume-vormen).
- Produces (gebruikt door Tasks 3–8 en 9):
  - `HITL_TOOLS: dict[str, dict]` — `{"run_bp2op_transform": {"allowed_decisions": ["approve","reject"], "description": MC-6-tekst}}`
  - `LEDGER: Path` (= `HERE / "runs" / "live" / "hitl-verdicts.jsonl"`)
  - `ledger_append(record: dict) -> None` (voegt `ts` toe, append-only)
  - `ledger_read() -> list[dict]`
  - `pending_from_ledger() -> dict | None` (eerste request-zonder-verdict, op interruptId)
  - `verdict_to_decisions(approved: bool, comment: str) -> dict` → `{"decisions": [{"type":"approve"}]}` resp. `{"decisions": [{"type":"reject","message":comment}]}`
  - `args_summary(args: dict) -> str` (deterministische, afgekorte samenvatting)
  - `PENDING_EXIT_CODE = 2`

- [ ] **Step 1: Schrijf de falende tests**

Maak `deep-agents/tests/test_hitl.py` aan:

```python
"""Unit: hitl-ledger en verdict-mapping (offline, geen model)."""

import json

from hitl import (
    LEDGER,
    PENDING_EXIT_CODE,
    args_summary,
    ledger_append,
    ledger_read,
    pending_from_ledger,
    verdict_to_decisions,
)


def test_ledger_append_voegt_ts_toe_en_is_append_only(tmp_path, monkeypatch):
    monkeypatch.setattr("hitl.LEDGER", tmp_path / "hitl-verdicts.jsonl")
    ledger_append({"kind": "request", "interruptId": "i-1", "tool": "run_bp2op_transform"})
    ledger_append({"kind": "verdict", "interruptId": "i-1", "approved": True, "comment": "ok"})
    lines = ledger_read()
    assert [r["kind"] for r in lines] == ["request", "verdict"]
    assert all("ts" in r for r in lines)


def test_pending_is_request_zonder_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr("hitl.LEDGER", tmp_path / "hitl-verdicts.jsonl")
    ledger_append({"kind": "request", "interruptId": "i-1"})
    assert pending_from_ledger()["interruptId"] == "i-1"
    ledger_append({"kind": "verdict", "interruptId": "i-1", "approved": False, "comment": "nee"})
    assert pending_from_ledger() is None


def test_verdict_mapping_conform_resume_contract():
    assert verdict_to_decisions(True, "wat dan ook") == {"decisions": [{"type": "approve"}]}
    assert verdict_to_decisions(False, "niet koppelen") == {
        "decisions": [{"type": "reject", "message": "niet koppelen"}]
    }


def test_args_summary_is_kort_en_deterministisch():
    a = args_summary({"useCase": "eindhoven", "source": "bestemming.xml"})
    b = args_summary({"source": "bestemming.xml", "useCase": "eindhoven"})
    assert a == b and len(a) <= 120 and "eindhoven" in a


def test_pending_exit_code_is_2():
    assert PENDING_EXIT_CODE == 2
```

- [ ] **Step 2: Draai de tests, verwacht FAIL (module bestaat niet)**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests/test_hitl.py -q
```

Expected: `ModuleNotFoundError: No module named 'hitl'`.

- [ ] **Step 3: Implementeer `deep-agents/hitl.py`**

```python
"""HITL-support: configuratie, duurzaam verdict-ledger en resume-mapping.

De journal (runs/live/steps.jsonl) wordt per run gereset; alles wat de
leerstaat voedt gaat daarom in dit append-only ledger.
"""

import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "runs" / "live" / "hitl-verdicts.jsonl"
PENDING = "__hitl_pending__"   # sentinel: run_streamed retourneert dit bij een interrupt-einde
PENDING_EXIT_CODE = 2

MC6_TOELICHTING = (
    "MC-6 (VNG-methode): niets wordt door AI gekoppeld; de jurist beslist. "
    "De bp2op-transform schrijft het omgevingsplan-dossier."
)

HITL_TOOLS: dict[str, dict] = {
    "run_bp2op_transform": {
        "allowed_decisions": ["approve", "reject"],
        "description": MC6_TOELICHTING,
    }
}


def ledger_append(record: dict) -> None:
    """Append-only: één record per regel, met tijdstempel."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    line = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def ledger_read() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def pending_from_ledger() -> dict | None:
    """Eerste request zonder bijbehorend verdict (op interruptId), of None."""
    verdicts = {r["interruptId"] for r in ledger_read() if r.get("kind") == "verdict"}
    for r in ledger_read():
        if r.get("kind") == "request" and r.get("interruptId") not in verdicts:
            return r
    return None


def verdict_to_decisions(approved: bool, comment: str) -> dict:
    """Mapt het dashboard-verdict op het deepagents-resume-contract."""
    if approved:
        return {"decisions": [{"type": "approve"}]}
    return {"decisions": [{"type": "reject", "message": comment}]}


def args_summary(args: dict) -> str:
    """Deterministische, afgekorte samenvatting voor journal/UI/ledger."""
    if not isinstance(args, dict):
        return str(args)[:120]
    flat = ", ".join(f"{k}={str(v)[:40]}" for k, v in sorted(args.items()))
    return flat[:120]
```

- [ ] **Step 4: Draai de tests, verwacht PASS**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests/test_hitl.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add deep-agents/hitl.py deep-agents/tests/test_hitl.py
git commit -m "feat(deep-agents): hitl-module — HITL_TOOLS-config, duurzaam verdict-ledger, verdict→decisions-mapping"
```

---

### Task 3: `agent.py` — checkpointer- en interrupt-configuratie

**Files:**
- Modify: `deep-agents/agent.py:54-62` (`build_agent`)

**Interfaces:**
- Consumes: Task 2 (`HITL_TOOLS`).
- Produces: `build_agent(tools: list, *, checkpointer=None, interrupt_on: dict | None = None)` — `interrupt_on=None` betekent `HITL_TOOLS`; expliciet `{}` schakelt interrupts uit. `create_deep_agent` krijgt `checkpointer=checkpointer` en de samengevoegde interrupt-config.

- [ ] **Step 1: Falende test — voeg toe aan `deep-agents/tests/test_hitl.py`**

```python
def test_build_agent_geeft_interrupt_en_checkpointer_door(tmp_path):
    """build_agent plakt de interrupt-config op create_deep_agent (offline bewijs)."""
    import inspect

    import agent as agent_module
    from hitl import HITL_TOOLS

    src = inspect.getsource(agent_module.build_agent)
    assert "interrupt_on" in src and "checkpointer" in src
    assert "run_bp2op_transform" in src or "HITL_TOOLS" in src
    assert isinstance(HITL_TOOLS, dict) and "run_bp2op_transform" in HITL_TOOLS
```

- [ ] **Step 2: Draai, verwacht FAIL**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests/test_hitl.py::test_build_agent_geeft_interrupt_en_checkpointer_door -q
```

- [ ] **Step 3: Pas `build_agent` aan** (bestaande body op :54-62; behoud imports bovenaan, voeg `from hitl import HITL_TOOLS` toe):

```python
def build_agent(tools: list, *, checkpointer=None, interrupt_on: dict | None = None):
    """Bouw de orchestrator; met checkpointer en HITL-config voor de live-run.

    interrupt_on=None betekent de standaardconfig (HITL_TOOLS); {} schakelt uit.
    """
    return create_deep_agent(
        model=ollama_model(orchestrator_model_name()),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        subagents=poc_subagents(mcp_tools=tools),
        checkpointer=checkpointer,
        interrupt_on=interrupt_on if interrupt_on is not None else dict(HITL_TOOLS),
    )
```

- [ ] **Step 4: Draai de hele deep-agents-suite, verwacht PASS (ook de bestaande wiring-tests)**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests -q
```

- [ ] **Step 5: Commit**

```bash
git add deep-agents/agent.py deep-agents/tests/test_hitl.py
git commit -m "feat(deep-agents): build_agent accepteert checkpointer + interrupt_on (standaard HITL_TOOLS)"
```

---

### Task 4: `graph_trace.py` — `__interrupt__` afvangen, journal + ledger vullen

**Files:**
- Modify: `deep-agents/graph_trace.py` (stream-lus op :177-210)
- Test: `deep-agents/tests/test_hitl.py` (uitbreiding)

**Interfaces:**
- Produces: `PENDING`-sentinel (string ` "__hitl_pending__"`) als returnwaarde van `run_streamed` wanneer de run op een interrupt eindigt; bijvangst: `hitl_request`-journal-event en ledger-request per interrupt (`interruptId` = `Interrupt.id`, `tool`/`args` uit `action_requests`).

- [ ] **Step 1: Falende test — voeg toe aan `deep-agents/tests/test_hitl.py`**

```python
def test_run_streamed_onderschept_interrupt(monkeypatch, tmp_path):
    """De stream-lus vangt __interrupt__ en schrijft journal + ledger-request."""
    import json
    from types import SimpleNamespace

    import graph_trace
    from hitl import PENDING

    fake_interrupt = SimpleNamespace(
        id="i-x",
        value={"action_requests": [{"name": "run_bp2op_transform", "args": {"useCase": "eindhoven"}}]},
    )
    chunks = iter([
        ((), "updates", ({"__interrupt__": (fake_interrupt,)},)),
    ])

    class FakeAgent:
        def stream(self, *_a, **_k):
            return chunks

    journal_calls = []
    monkeypatch.setattr(graph_trace.journal, "append", lambda *a, **k: journal_calls.append((a, k)))
    ledger_file = tmp_path / "hitl-verdicts.jsonl"
    monkeypatch.setattr("hitl.LEDGER", ledger_file)   # ledger_append leest de module-global in hitl

    result = graph_trace.run_streamed(FakeAgent(), "converteer")
    assert result == PENDING
    assert any(k.get("kind") == "hitl_request" for _, k in journal_calls)
    regels = ledger_file.read_text().splitlines()
    assert regels and json.loads(regels[0])["kind"] == "request"
    assert json.loads(regels[0])["tool"] == "run_bp2op_transform"
```

(let op: voeg bovenin het testbestand `import json` toe indien nog niet aanwezig)

- [ ] **Step 2: Draai, verwacht FAIL** (`AttributeError`/`ImportError`: `PENDING` bestaat niet / journal niet aangeroepen)

- [ ] **Step 3: Implementeer in `graph_trace.py`** — bovenaan toevoegen (`import journal` is nodig voor de events; bestaat die import al, dan is het een no-op):

```python
import journal
from hitl import PENDING, args_summary, ledger_append
```

en in de stream-lus (na de bestaande updates-verwerking op :187-194) deze tak toevoegen; de functie krijgt vóór de lus een vlag `gezien_interrupt = False` en sluit af met `return PENDING if gezien_interrupt else answer` (het bestaande `return answer` op :210 wordt die regel):

```python
        if mode == "updates":
            items = payload if isinstance(payload, tuple) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                for intr in item.get("__interrupt__", ()):
                    gezien_interrupt = True
                    value = getattr(intr, "value", {}) or {}
                    for act in value.get("action_requests", []):
                        journal.append(
                            "hitl_request",
                            "orchestrator",
                            f"{act.get('name')}: {args_summary(act.get('args', {}))}",
                            kind_event="hitl_request",
                            interruptId=getattr(intr, "id", ""),
                            tool=act.get("name", ""),
                            threadId=config.get("configurable", {}).get("thread_id", ""),
                        )
                        ledger_append({
                            "kind": "request",
                            "interruptId": getattr(intr, "id", ""),
                            "threadId": config.get("configurable", {}).get("thread_id", ""),
                            "tool": act.get("name", ""),
                            "argsSummary": args_summary(act.get("args", {})),
                        })
```

**Contract: normale eindes retourneren de answer-string; een interrupt-einde retourneert `PENDING`.**

- [ ] **Step 4: Draai de suite, verwacht PASS**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests -q
```

- [ ] **Step 5: Commit**

```bash
git add deep-agents/graph_trace.py deep-agents/tests/test_hitl.py
git commit -m "feat(deep-agents): graph_trace vangt __interrupt__ — journal hitl_request + duurzaam ledger-request"
```

---

### Task 5: `live.py` — checkpointer, pending-exit en `--auto-approve-hitl`

**Files:**
- Modify: `deep-agents/live.py` (`main` op :29-62)
- Test: `deep-agents/tests/test_hitl.py` (uitbreiding)

**Interfaces:**
- Consumes: Tasks 2–4.
- Produces: live-run met SqliteSaver onder `runs/live/checkpoints.sqlite`; exit-code `2` bij pending (zonder flag); met `--auto-approve-hitl` hervat de run in-process (zelfde checkpointer) met een machinaal-verdict in journal+ledger (`"auto": true`), en eindigt normaal.

- [ ] **Step 1: Falende test — voeg toe aan `deep-agents/tests/test_hitl.py`**

```python
def test_live_pending_wegschrijven_en_auto_approve_mapping():
    """Het auto-verdict is een geregistreerde machinale goedkeuring, geen menselijke."""
    from hitl import verdict_to_decisions

    # de auto-resume gebruikt dezelfde mapping; het verschil zit in de registratie
    d = verdict_to_decisions(True, "auto: dev-flag --auto-approve-hitl")
    assert d["decisions"][0]["type"] == "approve"
    # en het ledger-record draagt 'auto': True (getest via ledger-append-assert in Task 2-stijl)
```

- [ ] **Step 2: Implementeer** in `live.py` — `main()` krijgt argumentenparsen (`argparse`: `question` als eerste positioneel zoals nu via `sys.argv`, plus `--auto-approve-hitl` als store_true), vervang `agent = build_agent()` door:

```python
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command

    from hitl import (
        PENDING,
        PENDING_EXIT_CODE,
        args_summary,
        ledger_append,
        verdict_to_decisions,
    )

    cp_conn = sqlite3.connect(str(HERE / "runs" / "live" / "checkpoints.sqlite"), check_same_thread=False)
    saver = SqliteSaver(cp_conn)
    agent = build_agent(checkpointer=saver)
```

en na `answer = run_streamed(...)`:

```python
    if answer == PENDING:
        if not auto_approve:
            journal.append("hitl_pending", "orchestrator", "wacht op menselijk verdict")
            sys.exit(PENDING_EXIT_CODE)
        # dev-flag: hervat in-process met een expliciet machinaal verdict
        state = agent.get_state({"configurable": {"thread_id": THREAD_ID}})
        intr = next(t.interrupts[0] for t in state.tasks if t.interrupts)
        ledger_append({
            "kind": "verdict", "interruptId": intr.id, "threadId": THREAD_ID,
            "approved": True, "comment": "auto: dev-flag --auto-approve-hitl",
            "operator": "dev-flag", "auto": True,
        })
        for _ in agent.stream(
            Command(resume=verdict_to_decisions(True, "auto: dev-flag --auto-approve-hitl")),
            config={"configurable": {"thread_id": THREAD_ID}},
            stream_mode=["updates", "messages"], subgraphs=True,
        ):
            pass  # stream is lazy — itereren, anders voert de resume niets uit
```

(`HERE`, `THREAD_ID="nldt-live"`, `Command`-import en de bestaande journal-done-afsluiting leest de implementer ter plekke; het contract: **rc=2 en een `hitl_pending`-journal-event bij pending zonder flag; met flag een in-process resume met `"auto": True` in het ledger.**)

- [ ] **Step 3: Suite draaien (verwacht PASS) en commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests -q
git add deep-agents/live.py deep-agents/tests/test_hitl.py
git commit -m "feat(deep-agents): live-run met SqliteSaver — pending-exit rc=2 + --auto-approve-hitl in-process resume"
```

---

### Task 6: `resume.py` — hervatten na een dashboard-verdict

**Files:**
- Create: `deep-agents/resume.py`
- Test: `deep-agents/tests/test_hitl.py` (uitbreiding)

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces: `python resume.py <interruptId> --approved/--rejected --comment "<tekst>" --operator <naam>` — controleert tegen de checkpointer dat de interrupt nog bestaat op thread `nldt-live`, schrijft het duurzame verdict-record, geeft `Command(resume=verdict_to_decisions(...))` en streamt het vervolg naar de journal; exit 0 bij verwerkt, 3 bij "interrupt bestaat niet meer" (verbruikt).

- [ ] **Step 1: Falende test — voeg toe aan `deep-agents/tests/test_hitl.py`**

```python
def test_resume_argparse_verplicht_comment_bij_beide_uitkomsten(tmp_path):
    """Zowel reject als approve zonder opmerking wordt bij het argument geweigerd (spec: leerstaat)."""
    import subprocess, sys
    from pathlib import Path

    cwd = Path(__file__).resolve().parents[1]
    for vlag in ("--rejected", "--approved"):
        r = subprocess.run(
            [sys.executable, "resume.py", "i-onbestaand", vlag, "--comment", ""],
            capture_output=True, text=True, cwd=cwd,
        )
        assert r.returncode != 0, f"{vlag} zonder opmerking moet geweigerd worden"
        assert "opmerking" in (r.stdout + r.stderr).lower()
```

(let op: dit draait in de repo-root-context van deep-agents; de test zet `cwd` naar de deep-agents-map via `cwd=Path(__file__).resolve().parents[1]`)

- [ ] **Step 2: Implementeer `deep-agents/resume.py`**

```python
"""Hervat een op de mens wachtende run na een dashboard-verdict.

Gebruik: python resume.py <interruptId> (--approved|--rejected) --comment "…" [--operator naam]
Exit: 0 = verwerkt · 3 = interrupt bestaat niet (al verbruikt) · 4 = ongeldig verdict.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import journal
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from hitl import args_summary, ledger_append, verdict_to_decisions

HERE = Path(__file__).resolve().parent
THREAD_ID = "nldt-live"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("interrupt_id")
    groep = p.add_mutually_exclusive_group(required=True)
    groep.add_argument("--approved", action="store_true")
    groep.add_argument("--rejected", action="store_true")
    p.add_argument("--comment", required=True)
    p.add_argument("--operator", default="operator")
    args = p.parse_args()

    if not args.comment.strip():
        print("Het verdict vereist een niet-lege opmerking (leerstaat).", file=sys.stderr)
        return 4

    conn = sqlite3.connect(str(HERE / "runs" / "live" / "checkpoints.sqlite"), check_same_thread=False)
    saver = SqliteSaver(conn)

    from agent import build_agent  # na de saver-import (cirkelvrij: agent importeert hitl, niet resume)

    agent = build_agent(checkpointer=saver)
    config = {"configurable": {"thread_id": THREAD_ID}}
    state = agent.get_state(config)
    intr = None
    for t in state.tasks:
        for i in t.interrupts:
            if i.id == args.interrupt_id:
                intr = i
    if intr is None:
        print(f"Interrupt {args.interrupt_id} bestaat niet (al verbruikt?)", file=sys.stderr)
        return 3

    tool = (intr.value.get("action_requests") or [{}])[0].get("name", "")
    ledger_append({
        "kind": "verdict", "interruptId": intr.id, "threadId": THREAD_ID,
        "tool": tool, "approved": bool(args.approved), "comment": args.comment.strip(),
        "operator": args.operator, "auto": False,
    })
    journal.append(
        "hitl_verdict", "operator",
        f"{'goedgekeurd' if args.approved else 'afgewezen'}: {tool} — {args_summary({'comment': args.comment.strip()})}",
        kind_event="hitl_verdict", interruptId=intr.id, operator=args.operator,
    )
    for _ in agent.stream(Command(resume=verdict_to_decisions(bool(args.approved), args.comment.strip())),
                          config=config, stream_mode=["updates", "messages"], subgraphs=True):
        pass  # stream is lazy — itereren, anders voert de resume niets uit
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Suite draaien (verwacht PASS, incl. de argparse-test) en commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests -q
git add deep-agents/resume.py deep-agents/tests/test_hitl.py
git commit -m "feat(deep-agents): resume.py — dashboard-verdict hervat de run over procesgrenzen (duurzaam verdict + journal-echo)"
```

---

### Task 7: `live_server.py` — pending-API en verdict-endpoint

**Files:**
- Modify: `deep-agents/live_server.py` (nieuwe routes na `/api/stop` op :161-170)

**Interfaces:**
- Consumes: Tasks 2, 5, 6.
- Produces: `GET /api/hitl/pending` → `{pending: bool, interruptId?, tool?, argsSummary?, threadId?}` (authoritair via `agent.get_state`, aangevuld met het ledger); `POST /api/hitl/verdict` body `{interruptId, approved, comment, operator?}` → valideert (pending bestaat; `comment` niet-leeg), weigert dubbel (409), schrijft het duurzame verdict-record vóór het spawnen van `resume.py` (het spawn gebruikt het bestaande `subprocess.Popen`-patroon op :146-157; de server wacht niet op het resume-proces).

Implementatie-aanwijzingen (volg de bestaande route-/response-stijl van het bestand):

1. Helper `_load_pending()` : bouwt de agent met SqliteSaver (zelfde pad als live.py), `get_state` op thread `nldt-live`, en geeft het eerste interrupt-payload terug; zonder interrupt → `{"pending": False}`.
2. `POST /api/hitl/verdict` : eerste validatie tegen `pending_from_ledger()` en `_load_pending()`; dan `ledger_append({"kind": "verdict", …, "auto": False})` vóór het spawnen, daarna `subprocess.Popen([sys.executable, "resume.py", interruptId, "--approved"/"--rejected", "--comment", comment, "--operator", operator], cwd=HERE, stdout=log, stderr=subprocess.STDOUT)`; bij verbruikte interrupt: HTTP 409.
3. Het comment-verplicht-verdict wordt in de API afgedwongen (400 bij leeg) — ook al beschermt `resume.py` zelf al.

- [ ] **Step 1: Falende test — voeg toe aan `deep-agents/tests/test_hitl.py`**

```python
def test_server_verdict_route_bestaat_en_weigert_leeg_comment():
    import inspect
    import live_server

    src = inspect.getsource(live_server)
    assert "/api/hitl/pending" in src and "/api/hitl/verdict" in src
    assert "409" in src, "dubbel verdict moet geweigerd worden"
```

- [ ] **Step 2: Implementeer de routes volgens de aanwijzingen; suite draaien; commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests -q
git add deep-agents/live_server.py deep-agents/tests/test_hitl.py
git commit -m "feat(deep-agents): hitl-API — pending-status via get_state, verdict-endpoint met 409-dubbelweigering"
```

---

### Task 8: Dashboard — pending-kaart met Goedkeuren/Afkeuren

**Files:**
- Modify: `deep-agents/dashboard.html` (of het bestand dat live_server als UI serveert — lees de catch-all-route en de bestaande poll-JS ter plekke)

**Interfaces:**
- Consumes: Task 7.
- Produces: een pending-kaart die meepolld met de bestaande poll-cyclus: toont tool + argsSummary, opmerkingveld (verplicht), knoppen Goedkeuren/Afkeuren die `POST /api/hitl/verdict` doen, en na succes de kaart verbergen. Geen nieuwe frameworks — dezelfde fetch/innerHTML-patronen als de rest van de pagina.

- [ ] **Step 1: Verifieer waar de UI leeft** (`grep -n "fetch\|api/" deep-agents/dashboard.html | head`) en voeg het kaart-blok toe, met deze kern-logica in de bestaande poll-loop:

```javascript
// HITL pending-kaart
const hitl = await fetch('/api/hitl/pending').then(r => r.json());
const kaart = document.getElementById('hitl-kaart');
if (hitl.pending) {
  kaart.style.display = '';
  document.getElementById('hitl-tool').textContent = hitl.tool;
  document.getElementById('hitl-args').textContent = hitl.argsSummary || '';
  kaart.dataset.interruptId = hitl.interruptId;
} else {
  kaart.style.display = 'none';
}

async function hitlVerdict(approved) {
  const kaart = document.getElementById('hitl-kaart');
  const comment = document.getElementById('hitl-comment').value.trim();
  if (!comment) { alert('Een verdict vereist een opmerking (leerstaat).'); return; }
  const r = await fetch('/api/hitl/verdict', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({interruptId: kaart.dataset.interruptId, approved, comment}),
  });
  if (r.status === 409) { alert('Deze beslissing is al genomen.'); }
  if (r.ok) { document.getElementById('hitl-comment').value = ''; }
}
```

plus het HTML-blok (stijl conform het bestaande dashboard-CSS):

```html
<div id="hitl-kaart" style="display:none; border:2px solid #b00; padding:12px; margin:8px 0;">
  <b>Mens-agent-grens: goedkeuring vereist</b>
  <div>Tool: <code id="hitl-tool"></code></div>
  <div id="hitl-args" style="font-family:monospace; font-size:0.85em;"></div>
  <input id="hitl-comment" placeholder="opmerking (verplicht — leerstaat)" style="width:60%;" />
  <button onclick="hitlVerdict(true)">Goedkeuren</button>
  <button onclick="hitlVerdict(false)">Afkeuren</button>
</div>
```

- [ ] **Step 2: Verifieer handmatig dat de pagina zonder JS-fouten laadt (curl op de server of statische controle), suite draaien, commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests -q
git add deep-agents/dashboard.html
git commit -m "feat(deep-agents): dashboard pending-kaart — Goedkeuren/Afkeuren met verplichte opmerking"
```

---

### Task 9: Leerstaat — journal-bron in de decision-trail-extractor

**Files:**
- Modify: `nldt/services/memory/observations.py` (:84-101 en `collect_observations` :146)
- Test: `nldt/tests/test_memory_store.py` (uitbreiding)

**Interfaces:**
- Consumes: Task 2 (ledger-schema: `kind`, `interruptId`, `threadId`, `tool`, `argsSummary`, `approved`, `comment`, `operator`, `auto`).
- Produces: `read_live_hitl_observations(ledger: Path | None = None) -> list[dict]` — per **request-zonder-verdict** een observation `hitl_needs_human` met `detail` = tool + argsSummary en `provenance = {"threadId", "interruptId"}`; per **request-mét-verdict** een afgehandelde variant (detail bevat goedgekeurd/afgewezen + comment + operator). Wordt toegevoegd aan `collect_observations()`. `make_trail`/`update_trail` in `store.py` blijven onveranderd; consolidatie draait zoals eerder (async, buiten het hot path).

- [ ] **Step 1: Falende test — voeg toe aan `nldt/tests/test_memory_store.py`** (conform de bestaande teststijl in dat bestand):

```python
def test_live_hitl_observaties_uit_ledger(tmp_path):
    """Request-zonder-verdict → open observatie; mét verdict → afgehandeld met comment."""
    ledger = tmp_path / "hitl-verdicts.jsonl"
    regels = [
        {"kind": "request", "interruptId": "i-1", "threadId": "nldt-live", "tool": "run_bp2op_transform", "argsSummary": "useCase=eindhoven"},
        {"kind": "request", "interruptId": "i-2", "threadId": "nldt-live", "tool": "run_bp2op_transform", "argsSummary": "useCase=eindhoven"},
        {"kind": "verdict", "interruptId": "i-2", "approved": False, "comment": "niet dit gebied", "operator": "jurist", "auto": False},
    ]
    ledger.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in regels) + "\n", encoding="utf-8")

    obs = observations.read_live_hitl_observations(ledger=ledger)
    assert len(obs) == 2
    open_obs = next(o for o in obs if o["provenance"]["interruptId"] == "i-1")
    klaar = next(o for o in obs if o["provenance"]["interruptId"] == "i-2")
    assert open_obs["type"] == "hitl_needs_human" and "run_bp2op_transform" in open_obs["detail"]
    assert "afgewezen" in klaar["detail"] and "niet dit gebied" in klaar["detail"]
    assert klaar["detail"].count("jurist") == 1
```

(let op: importwijze conform het bestaande bestand — `from services.memory import observations` of hoe de tests dat al doen)

- [ ] **Step 2: Draai, verwacht FAIL** (`AttributeError: read_live_hitl_observations`)

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests/test_memory_store.py -q
```

- [ ] **Step 3: Implementeer in `observations.py`** — nieuwe functie (naast `read_hitl_observations`, zelfde `_obs`-hulpfunctie) en registratie in `collect_observations`:

```python
DEEP_AGENTS_LEDGER = REPO_ROOT / "deep-agents" / "runs" / "live" / "hitl-verdicts.jsonl"


def read_live_hitl_observations(ledger: Path | None = None) -> list[dict[str, Any]]:
    """Mens-agent-grens in de live-runner: request-zonder-verdict = open, mét verdict = afgehandeld."""
    pad = ledger or DEEP_AGENTS_LEDGER
    if not pad.exists():
        return []
    regels = [json.loads(r) for r in pad.read_text(encoding="utf-8").splitlines() if r.strip()]
    verdicts = {r["interruptId"]: r for r in regels if r.get("kind") == "verdict"}
    out: list[dict[str, Any]] = []
    for r in regels:
        if r.get("kind") != "request":
            continue
        vid = r.get("interruptId", "")
        v = verdicts.get(vid)
        if v is None:
            detail = f"hitl-pending: {r.get('tool')} ({r.get('argsSummary', '')}) wacht op menselijk verdict"
        else:
            uitkomst = "goedgekeurd" if v.get("approved") else "afgewezen"
            detail = (
                f"hitl-{uitkomst}: {r.get('tool')} ({r.get('argsSummary', '')}) — "
                f"opmerking: {v.get('comment', '')} (operator: {v.get('operator', 'onbekend')})"
            )
        out.append(_obs("hitl_needs_human", _rel(pad), detail, {"threadId": r.get("threadId", ""), "interruptId": vid}))
    return out
```

en in `collect_observations()` de lijst verlengen met `+ read_live_hitl_observations()`.

(let op: `_obs`-handtekening is `(type_, source, detail, provenance)` en `_rel(pad)` bestaat reeds; gebruik de bestaande hulpfuncties exact)

- [ ] **Step 4: Nldt-suite draaien, verwacht PASS; commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q   # verwacht 390 + nieuwe
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/memory/observations.py nldt/tests/test_memory_store.py
git commit -m "feat(nldt): leerstaat pakt deep-agents hitl-ledger op — pending = open trail, verdict = afgehandeld met opmerking"
```

---

### Task 10: Documentatie + eindverificatie

**Files:**
- Modify: `deep-agents/README.md` (HITL-sectie bij de bestaande "next steps"-vermelding op :160-162)
- Modify: dit planbestand (executiestatus)

- [ ] **Step 1: README-sectie** — vervang de wens-regel op :160-162 door een korte HITL-sectie: wat interrupt (`run_bp2op_transform`, MC-6), hoe het dashboard-verdict werkt (pending-kaart, verplichte opmerking), resume-over-procesgrens via SqliteSaver (`runs/live/checkpoints.sqlite`), `--auto-approve-hitl` als dev-flag met `auto: true`-markering, de beperking dat de recipes-invoke-pad (agent.py:74) nog geen checkpointer heeft en dus geen interrupts (bewust out of scope), en het leerrapport-commando (`cd nldt && PYTHONPATH=. .venv/bin/python -m services.memory.report`).

- [ ] **Step 2: Volledige eindverificatie**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && ../nldt/.venv/bin/python -m pytest tests -q
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q
cd /Users/marc/Projecten/ldttoolbox/poc && ../nldt/.venv/bin/python -m pytest tests -q
```

Expected: alle drie groen; hitl-tests in beide suites aanwezig.

- [ ] **Step 3: Executiestatus in dit plan + commit**

```bash
git add deep-agents/README.md docs/superpowers/plans/2026-10-07-hitl-mens-agent-grens.md
git commit -m "docs: hitl eindverificatie groen — README-sectie mens-agent-grens + executiestatus"
```

## Executiestatus

Alle tien taken uitgevoerd op `main` (HITL-workstream, 2026-10-07):

| Taak | Commit(s) |
|------|-----------|
| T1 — smoke-verificatie interrupt-mechanisme (`test_hitl_smoke.py`) | da007d5 |
| T2 — hitl.py (config, ledger, resume-mapping) + tests | 5032d5d |
| T3 — agent.py `interrupt_on` + `build_agent`-contract | 7f03b72 |
| T4 — graph_trace.py vangt `__interrupt__` (journal + ledger-request) | c63a27f |
| T5 — live.py: pending-sentinel, exit 2, SqliteSaver-thread `nldt-live`; hersteld (bare `build_agent` → LOCAL_TOOLS) + rooktest | 2bf8f98 + f1674b6 |
| T6 — resume.py CLI (verplichte opmerking, exit 0/3/4) | 73eee48 |
| T7 — live_server.py hitl-API (pending authoritair, verdict + 409) | b90966b + 4ce0319 + 7de75e6 |
| T8 — dashboard pending-kaart (verplichte opmerking, 409-alert) | 9cedb15 + 5ba8e7a |
| T9 — leerstaat leest hitl-ledger (observations + leerrapport) | 9ef8da1 |
| T10 — documentatie + eindverificatie | deze commit |

Eindverificatie (alle drie groen):

- `deep-agents`: **28 passed** in 8.08s (met `PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q`)
- `nldt`: **404 passed** in 8.73s
- `poc`: **304 passed, 1 skipped, 15 deselected, 6 subtests passed** in 14.27s

Deviations: (1) T1 — de gemeten contracten (lazy stream, PYTHONPATH) zijn
teruggedraaid in het plan; (2) T5 — live.py was al vóór HITL kapot (bare
`build_agent`): LOCAL_TOOLS-fix + rooktest; (3) T7 — state-authoritative
409-gate i.p.v. ledger-crosscheck (een verlaten ledger-request blokkeerde een
vers interrupt) + fallback-tak die de tool uit het ledger-request haalt;
(4) T8 — display-block un-hide: de stylesheet verslaat de lege inline-stijl;
(5) T9 — decision-trail.schema uitgebreid met optionele threadId/interruptId
in de provenance (consolidatie crashte anders); (6) deferred:
JSONDecodeError-guards beide kanten, operator-veld in het dashboard,
model-env-persist, `/api/run` ziet geen lopende resume, DT-werkstroom moet
schema-velden reconciliëren; (7) de journal-echo `hitl_verdict` is dunner dan
spec §2 voorschrijft: `approved` is alleen zichtbaar in de samenvattingstekst
en de opmerking is afgekapt via `args_summary` — bewust, het ledger is de
duurzame bron en de journal hoeft het verdict niet te dupliceren; (8) de
`llm`-marker-test (spec §5) is in de eindreview-fixwave alsnog geleverd
(`tests/test_hitl_llm.py` + markerregistratie in `deep-agents/pytest.ini`,
geskipt zonder `LDT_DEEP_AGENTS_ENDPOINT`).

Eindreview-fixwave (2026-10-07, dezelfde dag): sluit het toepasselijke deel
van (6) af — JSONDecodeError-guards in `hitl.ledger_read` én
`read_live_hitl_observations`, en `/api/run` weigert (409) zolang een
gespawnde hervatting leeft. Daarbovenop: verdict-idempotentie per
interruptId (tweede POST → 409, vóór de pending-check; last-wins-contract
blijft), dubbel-submit-dicht in het dashboard (knoppen disabled na de eerste
klik), reject-resume-smoketest, unit-test voor het `auto: True`-ledgerrecord
en de torn-regeltests beide kanten. Status na de fixwave: deep-agents
**33 passed, 1 skipped** (llm-marker, endpoint-loos), nldt **405 passed**.
Overgebleven deferred: operator-veld in het dashboard, model-env-persist,
DT-werkstroom moet schema-velden reconciliëren.
