"""POC demo catalog for the deep-agent simulation dashboard.

Each POC has its own prompting modes; only Utrecht (and Crosstrack) need a
scenario-run id from poc/scenario-runs/.
"""

from __future__ import annotations

from typing import Any

POC_IDS = ("breda", "rijnland", "utrecht", "crosstrack", "minigim", "eindhoven")

_UTRECHT_MODES: list[dict[str, str]] = [
    {
        "id": "execute",
        "label": "Uitvoeren + visual demo",
        "template": (
            "Delegeer naar utrecht: bouw de world scene voor scenario run {rid} "
            "en toon de visual demo."
        ),
    },
    {
        "id": "plan",
        "label": "Alleen run plan (geen executie)",
        "template": (
            "Delegeer naar utrecht: geef alléén een run plan voor de utrecht-world-scene "
            "recipe voor scenario run {rid}. Voer nog niets uit."
        ),
    },
    {
        "id": "critical",
        "label": "Kritische toets, daarna uitvoeren",
        "template": (
            "Toets kritisch of scenario run {rid} geschikt is voor een world-scene build "
            "(risico's, missende inputs, grounding). Delegeer daarna naar utrecht om te "
            "bouwen en de demo te tonen."
        ),
    },
    {
        "id": "compare",
        "label": "Control vs scenario vergelijking",
        "template": (
            "Bouw de world scene voor {rid}, laat geospecialist control vs scenario "
            "vergelijken (deltas, km²), en toon de demo."
        ),
    },
    {
        "id": "geo",
        "label": "Geo-analyse + critic-validatie",
        "template": (
            "Bouw de world scene voor scenario run {rid}, laat geospecialist de lagen "
            "analyseren en critic de bundle valideren. Toon de demo."
        ),
    },
    {
        "id": "normketen",
        "label": "Normketen: intake → norm → formaliseer",
        "template": (
            "Nieuwe aanvraag: 'Ik wil weten waar een zonnepark mag in de gemeente Utrecht, "
            "bij voorkeur buiten de Groene contour.' Doorloop de normketen: (1) intake "
            "normaliseert tot schema-geldig OpportunityMapRequest, (2) normspecialist "
            "zoekt normkaarten, (3) formalizer stelt FormalRule op. Rapporteer alle drie "
            "artefacten."
        ),
    },
    {
        "id": "keten",
        "label": "Volledige keten (intake → … → build → validatie)",
        "template": (
            "Volledige keten voor scenario run {rid}. Aanvraag: 'Ik wil weten waar een "
            "zonnepark mag in de gemeente Utrecht, bij voorkeur buiten de Groene contour.' "
            "Voer ALLEEN deze 6 stappen uit, in volgorde: (1) intake SUBMIT submit_request, "
            "(2) normspecialist SUBMIT submit_norm_cards, (3) formalizer SUBMIT "
            "submit_formal_rule, (4) utrecht bouwt world scene voor {rid} — géén andere "
            "run-ids, (5) parallel geospecialist + critic, (6) explainer met "
            "crosscheck_formal_rule. STOP daarna."
        ),
    },
    {
        "id": "uitdaging_overzicht",
        "label": "Uitdaging-overzicht (5 opgaven × 3 scenario's per track;"
                 " energietoets: 2 tot plan 2)",
        "template": (
            "Delegeer naar utrecht: geef het uitdaging-overzicht — lees "
            "poc/scenarios/uitdagingen.json (de tracks zijn declaratief "
            "beschreven in poc/tracks/<track>.json; verzin geen tracks buiten "
            "die lijst) en geef per uitdaging (5 stuks): de titel, "
            "de tracks, en per track de 3 scenario's (energietoets: 2 tot plan 2) "
            "met de headline-delta "
            "(deltaVsControlPct uit scenario-report.json van de run in scenarioRuns). "
            "Sluit af met per uitdaging de grootste hefboom (grootste |delta|)."
        ),
    },
]

POC_DEMOS: list[dict[str, Any]] = [
    {
        "id": "breda",
        "label": "Breda",
        "subtitle": "Plane A — five-value scan & scan QA (S4)",
        "requiresScenario": False,
        "viz": "breda-scan",
        "highlightRecipes": ["breda-five-value-scan", "breda-scan-qa"],
        "simulationPages": [
            {"title": "Flow demo", "path": "breda-flow-demo.html"},
            {"title": "What-if demo", "path": "breda-whatif-demo.html"},
            {"title": "Report demo", "path": "breda-report-demo.html"},
        ],
        "modes": [
            {
                "id": "scan_plan",
                "label": "Run plan — five-value scan",
                "template": (
                    "Delegeer naar breda: geef een concreet run plan voor recipe "
                    "breda-five-value-scan — inputs, stappen, process ids, outputs, risico."
                ),
            },
            {
                "id": "scan_execute",
                "label": "Execute — five-value scan (map)",
                "template": (
                    "Delegeer naar breda: voer de vijf-waardenscan uit met de tool "
                    "run_breda_scan en vat de uitslag samen — verdict, de rollup per "
                    "waarde (top/bottom) en de zwakste buurten. Vermeld dat de kaart "
                    "in het rechterpaneel staat."
                ),
            },
            {
                "id": "qa_plan",
                "label": "Run plan — grounded scan QA",
                "template": (
                    "Delegeer naar breda: run plan voor breda-scan-qa met cite-or-abstain "
                    "(GENAI seam S4) — welke inputs, welke QA-stappen, verwachte artefacten."
                ),
            },
            {
                "id": "inventory",
                "label": "Recipe-inventaris Breda",
                "template": (
                    "Welke nLDT-recipes horen bij de Breda POC? Gebruik list_recipes/get_recipe "
                    "of delegeer breda; vergelijk Plane A scan vs QA."
                ),
            },
        ],
    },
    {
        "id": "rijnland",
        "label": "Rijnland",
        "subtitle": "Peil conflict, what-if & live freshness (H3)",
        "requiresScenario": False,
        "viz": "rijnland-viz",
        "highlightRecipes": [
            "rijnland-peil-conflict",
            "rijnland-peil-whatif",
            "rijnland-peil-conflict-live",
        ],
        "simulationPages": [
            {"title": "Flow demo", "path": "rijnland-flow-demo.html"},
            {"title": "What-if demo", "path": "rijnland-whatif-demo.html"},
        ],
        "modes": [
            {
                "id": "execute_live",
                "label": "Execute — peilen what-if (live kaart)",
                "template": (
                    "Delegeer naar rijnland: voer de peilen what-if uit met de tool "
                    "run_rijnland_live en vat samen — aantal stations, het venster en "
                    "wat de geanimeerde kaart laat zien."
                ),
            },
            
                {
                "id": "conflict_plan",
                "label": "Run plan — peil conflict",
                "template": (
                    "Delegeer naar rijnland: run plan voor rijnland-peil-conflict "
                    "(vigerend peilgebied × praktijk peilafwijking) — inputs, replay vs execute."
                ),
            },
            {
                "id": "whatif_plan",
                "label": "Run plan — what-if peilen",
                "template": (
                    "Delegeer naar rijnland: run plan voor rijnland-peil-whatif via CDC — "
                    "scenario-delta's, vereiste runDir/mode."
                ),
            },
            {
                "id": "live_plan",
                "label": "Run plan — live freshness-gated",
                "template": (
                    "Delegeer naar rijnland: leg het verschil uit tussen canonical replay en "
                    "rijnland-peil-conflict-live (freshness gate) en geef een run plan."
                ),
            },
        ],
    },
    {
        "id": "utrecht",
        "label": "Utrecht",
        "subtitle": "Plane A/B — opportunity map, world scene, scenario sweep",
        "requiresScenario": True,
        "viz": "worldscene",
        "highlightRecipes": [
            "utrecht-opportunity-map",
            "utrecht-world-scene",
            "utrecht-scenario-author",
            "utrecht-scenario-sweep",
        ],
        "simulationPages": [
            {"title": "What-if demo", "path": "utrecht-whatif-demo.html"},
            {"title": "Flow demo", "path": "utrecht-flow-demo.html"},
            {"title": "Context — Energietransitie", "path": "utrecht-context-energietransitie.html"},
            {"title": "Context — Wonen & Werken", "path": "utrecht-context-wonen-werken.html"},
            {"title": "Context — Water & Bodem", "path": "utrecht-context-water-bodem.html"},
            {"title": "Context — Landschap & Infrastructuur", "path": "utrecht-context-landschap-infra.html"},
            {"title": "Context — Landelijk Gebied", "path": "utrecht-context-landelijk-gebied.html"},
        ],
        "modes": _UTRECHT_MODES,
    },
    {
        "id": "minigim",
        "label": "MiniGIM",
        "subtitle": "Gebiedscheck — Lijst-v0.91 (74 items)",
        "requiresScenario": False,
        "viz": "minigim-viz",
        "highlightRecipes": ["minigim-gebiedscheck", "beleidskompas-omgevingsanalyse"],
        "simulationPages": [],
        "modes": [
            {
                "id": "execute_live",
                "label": "Execute — gebiedscheck (live rapport)",
                "template": (
                    "Delegeer naar minigim: voer de gebiedscheck uit met de tool "
                    "run_minigim_live en vat samen — verdict, de checklist-binding "
                    "(manual/auto/partial) en het rapport in het rechterpaneel."
                ),
            },
            
                {
                "id": "gebiedscheck_plan",
                "label": "Run plan — gebiedscheck",
                "template": (
                    "Delegeer naar minigim: run plan voor minigim-gebiedscheck voor een "
                    "voorbeeld-AOI rond Utrecht — checklist Lijst-v0.91, open bronnen, "
                    "verwachte outputs."
                ),
            },
            {
                "id": "checklist",
                "label": "Checklist & open data",
                "template": (
                    "Delegeer naar minigim: welke items uit Lijst-v0.91 worden automatisch "
                    "ingevuld uit keyless open sources, en welke vereisen handmatige input?"
                ),
            },
        ],
    },
    {
        "id": "eindhoven",
        "label": "Eindhoven bp2op",
        "subtitle": "Bestemmingsplan → omgevingsplan (V4 HITL)",
        "requiresScenario": False,
        "viz": "eindhoven-viz",
        "highlightRecipes": ["eindhoven-bp2op"],
        "simulationPages": [
            {"title": "Flow demo", "path": "eindhoven-flow-demo.html"},
            {"title": "Report demo", "path": "eindhoven-report-demo.html"},
        ],
        "modes": [
            {
                "id": "execute_live",
                "label": "Execute — bp2op-omzetting (live rapport)",
                "template": (
                    "Delegeer naar eindhoven: voer de bp2op-omzetting uit met de tool "
                    "run_eindhoven_live en vat samen — verdict, de counts en de "
                    "V4-mens-status (pending by design)."
                ),
            },
            
                {
                "id": "bp2op_plan",
                "label": "Run plan — bp2op conversie",
                "template": (
                    "Delegeer naar eindhoven: run plan voor eindhoven-bp2op — inputs, "
                    "stappen, V4 human-in-the-loop (altijd pending), verwachte outputs."
                ),
            },
            {
                "id": "hitl",
                "label": "HITL & governance",
                "template": (
                    "Delegeer naar eindhoven: waar in het bp2op-recipe is menselijke "
                    "goedkeuring verplicht, en welke gates mogen agents nooit overslaan?"
                ),
            },
        ],
    },
]

_BY_ID: dict[str, dict[str, Any]] = {p["id"]: p for p in POC_DEMOS}


def list_pocs() -> list[dict[str, Any]]:
    """Public catalog for the dashboard (no mode templates)."""
    return [
        {
            "id": p["id"],
            "label": p["label"],
            "subtitle": p["subtitle"],
            "requiresScenario": p["requiresScenario"],
            "viz": p["viz"],
            "highlightRecipes": p.get("highlightRecipes", []),
            "simulationPages": p.get("simulationPages", []),
        }
        for p in POC_DEMOS
    ]


def get_poc(poc_id: str) -> dict[str, Any]:
    key = poc_id.strip().lower()
    if key not in _BY_ID:
        raise KeyError(f"unknown POC: {poc_id}")
    return _BY_ID[key]


def modes_for_poc(poc_id: str) -> list[dict[str, str]]:
    return list(get_poc(poc_id)["modes"])


def format_question(poc_id: str, mode_id: str, scenario_run_id: str | None) -> str:
    poc = get_poc(poc_id)
    mode = next((m for m in poc["modes"] if m["id"] == mode_id), None)
    if mode is None:
        raise ValueError(f"unknown mode {mode_id!r} for POC {poc_id!r}")
    if poc["requiresScenario"]:
        if not scenario_run_id:
            raise ValueError(f"POC {poc_id} requires a scenario run id")
        return mode["template"].format(rid=scenario_run_id)
    return mode["template"].format(rid=scenario_run_id or "")
