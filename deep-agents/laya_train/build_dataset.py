"""Build the nLDT routing fine-tune dataset from the POC scenario examples.

Sources (read-only):
  poc/scenarios/*.json        Utrecht track scenario sets (+ what-ifs)
  poc-nspd/scenarios/*.json   NSPD NL/BE scenario sets
  poc/scenario-runs/          executed scenario runs (real run ids)
  poc-nspd/scenario-runs/     executed NSPD scenario runs

Each scenario set becomes routing cases across the utrecht workflow modes from
deep-agents/poc_demos.py (execute / plan / vergelijk / geo+critic / normketen /
volledige keten / uitdaging-overzicht), grounded in the set's own object types,
scenario names and real run ids. Cross-track overlay cases (wind × zon × bos)
ground the crosstrack POC; control cases for breda / rijnland / minigim /
eindhoven / recipe-inventaris / unclear come from the demo-catalog phrasings.

Output (deterministic, seed=20261018):
  data/scenarios-train.jsonl   {state, questions, gold} rows
  data/scenarios-eval.jsonl    held-out scenario sets + controls
  data/manifest.jsonl          provenance per case (source, mode, run id)
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "deep-agents"))

from laya_router import nldt_orchestrator_questions  # noqa: E402

SEED = 20261018
OUT_DIR = Path(__file__).resolve().parent / "data"

OBJECT_NL: dict[str, str] = {
    "wind_turbine": "windturbines",
    "solar_field": "zonneparken",
    "solar_farm": "zonneparken",
    "forest": "bos",
    "forest_planting": "bosplanting",
    "energy_storage": "energieopslag",
    "biomass_installation": "biomassaverwerking",
    "soil_activity": "bodemactiviteiten",
    "agricultural_expansion": "landbouwuitbreiding",
    "landscape_intervention": "landschapsinterventies",
    "roadside_development": "weggebonden ontwikkeling",
    "recreation_development": "recreatievoorzieningen",
    "riparian_development": "water- en oeverontwikkeling",
    "business_development": "nieuwe werklocaties",
    "housing_development": "woningbouw",
}

TRACK_NL: dict[str, str] = {
    "wind": "wind", "zon": "zon", "bos": "bos", "water": "water",
    "bodem": "bodem", "mobiliteit": "mobiliteit", "landschap": "landschap",
    "landbouw": "landbouw", "wonen": "wonen", "werken": "werken",
    "recreatie": "recreatie", "biomassa": "biomassa",
    "energietoets": "energietoets",
}

# Workflow-mode → routing gold (grounded in poc_demos.py templates and the
# laya_router question criteria).
MODE_GOLD: dict[str, dict] = {
    "execute": {
        "primary_poc": "utrecht", "workflow": "execute_demo",
        "needs_intake": False, "needs_build": True, "needs_critic": False,
    },
    "plan": {
        "primary_poc": "utrecht", "workflow": "plan_only",
        "needs_intake": False, "needs_build": False, "needs_critic": False,
    },
    "critical": {
        "primary_poc": "utrecht", "workflow": "geo_and_critic",
        "needs_intake": False, "needs_build": True, "needs_critic": True,
    },
    "compare": {
        "primary_poc": "utrecht", "workflow": "compare_layers",
        "needs_intake": False, "needs_build": True, "needs_critic": False,
    },
    "geo": {
        "primary_poc": "utrecht", "workflow": "geo_and_critic",
        "needs_intake": False, "needs_build": True, "needs_critic": True,
    },
    "normketen": {
        "primary_poc": "utrecht", "workflow": "norm_chain_only",
        "needs_intake": True, "needs_build": False, "needs_critic": False,
    },
    "keten": {
        "primary_poc": "utrecht", "workflow": "full_chain",
        "needs_intake": True, "needs_build": True, "needs_critic": True,
    },
    "uitdaging": {
        "primary_poc": "utrecht", "workflow": "inventory",
        "needs_intake": False, "needs_build": False, "needs_critic": False,
    },
}

# Scenario sets held out entirely (by source+stem) so eval measures
# generalization to unseen sets, not memorized paraphrases.
EVAL_SETS = {
    ("poc", "recreatie.json"),
    ("poc", "energietoets.json"),
    ("poc-nspd", "wind-nl.json"),
    ("poc-nspd", "werken-be.json"),
}
EVAL_CONTROL_COUNT = 8  # stratified controls moved to eval


def load_scenario_sets() -> list[dict]:
    sets: list[dict] = []
    for source in ("poc", "poc-nspd"):
        for p in sorted((REPO_ROOT / source / "scenarios").glob("*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            if "scenarios" not in doc:
                continue
            regions = {"poc": "de provincie Utrecht"}
            region = regions.get(source)
            if source == "poc-nspd":
                region = "Nederland" if p.stem.endswith("-nl") else "Vlaanderen"
            track = str(doc.get("useCase") or "")
            objects = sorted({str(s.get("objectType")) for s in doc["scenarios"]})
            scen_names = [str(s.get("name") or "").strip() for s in doc["scenarios"]]
            scen_names = [n for n in scen_names if n]
            sets.append({
                "source": source,
                "stem": p.name,
                "track": track,
                "region": region,
                "objects": objects,
                "scen_names": scen_names,
                "whatif": "whatif" in p.stem,
            })
    return sets


def find_run_id(source: str, stem: str, track: str) -> str:
    """Resolve a real scenario-run id for the set, e.g. 20261013T193408Z-wind-scen."""
    runs_root = REPO_ROOT / source / "scenario-runs"
    if not runs_root.is_dir():
        return f"<scenario-run:{stem}>"
    candidates = []
    for d in runs_root.iterdir():
        if not d.is_dir() or not (d / "scenario-report.json").is_file():
            continue
        rid = d.name.lower()
        if source == "poc-nspd":
            suffix = stem.removesuffix(".json").lower()  # e.g. wind-nl / werken-be
            if suffix in rid or f"_{suffix}" in rid:
                candidates.append(d.name)
        else:
            if f"-{track.lower()}-scen" in rid or f"-{track.lower()}-whatif" in rid:
                candidates.append(d.name)
    return sorted(candidates)[-1] if candidates else f"<scenario-run:{stem}>"


def obj_phrase(objects: list[str]) -> str:
    names = [OBJECT_NL.get(o, o) for o in objects]
    return " of ".join(names) if names else "locaties"


# ----------------------------------------------------------------------------------
# Template families per mode. Deterministic rotation; NL majority + EN variants.
# ----------------------------------------------------------------------------------

T_EXECUTE = [
    "Delegeer naar utrecht: bouw de world scene voor scenario run {rid} en toon de visual demo.",
    "Bouw de world scene voor scenario run {rid} ({track}, {region}) en laat de demo zien.",
    "Ik wil zien waar ruimte is voor {obj} in {region} — voer scenario run {rid} uit en toon de kaart.",
    "Draai de utrecht-world-scene recipe voor scenario run {rid} en render de visual demo.",
    "Build the world scene for scenario run {rid} and show the visual demo.",
    "Run scenario {rid} ({track}, {region}) and show me the map for {obj}.",
]
T_PLAN = [
    "Delegeer naar utrecht: geef alléén een run plan voor de utrecht-world-scene recipe "
    "voor scenario run {rid}. Voer nog niets uit.",
    "Wat is het uitvoerplan voor scenario run {rid}? Alleen plannen, geen executie.",
    "Geef een run plan voor de world scene van {rid} ({track}); voer niets uit.",
    "Plan the world-scene build for scenario run {rid} only — do not execute anything.",
]
T_CRITICAL = [
    "Toets kritisch of scenario run {rid} geschikt is voor een world-scene build "
    "(risico's, missende inputs, grounding). Delegeer daarna naar utrecht om te bouwen "
    "en de demo te tonen.",
    "Check eerst kritisch of {rid} ({obj}, {region}) bouwbaar is, bouw daarna de world "
    "scene en toon de demo.",
    "Critically assess whether scenario run {rid} is ready for a world-scene build, then "
    "build it and show the demo.",
]
T_COMPARE = [
    "Bouw de world scene voor {rid}, laat geospecialist control vs scenario vergelijken "
    "(deltas, km²), en toon de demo.",
    "Vergelijk de control-run met scenario '{scen}' ({rid}) — geo-deltas in km².",
    "Laat geospecialist de lagen van control en scenario run {rid} naast elkaar leggen "
    "en toon het verschil.",
    "Compare control vs scenario run {rid} spatially (deltas in km²) and show the demo.",
]
T_GEO = [
    "Bouw de world scene voor scenario run {rid}, laat geospecialist de lagen analyseren "
    "en critic de bundle valideren. Toon de demo.",
    "Voor {rid}: world-scene build, geo-analyse per laag en critic-validatie van de bundle.",
    "Build the world scene for scenario run {rid}, have the geospecialist analyse the "
    "layers and the critic validate the bundle.",
]
T_NORMKETEN = [
    "Nieuwe aanvraag: 'Ik wil weten waar {obj} mogen in {region}.' Doorloop de normketen: "
    "(1) intake normaliseert tot schema-geldig verzoek, (2) normspecialist zoekt "
    "normkaarten, (3) formalizer stelt FormalRule op. Bouw nog niets.",
    "Start met intake voor 'waar mogen {obj} in {region}?' en loop alleen intake → "
    "normkaarten → formalisatie door.",
    "Norm chain only for '{obj} in {region}': intake, norm cards, formalizer — no build.",
]
T_KETEN = [
    "Volledige keten voor scenario run {rid}. Aanvraag: 'Ik wil weten waar {obj} mogen in "
    "{region}.' Doorloop: intake, normen, formalisatie, world-scene build voor {rid}, "
    "parallel geo + critic, en uitleg. Stop daarna.",
    "Run de hele keten voor {rid} ({track}, {region}): van intake tot validatie en uitleg.",
    "Full chain for scenario run {rid}: intake → norms → formal rule → build → geo/critic "
    "→ explainer.",
]
T_UITDAGING = [
    "Delegeer naar utrecht: geef het uitdaging-overzicht — per uitdaging de titel, de "
    "tracks en per track de scenario's met headline-delta (deltaVsControlPct). Begin bij "
    "track {track} ({region}).",
    "Geef per track uit de uitdagingen de scenario's met hun headline-delta; sluit af "
    "met de grootste hefboom. Loop {track} ({region}) als eerste door.",
    "List the uitdaging overview: tracks, scenarios per track and headline deltas; "
    "start with the {track} track ({region}).",
]
T_CROSSTRACK = [
    "Voer de crosstrack-overlay uit over de baseline runs van {tracks}: waar overlappen "
    "de kansen?",
    "Combineer {tracks} in één multi-track overlay (Plane C) en toon de onderlinge "
    "ruimte.",
    "Run the cross-track overlay across the {tracks} baseline runs.",
    "Welke plekken zijn geschikt voor {objcombo} tegelijk? Gebruik de crosstrack-overlay.",
]

CONTROL_MODES: list[tuple[str, dict]] = [
    ("breda_scan_plan", {"primary_poc": "breda", "workflow": "plan_only",
                         "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("breda_scan_execute", {"primary_poc": "breda", "workflow": "execute_demo",
                            "needs_intake": False, "needs_build": True, "needs_critic": False}),
    ("breda_qa_plan", {"primary_poc": "breda", "workflow": "plan_only",
                       "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("rijnland_execute", {"primary_poc": "rijnland", "workflow": "execute_demo",
                          "needs_intake": False, "needs_build": True, "needs_critic": False}),
    ("rijnland_conflict_plan", {"primary_poc": "rijnland", "workflow": "plan_only",
                                "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("rijnland_whatif_plan", {"primary_poc": "rijnland", "workflow": "plan_only",
                              "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("minigim_execute", {"primary_poc": "minigim", "workflow": "execute_demo",
                         "needs_intake": False, "needs_build": True, "needs_critic": False}),
    ("minigim_plan", {"primary_poc": "minigim", "workflow": "plan_only",
                      "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("minigim_checklist", {"primary_poc": "minigim", "workflow": "inventory",
                           "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("eindhoven_execute", {"primary_poc": "eindhoven", "workflow": "execute_demo",
                           "needs_intake": False, "needs_build": True, "needs_critic": False}),
    ("eindhoven_plan", {"primary_poc": "eindhoven", "workflow": "plan_only",
                        "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("eindhoven_hitl", {"primary_poc": "eindhoven", "workflow": "other",
                        "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("inventory", {"primary_poc": "cross_poc", "workflow": "inventory",
                   "needs_intake": False, "needs_build": False, "needs_critic": False}),
    ("unclear", {"primary_poc": "unclear", "workflow": "other",
                 "needs_intake": False, "needs_build": False, "needs_critic": False}),
]

CONTROLS: list[tuple[str, str]] = [
    ("breda_scan_plan",
     "Delegeer naar breda: geef een concreet run plan voor recipe breda-five-value-scan "
     "— inputs, stappen, process ids, outputs, risico."),
    ("breda_scan_execute",
     "Delegeer naar breda: voer de vijf-waardenscan uit met run_breda_scan en vat de "
     "uitslag samen — verdict, rollup per waarde en de zwakste buurten."),
    ("breda_qa_plan",
     "Delegeer naar breda: run plan voor breda-scan-qa met cite-or-abstain — welke "
     "inputs, welke QA-stappen, verwachte artefacten."),
    ("rijnland_execute",
     "Delegeer naar rijnland: voer de peilen what-if uit met run_rijnland_live en vat "
     "samen — aantal stations, het venster en wat de geanimeerde kaart laat zien."),
    ("rijnland_conflict_plan",
     "Delegeer naar rijnland: run plan voor rijnland-peil-conflict (vigerend peilgebied × "
     "praktijk peilafwijking) — inputs, replay vs execute."),
    ("rijnland_whatif_plan",
     "Delegeer naar rijnland: run plan voor rijnland-peil-whatif via CDC — "
     "scenario-delta's, vereiste runDir/mode."),
    ("minigim_execute",
     "Delegeer naar minigim: voer de gebiedscheck uit met run_minigim_live en vat samen "
     "— verdict, checklist-binding en het rapport in het rechterpaneel."),
    ("minigim_plan",
     "Delegeer naar minigim: run plan voor minigim-gebiedscheck voor een voorbeeld-AOI "
     "rond Utrecht — checklist Lijst-v0.91, open bronnen, verwachte outputs."),
    ("minigim_checklist",
     "Delegeer naar minigim: welke items uit Lijst-v0.91 worden automatisch ingevuld uit "
     "keyless open sources, en welke vereisen handmatige input?"),
    ("eindhoven_execute",
     "Delegeer naar eindhoven: voer de bp2op-omzetting uit met run_eindhoven_live en vat "
     "samen — verdict, de counts en de V4-mens-status."),
    ("eindhoven_plan",
     "Delegeer naar eindhoven: run plan voor eindhoven-bp2op — inputs, stappen, V4 "
     "human-in-the-loop (altijd pending), verwachte outputs."),
    ("eindhoven_hitl",
     "Delegeer naar eindhoven: waar in het bp2op-recipe is menselijke goedkeuring "
     "verplicht, en welke gates mogen agents nooit overslaan?"),
    ("inventory",
     "Welke nLDT-recipes zijn er en welke POC-capaciteiten dekken ze? Gebruik "
     "list_recipes/get_recipe."),
    ("inventory",
     "Welke nLDT-recipes horen bij de Breda POC? Vergelijk Plane A scan vs QA."),
    ("inventory",
     "Geef een overzicht van alle recipes in de toolbox, met per recipe de POC."),
    ("inventory",
     "Which recipes does the toolbox offer, and how do the POCs differ?"),
    ("unclear",
     "Wat is nLDT en hoe verhoudt de toolbox zich tot de omgevingswet-praktijk?"),
    ("unclear",
     "Leg uit wat een world scene is; ik begrijp het concept nog niet."),
    ("unclear",
     "Kun je het verschil uitleggen tussen een normkaart en een formele regel?"),
    ("unclear",
     "Wat betekent cite-or-abstain in jullie werk?"),
    ("unclear",
     "I have a general question about the toolbox — who or what is Laya in this setup?"),
    ("unclear",
     "Hoe zit het met provenance en auditability in de keten? Leg het principieel uit."),
    ("breda_scan_execute",
     "Draai de Breda vijf-waardenscan en geef het verdict met de rollup per waarde; de "
     "kaart mag in het rechterpaneel."),
    ("breda_scan_plan",
     "Wat kost het om de breda-five-value-scan te draaien? Geef een uitvoerplan, nog "
     "zonder executie."),
    ("rijnland_conflict_plan",
     "Ik wil het peilconflict tussen vigerend peilgebied en praktijkpeilen in kaart "
     "brengen — plan dit eerst voor de rijnland-recipe."),
    ("minigim_checklist",
     "Hoe ver komt de minigim-gebiedscheck met open bronnen alleen? Welke "
     "checklist-items blijven handmatig?"),
    ("eindhoven_hitl",
     "Welke stappen in bp2op zijn bewust als human-in-the-loop ontworpen, en waarom?"),
    ("unclear",
     "Vertel kort waar de nLDT-toolbox voor dient; ik wil eerst het grote plaatje."),
    ("unclear",
     "Waarvoor gebruiken jullie Laya in deze setup, en waarom geen LLM voor routing?"),
    ("unclear",
     "Leg de GENAI-seams (S4, S7) uit zoals die in deze repo worden bedoeld."),
    ("unclear",
     "Wat is het verschil tussen Plane A, Plane B en Plane C?"),
    ("unclear",
     "What is an opportunity map in this toolbox, conceptually?"),
    ("unclear",
     "Hoe worden de normkaarten bijgewerkt als beleid verandert?"),
    ("unclear",
     "How does cite-or-abstain work across the chain, in principle?"),
    ("inventory",
     "Welke POC's zitten er in de toolbox en wat test elk van hen?"),
    ("inventory",
     "Compare the capabilities of the Rijnland and MiniGIM POCs."),
    ("inventory",
     "Welke rollen (agents) zitten er in de multi-agent-keten en wie doet wat?"),
    ("inventory",
     "Welke datastromen en open bronnen gebruikt de toolbox als geheel?"),
]


def fmt(template: str, ctx: dict) -> str:
    return template.format(**ctx)


def gold_for(mode_gold: dict) -> dict:
    questions = {}
    for qid, value in mode_gold.items():
        if qid.startswith("needs_"):
            questions[qid] = {"probabilities": {"false": 1.0 if not value else 0.0,
                                                "true": 1.0 if value else 0.0}}
        else:
            questions[qid] = {"probabilities": {value: 1.0}}
    return questions


def build() -> None:
    rng = random.Random(SEED)
    questions = nldt_orchestrator_questions()
    rows, manifest = [], []

    def add(state_text: str, mode_gold: dict, provenance: dict) -> None:
        while state_text in seen:
            ctx_hint = str(provenance.get("track") or provenance.get("mode") or "context")
            state_text = f"{state_text} [context: {ctx_hint}]"
        seen.add(state_text)
        rows.append({"state": {"request": state_text},
                     "questions": questions,
                     "gold": gold_for(mode_gold)})
        manifest.append({"request": state_text, **provenance})

    sets = load_scenario_sets()
    seen: set[str] = set()
    for s in sets:
        rid = find_run_id(s["source"], s["stem"], s["track"])
        track_label = TRACK_NL.get(s["track"], s["track"])
        ctx = {"rid": rid, "track": track_label, "region": s["region"],
               "obj": obj_phrase(s["objects"])}
        scen = rng.choice(s["scen_names"]) if s["scen_names"] else ctx["obj"]
        ctx_scen = {**ctx, "scen": scen}
        for mode, templates in (
            ("execute", T_EXECUTE), ("plan", T_PLAN), ("critical", T_CRITICAL),
            ("compare", T_COMPARE), ("geo", T_GEO), ("normketen", T_NORMKETEN),
            ("keten", T_KETEN), ("uitdaging", T_UITDAGING),
        ):
            gold = MODE_GOLD[mode]
            picks = 2 if mode in ("execute", "compare") else 1
            for tpl in rng.sample(templates, picks):
                text = fmt(tpl, ctx if "{scen" not in tpl else ctx_scen)
                add(text, gold, {"source": f"{s['source']}/scenarios/{s['stem']}",
                                 "kind": "scenario", "mode": mode, "runId": rid,
                                 "track": s["track"], "evalSet": (s["source"], s["stem"]) in EVAL_SETS})

    # Cross-track overlay (crosstrack POC) grounded in real track combos.
    TRACK_OBJECT: dict[str, str] = {
        "wind": "wind_turbine", "zon": "solar_field", "bos": "forest_planting",
        "water": "riparian_development", "bodem": "soil_activity",
        "landbouw": "agricultural_expansion", "recreatie": "recreation_development",
        "mobiliteit": "roadside_development", "landschap": "landscape_intervention",
        "wonen": "housing_development", "werken": "business_development",
    }
    combos = [("wind", "zon", "bos"), ("wonen", "werken"), ("water", "bodem"),
              ("landbouw", "recreatie"), ("zon", "bos"), ("mobiliteit", "landschap")]
    for combo in combos:
        tracks_nl = [TRACK_NL[t] for t in combo]
        objects = obj_phrase([TRACK_OBJECT[t] for t in combo if t in TRACK_OBJECT])
        ctx = {"tracks": " × ".join(tracks_nl), "objcombo": objects}
        for i, tpl in enumerate(rng.sample(T_CROSSTRACK, 2)):
            is_eval = i == 0 and combo in (("wind", "zon", "bos"), ("water", "bodem"))
            add(fmt(tpl, ctx),
                {"primary_poc": "crosstrack", "workflow": "compare_layers",
                 "needs_intake": False, "needs_build": True, "needs_critic": False},
                {"source": "poc/tracks (cross-combinatie)", "kind": "crosstrack",
                 "mode": "crosstrack", "tracks": combo, "evalSet": is_eval})

    # Controls (demo-catalog phrasings), stratified move to eval.
    control_rows = list(CONTROLS)
    control_mode = {mid: gold for mid, gold in CONTROL_MODES}
    eval_pool = [i for i, (mid, _) in enumerate(control_rows)
                 if mid in ("breda_scan_execute", "rijnland_whatif_plan",
                            "minigim_execute", "eindhoven_plan", "eindhoven_hitl",
                            "inventory", "unclear")]
    rng.shuffle(eval_pool)
    eval_ids = set(eval_pool[:EVAL_CONTROL_COUNT])
    for i, (mid, text) in enumerate(control_rows):
        add(text, control_mode[mid],
            {"source": "deep-agents/poc_demos.py", "kind": "control", "mode": mid,
             "evalSet": i in eval_ids})

    train = [(r, m) for r, m in zip(rows, manifest) if not m["evalSet"]]
    evalr = [(r, m) for r, m in zip(rows, manifest) if m["evalSet"]]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, part in (("scenarios-train.jsonl", train), ("scenarios-eval.jsonl", evalr),
                       ("manifest.jsonl", list(zip(rows, manifest)))):
        with (OUT_DIR / name).open("w", encoding="utf-8") as fh:
            for r, m in part:
                if name == "manifest.jsonl":
                    fh.write(json.dumps(m, ensure_ascii=False) + "\n")
                else:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Balance report
    from collections import Counter
    wf = Counter(next(iter(r["gold"]["workflow"]["probabilities"])) for r, _ in train)
    poc = Counter(next(iter(r["gold"]["primary_poc"]["probabilities"])) for r, _ in train)
    print(f"sets: {len(sets)}  train: {len(train)}  eval: {len(evalr)}  (items = cases × 5 vragen)")
    print("train primary_poc:", dict(poc))
    print("train workflow:", dict(wf))


if __name__ == "__main__":
    build()
