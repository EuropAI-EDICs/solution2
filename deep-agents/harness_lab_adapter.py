"""Harness-lab adapter voor deep-agents: past een variant toe op de wiring
en voert de probe uit — fake (offline montuurbewijs met gescripte modellen)
of llm (echt model, zelfde deterministische rechter).

Dit is het enige lab-onderdeel dat de agent-laag importeert; de lab-motor
(poc-fundament/fundament/harnesslab.py) blijft er import-technisch van
gescheiden. De motor+schema's zeggen hóe evidence eruitziet, deze adapter
zegt wat een probe vóór deep-agents betekent:

- static    — geen model: de variant-wiring (slotgate-grants, promptswap)
              wordt gecontroleerd op de echte poc_subagents-wiring.
- route     — de orchestrator krijgt de vraag; fake-mode speelt de
              delegatie gescript na (montuur), llm-mode laat het echte
              model-routeren en toetst delegatesTo als gedrag.
- standalone— één poc-agent solo; restricted tot catalog-lees-tools zodat
              een probe nooit een pijplijn-run kan starten.

Journal en model-pinnen worden per probe geïsoleerd (journal.LIVE_DIR →
probe-map, env-overschrijvingen teruggemaakt in finally): een probe raakt
de live-dashboard-journal en de omgeving van de aanroeper niet aan.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

sys.path.append(str(REPO / "poc-fundament"))  # append, nooit insert(0) (M2-les)

from fundament import harnesslab as hl  # noqa: E402

ADAPTER = "deepagents"

PROMPT_TARGETS: dict[str, Path] = {
    "recipe_driver": HERE / "prompts" / "recipe_driver.md",
    **{f"poc/{p.stem}": p for p in (HERE / "prompts" / "poc").glob("*.md")},
    **{f"roles/{p.stem}": p for p in (HERE / "prompts" / "roles").glob("*.md")},
}

MODEL_PIN_VARS = ("DEEP_AGENT_MODEL", "DEEP_AGENT_SUBMODEL")

LIVE_ORCHESTRATOR_PROMPT = (HERE / "prompts" / "recipe_driver.md").read_text(encoding="utf-8")


def _fake_model(messages: list):
    """Offline model-stub (patroon tests/test_hitl_smoke.py): scripted
    berichten, bind_tools is een no-op, streaming uit."""
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

    class _Stub(GenericFakeChatModel):
        disable_streaming: bool = True

        def bind_tools(self, tools, **kwargs):
            return self

    return _Stub(messages=iter(messages))


def _tool_name(t) -> str:
    return getattr(t, "name", getattr(t, "__name__", ""))


def _names(tools) -> set[str]:
    return {_tool_name(t) for t in tools}


def _component_path(comp: dict, variant_path: Path) -> Path:
    p = Path(comp["path"])
    return p if p.is_absolute() else Path(variant_path).parent / p


def apply_variant(specs: list[dict], variant: dict, *, variant_path: Path):
    """Zuiver: geef (nieuwe specs, context) terug; de invoerlijst blijft
    ongemoeid. Onbekende targets faallen luid."""
    by_name = {s["name"]: s for s in specs}
    ctx: dict[str, Any] = {
        "orchestrator_prompt": None,
        "prompts": {},          # agent-naam → varianttekst
        "allow": {}, "deny": {},
        "model_env": {},
    }
    for comp in variant["components"]:
        ctype, target = comp["type"], comp["target"]
        if ctype == "prompt":
            if target == "recipe_driver":
                ctx["orchestrator_prompt"] = _component_path(comp, variant_path).read_text(encoding="utf-8")
            elif "/" in target and target.split("/", 1)[1] in by_name:
                naam = target.split("/", 1)[1]
                ctx["prompts"][naam] = _component_path(comp, variant_path).read_text(encoding="utf-8")
            else:
                raise hl.HarnessLabError(f"onbekende prompt-target {target!r}")
        elif ctype == "toolGrants":
            ctx["allow"].update(comp.get("allow", {}))
            ctx["deny"].update(comp.get("deny", {}))
        elif ctype == "modelPin":
            ctx["model_env"].update(comp.get("env", {}))
    out = []
    for s in specs:
        tekst = ctx["prompts"].get(s["name"])
        out.append({**s, "system_prompt": tekst} if tekst is not None else s)
    return out, ctx


def apply_grants(specs: list[dict], manifest: dict, poc_agent_names: set[str],
                 allow: dict, deny: dict) -> list[dict]:
    """Slotgate met variant-grants: allow verbreedt binnen de pre-slotgate
    toolset van de agent, deny versmalt hoe dan ook (pure functie)."""
    if not allow and not deny:
        return specs
    from fase_slotgate import apply_slotgate

    pre = {s["name"]: list(s["tools"]) for s in specs}
    gefilterd = {s["name"]: s for s in apply_slotgate(specs, manifest, poc_agent_names)}
    out = []
    for s in specs:
        naam = s["name"]
        toegestaan = set(_names(gefilterd[naam]["tools"]))
        toegestaan |= set(allow.get(naam, []))
        toegestaan -= set(deny.get(naam, []))
        out.append({**gefilterd[naam],
                    "tools": [t for t in pre[naam] if _tool_name(t) in toegestaan]})
    return out


# ---- checks ----------------------------------------------------------------

def _static_check(specs: list[dict], hard: dict, naam: str, waarde: dict) -> dict:
    tools = set(waarde["tools"])
    aanwezig = _names(next(s["tools"] for s in specs if s["name"] == waarde["agent"]))
    if naam == "slotgateAllows":
        return {"check": naam, "pass": tools <= aanwezig,
                "detail": f"ontbreken: {sorted(tools - aanwezig)}", **hard}
    if naam == "slotgateForbids":
        return {"check": naam, "pass": not (tools & aanwezig),
                "detail": f"gelekt: {sorted(tools & aanwezig)}", **hard}
    raise hl.HarnessLabError(f"check {naam!r} hoort niet bij een static-taak")


def _gedrags_checks(expect: list[dict], antwoord: str, trace: list[str],
                    soort: str) -> list[dict]:
    uit = []
    for e in expect:
        naam, waarde = e["check"], e["value"]
        hard = {"hard": True} if e.get("hard") else {}
        if naam == "delegatesTo":
            gedelegeerd = {t.split("(", 1)[1].rstrip(")")
                           for t in trace if t.startswith("task(")}
            uit.append({"check": naam, "pass": waarde in gedelegeerd,
                        "detail": f"gedelegeerd naar {sorted(gedelegeerd)}", **hard})
        elif naam == "toolTraceIncludes":
            ontbreekt = [t for t in waarde if not any(t in sp for sp in trace)]
            uit.append({"check": naam, "pass": not ontbreekt,
                        "detail": f"ontbreekt: {ontbreekt}", **hard})
        elif naam == "answerContains":
            mist = [s for s in waarde if s.lower() not in antwoord.lower()]
            uit.append({"check": naam, "pass": not mist, "detail": f"mist: {mist}", **hard})
        elif naam == "answerNotContains":
            lekt = [s for s in waarde if s.lower() in antwoord.lower()]
            uit.append({"check": naam, "pass": not lekt, "detail": f"gelekt: {lekt}", **hard})
        else:
            raise hl.HarnessLabError(f"check {naam!r} hoort niet bij een {soort}-taak")
    return uit


def _uit_komst(resultaat: dict) -> tuple[str, list[str]]:
    """(laatste antwoord, compacte tool-trace) uit een graaf-resultaat."""
    trace = []
    for msg in resultaat["messages"]:
        for call in getattr(msg, "tool_calls", None) or []:
            args = call.get("args", {})
            target = args.get("subagent_type", args.get("recipe_id", ""))
            trace.append(f"{call['name']}({target})" if target else call["name"])
    laatste = resultaat["messages"][-1]
    antwoord = laatste.content if isinstance(laatste.content, str) else str(laatste.content)
    return antwoord, trace


# ---- taak-uitvoering -------------------------------------------------------

def _graaf(soort: str, task: dict, specs: list[dict], ctx: dict, model,
           *, fake_sub=None):
    """Graaf met de variant-wiring. route: orchestrator + patched specs
    (fake: subagents krijgen het gescripte submodel; llm: hun echte model uit
    de specs). standalone: één agent, geen subagents."""
    from deepagents import create_deep_agent

    if soort == "standalone":
        spec = next((s for s in specs if s["name"] == task["poc"]), None)
        if spec is None:
            raise hl.HarnessLabError(f"taak {task['id']}: onbekende poc {task['poc']!r}")
        return create_deep_agent(
            model=model, tools=[], system_prompt=spec["system_prompt"],
            interrupt_on={})
    subagents = [{**s, "model": fake_sub} for s in specs] if fake_sub is not None else specs
    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=ctx["orchestrator_prompt"] or LIVE_ORCHESTRATOR_PROMPT,
        subagents=subagents,
        interrupt_on={},
    )


def _route_fake(task: dict, specs: list[dict], ctx: dict) -> tuple[str, list[str]]:
    """Gescripte delegatie door de échte orchestrator-graaf (offline)."""
    from langchain_core.messages import AIMessage

    delegate = task.get("delegateTo")
    if not delegate:
        raise hl.HarnessLabError(f"taak {task['id']}: fake-modus vereist delegateTo")
    vraag = task.get("question", task["id"])
    antwoord = task.get("fakeAnswer", f"[{task['id']}] antwoord van {delegate}")
    orakel = _fake_model([
        AIMessage("", tool_calls=[{"name": "task",
                                   "args": {"description": vraag,
                                             "subagent_type": delegate},
                                   "id": "call-probe"}]),
        AIMessage(antwoord),
    ])
    sub = _fake_model([AIMessage(antwoord)])
    graaf = _graaf("route", task, specs, ctx, orakel, fake_sub=sub)
    return _uit_komst(graaf.invoke(
        {"messages": [{"role": "user", "content": vraag}]},
        config={"configurable": {"thread_id": f"probe-{task['id']}"}},
    ))


def _standalone_fake(task: dict, specs: list[dict], ctx: dict) -> tuple[str, list[str]]:
    from langchain_core.messages import AIMessage

    vraag = task.get("question", task["id"])
    antwoord = task.get("fakeAnswer", f"[{task['id']}] antwoord van {task['poc']}")
    graaf = _graaf("standalone", task, specs, ctx,
                   _fake_model([AIMessage(antwoord)]))
    return _uit_komst(graaf.invoke(
        {"messages": [{"role": "user", "content": vraag}]},
        config={"configurable": {"thread_id": f"probe-{task['id']}"}},
    ))


def _eis_modellen() -> tuple[str, str]:
    """llm-modus: fail-luid als de provider of een model ontbreekt."""
    sys.path.insert(0, str(REPO / "nldt"))
    from models import check_ollama, orchestrator_model_name, subagent_model_name

    orakel_naam, sub_naam = orchestrator_model_name(), subagent_model_name()
    try:
        check_ollama([orakel_naam, sub_naam])
    except SystemExit as exc:
        raise hl.HarnessLabError(f"llm-modus niet beschikbaar: {exc}") from exc
    return orakel_naam, sub_naam


def _route_llm(task: dict, specs: list[dict], ctx: dict) -> tuple[str, list[str]]:
    from deepagents import create_deep_agent

    from models import ollama_model, orchestrator_model_name

    orakel_naam, _ = _eis_modellen()
    vraag = task["question"]
    graaf = create_deep_agent(
        model=ollama_model(orakel_naam),
        tools=[],
        system_prompt=ctx["orchestrator_prompt"] or LIVE_ORCHESTRATOR_PROMPT,
        subagents=specs,
        interrupt_on={},
    )
    return _uit_komst(graaf.invoke(
        {"messages": [{"role": "user", "content": vraag}]},
        config={"configurable": {"thread_id": f"probe-{task['id']}"}},
    ))


def _standalone_llm(task: dict, specs: list[dict], ctx: dict) -> tuple[str, list[str]]:
    """Eén poc-agent solo, restricted tot catalog-lees-tools (een probe start
    nooit een pijplijn-run)."""
    from deepagents import create_deep_agent

    from models import ollama_model, subagent_model_name
    from tools.recipes import get_recipe, list_recipes

    _, sub_naam = _eis_modellen()
    graaf = create_deep_agent(
        model=ollama_model(sub_naam),
        tools=[list_recipes, get_recipe],
        system_prompt=next(s["system_prompt"] for s in specs if s["name"] == task["poc"]),
        interrupt_on={},
    )
    return _uit_komst(graaf.invoke(
        {"messages": [{"role": "user", "content": task["question"]}]},
        config={"configurable": {"thread_id": f"probe-{task['id']}"}},
    ))


# ---- scaffold --------------------------------------------------------------

def snapshot_register_basis() -> dict:
    """Baselijn: de huidige harness als actieve register-entries."""
    sys.path.insert(0, str(REPO / "nldt"))
    from services.common import model_config

    entries = []
    for target, pad in sorted(PROMPT_TARGETS.items()):
        entries.append({
            "id": f"prompt-{target.replace('/', '-').replace('_', '-')}",
            "title": f"prompt {target}",
            "component": "prompt", "target": target,
            "riskLevel": "low", "version": "1.0.0", "status": "actief",
            "artifact": {"kind": "promptFile",
                         "path": str(pad.relative_to(HERE)),
                         "sha256": hl.sha256_file(pad)},
            "prov": {"registeredBy": "harness-lab scaffold"},
        })
    for target, var, waarde in (
        ("orchestrator", "DEEP_AGENT_MODEL", model_config.orchestrator_model_name()),
        ("subagent", "DEEP_AGENT_SUBMODEL", model_config.subagent_model_name()),
    ):
        entries.append({
            "id": f"modelpin-{target}",
            "title": f"model-pin {target}",
            "component": "modelPin", "target": target,
            "riskLevel": "low", "version": "1.0.0", "status": "actief",
            "artifact": {"kind": "envPin", "env": {var: waarde}},
            "prov": {"registeredBy": "harness-lab scaffold"},
        })
    return {"poc": "deep-agents", "harnesses": entries}


def snapshot_variant_basis(variant_pad: Path) -> dict:
    """Baselijn-variant (identiteitscontrolegreep): wijzigt niets, wijst alleen
    de actieve prompts aan. Paden t.o.v. de map van het variantbestand."""
    def _rel(pad: Path) -> str:
        return os.path.relpath(pad, variant_pad.parent)

    return {
        "id": "baseline",
        "title": "huidige harness (ongewijzigd)",
        "notes": ["scaffold-baselijn: geen wijziging, dient als controlegreep"],
        "components": [
            {"type": "prompt", "target": target, "path": _rel(pad)}
            for target, pad in sorted(PROMPT_TARGETS.items())
        ],
    }


# ---- probe-hoofdloop -------------------------------------------------------

def run_probe(*, variant: dict, variant_path: Path, taskset: dict,
              taskset_path: Path, mode: str, out_dir: Path) -> dict:
    """Voer één variant × taskset uit; geeft het definitieve evidence-document
    terug (ook weggeschreven als probe-evidence.json in out_dir)."""
    import journal
    import pocs

    start = time.time()
    out_dir = Path(out_dir)
    evidence = hl.new_evidence(
        variant=variant, variant_path=variant_path,
        taskset=taskset, taskset_path=taskset_path,
        adapter=ADAPTER, mode=mode)

    # per-probe isolatie: journal en model-pinnen nooit in de live-omgeving
    oude_journal = (journal.LIVE_DIR, journal.JOURNAL)
    journal.LIVE_DIR = out_dir / "journal"
    journal.JOURNAL = journal.LIVE_DIR / "steps.jsonl"
    oude_env = {var: os.environ.get(var) for var in MODEL_PIN_VARS}
    try:
        for var, waarde in variant_env(variant).items():
            os.environ[var] = waarde
        # specs ná de env-pinnen bouwen: llm-modus bouwt echte modellen
        specs = pocs.poc_subagents(mcp_tools=None)
        gepatcht, ctx = apply_variant(specs, variant, variant_path=variant_path)
        manifest = pocs.load_manifest()
        if manifest is not None:
            gepatcht = apply_grants(
                gepatcht, manifest,
                {s["name"] for s in pocs.POC_AGENTS},
                ctx["allow"], ctx["deny"])
        evidence["applied"] = {
            "promptTargets": sorted(c["target"] for c in variant["components"]
                                    if c["type"] == "prompt"),
            "modelEnv": ctx["model_env"],
        }
        for task in taskset["tasks"]:
            begin = time.time()
            soort = task["kind"]
            if soort == "static":
                checks = [_static_check(gepatcht,
                                        {"hard": True} if e.get("hard") else {},
                                        e["check"], e["value"])
                          for e in task["expect"]]
                hl.record_task(evidence, task_id=task["id"], kind=soort, checks=checks)
                continue
            if mode == "fake":
                uitvoerder = _route_fake if soort == "route" else _standalone_fake
            else:
                uitvoerder = _route_llm if soort == "route" else _standalone_llm
            antwoord, trace = uitvoerder(task, gepatcht, ctx)
            checks = _gedrags_checks(task["expect"], antwoord, trace, soort)
            hl.record_task(evidence, task_id=task["id"], kind=soort, checks=checks,
                           metrics={"toolCalls": len(trace),
                                    "durationS": round(time.time() - begin, 3)})
    finally:
        journal.LIVE_DIR, journal.JOURNAL = oude_journal
        for var, oude in oude_env.items():
            if oude is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = oude

    hl.finalize_evidence(evidence, duration_s=time.time() - start)
    evidence["runDir"] = str(out_dir)
    hl.write_evidence(evidence, out_dir)
    return evidence


def variant_env(variant: dict) -> dict:
    """De model-pin env-overschrijvingen van een variant (alleen DEEP_AGENT_*)."""
    uit = {}
    for comp in variant["components"]:
        if comp["type"] == "modelPin":
            for var, waarde in comp.get("env", {}).items():
                if var not in MODEL_PIN_VARS:
                    raise hl.HarnessLabError(
                        f"modelPin-var {var!r} is geen DEEP_AGENT_MODEL/DEEP_AGENT_SUBMODEL")
                uit[var] = waarde
    return uit
