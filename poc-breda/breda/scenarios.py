"""What-if-naad voor de Breda vijf-waardenscan (S7/S8-analoog, PoC-4).

Een scenario is een **contract, geen prompt**: mutaties over de
samenstel-parameters van de scan (``indicators.DEFAULT_PARAMS``), met
verplichte bewijsklasse:

- ``indicator_variance`` — varieert een geciteerde drempel/waarde
  (bv. ``access_min_present`` 4 → 6);
- ``policy_variant`` — slaat een gedocumenteerde samenstelkeuze om
  (``deals_rule`` → floor, ``social_rule`` → ouderen_gated);
- ``hypothetical`` — vrije verkenning zonder onderbouwing; ``rationale``
  verplicht (het eerlijke tegenover van het missing-beleid).

Runner-garanties: de ongemuteerde **control** moet de baseline-scores
bit-identiek reproduceren (V3) vóór er één variant wordt geloofd; elke
mutatie groundt tegen het mutatie-woordenboek (V2); het set-bestand is
schema-valide (V0). Auteurs: ``file`` · ``auto`` (deterministisch) ·
``llm`` (voorstel-only, ledger, identiteitsstempel door de naad).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import indicators
from .values import CONGRESS, PROGRAMME_URL

ROOT = Path(__file__).resolve().parent.parent
SPEC_SCHEMA_PATH = ROOT / "schemas" / "value-scenario.schema.json"

WAARDEN = ("democratic", "spatial", "economic", "social")

ACTION_TO_ASPECT = {
    "set_access_min_present": "access_min_present",
    "set_deals_rule": "deals_rule",
    "set_social_rule": "social_rule",
    "set_spatial_weights": "spatial_weights",
    "set_economic_weights": "economic_weights",
    "drop_input": "drop_input",
}
POLICY_ASPECTS = {"deals_rule", "social_rule"}  # gedocumenteerde samenstelkeuzes


class ScenarioError(RuntimeError):
    """Auteurs- of gate-fout (nooit stil hersteld)."""


# --------------------------------------------------------------------------- #
# Schema + gronding (V0/V2)
# --------------------------------------------------------------------------- #


def load_spec_schema() -> dict:
    return json.loads(SPEC_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_scenario(spec: dict) -> list[str]:
    """V0 (schema) + V2 (basis-gronding). Geeft schendingen terug (leeg=ok)."""
    import jsonschema

    schendingen = []
    try:
        jsonschema.validate(spec, load_spec_schema())
    except jsonschema.ValidationError as exc:
        return [f"schema: {exc.message}"]

    basis = spec["basis"]
    aspect = ACTION_TO_ASPECT[spec["mutations"][0]["action"]]
    for m in spec["mutations"]:
        a = ACTION_TO_ASPECT.get(m["action"])
        if a is None:
            schendingen.append(f"onbekende actie {m['action']!r}")
        elif a != aspect:
            aspect = None  # meerdere aspecten: variedAspect moet weg of afgedwongen

    btype = basis["type"]
    if btype == "indicator_variance":
        if not basis.get("variedAspect"):
            schendingen.append("indicator_variance vereist variedAspect")
        elif aspect is not None and basis["variedAspect"] != aspect:
            schendingen.append(
                f"variedAspect {basis['variedAspect']!r} matcht geen enkele mutatie "
                f"(acties wijzen naar {aspect!r})"
            )
    elif btype == "policy_variant":
        if not basis.get("variedAspect"):
            schendingen.append("policy_variant vereist variedAspect")
        elif basis["variedAspect"] not in POLICY_ASPECTS:
            schendingen.append(
                f"policy_variant {basis['variedAspect']!r} is geen gedocumenteerde "
                f"samenstelkeuze (verwacht één van {sorted(POLICY_ASPECTS)})"
            )
    elif btype == "hypothetical" and not basis.get("rationale"):
        schendingen.append("hypothetical vereist rationale (geen onderbouwing claimen)")

    # regel-specifieke kruiscontroles die het schema niet vangt
    for m in spec["mutations"]:
        if m["action"] == "set_deals_rule" and m.get("rule") == "ouderen_gated":
            schendingen.append("set_deals_rule kent alleen mean|floor")
        if m["action"] == "set_social_rule" and m.get("rule") == "floor":
            schendingen.append("set_social_rule kent alleen mean|ouderen_gated")
    return schendingen


# --------------------------------------------------------------------------- #
# Mutaties → parameters
# --------------------------------------------------------------------------- #


def apply_mutations(mutations: list[dict]) -> dict:
    """Mutatielijst → parameters-dict (toegepast op een verse kopie van
    DEFAULT_PARAMS). Onbekende waarden zijn al door het schema geblokkeerd;
    hier wordt alleen nog grondig samengesteld."""
    params = json.loads(json.dumps(indicators.DEFAULT_PARAMS))  # diepe kopie
    for m in mutations:
        action = m["action"]
        if action == "set_access_min_present":
            params["accessMinPresent"] = m["value"]
        elif action == "set_deals_rule":
            params["dealsRule"] = m["rule"]
        elif action == "set_social_rule":
            params["socialRule"] = m["rule"]
            if "thresholdPct" in m:
                params["socialGatePct"] = m["thresholdPct"]
        elif action == "set_spatial_weights":
            for k in ("groen", "afstand", "bomen"):
                if k in m:
                    params["spatialWeights"][k] = m[k]
        elif action == "set_economic_weights":
            for k in ("dak", "bedrijven"):
                if k in m:
                    params["economicWeights"][k] = m[k]
        elif action == "drop_input":
            params["dropInputs"] = sorted(
                set(params["dropInputs"]) | {m["input"]}
            )
    return params


# --------------------------------------------------------------------------- #
# Runner: control + varianten + stabiliteit
# --------------------------------------------------------------------------- #


def _scores_by_code(scan: dict) -> dict:
    return {
        b["buurtcode"]: {v: b["scores"][v]["score"] for v in WAARDEN}
        for b in scan["buurten"]
    }


def _ranks(scan: dict) -> dict:
    """Per waarde: buurtcode → rang (1 = hoogste score, land-buurten)."""
    out = {}
    for v in WAARDEN:
        gesorteerd = sorted(
            (
                (b["scores"][v]["score"], b["buurtcode"])
                for b in scan["buurten"]
                if b.get("water") == "NEE" and b["scores"][v]["score"] is not None
            ),
            key=lambda t: (-t[0], t[1]),
        )
        out[v] = {code: i for i, (_s, code) in enumerate(gesorteerd, start=1)}
    return out


def run_scenarios(baseline_scan: dict, layers: dict, specs: list[dict]) -> dict:
    """Voert control + alle varianten deterministisch uit (offline, vanaf
    lagen-cache) en produceert het rapport-artefact met V0/V2/V3-verdict."""
    errors: list[str] = []
    checks: list[dict] = []

    def check(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            errors.append(f"{cid}: {detail}")

    # V0/V2 per scenario vóór enige executie
    gevalideerd, afgewezen = [], []
    for spec in specs:
        schendingen = validate_scenario(spec)
        if schendingen:
            afgewezen.append({"scenarioId": spec.get("scenarioId"),
                              "reden": "; ".join(schendingen)})
        else:
            gevalideerd.append(spec)
    check("V0-V2-scenariocontracten", not afgewezen,
          f"{len(gevalideerd)} aangenomen, {len(afgewezen)} afgewezen"
          + (f" ({', '.join(a['scenarioId'] or '?' for a in afgewezen)})" if afgewezen else ""))

    # V3: control moet de baseline bit-identiek reproduceren
    control = indicators.compute_scan(layers)
    base = _scores_by_code(baseline_scan)
    ctrl = _scores_by_code(control)
    verschillen = [
        f"{code}/{v}" for code in base
        for v in WAARDEN
        if base[code][v] != ctrl.get(code, {}).get(v)
    ]
    check("V3-control-identiteit", not verschillen,
          "control reproduceert de baseline exact" if not verschillen
          else f"{len(verschillen)} scoreverschilen, o.a. {verschillen[:5]}")

    varianten = []
    variant_scans = []
    if not verschillen:  # alleen geloven als de control klopt
        ctrl_ranks = _ranks(control)
        naam_by_code = {b["buurtcode"]: b.get("buurtnaam") for b in control["buurten"]}
        for spec in gevalideerd:
            params = apply_mutations(spec["mutations"])
            variant = indicators.compute_scan(layers, params)
            variant_scans.append(variant)
            var_scores = _scores_by_code(variant)
            var_ranks = _ranks(variant)
            per_buurt = {}
            movers = []
            profiel = {v: {"winst": 0, "verlies": 0, "som": 0.0, "n": 0}
                       for v in WAARDEN}
            for code in ctrl:
                deltas = {}
                van_naar = {}
                rank_deltas = {}
                for v in WAARDEN:
                    c0, c1 = ctrl[code][v], var_scores[code][v]
                    if c0 is not None and c1 is not None:
                        d = round(c1 - c0, 1)
                        van_naar[v] = {"van": c0, "naar": c1}
                        if d != 0:
                            deltas[v] = d
                            profiel[v]["som"] += d
                            profiel[v]["n"] += 1
                            if d > 0:
                                profiel[v]["winst"] += 1
                            else:
                                profiel[v]["verlies"] += 1
                    r0 = ctrl_ranks[v].get(code)
                    r1 = var_ranks[v].get(code)
                    if r0 is not None and r1 is not None and r0 != r1:
                        rank_deltas[v] = r1 - r0
                if deltas:
                    per_buurt[code] = {"deltas": deltas, "vanNaar": van_naar}
                if rank_deltas:
                    movers.append((code, rank_deltas))
            profiel_out = {}
            for v, p in profiel.items():
                if p["n"]:
                    profiel_out[v] = {**p, "gem": round(p["som"] / p["n"], 2)}
            varianten.append({
                "scenarioId": spec["scenarioId"],
                "name": spec["name"],
                "basis": spec["basis"],
                "mutations": spec["mutations"],
                "params": params,
                "proposedBy": spec.get("proposedBy", "file"),
                "provenanceNote": spec.get("provenanceNote") or "",
                "lakeSeriesHints": spec.get("lakeSeriesHints") or [],
                "nBuurtenVeranderd": len(per_buurt),
                "deltas": per_buurt,
                "profiel": profiel_out,
                "grootsteVerschuivers": [
                    {"buurtcode": c, "buurt": naam_by_code.get(c, c),
                     "rangDelta": d} for c, d in
                    sorted(movers, key=lambda t: -sum(abs(x) for x in t[1].values()))[:5]
                ],
            })

    # rank-stabiliteit over control + varianten per waarde
    stabiliteit = _stability([control] + variant_scans) if not verschillen else {}

    verdict = "pass" if not errors else "fail"
    return {
        "congress": CONGRESS,
        "programmeUrl": PROGRAMME_URL,
        "nScenarios": len(specs),
        "nAccepted": len(gevalideerd),
        "rejected": afgewezen,
        "control": {"identicalToBaseline": not verschillen},
        "variants": varianten,
        "stability": stabiliteit,
        "validation": {"checks": checks, "errors": errors, "verdict": verdict},
    }


def _stability(scans: list[dict]) -> dict:
    """Per waarde: hoe vaak staat een buurt in de top-5 óf onderste-5 over
    alle runs (control + varianten)? Score n/n = robuust."""
    first = scans[0]
    out = {}
    for v in WAARDEN:
        telling: dict[str, dict] = {}
        n_runs = 0
        for scan in scans:
            land = [b for b in scan["buurten"]
                    if b.get("water") == "NEE" and b["scores"][v]["score"] is not None]
            if not land:
                continue
            n_runs += 1
            gesorteerd = sorted(land, key=lambda b: (-b["scores"][v]["score"], b["buurtcode"]))
            top = {b["buurtcode"] for b in gesorteerd[:5]}
            bodem = {b["buurtcode"] for b in gesorteerd[-5:]}
            for b in gesorteerd:
                code = b["buurtcode"]
                t = telling.setdefault(code, {"buurt": b.get("buurtnaam"), "top": 0, "bodem": 0})
                if code in top:
                    t["top"] += 1
                if code in bodem:
                    t["bodem"] += 1
        robuust = [
            {"buurtcode": c, "buurt": t["buurt"],
             "top": t["top"], "bodem": t["bodem"], "runs": n_runs}
            for c, t in telling.items() if t["top"] == n_runs or t["bodem"] == n_runs
        ]
        out[v] = {"runs": n_runs, "robust": sorted(
            robuust, key=lambda r: -(r["top"] + r["bodem"]))}
    return out


# --------------------------------------------------------------------------- #
# Auteurs — file · auto · llm (voorstel-only, één interface)
# --------------------------------------------------------------------------- #


def author_from_file(path: Path) -> tuple[list[dict], list[dict]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    specs = doc["scenarios"] if isinstance(doc, dict) else doc
    aangenomen, afgewezen = [], []
    for spec in specs:
        if validate_scenario(spec):
            afgewezen.append({"scenarioId": spec.get("scenarioId"),
                              "reden": "; ".join(validate_scenario(spec))})
        else:
            spec.setdefault("proposedBy", "file")
            aangenomen.append(spec)
    return aangenomen, afgewezen


def deterministic_author(max_scenarios: int = 6) -> tuple[list[dict], list[dict]]:
    """Mechanische afleiding uit de parameters-zelfde set die de LLM-auteur
    zou mogen voorstellen — doubles as golden set voor de LLM-naad."""
    voorstellen = [
        {
            "scenarioId": "VS-ACC-MIN6",
            "name": "Accessibility requires all six services",
            "basis": {"type": "indicator_variance", "variedAspect": "access_min_present"},
            "mutations": [{"action": "set_access_min_present", "value": 6}],
            "provenanceNote": "threshold 4/6 → 6/6 (canonical value is 4)",
        },
        {
            "scenarioId": "VS-DEM-FLOOR",
            "name": "Neighbourhood deals as a hard democratic floor",
            "basis": {"type": "policy_variant", "variedAspect": "deals_rule"},
            "mutations": [{"action": "set_deals_rule", "rule": "floor"}],
            "provenanceNote": "mean → minimum of accessibility and deals",
        },
        {
            "scenarioId": "VS-SOC-GATED",
            "name": "Heat attention doubled above 25% aged 65+",
            "basis": {"type": "policy_variant", "variedAspect": "social_rule"},
            "mutations": [{"action": "set_social_rule", "rule": "ouderen_gated",
                           "thresholdPct": 25}],
            "provenanceNote": "paved share counts double where the 65+ share exceeds 25%",
        },
        {
            "scenarioId": "VS-SPA-GROEN2",
            "name": "Green coverage doubled in spatial value",
            "basis": {
                "type": "hypothetical",
                "rationale": "exploration: no policy document weighs green "
                             "coverage heavier than green distance and trees",
            },
            "mutations": [{"action": "set_spatial_weights", "groen": 2}],
            "provenanceNote": "weight 1 → 2 (hypothetical)",
        },
        {
            "scenarioId": "VS-SPA-ZONDER-BOMEN",
            "name": "Spatial value without the tree counter",
            "basis": {
                "type": "hypothetical",
                "rationale": "sensitivity test without a policy basis: the "
                             "tree layer counts public green only, so dropping it "
                             "shows how much the spatial score depends on that "
                             "single source",
            },
            "mutations": [{"action": "drop_input", "input": "bomen"}],
            "provenanceNote": "sensitivity test — not a documented policy choice",
        },
        {
            "scenarioId": "VS-ECO-DAK-ZWAAR",
            "name": "Roof potential dominates economic value",
            "basis": {
                "type": "hypothetical",
                "rationale": "exploration: weighing energy yield heavier than "
                             "business density",
            },
            "mutations": [{"action": "set_economic_weights", "dak": 3}],
            "provenanceNote": "weight 1 → 3 (hypothetical)",
        },
    ]
    return voorstellen[:max_scenarios], []


class LLMScenarioAuthor:
    """Stelt ValueScenarioSpecs voor; beslist nooit. Zelfde transport en
    dezelfde lessen als de Q&A-naad (qa.resolve_transport)."""

    def __init__(self, llm_call=None, model=None, endpoint=None, timeout=180.0):
        import os

        from . import qa

        self.endpoint = endpoint if endpoint is not None else os.environ.get(
            "LDT_SCENARIO_LLM_ENDPOINT", ""
        )
        self.model = model or os.environ.get("LDT_SCENARIO_LLM_MODEL", "open-model-local")
        self._llm_call = llm_call or qa.resolve_transport()
        self.timeout = timeout

    def system_prompt(
        self,
        max_scenarios: int,
        lake_series_hints: list[dict] | None = None,
        horizon_projections: list[dict] | None = None,
    ) -> str:
        hints = lake_series_hints or []
        hints_block = ""
        if hints:
            lines = []
            for h in hints[:12]:
                sid = h.get("seriesId") or "?"
                var = h.get("variable") or ""
                note = h.get("note") or h.get("title") or ""
                lines.append(f"- {sid} ({var}): {note}")
            hints_block = (
                " Lake time-series hints (cite seriesId in provenanceNote when "
                "relevant; never invent seriesIds):\n" + "\n".join(lines) + "\n"
                " Prefer exploring social_rule ouderen_gated near the 25% 65+ "
                "gate and heat context from KNMI Gilze-Rijen when hints support it."
                " HARD: do NOT duplicate the deterministic golden set — forbidden "
                "exact clones: accessMinPresent=6, deals_rule=floor, "
                "social_rule=ouderen_gated@25 alone, spatial groen=2 only, "
                "drop_input bomen alone. Combine TS evidence into NEW variants "
                "(e.g. ouderen_gated with a different thresholdPct grounded in "
                "CBS 65+ trends; economic weights for zonnestroom; spatial mixes "
                "tied to KNMI tmax). At least two scenarios must name a "
                "seriesId in provenanceNote."
            )
        if horizon_projections:
            nldt = Path(__file__).resolve().parents[2] / "nldt"
            if str(nldt) not in sys.path:
                sys.path.insert(0, str(nldt))
            from services.timeseries.horizon import format_projections_for_prompt

            hints_block += (
                "\n Horizon linear projections to 2050 (method=linear_ols; "
                "percentages clamped 0–100). Use these to justify thresholdPct "
                "or weights; cite seriesId + '2050' in provenanceNote:\n"
                + format_projections_for_prompt(horizon_projections, limit=10)
                + "\n Do not clone VS-2050-* floor mutations if already present."
            )
        return (
            "Je stelt what-if-scenario's voor de Breda vijf-waardenscan voor als "
            "JSON-array (geen uitleg). Een deterministische engine voert ze uit; "
            "jij beslist NIET. Regels: (1) scenarioId begint met 'VS-' en is "
            "uniek; (2) mutaties alléén uit: set_access_min_present{value:1-6}, "
            "set_deals_rule{rule:mean|floor}, set_social_rule{rule:mean|"
            "ouderen_gated,thresholdPct:0-100}, set_spatial_weights{groen/afstand/"
            "bomen:1-9}, set_economic_weights{dak/bedrijven:1-9}, drop_input{input:"
            "bomen|bedrijvigheid|deals|groen_afstand}; (3) elke basis verklaart "
            "zichzelf: indicator_variance vereist variedAspect dat bij de mutatie "
            "past (access_min_present/spatial_weights/economic_weights/drop_input); "
            "policy_variant alléén voor de gedocumenteerde samenstelkeuzes "
            "deals_rule of social_rule; hypothetical vereist rationale (≥10 tekens) "
            "— gebruik het voor wegingen zonder onderbouwing; (4) max "
            f"{max_scenarios} scenario's, prefererend wat een bestuurder echt "
            "overweegt; (5) elk object precies deze vorm: "
            '{"scenarioId":"VS-…","name":"…","basis":{"type":"…","variedAspect":'
            '"…","rationale":"…"},"mutations":[…],"provenanceNote":"…"}. '
            "Huidige parameters: accessMinPresent=4, dealsRule=mean, socialRule="
            f"mean, gewichten alles 1.{hints_block}"
        )

    def propose(
        self,
        max_scenarios: int = 4,
        lake_series_hints: list[dict] | None = None,
        horizon_projections: list[dict] | None = None,
    ) -> tuple[list[dict], list[dict]]:
        from . import qa

        if not self.endpoint:
            raise ScenarioError(
                "LLMScenarioAuthor vereist LDT_SCENARIO_LLM_ENDPOINT (geen gisfallback)"
            )
        hints = lake_series_hints or []
        horizons = horizon_projections or []
        user_msg = "Stel scenario's voor."
        if hints or horizons:
            user_msg += (
                f" Gebruik de {len(hints)} lakeSeriesHints"
                + (f" en {len(horizons)} 2050-projecties" if horizons else "")
                + " om minstens één scenario te onderbouwen met een seriesId."
            )
        raw = qa._strip_think(self._llm_call(
            self.endpoint, self.model,
            self.system_prompt(
                max_scenarios,
                lake_series_hints=hints,
                horizon_projections=horizons,
            ),
            user_msg, self.timeout,
        ))
        try:
            body = json.loads(raw[raw.index("["): raw.rindex("]") + 1])
        except (ValueError, IndexError) as exc:
            return [], [{"reason": f"JSON onparseerbaar: {exc}", "raw": raw[:300]}]
        aangenomen, afgewezen = [], []
        for item in body:
            if not isinstance(item, dict):
                afgewezen.append({"reason": f"geen object: {str(item)[:80]}"})
                continue
            for mut in item.get("mutations", []):
                # PoC-1-les §5.2: modellen zeggen 'type' waar het contract
                # 'action' vraagt — deterministische alias-reparatie door de naad
                if isinstance(mut, dict) and "type" in mut and "action" not in mut:
                    mut["action"] = mut.pop("type")
            item["proposedBy"] = f"llm-proposal#{qa._slug(self.model)}"
            # Prefer seriesIds the model named in provenance; else attach digest hints
            note = str(item.get("provenanceNote") or "")
            cited = [
                {"seriesId": h.get("seriesId"), "variable": h.get("variable")}
                for h in hints
                if h.get("seriesId") and str(h["seriesId"]) in note
            ]
            if not cited and hints:
                cited = [
                    {"seriesId": h.get("seriesId"), "variable": h.get("variable")}
                    for h in hints if h.get("seriesId")
                ][:4]
            if cited:
                item["lakeSeriesHints"] = cited
            schendingen = validate_scenario(item)
            if schendingen:
                afgewezen.append({"scenarioId": item.get("scenarioId"),
                                  "reden": "; ".join(schendingen)})
            else:
                aangenomen.append(item)
        # dubbele ids en budgetbewaking (auteur-ledger)
        gezien = set()
        for spec in list(aangenomen):
            sid = spec["scenarioId"]
            if sid in gezien or len(aangenomen) > max_scenarios:
                aangenomen.remove(spec)
                afgewezen.append({"scenarioId": sid,
                                  "reden": "dubbel scenarioId of budget overschreden"})
            gezien.add(sid)
        return aangenomen, afgewezen


def breda_lake_series_hints() -> list[dict]:
    """Curated open TS hints aligned with the five-value scan (CBS KWB + KNMI 350).

    Prefer live lake/Elasticsearch when available; otherwise fixture-derived notes
    so S7 LLM can cite series without inventing ids.
    """
    # Try live discovery first (nLDT lake + ES mock/real).
    try:
        import os
        from pathlib import Path

        nldt = Path(__file__).resolve().parents[2] / "nldt"
        if str(nldt) not in sys.path:
            sys.path.insert(0, str(nldt))
        os.environ.setdefault("NLDT_ELASTICSEARCH_MOCK", "1")
        from services.elasticsearch import reset_memory_store, search_lake
        from services.elasticsearch.indexer import bulk_index, docs_from_series_json
        from services.timeseries.ingest import ingest_cbs_kwb_breda, ingest_knmi_gilze_rijen

        if not os.environ.get("NLDT_LAKE_FS_ROOT"):
            import tempfile
            os.environ["NLDT_LAKE_BACKEND"] = "fs"
            os.environ["NLDT_LAKE_FS_ROOT"] = tempfile.mkdtemp(prefix="nldt-breda-s7-")
        reset_memory_store()
        ingest_knmi_gilze_rijen()
        ingest_cbs_kwb_breda()
        bulk_index(docs_from_series_json())
        hits = search_lake("breda tmax zonnestroom 65", poc="breda", size=12)
        live = []
        for h in hits:
            if not h.get("seriesId"):
                continue
            live.append({
                "seriesId": h.get("seriesId"),
                "variable": h.get("variable"),
                "poc": h.get("poc") or "breda",
                "title": h.get("title"),
                "note": h.get("title") or h.get("variable"),
            })
        if live:
            return live
    except Exception:
        pass

    return [
        {
            "seriesId": "knmi-daily-tmax-350",
            "variable": "tmax",
            "poc": "breda",
            "title": "KNMI Gilze-Rijen daily max temperature",
            "note": "Jul–Aug 2024 peaks ~31°C — heat context for social value",
        },
        {
            "seriesId": "knmi-daily-neerslag-350",
            "variable": "neerslag",
            "poc": "breda",
            "title": "KNMI Gilze-Rijen daily precipitation",
            "note": "Local rainfall series for climate stress narratives",
        },
        {
            "seriesId": "cbs-kwb-percentagepersonen65jaarenouder-bu07580202",
            "variable": "percentagePersonen65JaarEnOuder",
            "poc": "breda",
            "title": "Heusdenhout 65+ share",
            "note": "Heusdenhout 65+ rose 22.0→25.1% (2020–2024); crosses 25% social gate",
        },
        {
            "seriesId": "cbs-kwb-percentagepersonen65jaarenouder-bu07580101",
            "variable": "percentagePersonen65JaarEnOuder",
            "poc": "breda",
            "title": "Belcrum 65+ share",
            "note": "Belcrum 65+ rose 16.2→18.9% (2020–2024); below 25% gate",
        },
        {
            "seriesId": "cbs-kwb-percentagewoningenmetzonnestroom-bu07580101",
            "variable": "percentageWoningenMetZonnestroom",
            "poc": "breda",
            "title": "Belcrum solar share",
            "note": "Belcrum zonnestroom 8.5→22.1% — economic/dakpotentieel trend",
        },
        {
            "seriesId": "cbs-kwb-percentagewoningenmetzonnestroom-bu07580202",
            "variable": "percentageWoningenMetZonnestroom",
            "poc": "breda",
            "title": "Heusdenhout solar share",
            "note": "Heusdenhout zonnestroom 12.0→28.4% — economic trend",
        },
    ]


def breda_horizon_projections(target_year: int = 2050) -> list[dict]:
    """Linear OLS projections from CBS KWB Breda fixture (and lake if available)."""
    nldt = Path(__file__).resolve().parents[2] / "nldt"
    if str(nldt) not in sys.path:
        sys.path.insert(0, str(nldt))
    from services.timeseries.horizon import projections_from_cbs_kwb_rows

    fixture = nldt / "tests" / "fixtures" / "timeseries" / "cbs_kwb_breda_sample.json"
    rows = json.loads(fixture.read_text(encoding="utf-8")).get("rows") or []
    return projections_from_cbs_kwb_rows(rows, target_year=target_year)


def enrich_hints_with_projections(
    hints: list[dict],
    projections: list[dict],
) -> list[dict]:
    """Append 2050 projection notes onto matching lakeSeriesHints."""
    by_id = {p["seriesId"]: p for p in projections}
    out = []
    for h in hints:
        sid = h.get("seriesId")
        note = h.get("note") or h.get("title") or ""
        p = by_id.get(sid)
        if p:
            note = (
                f"{note} | linear→{p['horizon']}: {p['projected']}{p['unit']} "
                f"(from {p['lastObserved']['year']}={p['lastObserved']['value']})"
            ).strip(" |")
        out.append({**h, "note": note, "horizonProjection": p})
    # Also expose projection-only entries not already in hints
    known = {h.get("seriesId") for h in out}
    for p in projections:
        if p["seriesId"] in known:
            continue
        out.append({
            "seriesId": p["seriesId"],
            "variable": p["variable"],
            "poc": "breda",
            "title": f"{p['buurtnaam']} {p['variable']} → {p['horizon']}",
            "note": (
                f"linear OLS {p['lastObserved']['year']}={p['lastObserved']['value']}"
                f"{p['unit']} → {p['horizon']}≈{p['projected']}{p['unit']}"
            ),
            "horizonProjection": p,
        })
    return out


def deterministic_scenarios_2050(
    projections: list[dict],
    *,
    max_scenarios: int = 3,
) -> tuple[list[dict], list[dict]]:
    """Fixed 2050 what-if contracts calibrated to linear CBS projections."""
    def _find(var: str, buurt: str | None = None) -> dict | None:
        for p in projections:
            if p["variable"] != var:
                continue
            if buurt and p["buurtcode"] != buurt:
                continue
            return p
        return None

    h65 = _find("percentagePersonen65JaarEnOuder", "BU07580202")
    b65 = _find("percentagePersonen65JaarEnOuder", "BU07580101")
    zon_h = _find("percentageWoningenMetZonnestroom", "BU07580202")
    groen = _find("afstandTotOpenbaarGroenTotaal")

    specs: list[dict] = []
    if h65:
        thr = int(round(min(100, max(1, h65["projected"]))))
        specs.append({
            "scenarioId": "VS-2050-SOC-GATE",
            "name": f"Extra heat focus where over {thr}% are aged 65+ (2050 projection)",
            "basis": {
                "type": "policy_variant",
                "variedAspect": "social_rule",
                "rationale": (
                    f"Linear CBS trend projects Heusdenhout 65+ to "
                    f"{h65['projected']}% in {h65['horizon']} "
                    f"(was {h65['lastObserved']['value']}% in "
                    f"{h65['lastObserved']['year']}); calibrate ouderen_gated "
                    f"threshold to that horizon."
                ),
            },
            "mutations": [{
                "action": "set_social_rule",
                "rule": "ouderen_gated",
                "thresholdPct": thr,
            }],
            "provenanceNote": (
                f"{h65['seriesId']} linear→{h65['horizon']}={h65['projected']}%"
            ),
            "proposedBy": "auto-horizon-2050",
            "lakeSeriesHints": [
                {"seriesId": h65["seriesId"], "variable": h65["variable"]},
            ],
        })
    if zon_h and zon_h["projected"] >= 40:
        dak = 8 if zon_h["projected"] >= 60 else 6
        specs.append({
            "scenarioId": "VS-2050-ECO-ZON",
            "name": (
                f"Roof solar potential dominates the economy score "
                f"({dak}×; 2050 solar projection)"
            ),
            "basis": {
                "type": "hypothetical",
                "variedAspect": "economic_weights",
                "rationale": (
                    f"CBS projects Heusdenhout solar share to {zon_h['projected']}% "
                    f"by {zon_h['horizon']}; raise dak weight to reflect "
                    "saturated roof potential in the economic value."
                ),
            },
            "mutations": [{"action": "set_economic_weights", "dak": dak, "bedrijven": 2}],
            "provenanceNote": (
                f"{zon_h['seriesId']} linear→{zon_h['horizon']}={zon_h['projected']}%"
            ),
            "proposedBy": "auto-horizon-2050",
            "lakeSeriesHints": [
                {"seriesId": zon_h["seriesId"], "variable": zon_h["variable"]},
            ],
        })
    if groen or h65:
        specs.append({
            "scenarioId": "VS-2050-SPA-HITTE",
            "name": (
                "More weight on green cover, park distance and trees "
                "(2050 heat & ageing)"
            ),
            "basis": {
                "type": "hypothetical",
                "variedAspect": "spatial_weights",
                "rationale": (
                    "Horizon narrative: ageing (CBS 65+↑) plus heat (KNMI Gilze-Rijen) "
                    "justifies heavier spatial green and tree weights by 2050."
                ),
            },
            "mutations": [{
                "action": "set_spatial_weights",
                "groen": 7,
                "afstand": 5,
                "bomen": 6,
            }],
            "provenanceNote": (
                "knmi-daily-tmax-350; "
                + (f"{groen['seriesId']}→{groen['horizon']}" if groen else "cbs-kwb-65+")
            ),
            "proposedBy": "auto-horizon-2050",
            "lakeSeriesHints": (
                [{"seriesId": "knmi-daily-tmax-350", "variable": "tmax"}]
                + ([{"seriesId": groen["seriesId"], "variable": groen["variable"]}] if groen else [])
            ),
        })
    # optional Belcrum note-only not needed as scenario
    _ = b65
    specs = specs[:max_scenarios]
    afgewezen = []
    ok = []
    for spec in specs:
        schendingen = validate_scenario(spec)
        if schendingen:
            afgewezen.append({"scenarioId": spec.get("scenarioId"),
                              "reden": "; ".join(schendingen)})
        else:
            ok.append(spec)
    return ok, afgewezen


def _mutation_fingerprint(spec: dict) -> str:
    parts = []
    for m in spec.get("mutations") or []:
        items = sorted((k, v) for k, v in m.items())
        parts.append(str(items))
    return "|".join(parts)


def merge_horizon_floor_and_llm(
    floor: list[dict],
    llm_specs: list[dict],
    *,
    max_scenarios: int,
) -> tuple[list[dict], list[dict]]:
    """Deterministic 2050 floor first; LLM fills remaining budget without clones."""
    accepted = list(floor)
    rejected = []
    keys = {_mutation_fingerprint(s) for s in accepted}
    for spec in llm_specs:
        fp = _mutation_fingerprint(spec)
        if fp in keys:
            rejected.append({
                "scenarioId": spec.get("scenarioId"),
                "reden": "superseded by 2050 horizon floor (same mutation)",
            })
            continue
        if len(accepted) >= max_scenarios:
            rejected.append({
                "scenarioId": spec.get("scenarioId"),
                "reden": f"budget: max_scenarios={max_scenarios}",
            })
            continue
        accepted.append(spec)
        keys.add(fp)
    return accepted, rejected


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_params_to_end(
    year: int,
    *,
    start_year: int,
    end_year: int,
    end_params: dict,
) -> dict:
    """Lerp policy params from today's defaults toward an end-state dict."""
    span = max(1, end_year - start_year)
    t = max(0.0, min(1.0, (year - start_year) / span))
    start = indicators.DEFAULT_PARAMS
    end = end_params
    # Categorical switches flip halfway (or immediately if end differs and t>0
    # for social gate path — keep halfway for stability).
    use_end_cat = t >= 0.5
    return {
        "accessMinPresent": int(round(_lerp(
            float(start["accessMinPresent"]), float(end["accessMinPresent"]), t
        ))),
        "dealsRule": end["dealsRule"] if use_end_cat else start["dealsRule"],
        "socialRule": end["socialRule"] if use_end_cat else start["socialRule"],
        "socialGatePct": round(_lerp(
            float(start["socialGatePct"]), float(end["socialGatePct"]), t
        ), 1),
        "spatialWeights": {
            k: int(round(_lerp(
                float(start["spatialWeights"][k]),
                float(end["spatialWeights"][k]),
                t,
            )))
            for k in ("groen", "afstand", "bomen")
        },
        "economicWeights": {
            k: int(round(_lerp(
                float(start["economicWeights"][k]),
                float(end["economicWeights"][k]),
                t,
            )))
            for k in ("dak", "bedrijven")
        },
        "dropInputs": list(end["dropInputs"]) if use_end_cat else [],
        "_meta": {"horizonT": round(t, 4), "year": year},
    }


def _pathway_params_for_year(
    year: int,
    *,
    start_year: int,
    end_year: int,
    thr_end: float,
) -> dict:
    """Lerp policy params from today's defaults toward the 2050 floor."""
    end = {
        "accessMinPresent": indicators.DEFAULT_PARAMS["accessMinPresent"],
        "dealsRule": "mean",
        "socialRule": "ouderen_gated",
        "socialGatePct": float(thr_end),
        "spatialWeights": {"groen": 7, "afstand": 5, "bomen": 6},
        "economicWeights": {"dak": 8, "bedrijven": 2},
        "dropInputs": [],
    }
    # Keep prior behaviour: socialRule is ouderen_gated for the whole path.
    params = _lerp_params_to_end(
        year, start_year=start_year, end_year=end_year, end_params=end
    )
    params["socialRule"] = "ouderen_gated"
    params["dealsRule"] = "mean"
    params["dropInputs"] = []
    params["accessMinPresent"] = indicators.DEFAULT_PARAMS["accessMinPresent"]
    return params


def _build_pathway_keyframes(
    layers: dict,
    control_scan: dict,
    end_params: dict,
    *,
    start_year: int,
    end_year: int,
    step: int,
    param_fn=None,
) -> dict[str, dict]:
    """Shared keyframe builder: param_fn(year) → scan params (+ optional _meta)."""
    ctrl = _scores_by_code(control_scan)
    keyframes: dict[str, dict] = {}
    years = list(range(start_year, end_year + 1, step))
    if not years or years[-1] != end_year:
        years.append(end_year)
    for year in years:
        if param_fn:
            params = param_fn(year)
        else:
            params = _lerp_params_to_end(
                year,
                start_year=start_year,
                end_year=end_year,
                end_params=end_params,
            )
        meta_extra = params.pop("_meta", {"horizonT": 0.0, "year": year})
        meta = {
            "year": year,
            "t": meta_extra.get("horizonT", 0.0),
            "socialGatePct": params["socialGatePct"],
            "accessMinPresent": params.get("accessMinPresent"),
            "socialRule": params.get("socialRule"),
            "spatialWeights": dict(params["spatialWeights"]),
            "economicWeights": dict(params["economicWeights"]),
        }
        scan = indicators.compute_scan(layers, params)
        scores = _scores_by_code(scan)
        per_buurt = {}
        for code, c0 in ctrl.items():
            c1 = scores.get(code) or {}
            deltas = {}
            for v in WAARDEN:
                a, b = c0.get(v), c1.get(v)
                if a is not None and b is not None:
                    d = round(b - a, 1)
                    if d != 0:
                        deltas[v] = d
            per_buurt[code] = {
                "scores": {v: c1.get(v) for v in WAARDEN},
                "deltas": deltas,
                "vanNaar": {
                    v: {"van": c0[v], "naar": c1[v]}
                    for v in WAARDEN
                    if c0.get(v) is not None and c1.get(v) is not None
                },
            }
        keyframes[str(year)] = {"meta": meta, "perBuurt": per_buurt}
    return keyframes


def build_horizon_pathway_frames(
    layers: dict,
    control_scan: dict,
    projections: list[dict],
    *,
    start_year: int = 2026,
    end_year: int = 2050,
    step: int = 4,
) -> dict:
    """Precompute keyframe scans along the 2026→2050 policy pathway.

    Intermediate slider years are linearly interpolated in the browser between
    keyframes (compute_scan is ~5s; full yearly recompute is too slow for PoC).
    """
    h65 = next(
        (
            p for p in projections
            if p.get("variable") == "percentagePersonen65JaarEnOuder"
            and p.get("buurtcode") == "BU07580202"
        ),
        None,
    )
    thr_end = float(h65["projected"]) if h65 else 45.0
    thr_end = max(25.0, min(100.0, thr_end))

    def param_fn(year: int) -> dict:
        return _pathway_params_for_year(
            year, start_year=start_year, end_year=end_year, thr_end=thr_end
        )

    keyframes = _build_pathway_keyframes(
        layers,
        control_scan,
        {},
        start_year=start_year,
        end_year=end_year,
        step=step,
        param_fn=param_fn,
    )
    return {
        "startYear": start_year,
        "endYear": end_year,
        "step": step,
        "thrStart": 25.0,
        "thrEnd": thr_end,
        "bron": "deterministisch",
        "method": "lerp-params + keyframe compute_scan + browser score lerp",
        "keyframes": keyframes,
    }


def build_llm_scenario_pathway_frames(
    layers: dict,
    control_scan: dict,
    variant: dict,
    *,
    start_year: int = 2026,
    end_year: int = 2050,
    step: int = 4,
) -> dict | None:
    """Year-sweep toward one LLM proposal's end-params (not merged with others)."""
    by = str(variant.get("proposedBy") or "")
    if not by.lower().startswith("llm"):
        return None
    mutations = variant.get("mutations") or []
    if not mutations:
        return None
    end_params = apply_mutations(mutations)
    keyframes = _build_pathway_keyframes(
        layers,
        control_scan,
        end_params,
        start_year=start_year,
        end_year=end_year,
        step=step,
    )
    sid = variant.get("scenarioId") or ""
    title = _scenario_display_name(mutations, fallback=variant.get("name") or sid)
    return {
        "startYear": start_year,
        "endYear": end_year,
        "step": step,
        "thrStart": float(indicators.DEFAULT_PARAMS["socialGatePct"]),
        "thrEnd": float(end_params["socialGatePct"]),
        "bron": "llm",
        "scenarioId": sid,
        "title": title,
        "endParams": {
            "accessMinPresent": end_params["accessMinPresent"],
            "socialRule": end_params["socialRule"],
            "socialGatePct": end_params["socialGatePct"],
            "spatialWeights": dict(end_params["spatialWeights"]),
            "economicWeights": dict(end_params["economicWeights"]),
        },
        "method": (
            "single LLM proposal → lerp-params + keyframe compute_scan "
            "+ browser score lerp"
        ),
        "keyframes": keyframes,
    }


def build_llm_scenario_pathways(
    layers: dict,
    control_scan: dict,
    llm_variants: list[dict],
    *,
    start_year: int = 2026,
    end_year: int = 2050,
    step: int = 4,
) -> dict[str, dict]:
    """One independent 2026→2050 pathway per accepted LLM variant."""
    out: dict[str, dict] = {}
    for v in llm_variants:
        sid = v.get("scenarioId")
        if not sid:
            continue
        path = build_llm_scenario_pathway_frames(
            layers,
            control_scan,
            v,
            start_year=start_year,
            end_year=end_year,
            step=step,
        )
        if path:
            out[sid] = path
    return out


def build_llm_horizon_pathway_frames(
    layers: dict,
    control_scan: dict,
    llm_variants: list[dict],
    *,
    start_year: int = 2026,
    end_year: int = 2050,
    step: int = 4,
) -> dict | None:
    """Deprecated: prefer build_llm_scenario_pathways (one path per proposal).

    Kept for older reports; returns the first LLM variant's pathway only.
    """
    paths = build_llm_scenario_pathways(
        layers,
        control_scan,
        llm_variants,
        start_year=start_year,
        end_year=end_year,
        step=step,
    )
    if not paths:
        return None
    first_id = next(iter(paths))
    return paths[first_id]


def _mutatie_str(m: dict) -> str:
    action = m["action"]
    if action in ("set_spatial_weights", "set_economic_weights"):
        delen = [f"{k}={v}" for k, v in m.items() if k != "action"]
        return f"{action}({', '.join(delen)})"
    tekst = action + (
        f"={m.get('value') or m.get('rule') or m.get('input') or ''}"
    )
    if "thresholdPct" in m:
        tekst += f" [{m['thresholdPct']}%]"
    return tekst


WAARDE_NL = {
    "democratic": "Democratic",
    "spatial": "Spatial",
    "economic": "Economic",
    "social": "Social",
}
BASIS_NL = {
    "indicator_variance": "Threshold adjusted",
    "policy_variant": "Policy choice",
    "hypothetical": "Exploration",
}
# congres-trackkleuren per waarde: [licht, donker] — donker bij grote onderlinge spreiding
WAARDE_KLEUREN = {
    "democratic": ["#7fd8e8", "#0087a8"],
    "spatial": ["#8fd3a8", "#2e8b57"],
    "economic": ["#f3cd8a", "#c07d17"],
    "social": ["#f8b99b", "#d45d10"],
}


def _mutatie_plat(m: dict) -> str:
    """Mutatie in plain language (for the map and reports)."""
    a = m["action"]
    if a == "set_access_min_present":
        return ("all six everyday services must be nearby"
                if m["value"] == 6 else
                f"at least {m['value']} of the six everyday services must be nearby")
    if a == "set_deals_rule":
        return {"mean": "neighbourhood deals and services weigh equally",
                "floor": "neighbourhood deals become a hard floor"}[m["rule"]]
    if a == "set_social_rule":
        return {"mean": "heat and ageing (65+) weigh equally",
                "ouderen_gated": f"heat counts double where more than "
                                 f"{m.get('thresholdPct', 25)}% are aged 65+"}[m["rule"]]
    if a == "set_spatial_weights":
        labels = {"groen": "green cover", "afstand": "distance to parks", "bomen": "trees"}
        delen = []
        for k, label in labels.items():
            if k not in m:
                continue
            v = m[k]
            if v <= 1:
                delen.append(f"{label} normal")
            elif v == 2:
                delen.append(f"{label} double")
            else:
                delen.append(f"{label} {v}×")
        return "green score: " + ", ".join(delen)
    if a == "set_economic_weights":
        labels = {"dak": "roof solar potential", "bedrijven": "business density"}
        delen = []
        for k, label in labels.items():
            if k not in m:
                continue
            v = m[k]
            if v <= 1:
                delen.append(f"{label} normal")
            elif v == 2:
                delen.append(f"{label} double")
            else:
                delen.append(f"{label} {v}×")
        return "economy score: " + ", ".join(delen)
    if a == "drop_input":
        return {"bomen": "trees no longer count in the green score",
                "bedrijvigheid": "business density no longer counts",
                "deals": "neighbourhood deals no longer count",
                "groen_afstand": "distance to parks no longer counts"}[m["input"]]
    return _mutatie_str(m)


def _scenario_display_name(mutations: list, fallback: str = "") -> str:
    """Short plain-language title for dropdowns (no VS-ids / jargon)."""
    if not mutations:
        return fallback or "Unnamed what-if"
    parts: list[str] = []
    for m in mutations:
        a = m.get("action")
        if a == "set_social_rule":
            if m.get("rule") == "ouderen_gated":
                thr = m.get("thresholdPct", 25)
                parts.append(
                    f"Extra heat focus where over {thr}% are aged 65+"
                )
            else:
                parts.append("Heat and ageing weigh equally again")
        elif a == "set_economic_weights":
            dak = int(m.get("dak", 1))
            bed = int(m.get("bedrijven", 1))
            if dak >= 6 and dak >= bed:
                parts.append(
                    f"Roof solar potential dominates the economy score ({dak}×)"
                )
            elif bed > dak:
                parts.append(
                    f"Business density weighs more in the economy score ({bed}×)"
                )
            else:
                parts.append(
                    f"Economy score: roofs {dak}×, businesses {bed}×"
                )
        elif a == "set_spatial_weights":
            g = int(m.get("groen", 1))
            af = int(m.get("afstand", 1))
            b = int(m.get("bomen", 1))
            high = []
            if g > 1:
                high.append("green cover")
            if af > 1:
                high.append("park distance")
            if b > 1:
                high.append("trees")
            if high and b <= 2 and (g >= 5 or af >= 5) and b < max(g, af):
                parts.append(
                    "More weight on green cover and park distance "
                    "(trees stay lighter)"
                )
            elif high:
                parts.append(
                    "More weight on " + ", ".join(high) + " in the green score"
                )
            else:
                parts.append("Green score weights back to normal")
        elif a == "set_access_min_present":
            v = int(m["value"])
            if v >= 6:
                parts.append("All six everyday services must be nearby")
            elif v < 4:
                parts.append(
                    f"Only {v} of six everyday services need to be nearby"
                )
            else:
                parts.append(
                    f"At least {v} of six everyday services must be nearby"
                )
        elif a == "set_deals_rule":
            if m.get("rule") == "floor":
                parts.append("Neighbourhood deals become a hard minimum")
            else:
                parts.append("Neighbourhood deals and services weigh equally")
        elif a == "drop_input":
            drop = {
                "bomen": "Ignore trees in the green score",
                "bedrijvigheid": "Ignore business density",
                "deals": "Ignore neighbourhood deals",
                "groen_afstand": "Ignore distance to parks",
            }
            parts.append(drop.get(m.get("input"), "Drop one input"))
        else:
            parts.append(_mutatie_plat(m))
    if not parts:
        return fallback or "Policy what-if"
    if len(parts) == 1:
        return parts[0]
    return parts[0] + f" (+{len(parts) - 1} more)"


def build_whatif_html(report: dict, layers: dict) -> str:
    """What-if-kaart in beleidstaal. Standaardmodus 'waarden onderling':
    kleur = de waarde die in de buurt relatief wint t.o.v. de andere drie
    (congreskleuren, donker bij grote spreiding); optioneel één waarde
    volgen (wint/verliest t.o.v. het 0-scenario). Zelfde offline-Leaflet-
    idioom als het hoofdrapport; JSON letterlijk ge-escaped."""
    from . import report as report_mod

    buurten_fc = layers.get("buurten") or {}
    shapes = report_mod._shapes(buurten_fc)
    codes = [(f.get("properties") or {}).get("buurtcode") for f in buurten_fc["features"]]
    namen = [(f.get("properties") or {}).get("buurtnaam") for f in buurten_fc["features"]]
    features = [
        {"type": "Feature",
         "geometry": report_mod._geom_to_geojson(report_mod._wgs84_geom(geom)),
         "properties": {"code": code, "naam": naam}}
        for geom, code, naam in zip(shapes, codes, namen)
    ]
    per_buurt_all = {}
    for v in report["variants"]:
        for code, blob in v["deltas"].items():
            per_buurt_all.setdefault(code, {})[v["scenarioId"]] = blob

    import json as _json

    def _bron(proposed_by: str) -> str:
        pb = (proposed_by or "").lower()
        return "llm" if pb.startswith("llm") else "deterministisch"

    scenarios_payload = []
    for v in report["variants"]:
        by = v.get("proposedBy") or report.get("author") or ""
        muts = v.get("mutations") or []
        title = _scenario_display_name(muts, fallback=v.get("name") or "")
        scenarios_payload.append({
            "id": v["scenarioId"],
            "name": title,
            "techName": v.get("name") or "",
            "soort": BASIS_NL.get(v["basis"]["type"], v["basis"]["type"]),
            "wat": "; ".join(_mutatie_plat(m) for m in muts),
            "n": v["nBuurtenVeranderd"],
            "profiel": v.get("profiel", {}),
            "movers": v["grootsteVerschuivers"],
            "proposedBy": by,
            "bron": _bron(by),
            "rationale": (v.get("basis") or {}).get("rationale") or "",
            "provenanceNote": v.get("provenanceNote") or "",
            "citedSeries": [
                h.get("seriesId") for h in (v.get("lakeSeriesHints") or [])
                if h.get("seriesId")
            ][:6],
        })

    def _end_meta_from_pathway(path: dict | None) -> dict | None:
        if not path or not path.get("keyframes"):
            return None
        years = sorted(int(y) for y in path["keyframes"])
        meta = dict((path["keyframes"][str(years[-1])] or {}).get("meta") or {})
        if path.get("endParams"):
            meta.update(path["endParams"])
        meta["thrEnd"] = path.get("thrEnd")
        meta["sourceScenarioIds"] = path.get("sourceScenarioIds") or []
        return meta

    det_end = _end_meta_from_pathway(report.get("horizonPathway"))
    llm_paths = report.get("llmScenarioPathways") or {}
    # legacy single merged path → treat as one entry
    if not llm_paths and report.get("llmHorizonPathway"):
        legacy = report["llmHorizonPathway"]
        sid = (legacy.get("scenarioId")
               or (legacy.get("sourceScenarioIds") or ["llm"])[0])
        llm_paths = {sid: legacy}
    pathway_diff = None
    if det_end and llm_paths:
        sw_d = det_end.get("spatialWeights") or {}
        ew_d = det_end.get("economicWeights") or {}
        llm_rows = []
        for sid, path in llm_paths.items():
            le = _end_meta_from_pathway(path) or {}
            sw = le.get("spatialWeights") or {}
            ew = le.get("economicWeights") or {}
            title = path.get("title") or sid
            llm_rows.append({
                "id": sid,
                "title": title,
                "gate": f"{le.get('thrEnd') or le.get('socialGatePct')}%",
                "spatial": f"{sw.get('groen')}/{sw.get('afstand')}/{sw.get('bomen')}",
                "economic": f"{ew.get('dak')}/{ew.get('bedrijven')}",
                "access": str(le.get("accessMinPresent") or "—"),
            })
        pathway_diff = {
            "summary": (
                "Same calculation engine. The CBS year-sweep follows one data-driven "
                "path. Each AI proposal has its own year-sweep toward that proposal "
                "only — proposals are not combined or averaged."
            ),
            "rows": [
                {
                    "param": "Heat focus threshold (share aged 65+)",
                    "det": f"{det_end.get('thrEnd') or det_end.get('socialGatePct')}%",
                    "llm": " / ".join(r["gate"] for r in llm_rows) or "—",
                },
                {
                    "param": "Green score weights (cover / parks / trees)",
                    "det": f"{sw_d.get('groen')}/{sw_d.get('afstand')}/{sw_d.get('bomen')}",
                    "llm": " · ".join(r["spatial"] for r in llm_rows) or "—",
                },
                {
                    "param": "Economy weights (roofs / businesses)",
                    "det": f"{ew_d.get('dak')}/{ew_d.get('bedrijven')}",
                    "llm": " · ".join(r["economic"] for r in llm_rows) or "—",
                },
                {
                    "param": "Nearby services required (of 6)",
                    "det": str(det_end.get("accessMinPresent") or 4),
                    "llm": " / ".join(r["access"] for r in llm_rows) or "—",
                },
            ],
            "llmProposals": llm_rows,
            "bullets": [
                "Pick an AI scenario in the list to run its own 2026→2050 slider.",
                "CBS path stays one coherent trend story (ageing, solar, green/heat).",
                "Differences come from different end-settings per proposal — not from averaging.",
            ],
        }

    lang_graph = {
        "id": report.get("graph") or "breda_scenario",
        "title": "LangGraph — Breda what-if plane",
        "source": "nldt/agents/breda_scenario/graph.py",
        "nodes": [
            {
                "id": "deep_research",
                "label": "S10 Research",
                "hint": "Deep Agents / stub → ResearchBrief",
            },
            {
                "id": "horizon_inputs",
                "label": "Horizon inputs",
                "hint": "CBS / KNMI projections + lake hints",
            },
            {
                "id": "author_floor",
                "label": "S7 Floor",
                "hint": "Deterministic 2050 proposals",
            },
            {
                "id": "author_llm",
                "label": "S7 AI author",
                "hint": "LLM propose-only scenarios",
            },
            {
                "id": "merge_and_gate",
                "label": "Merge + gate",
                "hint": "Floor first; novel LLM only",
            },
            {
                "id": "run_scenarios",
                "label": "Dispose",
                "hint": "Deterministic compute_scan / control",
            },
            {
                "id": "pathways",
                "label": "Per-AI pathways",
                "hint": "One year-sweep per AI proposal",
            },
            {
                "id": "assemble",
                "label": "Report",
                "hint": "what-if.html + scenario-report",
            },
        ],
        "edges": [
            ["deep_research", "horizon_inputs"],
            ["horizon_inputs", "author_floor"],
            ["author_floor", "author_llm"],
            ["author_llm", "merge_and_gate"],
            ["merge_and_gate", "run_scenarios"],
            ["run_scenarios", "pathways"],
            ["pathways", "assemble"],
        ],
    }

    payload = {
        "author": report.get("author") or "file",
        "lakeSeriesHints": report.get("lakeSeriesHints") or [],
        "horizonYear": report.get("horizonYear"),
        "horizonProjections": report.get("horizonProjections") or [],
        "horizonPathway": report.get("horizonPathway") or None,
        "llmScenarioPathways": llm_paths or None,
        "pathwayDiff": pathway_diff,
        "langGraph": lang_graph,
        "researchBrief": report.get("researchBrief") or report.get("research_brief"),
        "rejectedAuthoring": report.get("rejectedAuthoring") or [],
        "scenarios": scenarios_payload,
        "geo": {"type": "FeatureCollection", "features": features},
        "perBuurt": per_buurt_all,
        "waarden": [
            {"key": w, "label": WAARDE_NL[w],
             "kleur": WAARDE_KLEUREN[w]} for w in WAARDEN
        ],
    }
    data = _json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")

    return '''<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What if…? — Breda five-value scan</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
 body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,sans-serif;color:#111827;
   background:#e8ecf0;display:flex;flex-direction:column;height:100vh;overflow:hidden}
 header{flex:0 0 auto;background:#060644;color:#fff;padding:12px 24px}
 header h1{margin:0;font-size:20px} header p{margin:4px 0 0;color:#9fb3d9;font-size:13px}
 #stage{flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
 #map{flex:1 1 auto;min-height:180px;position:relative;background:#eef2f5}
 #logBar{flex:0 0 auto;max-height:34vh;overflow-y:auto;overflow-x:hidden;
   background:#e8ecf0;border-top:1px solid #c5ccd6;padding:10px 20px 12px;
   -webkit-overflow-scrolling:touch;overscroll-behavior:contain}
 .log-graph{margin:0 0 10px;padding:8px 10px;background:#fff;border:1px solid #d1d5db;
   border-radius:8px}
 .log-graph h3{margin:0 0 6px;font-size:12px;color:#6b7280;font-weight:600;
   text-transform:uppercase;letter-spacing:.04em}
 .log-graph .graph-meta{font-size:11px;color:#6b7280;margin:0 0 8px}
 .log-graph .graph-meta code{font-size:10.5px;background:#f3f4f6;padding:1px 5px;border-radius:4px}
 .lg-flow{display:flex;flex-wrap:wrap;align-items:center;gap:4px 2px}
 .lg-node{position:relative;min-width:72px;max-width:110px;padding:6px 8px;border-radius:8px;
   border:1px solid #d1d5db;background:#f9fafb;font-size:11px;line-height:1.25;
   color:#374151;cursor:pointer;transition:background .2s,border-color .2s,box-shadow .2s,transform .2s}
 .lg-node b{display:block;font-size:11.5px;color:#111827;font-weight:600}
 .lg-node .lg-seam{display:inline-block;margin-top:2px;font-size:9.5px;color:#6b7280}
 .lg-node.done{border-color:#059669;background:#ecfdf5}
 .lg-node.done b{color:#047857}
 .lg-node.skip{opacity:.55;border-style:dashed}
 .lg-node.active-view{box-shadow:0 0 0 2px #060644;border-color:#060644}
 .lg-node.sim-pending{opacity:.4;filter:grayscale(.3)}
 .lg-node.sim-running{opacity:1;border-color:#c2410c;background:#fff7ed;transform:scale(1.06);
   box-shadow:0 0 0 3px rgba(194,65,12,.35);animation:lgPulse 1s ease-in-out infinite}
 .lg-node.sim-running b{color:#c2410c}
 .lg-node.sim-done{opacity:1;border-color:#059669;background:#ecfdf5}
 .lg-node.sim-skip{opacity:.4;border-style:dashed;background:#f3f4f6}
 @keyframes lgPulse{0%,100%{box-shadow:0 0 0 3px rgba(194,65,12,.25)}50%{box-shadow:0 0 0 6px rgba(194,65,12,.15)}}
 .lg-arrow{color:#9ca3af;font-size:14px;padding:0 2px;user-select:none}
 .lg-arrow.sim-lit{color:#c2410c}
 .lg-controls{display:flex;gap:8px;margin:8px 0 6px;flex-wrap:wrap;align-items:center}
 .lg-controls button{font-size:12.5px;padding:6px 12px;border-radius:8px;border:1px solid #d1d5db;
   background:#fff;color:#111827;cursor:pointer}
 .lg-controls button:hover{border-color:#099f80}
 .lg-controls button.actief{background:#060644;color:#fff;border-color:#060644}
 .lg-controls .lg-step{font-size:12px;color:#6b7280}
 .lg-narrate{margin-top:6px;padding:8px 10px;border-radius:8px;background:#f8fafc;border:1px solid #e5e7eb;
   font-size:12.5px;color:#374151;line-height:1.45;min-height:3.2em}
 .lg-narrate b{color:#060644}
 .lg-narrate .lg-tag{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:999px;
   margin-right:6px;background:#fff7ed;color:#c2410c;font-weight:600}
 .lg-narrate .lg-tag.ok{background:#ecfdf5;color:#047857}
 .lg-narrate .lg-tag.skip{background:#f3f4f6;color:#6b7280}
 .lg-legend{display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;font-size:11px;color:#6b7280}
 .lg-legend span i{display:inline-block;width:10px;height:10px;border-radius:3px;
   border:1px solid #d1d5db;margin-right:4px;vertical-align:-1px}
 .lg-legend .done i{background:#ecfdf5;border-color:#059669}
 .lg-legend .skip i{background:#f9fafb;border-style:dashed}
 .lg-legend .view i{background:#fff;box-shadow:0 0 0 2px #060644}
 .lg-legend .run i{background:#fff7ed;border-color:#c2410c}
 .log-cols{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:18px 28px;
   max-width:1280px;margin:0 auto}
 .log-live h3,.log-diff h3{margin:0 0 6px;font-size:12px;color:#6b7280;font-weight:600;
   text-transform:uppercase;letter-spacing:.04em}
 .log-live .zin{font-size:14px;color:#060644;font-weight:600;line-height:1.35;margin:0 0 6px}
 .log-live .delta-meta{font-size:12.5px;color:#374151;line-height:1.45;margin:0 0 6px}
 .log-live .delta-meta b{color:#060644}
 .log-live .delta-stats{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}
 .log-live .stat{font-size:12px;padding:3px 8px;border-radius:6px;background:#fff;
   border:1px solid #d1d5db;color:#374151}
 .log-live .stat b{color:#060644}
 .log-live .hint{font-size:12px;color:#6b7280;line-height:1.4;margin:4px 0 0}
 .paneel{position:absolute;top:12px;right:12px;z-index:1000;background:#fff;
   border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.3);padding:14px 16px;
   font-size:14px;width:360px;max-height:calc(100% - 24px);overflow-y:auto;
   overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;
   pointer-events:auto}
 .paneel h3{margin:0 0 6px;font-size:14px;color:#6b7280;font-weight:600;
   text-transform:uppercase;letter-spacing:.04em}
 #scenSelect{width:100%;box-sizing:border-box;font-size:13.5px;padding:8px 10px;
   border:1px solid #d1d5db;border-radius:8px;background:#fff;color:#111827;
   margin:0 0 8px}
 .scen-detail{border:1px solid #e5e7eb;border-radius:8px;padding:8px 10px;margin:0 0 4px;
   background:#f9fafb}
 .scen-detail b{display:block;font-size:14px}
 .scen-detail .soort{font-size:11px;padding:1px 7px;border-radius:9px;background:#eef2f7;
   color:#1d6fa4;display:inline-block;margin:3px 4px 3px 0}
 .scen-detail .wat{font-size:12.5px;color:#4b5563}
 .scen-detail .meta{font-size:11.5px;color:#6b7280;margin-top:4px;line-height:1.35}
 .scen-detail .hint{font-size:11px;color:#0f766e;margin-top:3px;word-break:break-all}
 .author-badge{display:inline-block;margin-left:8px;padding:2px 8px;border-radius:999px;
   background:#1e3a5f;color:#dbeafe;font-size:12px}
 .bron-pill{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;
   margin:0 4px 0 0;font-weight:600;letter-spacing:.02em}
 .bron-pill.det{background:#ecfdf5;color:#047857}
 .bron-pill.llm{background:#fff7ed;color:#c2410c}
 .bron-filter{margin:0 0 8px}
 .bron-filter label{display:inline-block;margin:2px 4px 2px 0;cursor:pointer;
   border:1px solid #e5e7eb;border-radius:6px;padding:2px 8px;font-size:12.5px}
 .bron-filter input{margin-right:3px}
 .bron-filter label.actief{border-color:#060644;background:#060644;color:#fff}
 .bron-empty{font-size:12.5px;color:#6b7280;padding:6px 0 2px;line-height:1.4}
 .modus-rij label,.waarde-rij label{display:inline-block;margin:2px 6px 2px 0;cursor:pointer;
   border:1px solid #e5e7eb;border-radius:6px;padding:2px 8px;font-size:13px}
 .modus-rij input,.waarde-rij input{margin-right:3px}
 .modus-rij label.actief,.waarde-rij label.actief{border-color:#060644;background:#060644;color:#fff}
 .waarde-rij{display:none}
 .waarde-rij.zichtbaar{display:block}
 .uitleg{margin-top:10px;border-top:1px solid #eef0f3;padding-top:8px;font-size:13.5px}
 .uitleg .zin{font-size:14px;color:#060644;font-weight:600}
 .kaartvraag{font-size:12.5px;color:#6b7280;margin-top:6px}
 .chips{margin:6px 0}
 .chip{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;margin:2px 2px}
 .chip.winst{background:#e6f4ea;color:#1e7e34}.chip.verlies{background:#fdecea;color:#b00020}
 .movers{font-size:13px;margin-top:6px}
 .legend{background:#fff;padding:8px 10px;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.25);
   font-size:12px}
 .legend .sw span{display:inline-block;width:22px;height:11px;border:1px solid #999;margin-right:2px}
 .leaflet-popup-content{font-size:13.5px;min-width:270px}
 .rij{display:flex;justify-content:space-between;border-bottom:1px solid #f0f2f5;padding:3px 0}
 .pijl{font-weight:700}.op{color:#1e7e34}.neer{color:#b00020}
 .onderling{margin:6px 0 2px;font-size:13.5px}
 .grootste{margin-top:6px;font-size:12.5px;color:#4b5563}
 .horizon-box{margin-top:12px;padding-top:10px;border-top:1px solid #eef0f3}
 .horizon-box label{display:block;font-size:12px;color:#6b7280;margin-bottom:4px}
 #yearSlider{width:100%}
 .horizon-meta{font-size:12px;color:#374151;margin-top:6px;line-height:1.4}
 .horizon-meta b{color:#060644}
 .horizon-btns{display:flex;gap:8px;margin-top:8px}
 .horizon-btns button{flex:1;font-size:13px;padding:7px 10px;border-radius:8px;
   border:1px solid #d1d5db;background:#fff;color:#111827;cursor:pointer}
 .horizon-btns button:hover{border-color:#099f80}
 .horizon-btns button.actief{background:#060644;color:#fff;border-color:#060644}
 .diff-box{margin:0}
 .diff-box .diff-zin{font-size:12.5px;color:#374151;line-height:1.45;margin:0 0 8px}
 .diff-box table{width:100%;border-collapse:collapse;font-size:11.5px;margin:4px 0;background:#fff;
   border-radius:6px;overflow:hidden}
 .diff-box th,.diff-box td{text-align:left;padding:4px 8px;border-bottom:1px solid #eef0f3;
   vertical-align:top}
 .diff-box th{color:#6b7280;font-weight:600}
 .diff-box .det-col{color:#047857}.diff-box .llm-col{color:#c2410c}
 .diff-box ul{margin:6px 0 0;padding-left:18px;font-size:12px;color:#4b5563;line-height:1.4}
 .diff-box li{margin:2px 0}
 @media (max-width:900px){
  .log-cols{grid-template-columns:1fr}
  #logBar{max-height:36vh}
 }
</style></head><body>
<header>
 <h1>What if…? — consequences per neighbourhood</h1>
 <p>Compared against the <b>zero scenario</b>: the current situation. The control
    replayed the current situation exactly (check passed), so every difference below
    is genuinely caused by the chosen scenario.
    <span id="authorBadge"></span></p>
</header>
<div id="stage">
<div id="map">
 <div class="paneel">
  <h3>Choose a scenario</h3>
  <div class="bron-filter" id="bronFilter" role="group" aria-label="Author filter">
   <label class="actief"><input type="radio" name="bron" value="alle" checked> All</label>
   <label><input type="radio" name="bron" value="deterministisch"> From data trends</label>
   <label><input type="radio" name="bron" value="llm"> From AI</label>
  </div>
  <select id="scenSelect" aria-label="Scenario"></select>
  <div id="bronEmpty" class="bron-empty" style="display:none"></div>
  <div id="scenDetail" class="scen-detail"></div>
  <h3 style="margin-top:12px">Map mode</h3>
  <div class="modus-rij" id="modus">
   <label class="actief"><input type="radio" name="modus" value="onderling" checked> Values relative to each other</label>
   <label><input type="radio" name="modus" value="een"> Follow one value</label>
  </div>
  <div class="waarde-rij" id="vals"></div>
  <div id="horizonBox" class="horizon-box" style="display:none">
   <h3 id="horizonTitle">Year sweep</h3>
   <label for="yearSlider">Year <span id="yearLabel">2026</span></label>
   <input id="yearSlider" type="range" min="2026" max="2050" step="1" value="2026">
   <div class="horizon-btns">
    <button type="button" id="btnPlay" aria-label="Play sweep">Play</button>
    <button type="button" id="btnReset" aria-label="Reset to 2026">Reset</button>
   </div>
   <div class="horizon-meta" id="horizonMeta"></div>
  </div>
  <div class="uitleg" id="uitleg"></div>
 </div>
</div>
<aside id="logBar" aria-label="Explanation">
 <div class="log-graph" id="langGraphBox">
  <h3 id="langGraphTitle">LangGraph</h3>
  <p class="graph-meta" id="langGraphMeta"></p>
  <div class="lg-controls">
   <button type="button" id="btnGraphPlay" aria-label="Play graph simulation">Play pipeline</button>
   <button type="button" id="btnGraphReset" aria-label="Reset graph simulation">Reset</button>
   <span class="lg-step" id="langGraphStep"></span>
  </div>
  <div class="lg-flow" id="langGraphFlow" role="list"></div>
  <div class="lg-narrate" id="langGraphNarrate">Press <b>Play pipeline</b> to walk the LangGraph steps for this run.</div>
  <div class="lg-legend">
   <span class="done"><i></i>ran / present in report</span>
   <span class="skip"><i></i>skipped / not in this run</span>
   <span class="run"><i></i>running in simulation</span>
   <span class="view"><i></i>feeds what you view now</span>
  </div>
 </div>
 <div class="log-cols">
  <div class="log-live">
   <h3>What the colours mean now</h3>
   <div id="logLive"></div>
  </div>
  <div class="log-diff diff-box" id="diffBox" style="display:none">
   <h3>Why data trends ≠ AI</h3>
   <div id="diffBody"></div>
  </div>
 </div>
</aside>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        onerror="window.__noLeaflet=true"></script>
<script>
window.__DATA__ = __PAYLOAD__;
(function(){
 if(window.__noLeaflet||typeof L==='undefined'){
  document.getElementById('map').innerHTML='<div style="padding:40px">'+
   'Map (Leaflet, CDN) unreachable — open this file with an internet connection.</div>';return;}
 var D=window.__DATA__;
 var map=L.map('map',{preferCanvas:true}).setView([51.59,4.78],12);
 var paneelEl=document.querySelector('.paneel');
 if(paneelEl){
  L.DomEvent.disableScrollPropagation(paneelEl);
  L.DomEvent.disableClickPropagation(paneelEl);
 }
 var logBarEl=document.getElementById('logBar');
 if(logBarEl){
  L.DomEvent.disableScrollPropagation(logBarEl);
  L.DomEvent.disableClickPropagation(logBarEl);
 }
 setTimeout(function(){map.invalidateSize();},50);
 window.addEventListener('resize',function(){map.invalidateSize();});
 // Keyless Dutch basemap (Carto raster now watermarks "API key required"; OSM often blocked).
 var pdok=L.tileLayer('https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/{z}/{x}/{y}.png',{
   maxZoom:19, attribution:'&copy; Kadaster / PDOK BRT'});
 var pdokGrijs=L.tileLayer('https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/grijs/EPSG:3857/{z}/{x}/{y}.png',{
   maxZoom:19, attribution:'&copy; Kadaster / PDOK BRT'});
 var esri=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',{
   maxZoom:16, attribution:'&copy; Esri'});
 pdok.addTo(map);
 L.control.layers({"PDOK BRT":pdok,"PDOK grijs":pdokGrijs,"Esri light gray":esri},null,{position:'bottomleft'}).addTo(map);
 var KLEUREN={op:['#a5d6a7','#2e7d32','#14520f'],neer:['#f2b8b5','#b71c1c','#7f0d0d']};
 var actScen=null,actModus='onderling',actVal=D.waarden[0].key;
 var actPathwayKey=null; // 'det' | 'llm' | null  (llm = per selected actScen)
 var actYear=2026;
 var useHorizon=false;
 var yMin=2026,yMax=2050,sl=null,btnPlay=null,btnReset=null,playTimer=null;
 function llmPaths(){return D.llmScenarioPathways||{};}
 function hasLlmPathFor(id){return !!(id&&llmPaths()[id]&&llmPaths()[id].keyframes);}
 function activePathway(){
  if(actPathwayKey==='det')return D.horizonPathway;
  if(actPathwayKey==='llm'&&actScen)return llmPaths()[actScen]||null;
  return null;
 }
 function syncYearBounds(P){
  if(!P)return;
  yMin=Number(P.startYear||2026);
  yMax=Number(P.endYear||2050);
  if(sl){sl.min=String(yMin);sl.max=String(yMax);}
  actYear=Math.max(yMin,Math.min(yMax,actYear));
  if(sl)sl.value=String(actYear);
 }
 function label(k){var w=D.waarden.find(function(x){return x.key===k;});return w?w.label:k;}
 function kleurVan(k,donker){var w=D.waarden.find(function(x){return x.key===k;});
   return w.kleur[donker?1:0];}
 function lerp(a,b,t){return a+(b-a)*t;}
 function frameAt(year){
  var P=activePathway();if(!P||!P.keyframes)return null;
  var keys=Object.keys(P.keyframes).map(Number).sort(function(a,b){return a-b;});
  if(!keys.length)return null;
  if(year<=keys[0])return P.keyframes[String(keys[0])].perBuurt;
  if(year>=keys[keys.length-1])return P.keyframes[String(keys[keys.length-1])].perBuurt;
  var lo=keys[0],hi=keys[1];
  for(var i=0;i<keys.length-1;i++){
   if(year>=keys[i]&&year<=keys[i+1]){lo=keys[i];hi=keys[i+1];break;}}
  if(year===lo)return P.keyframes[String(lo)].perBuurt;
  if(year===hi)return P.keyframes[String(hi)].perBuurt;
  var t=(year-lo)/(hi-lo);
  var A=P.keyframes[String(lo)].perBuurt,B=P.keyframes[String(hi)].perBuurt,out={};
  Object.keys(A).forEach(function(code){
   var a=A[code]||{},b=B[code]||{},deltas={},vanNaar={},scores={};
   D.waarden.forEach(function(w){
    var k=w.key;
    var da=(a.deltas&&a.deltas[k]),db=(b.deltas&&b.deltas[k]);
    var d0=(da===undefined||da===null)?0:da,d1=(db===undefined||db===null)?0:db;
    var d=Math.round(lerp(d0,d1,t)*10)/10;
    if(d!==0)deltas[k]=d;
    var sa=a.scores&&a.scores[k],sb=b.scores&&b.scores[k];
    if(sa!=null&&sb!=null)scores[k]=Math.round(lerp(sa,sb,t)*10)/10;
    var va=a.vanNaar&&a.vanNaar[k],vb=b.vanNaar&&b.vanNaar[k];
    if(va&&vb)vanNaar[k]={van:va.van,naar:Math.round(lerp(va.naar,vb.naar,t)*10)/10};
   });
   out[code]={deltas:deltas,scores:scores,vanNaar:vanNaar};
  });
  return out;
 }
 function metaAt(year){
  var P=activePathway();if(!P||!P.keyframes)return null;
  var keys=Object.keys(P.keyframes).map(Number).sort(function(a,b){return a-b;});
  var lo=keys[0],hi=keys[keys.length-1];
  for(var i=0;i<keys.length-1;i++){
   if(year>=keys[i]&&year<=keys[i+1]){lo=keys[i];hi=keys[i+1];break;}}
  var A=P.keyframes[String(lo)].meta,B=P.keyframes[String(hi)].meta;
  if(year===lo)return A;if(year===hi)return B;
  var t=(year-lo)/Math.max(1,hi-lo);
  return {
   year:year,t:lerp(A.t,B.t,t),
   socialGatePct:Math.round(lerp(A.socialGatePct,B.socialGatePct,t)*10)/10,
   accessMinPresent:A.accessMinPresent!=null&&B.accessMinPresent!=null
    ?Math.round(lerp(A.accessMinPresent,B.accessMinPresent,t)):undefined,
   spatialWeights:{
    groen:Math.round(lerp(A.spatialWeights.groen,B.spatialWeights.groen,t)),
    afstand:Math.round(lerp(A.spatialWeights.afstand,B.spatialWeights.afstand,t)),
    bomen:Math.round(lerp(A.spatialWeights.bomen,B.spatialWeights.bomen,t))},
   economicWeights:{
    dak:Math.round(lerp(A.economicWeights.dak,B.economicWeights.dak,t)),
    bedrijven:Math.round(lerp(A.economicWeights.bedrijven,B.economicWeights.bedrijven,t))}
  };
 }
 function blob(f){
  if(useHorizon){var fr=frameAt(actYear);return (fr&&fr[f.properties.code])||null;}
  var b=(D.perBuurt[f.properties.code]||{})[actScen];return b||null;}
 function sterkste(b){ // onderling: sterkst verschuivende waarde t.o.v. de rest
   var vector={};
   D.waarden.forEach(function(w){vector[w.key]=
     (b.deltas[w.key]!==undefined&&b.deltas[w.key]!==null)?b.deltas[w.key]:0;});
   var ks=D.waarden.map(function(w){return w.key;});
   var w=ks[0],v=ks[0],m=ks[0],mv=0;
   ks.forEach(function(k){
     if(vector[k]>vector[w])w=k;
     if(vector[k]<vector[v])v=k;
     if(Math.abs(vector[k])>mv){mv=Math.abs(vector[k]);m=k;}});
   return {w:w,v:v,m:m,omvang:mv,spreiding:vector[w]-vector[v]};}
 function maxSpreiding(){var m=0.5;D.geo.features.forEach(function(f){var b=blob(f);
   if(!b)return;var sv=sterkste(b);
   if(sv&&sv.omvang>m)m=sv.omvang;});return m;}
 function maxAbsEen(){var m=0.5;D.geo.features.forEach(function(f){var b=blob(f);
   if(!b)return;var d=b.deltas[actVal];
   if(d!==undefined&&Math.abs(d)>m)m=Math.abs(d);});return m;}
 function kleur(f){var b=blob(f);
   if(!b)return '#d1d5db';
   if(actModus==='onderling'){
     var sv=sterkste(b);
     if(!sv||sv.omvang<0.5)return '#d1d5db';
     var donker=sv.omvang>0.55*maxSpreiding();
     return kleurVan(sv.m,donker);}
   var d=b.deltas[actVal];
   if(d===undefined||d===null)return '#d1d5db';
   var t=Math.abs(d)/maxAbsEen();if(t<0.08)return '#cfd4da';
   var i=t>0.66?2:(t>0.33?1:0);return KLEUREN[d>0?'op':'neer'][i];}
 var layer=L.geoJSON(D.geo,{style:function(f){return{color:'#fff',weight:1,
     fillOpacity:0.85,fillColor:kleur(f)};},
   onEachFeature:function(f,lyr){lyr.bindPopup(function(){return popup(f);});}});
 layer.addTo(map);map.fitBounds(layer.getBounds(),{padding:[10,10]});
 function fmtGetal(g){return (g>0?'+':'')+g.toLocaleString('nl-NL');}
 function popup(f){var b=blob(f);
  var kop='<b>'+(f.properties.naam||f.properties.code)+'</b>';
  if(!b)return kop+'<div class="onderling" style="color:#6b7280">'+
    '<i>nothing changes here in this scenario</i></div>';
  var sv=sterkste(b),regels='';
  if(sv&&sv.omvang>=0.5){
   var dW=b.deltas[sv.w],dV=b.deltas[sv.v];
   if(sv.w!==sv.v&&dV<0&&dW>0)
    regels+='<div class="onderling">relative to the other values this shifts from <b>'+label(sv.v)+
     '</b> towards <b>'+label(sv.w)+'</b> ('+fmtGetal(dV)+' → '+
     fmtGetal(dW)+')</div>';
   else{
    var richting=b.deltas[sv.m]>0?'gains':'loses';
    regels+='<div class="onderling"><b>'+label(sv.m)+'</b> '+richting+
     ' most here ('+fmtGetal(b.deltas[sv.m])+
     ') relative to the other values</div>';}}
  D.waarden.forEach(function(w){
   var vn=b.vanNaar[w.key];if(!vn)return;
   var d=b.deltas[w.key];
   var pijl='<span class="pijl">=</span>';
   if(d>0)pijl='<span class="pijl op">&#8593; +'+d.toLocaleString('nl-NL')+'</span>';
   if(d<0)pijl='<span class="pijl neer">&#8595; '+d.toLocaleString('nl-NL')+'</span>';
   regels+='<div class="rij"><span>'+w.label+'</span><span>'+
     vn.van.toLocaleString('nl-NL')+' &rarr; '+vn.naar.toLocaleString('nl-NL')+
     ' &nbsp;'+pijl+'</span></div>';});
  return kop+regels;}
 var legend=L.control({position:'bottomleft'});
 legend.onAdd=function(){var d=L.DomUtil.create('div','legend');this._d=d;this.upd();return d;};
 legend.upd=function(){
  if(actModus==='onderling'){
   var sw=D.waarden.map(function(w){
     return '<span style="background:'+w.kleur[0]+'"></span>';}).join('');
   this._d.innerHTML='<b>Which value shifts the most?</b><br><div class="sw">'+sw+
     '</div><div style="margin-top:2px">'+D.waarden.map(function(w){
       return w.label;}).join(' · ')+
     '</div><br><span style="background:#d1d5db;display:inline-block;width:22px;height:11px;'+
     'border:1px solid #999"></span> no shift<br>(dark = strong shift relative to '+
     'the other values; click a neighbourhood for gain or loss)';}
  else{this._d.innerHTML='<b>Where does '+label(actVal)+' change?</b>'+
   '<br><div class="sw">'+['<span style="background:#a5d6a7"></span>',
   '<span style="background:#2e7d32"></span>','<span style="background:#cfd4da"></span>',
   '<span style="background:#f2b8b5"></span>','<span style="background:#b71c1c"></span>'
   ].join('')+'</div><br>gains &nbsp;&middot;&nbsp; no change &nbsp;&middot;&nbsp; loses<br>(vs the zero scenario)';}};
 legend.addTo(map);
 function nadruk(s){
  if(s.n===0)return 'This scenario changes <b>nothing</b> — the outcome is robust '+
   'for this adjustment.';
  var items=Object.keys(s.profiel).map(function(v){return {v:v,g:s.profiel[v].gem,
    w:s.profiel[v].winst,vt:s.profiel[v].verlies};});
  if(!items.length)return '';
  items.sort(function(a,b){return a.g-b.g;});
  var laagste=items[0],hoogste=items[items.length-1];
  var fmt=function(g){return (g>0?'+':'')+g.toLocaleString('nl-NL');};
  if(Math.abs(hoogste.g)<0.05&&Math.abs(laagste.g)<0.05)
   return 'The changes spread evenly across the values — no shift of emphasis.';
  if(laagste.v===hoogste.v)
   {var nchg=hoogste.w+hoogste.vt;
    return 'The change sits entirely in <b>'+label(laagste.v)+'</b>: '+
    nchg+' neighbourhood'+(nchg===1?'':'s')+' change (on average '+
    fmt(hoogste.g)+' points).';}
  return 'The emphasis shifts from <b>'+label(laagste.v)+'</b> to <b>'+
   label(hoogste.v)+'</b> (on average '+fmt(laagste.g)+' and '+
   fmt(hoogste.g)+' points where neighbourhoods change).';}
 function chips(s){var uit='';
  D.waarden.forEach(function(w){var p=s.profiel[w.key];if(!p||(!p.winst&&!p.verlies))return;
   uit+='<span class="chip '+(p.winst>=p.verlies?'winst':'verlies')+'">'+w.label+
   ': '+p.winst+' gain, '+p.verlies+' loss</span>';});
  return uit?'<div class="chips">'+uit+'</div>':'';}
 function movers(s){if(!s.movers.length)return '';
  var rijen=s.movers.slice(0,3).map(function(m){
   var delen=Object.keys(m.rangDelta).map(function(v){
     var d=m.rangDelta[v];return label(v)+' '+(d>0?'+':'')+d+' place'+(Math.abs(d)===1?'':'s');});
   return '<div><b>'+(m.buurt||m.buurtcode)+'</b>: '+delen.join(', ')+'</div>';}).join('');
  return '<div class="movers"><b>Biggest movers</b>'+rijen+
   '<span style="color:#6b7280;font-size:11.5px">+ = rises in the Breda ranking</span></div>';}
 function kaartvraag(){
  return actModus==='onderling'
   ?'<div class="kaartvraag">The map colours, per neighbourhood, the value that shifts '+
    'the most <b>relative to the other values</b> (gain or loss — '+
    'click the neighbourhood). Dark = strong deviation.</div>'
   :'<div class="kaartvraag">The map shows gain/loss on <b>'+label(actVal)+
    '</b> versus the zero scenario.</div>';}
 function frameDeltaStats(fr){
  var n=0, absSum=0, by={};
  D.waarden.forEach(function(w){by[w.key]={abs:0,pos:0,neg:0};});
  if(!fr)return {n:0,absSum:0,by:by};
  Object.keys(fr).forEach(function(code){
   var d=(fr[code]&&fr[code].deltas)||{};
   var keys=Object.keys(d);
   if(!keys.length)return;
   n++;
   keys.forEach(function(k){
    var v=d[k];if(v==null)return;
    absSum+=Math.abs(v);
    if(!by[k])by[k]={abs:0,pos:0,neg:0};
    by[k].abs+=Math.abs(v);
    if(v>0)by[k].pos++;else if(v<0)by[k].neg++;
   });
  });
  return {n:n,absSum:Math.round(absSum*10)/10,by:by};
 }
 function fillLog(htmlExtra){
  var live=document.getElementById('logLive');
  if(!live)return;
  live.innerHTML=htmlExtra||'';
  if(!graphSim.playing)updateLangGraphView();
 }
 function nodeStatus(id){
  var nDet=(D.scenarios||[]).filter(function(s){return s.bron!=='llm';}).length;
  var nLlm=(D.scenarios||[]).filter(function(s){return s.bron==='llm';}).length;
  var hasResearch=!!(D.researchBrief&&D.researchBrief.briefId);
  var hasProj=!!((D.horizonProjections||[]).length||D.horizonYear);
  var hasPaths=!!(D.llmScenarioPathways&&Object.keys(D.llmScenarioPathways).length);
  var hasDetPath=!!(D.horizonPathway&&D.horizonPathway.keyframes);
  var map={
   deep_research:hasResearch?'done':'skip',
   horizon_inputs:(hasProj||hasDetPath)?'done':'skip',
   author_floor:nDet>0?'done':'skip',
   author_llm:nLlm>0?'done':'skip',
   merge_and_gate:(nDet+nLlm)>0?'done':'skip',
   run_scenarios:(nDet+nLlm)>0?'done':'skip',
   pathways:hasPaths?'done':'skip',
   assemble:'done'
  };
  return map[id]||'skip';
 }
 function viewNodes(){
  if(useHorizon&&actPathwayKey==='det')return ['horizon_inputs','author_floor','pathways','assemble'];
  if(useHorizon&&actPathwayKey==='llm')return ['author_llm','pathways','assemble'];
  if(actScen){
   var s=(D.scenarios||[]).find(function(x){return x.id===actScen;});
   if(s&&s.bron==='llm')return ['author_llm','merge_and_gate','run_scenarios','assemble'];
   return ['author_floor','merge_and_gate','run_scenarios','assemble'];
  }
  return ['assemble'];
 }
 function narrateNode(id, status){
  var nDet=(D.scenarios||[]).filter(function(s){return s.bron!=='llm';}).length;
  var nLlm=(D.scenarios||[]).filter(function(s){return s.bron==='llm';}).length;
  var rej=(D.rejectedAuthoring||[]).length;
  var brief=D.researchBrief;
  var paths=Object.keys(D.llmScenarioPathways||{});
  var texts={
   deep_research: status==='skip'
    ? 'S10 Deep Research was not enabled for this run — no ResearchBrief attached.'
    : ('S10 proposes a <b>ResearchBrief</b>'+(brief&&brief.topic?(' on “'+brief.topic+'”'):'')+
      ' (propose-only). Hints may feed S7; nothing is executed here.'+
      (brief&&brief.harness?' Harness: <b>'+brief.harness+'</b>.':'')),
   horizon_inputs: status==='skip'
    ? 'No horizon projections in this report.'
    : ('Load CBS / weather projections'+(D.horizonYear?(' → <b>'+D.horizonYear+'</b>'):'')+
      ' and lake series hints ('+((D.lakeSeriesHints||[]).length)+' series).'),
   author_floor: status==='skip'
    ? 'No deterministic floor scenarios.'
    : ('S7 floor: <b>'+nDet+'</b> data-driven proposal(s) (e.g. heat focus / roofs / green weights).'),
   author_llm: status==='skip'
    ? 'No accepted AI proposals (or author was file/auto only).'
    : ('S7 AI author proposes <b>'+nLlm+'</b> novel scenario(s). Schema gate stamps <code>proposedBy</code>; model does not execute.'),
   merge_and_gate: 'Hybrid merge: keep floor first; add AI only if mutation fingerprint is novel. Rejected at authoring: <b>'+rej+'</b>.',
   run_scenarios: 'Dispose: control re-run must match baseline, then compute neighbourhood score deltas for each accepted scenario.',
   pathways: status==='skip'
    ? 'No per-AI year-sweeps in this report.'
    : ('Build <b>one year-sweep per AI proposal</b> ('+paths.join(', ')+') — not a merged AI path. CBS pathway is separate.'),
   assemble: 'Assemble report + what-if map. You are viewing that artefact now — colours are Δ vs today.'
  };
  return texts[id]||(status==='skip'?'Step skipped.':'Step runs.');
 }
 var graphSim={idx:-1,timer:null,playing:false};
 function stopGraphSim(){
  if(graphSim.timer){clearInterval(graphSim.timer);graphSim.timer=null;}
  graphSim.playing=false;
  var btn=document.getElementById('btnGraphPlay');
  if(btn){btn.textContent='Play pipeline';btn.classList.remove('actief');}
 }
 function clearSimClasses(){
  var flow=document.getElementById('langGraphFlow');
  if(!flow)return;
  Array.prototype.forEach.call(flow.querySelectorAll('.lg-node'),function(el){
   el.classList.remove('sim-pending','sim-running','sim-done','sim-skip');
  });
  Array.prototype.forEach.call(flow.querySelectorAll('.lg-arrow'),function(el){
   el.classList.remove('sim-lit');
  });
 }
 function applySimFrame(idx){
  var G=D.langGraph;if(!G||!G.nodes)return;
  var flow=document.getElementById('langGraphFlow');
  var narr=document.getElementById('langGraphNarrate');
  var stepEl=document.getElementById('langGraphStep');
  if(!flow)return;
  var nodes=flow.querySelectorAll('.lg-node');
  var arrows=flow.querySelectorAll('.lg-arrow');
  Array.prototype.forEach.call(nodes,function(el,i){
   var st=nodeStatus(el.getAttribute('data-node'));
   el.classList.remove('sim-pending','sim-running','sim-done','sim-skip','active-view');
   if(idx<0){ /* idle: base status from report */ el.classList.add(st); return; }
   if(i<idx){
    el.classList.add(st==='skip'?'sim-skip':'sim-done');
   }else if(i===idx){
    el.classList.add(st==='skip'?'sim-skip':'sim-running');
   }else{
    el.classList.add('sim-pending');
   }
  });
  Array.prototype.forEach.call(arrows,function(el,i){
   el.classList.toggle('sim-lit', idx>=0 && i<idx);
  });
  if(idx<0){
   if(narr)narr.innerHTML='Press <b>Play pipeline</b> to walk the LangGraph steps for this run.';
   if(stepEl)stepEl.textContent='';
   updateLangGraphView();
   return;
  }
  var n=G.nodes[idx];
  var st=nodeStatus(n.id);
  var tag=st==='skip'
   ?'<span class="lg-tag skip">skipped</span>'
   :'<span class="lg-tag ok">running</span>';
  if(narr)narr.innerHTML=tag+'<b>'+n.label+'</b> — '+narrateNode(n.id, st);
  if(stepEl)stepEl.textContent='Step '+(idx+1)+' / '+G.nodes.length;
 }
 function startGraphSim(){
  if(graphSim.playing){stopGraphSim();applySimFrame(graphSim.idx);return;}
  // pause year sweep so only one simulation runs
  if(typeof stopPlay==='function')stopPlay();
  var G=D.langGraph;if(!G||!G.nodes||!G.nodes.length)return;
  if(graphSim.idx>=G.nodes.length-1)graphSim.idx=-1;
  graphSim.playing=true;
  var btn=document.getElementById('btnGraphPlay');
  if(btn){btn.textContent='Pause';btn.classList.add('actief');}
  function tick(){
   graphSim.idx++;
   if(graphSim.idx>=G.nodes.length){
    stopGraphSim();
    applySimFrame(G.nodes.length-1);
    var narr=document.getElementById('langGraphNarrate');
    if(narr)narr.innerHTML='<span class="lg-tag ok">done</span><b>Pipeline complete.</b> '+
     'Switch scenarios or year-sweep to explore dispose outputs.';
    var stepEl=document.getElementById('langGraphStep');
    if(stepEl)stepEl.textContent='Done';
    return;
   }
   applySimFrame(graphSim.idx);
  }
  tick();
  graphSim.timer=setInterval(tick, 1400);
 }
 function resetGraphSim(){
  stopGraphSim();
  graphSim.idx=-1;
  clearSimClasses();
  applySimFrame(-1);
  renderLangGraphBase();
 }
 function renderLangGraphBase(){
  var G=D.langGraph;if(!G||!G.nodes)return;
  var title=document.getElementById('langGraphTitle');
  var meta=document.getElementById('langGraphMeta');
  var flow=document.getElementById('langGraphFlow');
  if(title)title.textContent=G.title||'LangGraph';
  if(meta)meta.innerHTML='Source <code>'+(G.source||'')+'</code> · graph id <code>'+
   (G.id||'?')+'</code> · AI proposes · pipeline disposes';
  if(!flow)return;
  var html='';
  G.nodes.forEach(function(n,i){
   if(i)html+='<span class="lg-arrow" aria-hidden="true">→</span>';
   var st=nodeStatus(n.id);
   html+='<div class="lg-node '+st+'" data-node="'+n.id+'" role="listitem" title="'+
    (n.hint||n.label).replace(/"/g,'&quot;')+'"><b>'+n.label+'</b>'+
    (n.hint?'<span class="lg-seam">'+n.hint+'</span>':'')+'</div>';
  });
  flow.innerHTML=html;
  updateLangGraphView();
 }
 function renderLangGraph(){
  renderLangGraphBase();
  var btnPlay=document.getElementById('btnGraphPlay');
  var btnReset=document.getElementById('btnGraphReset');
  if(btnPlay)btnPlay.onclick=function(){startGraphSim();};
  if(btnReset)btnReset.onclick=function(){resetGraphSim();};
  var flow=document.getElementById('langGraphFlow');
  if(flow){
   flow.onclick=function(ev){
    var el=ev.target.closest('.lg-node');
    if(!el)return;
    var G=D.langGraph;if(!G||!G.nodes)return;
    var id=el.getAttribute('data-node');
    var idx=-1;
    for(var i=0;i<G.nodes.length;i++){if(G.nodes[i].id===id){idx=i;break;}}
    if(idx<0)return;
    stopGraphSim();
    graphSim.idx=idx;
    applySimFrame(idx);
   };
  }
 }
 function updateLangGraphView(){
  if(graphSim.playing||graphSim.idx>=0)return;
  var flow=document.getElementById('langGraphFlow');
  if(!flow)return;
  var active=viewNodes();
  Array.prototype.forEach.call(flow.querySelectorAll('.lg-node'),function(el){
   el.classList.toggle('active-view', active.indexOf(el.getAttribute('data-node'))>=0);
  });
 }
 function ververs(){layer.setStyle(function(f){return{color:'#fff',weight:1,
    fillOpacity:0.85,fillColor:kleur(f)};});legend.upd();
  var u=document.getElementById('uitleg');
  var det=document.getElementById('scenDetail');
  if(useHorizon){
   var P=activePathway()||{};
   var m=metaAt(actYear)||{};
   var isLlm=actPathwayKey==='llm';
   var ht=document.getElementById('horizonTitle');
   var pathTitle=(P.title)||(isLlm?'This AI proposal':'CBS / weather');
   if(ht)ht.textContent=isLlm?'Year sweep — this AI proposal':'Year sweep — CBS / weather';
   document.getElementById('yearLabel').textContent=String(actYear);
   document.getElementById('horizonMeta').innerHTML=
    '<b>'+actYear+'</b>: heat focus &gt; <b>'+(m.socialGatePct!=null?m.socialGatePct:'?')+
    '%</b> aged 65+ · green '+
    ((m.spatialWeights&&(m.spatialWeights.groen+'/'+m.spatialWeights.afstand+'/'+m.spatialWeights.bomen))||'?')+
    ' · economy '+
    ((m.economicWeights&&(m.economicWeights.dak+'/'+m.economicWeights.bedrijven))||'?');
   var pill=isLlm
    ?'<span class="bron-pill llm">from AI</span>'
    :'<span class="bron-pill det">from data</span>';
   if(det)det.innerHTML='<b>'+(isLlm?pathTitle:'Year sweep — CBS / weather pathway')+'</b>'+pill+
    '<span class="soort">2026–'+(P.endYear||2050)+'</span>'+
    '<div class="wat">'+(isLlm
      ?('Year sweep for this AI proposal only (not combined with other AI what-ifs).')
      :('Gradually raises heat focus, roof solar weight and green weights toward 2050 CBS trends.'))+
    '</div>';
   var t=m.t!=null?m.t:((actYear-yMin)/Math.max(1,yMax-yMin));
   var pct=Math.round(t*100);
   var fr=frameAt(actYear);
   var st=frameDeltaStats(fr);
   var statsHtml=D.waarden.map(function(w){
    var b=st.by[w.key]||{abs:0,pos:0,neg:0};
    if(b.abs<0.05)return '';
    return '<span class="stat"><b>'+w.label+'</b> Σ|Δ| '+
     (Math.round(b.abs*10)/10)+' · +'+b.pos+'/−'+b.neg+'</span>';
   }).join('');
   var pathLabel=isLlm?('AI proposal: '+pathTitle):'CBS / weather path';
   fillLog(
    '<p class="zin">Year <b>'+actYear+'</b> · '+pathLabel+' · '+pct+
    '% of the way to '+(P.endYear||2050)+'</p>'+
    '<p class="delta-meta">Policy settings this year: heat focus above <b>'+
    (m.socialGatePct!=null?m.socialGatePct:'?')+'%</b> aged 65+; green weights '+
    '<b>'+((m.spatialWeights&&(m.spatialWeights.groen+' / '+m.spatialWeights.afstand+' / '+
     m.spatialWeights.bomen))||'?')+'</b> (cover / parks / trees); economy '+
    '<b>'+((m.economicWeights&&(m.economicWeights.dak+' / '+m.economicWeights.bedrijven))||'?')+
    '</b> (roofs / businesses)'+
    (m.accessMinPresent!=null?'; services needed ≥<b>'+m.accessMinPresent+'</b>':'')+
    '.</p>'+
    '<p class="delta-meta">Each neighbourhood colour is the <b>score change vs today (2026)</b> '+
    'under those settings — not a forecast of the neighbourhood itself. '+
    (isLlm?'This sweep follows <b>only this</b> AI proposal. ':'')+
    'Grey ≈ no meaningful change. In “values relative” mode the colour is which value '+
    'moves most compared with the other three; darker = larger move.</p>'+
    '<div class="delta-stats">'+
    '<span class="stat"><b>'+st.n+'</b> / '+D.geo.features.length+' neighbourhoods change</span>'+
    '<span class="stat">total Σ|Δ| <b>'+st.absSum+'</b></span>'+
    statsHtml+'</div>'+
    '<p class="hint">Slider years between keyframes (every '+(P.step||4)+
    'y) are interpolated. Play runs 2026→'+(P.endYear||2050)+
    '. Click a neighbourhood for exact before→after scores.</p>'
   );
   u.innerHTML=kaartvraag();
   return;}
  var s=D.scenarios.find(function(x){return x.id===actScen;});
  if(!s){u.innerHTML='';if(det)det.innerHTML='';fillLog('<p class="hint">Choose a scenario or year sweep.</p>');return;}
  var by=s.proposedBy||D.author||'';
  var bron=s.bron||'deterministisch';
  var pill=bron==='llm'
   ?'<span class="bron-pill llm">from AI</span>'
   :'<span class="bron-pill det">from data</span>';
  det.innerHTML='<b>'+s.name+'</b>'+pill+'<span class="soort">'+s.soort+'</span>'+
   '<div class="wat">'+s.wat+' — effect on '+s.n+' of the '+D.geo.features.length+
   ' neighbourhoods</div>'+
   (by?'<div class="meta">source: '+by+'</div>':'')+
   (s.rationale?'<div class="meta">'+s.rationale+'</div>':'')+
   (s.provenanceNote?'<div class="hint">'+s.provenanceNote+'</div>':'')+
   ((s.citedSeries&&s.citedSeries.length)?'<div class="hint">series: '+s.citedSeries.join(', ')+'</div>':'');
  u.innerHTML=chips(s)+movers(s)+kaartvraag();
  fillLog(
   '<p class="zin">'+nadruk(s)+'</p>'+
   '<p class="delta-meta">This is a <b>single full what-if</b> (year = 2050 end-state). '+
   'Colours = score change vs today after applying: <b>'+s.wat+'</b>.</p>'+
   '<div class="delta-stats"><span class="stat"><b>'+s.n+'</b> neighbourhoods change</span></div>'+
   (hasLlmPathFor(s.id)
    ?'<p class="hint">This AI proposal also has a year sweep — use Play / the year slider above to watch it build from 2026 to 2050.</p>'
    :'<p class="hint">Choose “Year by year — CBS / weather pathway” for the data-driven sweep.</p>')
  );
 }
 var nDet=(D.scenarios||[]).filter(function(s){return s.bron!=='llm';}).length;
 var nLlm=(D.scenarios||[]).filter(function(s){return s.bron==='llm';}).length;
 var nRej=(D.rejectedAuthoring||[]).length;
 var ab=document.getElementById('authorBadge');
 if(ab){
  var hintN=(D.lakeSeriesHints||[]).length;
  var hz=D.horizonYear||((D.horizonProjections||[])[0]&&(D.horizonProjections||[])[0].horizon);
  ab.innerHTML='<span class="author-badge">'+
   nDet+' from data · '+nLlm+' from AI'+
   (nRej?' · '+nRej+' AI rejected':'')+
   (hintN?' · '+hintN+' time series':'')+
   (hz?' · horizon '+hz:'')+'</span>';
 }
 (function fillDiff(){
  var box=document.getElementById('diffBox');
  var body=document.getElementById('diffBody');
  var diff=D.pathwayDiff;
  if(!box||!body||!diff)return;
  box.style.display='block';
  var rows=(diff.rows||[]).map(function(r){
   return '<tr><th>'+r.param+'</th><td class="det-col">'+r.det+
    '</td><td class="llm-col">'+r.llm+'</td></tr>';
  }).join('');
  var bullets=(diff.bullets||[]).map(function(b){return '<li>'+b+'</li>';}).join('');
  body.innerHTML='<p class="diff-zin">'+diff.summary+'</p>'+
   '<table><thead><tr><th>Setting</th><th class="det-col">Data 2050</th>'+
   '<th class="llm-col">AI 2050</th></tr></thead><tbody>'+rows+'</tbody></table>'+
   (bullets?'<ul>'+bullets+'</ul>':'');
 })();
 renderLangGraph();
 var sel=document.getElementById('scenSelect');
 var bronFilter='alle';
 var hasDetPath=!!(D.horizonPathway&&D.horizonPathway.keyframes);
 function stopPlay(){
  if(playTimer){clearInterval(playTimer);playTimer=null;}
  if(btnPlay){btnPlay.textContent='Play';btnPlay.classList.remove('actief');}
 }
 function updateHorizonVisibility(){
  var hb=document.getElementById('horizonBox');
  var show=actPathwayKey==='det'||(actPathwayKey==='llm'&&hasLlmPathFor(actScen));
  if(hb)hb.style.display=show?'block':'none';
  if(!show){stopPlay();useHorizon=false;}
 }
 function selectDetPathway(){
  actPathwayKey='det';
  useHorizon=true;
  actScen=null;
  syncYearBounds(activePathway());
  if(sel)sel.value='__horizon_det__';
  updateHorizonVisibility();
  ververs();
 }
 function selectLlmScenario(id, preferYear){
  actScen=id;
  if(hasLlmPathFor(id)){
   actPathwayKey='llm';
   useHorizon=true;
   if(preferYear!=null)actYear=Number(preferYear);
   syncYearBounds(activePathway());
  }else{
   actPathwayKey=null;
   useHorizon=false;
  }
  if(sel)sel.value=id;
  updateHorizonVisibility();
  ververs();
 }
 function setYear(y){
  actYear=Math.max(yMin,Math.min(yMax,Number(y)));
  if(sl)sl.value=String(actYear);
  useHorizon=true;
  if(sel){
   if(actPathwayKey==='det')sel.value='__horizon_det__';
   else if(actPathwayKey==='llm'&&actScen)sel.value=actScen;
  }
  ververs();
 }
 function startPlay(){
  if(playTimer){stopPlay();return;}
  if(typeof stopGraphSim==='function')stopGraphSim();
  if(!activePathway()){
   if(bronFilter==='llm'){
    var first=(filteredScenarios().filter(function(s){return hasLlmPathFor(s.id);})[0]);
    if(first)selectLlmScenario(first.id, yMin);
    else return;
   }else if(hasDetPath){selectDetPathway();}
   else return;
  }
  useHorizon=true;
  if(actYear>=yMax)setYear(yMin);
  if(btnPlay){btnPlay.textContent='Pause';btnPlay.classList.add('actief');}
  playTimer=setInterval(function(){
   if(actYear>=yMax){stopPlay();return;}
   setYear(actYear+1);
  },280);
 }
 function filteredScenarios(){
  return (D.scenarios||[]).filter(function(s){
   if(bronFilter==='alle')return true;
   return s.bron===bronFilter;
  });
 }
 function rebuildSelect(preferId){
  var keep=preferId||sel.value||(actPathwayKey==='det'?'__horizon_det__':actScen);
  sel.innerHTML='';
  var showDet=hasDetPath&&bronFilter!=='llm';
  if(showDet){
   var hop=document.createElement('option');
   hop.value='__horizon_det__';
   hop.textContent='▶ Year by year — CBS / weather pathway';
   sel.appendChild(hop);
  }
  var list=filteredScenarios();
  list.forEach(function(s){
   var opt=document.createElement('option');
   opt.value=s.id;
   var tag=s.bron==='llm'?'[AI]':'[data]';
   var sweep=hasLlmPathFor(s.id)?' · year sweep':'';
   opt.textContent=tag+' '+s.name+' ('+s.n+' neighbourhoods'+sweep+')';
   sel.appendChild(opt);
  });
  var empty=document.getElementById('bronEmpty');
  var anyLlmSweep=list.some(function(s){return hasLlmPathFor(s.id);});
  var showAny=showDet||list.length;
  if(!showAny){
   sel.style.display='none';
   if(empty){
    empty.style.display='block';
    var rej=(D.rejectedAuthoring||[]).slice(0,4).map(function(r){
     return (r.scenarioId||'?')+': '+(r.reden||'');
    }).join('<br>');
    if(bronFilter==='llm'){
     empty.innerHTML='No accepted AI scenarios.'+
      (nRej?' <b>'+nRej+' rejected</b> at authoring.':'')+
      (rej?'<br>'+rej:'');
    }else{
     empty.innerHTML='No scenarios in this filter.';
    }
   }
   actPathwayKey=null;actScen=null;useHorizon=false;updateHorizonVisibility();ververs();return;
  }
  sel.style.display='';
  if(empty)empty.style.display='none';
  var ids=list.map(function(s){return s.id;});
  if(keep==='__horizon_det__'&&showDet){selectDetPathway();return;}
  if(keep==='__horizon__'&&showDet){selectDetPathway();return;}
  if(keep&&ids.indexOf(keep)>=0){
   if(hasLlmPathFor(keep)){selectLlmScenario(keep, actYear);return;}
   actScen=keep;actPathwayKey=null;useHorizon=false;
   if(sel)sel.value=keep;
   updateHorizonVisibility();ververs();return;
  }
  if(bronFilter==='llm'&&anyLlmSweep){
   var firstL=list.filter(function(s){return hasLlmPathFor(s.id);})[0];
   selectLlmScenario(firstL.id, yMin);return;
  }
  if(showDet){selectDetPathway();return;}
  if(ids.length){
   if(hasLlmPathFor(ids[0])){selectLlmScenario(ids[0], yMin);return;}
   actScen=ids[0];actPathwayKey=null;useHorizon=false;
   sel.value=ids[0];updateHorizonVisibility();ververs();return;
  }
 }
 Array.prototype.forEach.call(document.querySelectorAll('#bronFilter input'),function(r){
  r.onchange=function(){
   stopPlay();
   bronFilter=r.value;
   Array.prototype.forEach.call(document.querySelectorAll('#bronFilter label'),
    function(c){c.classList.remove('actief');});
   r.parentElement.classList.add('actief');
   rebuildSelect(
    bronFilter==='llm'?null:
    (bronFilter==='deterministisch'?'__horizon_det__':sel.value)
   );
  };
 });
 sel.onchange=function(){
  stopPlay();
  if(sel.value==='__horizon_det__'||sel.value==='__horizon__'){selectDetPathway();}
  else if(hasLlmPathFor(sel.value)){selectLlmScenario(sel.value, actYear);}
  else{actPathwayKey=null;actScen=sel.value;useHorizon=false;updateHorizonVisibility();ververs();}
 };
 sl=document.getElementById('yearSlider');
 btnPlay=document.getElementById('btnPlay');
 btnReset=document.getElementById('btnReset');
 if(sl)sl.oninput=function(){stopPlay();useHorizon=true;actYear=Number(sl.value);ververs();};
 if(btnPlay)btnPlay.onclick=function(){startPlay();};
 if(btnReset)btnReset.onclick=function(){stopPlay();setYear(yMin);};
 rebuildSelect(hasDetPath?'__horizon_det__':null);
 var vr=document.getElementById('vals');
 D.waarden.forEach(function(w,i){var l=document.createElement('label');
  if(i===0)l.classList.add('actief');
  var r=document.createElement('input');r.type='radio';r.name='val';r.value=w.key;
  if(i===0)r.checked=true;
  r.onchange=function(){actVal=r.value;
   Array.prototype.forEach.call(vr.children,function(c){c.classList.remove('actief');});
   l.classList.add('actief');ververs();};
  l.appendChild(r);l.appendChild(document.createTextNode(w.label));vr.appendChild(l);});
 Array.prototype.forEach.call(document.querySelectorAll('#modus input'),function(r){
  r.onchange=function(){actModus=r.value;
   Array.prototype.forEach.call(document.querySelectorAll('#modus label'),
     function(c){c.classList.remove('actief');});
   r.parentElement.classList.add('actief');
   document.getElementById('vals').classList.toggle('zichtbaar',actModus==='een');
   ververs();};});
 ververs();
})();
</script></body></html>'''.replace("__PAYLOAD__", data)


def build_report_md(report: dict) -> str:
    lines = [
        "# What-if scenarios — Breda five-value scan",
        "",
        f"Verdict: **{report['validation']['verdict']}** · "
        f"{report['nAccepted']}/{report['nScenarios']} scenarios accepted · "
        f"control {'identical to baseline' if report['control']['identicalToBaseline'] else 'DEVIATES'}.",
        "",
        "| scenario | basis | mutations | neighbourhoods Δ | biggest movers |",
        "|---|---|---|---|---|",
    ]
    for v in report["variants"]:
        muts = "; ".join(_mutatie_str(m) for m in v["mutations"])
        movers = ", ".join(
            f"{g['buurtcode']} ({'/'.join(f'{k}{d:+d}' for k, d in g['rangDelta'].items())})"
            for g in v["grootsteVerschuivers"][:3]
        ) or "—"
        lines.append(
            f"| {v['name']} | {v['basis']['type']} | {muts} | "
            f"{v['nBuurtenVeranderd']} | {movers} |"
        )
    lines += ["", "## Rank stability (top-5/bottom-5 across all runs)", ""]
    for waarde, s in report.get("stability", {}).items():
        robuust = ", ".join(
            f"{r['buurt']} ({'top' if r['top'] == s['runs'] else 'bodem'} {r['top']}/{r['bodem']})"
            for r in s["robust"][:4]
        ) or "—"
        lines.append(f"- **{waarde}** ({s['runs']} runs): {robuust}")
    if report["rejected"]:
        lines += ["", "## Rejected (ledger)", ""]
        lines += [f"- {r.get('scenarioId') or '?'}: {r['reden']}" for r in report["rejected"]]
    return "\n".join(lines) + "\n"
