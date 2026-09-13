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
            "name": "Toegankelijkheid vereist alle zes voorzieningen",
            "basis": {"type": "indicator_variance", "variedAspect": "access_min_present"},
            "mutations": [{"action": "set_access_min_present", "value": 6}],
            "provenanceNote": "drempel 4/6 → 6/6 (canonieke waarde is 4)",
        },
        {
            "scenarioId": "VS-DEM-FLOOR",
            "name": "Wijkdeals als harde democratische ondergrens",
            "basis": {"type": "policy_variant", "variedAspect": "deals_rule"},
            "mutations": [{"action": "set_deals_rule", "rule": "floor"}],
            "provenanceNote": "gemiddelde → minimum van toegankelijkheid en deals",
        },
        {
            "scenarioId": "VS-SOC-GATED",
            "name": "Hitte-aandacht dubbel boven 25% 65+",
            "basis": {"type": "policy_variant", "variedAspect": "social_rule"},
            "mutations": [{"action": "set_social_rule", "rule": "ouderen_gated",
                           "thresholdPct": 25}],
            "provenanceNote": "verharding telt dubbel waar 65+-aandeel > 25%",
        },
        {
            "scenarioId": "VS-SPA-GROEN2",
            "name": "Groendekking dubbel in ruimtelijke waarde",
            "basis": {
                "type": "hypothetical",
                "rationale": "exploratie: géén beleidsdocument die groendekking "
                             "zwaarder weegt dan groenafstand en bomen",
            },
            "mutations": [{"action": "set_spatial_weights", "groen": 2}],
            "provenanceNote": "gewicht 1 → 2 (hypothetisch)",
        },
        {
            "scenarioId": "VS-SPA-ZONDER-BOMEN",
            "name": "Ruimtelijke waarde zonder bomen-teller",
            "basis": {
                "type": "hypothetical",
                "rationale": "gevoeligheidstest zonder beleidsonderbouwing: de "
                             "bomenlaag telt alleen openbaar groen, dus weglaten "
                             "toont hoeveel de ruimtelijke score van die ene bron "
                             "afhangt",
            },
            "mutations": [{"action": "drop_input", "input": "bomen"}],
            "provenanceNote": "gevoeligheidstest — geen gedocumenteerde beleidskeuze",
        },
        {
            "scenarioId": "VS-ECO-DAK-ZWAAR",
            "name": "Dakpotentieel domineert economische waarde",
            "basis": {
                "type": "hypothetical",
                "rationale": "exploratie: energie-opbrengst zwaarder wegen dan "
                             "bedrijvigheidsdichtheid",
            },
            "mutations": [{"action": "set_economic_weights", "dak": 3}],
            "provenanceNote": "gewicht 1 → 3 (hypothetisch)",
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

    def system_prompt(self, max_scenarios: int) -> str:
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
            "mean, gewichten alles 1."
        )

    def propose(self, max_scenarios: int = 4) -> tuple[list[dict], list[dict]]:
        import os
        import re as _re

        from . import qa

        if not self.endpoint:
            raise ScenarioError(
                "LLMScenarioAuthor vereist LDT_SCENARIO_LLM_ENDPOINT (geen gisfallback)"
            )
        raw = qa._strip_think(self._llm_call(
            self.endpoint, self.model, self.system_prompt(max_scenarios),
            "Stel scenario's voor.", self.timeout,
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
    "democratic": "Democratisch",
    "spatial": "Ruimtelijk",
    "economic": "Economisch",
    "social": "Sociaal",
}
BASIS_NL = {
    "indicator_variance": "Drempel aangepast",
    "policy_variant": "Beleidskeuze",
    "hypothetical": "Verkenning — geen onderbouwing",
}
# congres-trackkleuren per waarde: [licht, donker] — donker bij grote onderlinge spreiding
WAARDE_KLEUREN = {
    "democratic": ["#7fd8e8", "#0087a8"],
    "spatial": ["#8fd3a8", "#2e8b57"],
    "economic": ["#f3cd8a", "#c07d17"],
    "social": ["#f8b99b", "#d45d10"],
}


def _mutatie_plat(m: dict) -> str:
    """Mutatie in beleidstaal (voor de kaart en rapporten)."""
    a = m["action"]
    if a == "set_access_min_present":
        return ("alle zes voorzieningen moeten dichtbij zijn"
                if m["value"] == 6 else
                f"minimaal {m['value']} van de zes voorzieningen moet dichtbij zijn")
    if a == "set_deals_rule":
        return {"mean": "wijkdeals en voorzieningen wegen even zwaar",
                "floor": "wijkdeals worden een harde ondergrens"}[m["rule"]]
    if a == "set_social_rule":
        return {"mean": "hitte en 65+ wegen even zwaar",
                "ouderen_gated": f"hitte telt dubbel waar meer dan "
                                 f"{m.get('thresholdPct', 25)}% 65+ woont"}[m["rule"]]
    if a == "set_spatial_weights":
        delen = [f"{k} weegt {'dubbel zo zwaar' if v == 2 else f'{v}× zo zwaar' if v > 2 else 'normaal'}"
                 for k, v in m.items() if k != "action"]
        return "groen-teller hergewogen: " + ", ".join(delen)
    if a == "set_economic_weights":
        delen = [f"{k} weegt {'dubbel zo zwaar' if v == 2 else f'{v}× zo zwaar' if v > 2 else 'normaal'}"
                 for k, v in m.items() if k != "action"]
        return "economische teller hergewogen: " + ", ".join(delen)
    if a == "drop_input":
        return {"bomen": "bomen (openbaar groen) tellen niet meer mee",
                "bedrijvigheid": "bedrijvigheid telt niet meer mee",
                "deals": "wijkdeals tellen niet meer mee",
                "groen_afstand": "afstand tot openbaar groen telt niet meer mee"}[m["input"]]
    return _mutatie_str(m)


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

    payload = {
        "scenarios": [
            {"id": v["scenarioId"], "name": v["name"],
             "soort": BASIS_NL.get(v["basis"]["type"], v["basis"]["type"]),
             "wat": "; ".join(_mutatie_plat(m) for m in v["mutations"]),
             "n": v["nBuurtenVeranderd"],
             "profiel": v.get("profiel", {}),
             "movers": v["grootsteVerschuivers"]}
            for v in report["variants"]
        ],
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
<title>Wat als…? — Breda vijf-waardenscan</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
 body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,sans-serif;color:#111827;background:#f4f6f8}
 header{background:#060644;color:#fff;padding:16px 24px}
 header h1{margin:0;font-size:21px} header p{margin:4px 0 0;color:#9fb3d9;font-size:13.5px}
 #map{height:76vh;background:#eef2f5}
 .paneel{position:absolute;top:12px;right:12px;z-index:1000;background:#fff;
   border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.3);padding:14px 16px;
   font-size:14px;width:350px;max-height:86vh;overflow-y:auto}
 .paneel h3{margin:0 0 6px;font-size:14px;color:#6b7280;font-weight:600;
   text-transform:uppercase;letter-spacing:.04em}
 .scen-kaart{border:1px solid #e5e7eb;border-radius:8px;padding:8px 10px;margin:5px 0;
   cursor:pointer;display:block}
 .scen-kaart:hover{border-color:#099f80}
 .scen-kaart.actief{border-color:#099f80;background:#f0fdf9}
 .scen-kaart b{display:block;font-size:14px}
 .scen-kaart .soort{font-size:11px;padding:1px 7px;border-radius:9px;background:#eef2f7;
   color:#1d6fa4;display:inline-block;margin:3px 4px 3px 0}
 .scen-kaart .wat{font-size:12.5px;color:#4b5563}
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
</style></head><body>
<header>
 <h1>Wat als…? — gevolgen per buurt</h1>
 <p>Vergeleken met het <b>0-scenario</b>: de huidige situatie. De control herhaalde
    de huidige situatie exact (controle geslaagd), dus elk verschil hieronder komt
    écht door het gekozen scenario.</p>
</header>
<div id="map">
 <div class="paneel">
  <h3>Kies een scenario</h3><div id="scen"></div>
  <h3 style="margin-top:12px">Kaartmodus</h3>
  <div class="modus-rij" id="modus">
   <label class="actief"><input type="radio" name="modus" value="onderling" checked> Waarden onderling</label>
   <label><input type="radio" name="modus" value="een"> Één waarde volgen</label>
  </div>
  <div class="waarde-rij" id="vals"></div>
  <div class="uitleg" id="uitleg"></div>
 </div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        onerror="window.__noLeaflet=true"></script>
<script>
window.__DATA__ = __PAYLOAD__;
(function(){
 if(window.__noLeaflet||typeof L==='undefined'){
  document.getElementById('map').innerHTML='<div style="padding:40px">'+
   'Kaart (Leaflet, CDN) onbereikbaar — open dit bestand met internetverbinding.</div>';return;}
 var D=window.__DATA__;
 var map=L.map('map',{preferCanvas:true}).setView([51.59,4.78],12);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,
   attribution:'&copy; OpenStreetMap-bijdragers'}).addTo(map);
 var KLEUREN={op:['#a5d6a7','#2e7d32','#14520f'],neer:['#f2b8b5','#b71c1c','#7f0d0d']};
 var actScen=null,actModus='onderling',actVal=D.waarden[0].key;
 function label(k){var w=D.waarden.find(function(x){return x.key===k;});return w?w.label:k;}
 function kleurVan(k,donker){var w=D.waarden.find(function(x){return x.key===k;});
   return w.kleur[donker?1:0];}
 function blob(f){var b=(D.perBuurt[f.properties.code]||{})[actScen];return b||null;}
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
    '<i>in dit scenario verandert hier niets</i></div>';
  var sv=sterkste(b),regels='';
  if(sv&&sv.omvang>=0.5){
   var dW=b.deltas[sv.w],dV=b.deltas[sv.v];
   if(sv.w!==sv.v&&dV<0&&dW>0)
    regels+='<div class="onderling">onderling verschuift dit van <b>'+label(sv.v)+
     '</b> naar <b>'+label(sv.w)+'</b> ('+fmtGetal(dV)+' → '+
     fmtGetal(dW)+')</div>';
   else{
    var richting=b.deltas[sv.m]>0?'wint':'verliest';
    regels+='<div class="onderling"><b>'+label(sv.m)+'</b> '+richting+
     ' hier het sterkst ('+fmtGetal(b.deltas[sv.m])+
     ') t.o.v. de andere waarden</div>';}}
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
   this._d.innerHTML='<b>Welke waarde verschuift het sterkst?</b><br><div class="sw">'+sw+
     '</div><div style="margin-top:2px">'+D.waarden.map(function(w){
       return w.label;}).join(' · ')+
     '</div><br><span style="background:#d1d5db;display:inline-block;width:22px;height:11px;'+
     'border:1px solid #999"></span> geen verschuiving<br>(donker = sterke verschuiving '+
     't.o.v. de andere waarden; klik een buurt voor winst of verlies)';}
  else{this._d.innerHTML='<b>Waar verandert '+label(actVal)+'?</b>'+
   '<br><div class="sw">'+['<span style="background:#a5d6a7"></span>',
   '<span style="background:#2e7d32"></span>','<span style="background:#cfd4da"></span>',
   '<span style="background:#f2b8b5"></span>','<span style="background:#b71c1c"></span>'
   ].join('')+'</div><br>wint &nbsp;&middot;&nbsp; geen verandering &nbsp;&middot;&nbsp; verliest<br>(t.o.v. het 0-scenario)';}};
 legend.addTo(map);
 function nadruk(s){
  if(s.n===0)return 'Dit scenario verandert <b>niets</b> — de uitkomst is robuust '+
   'voor deze aanpassing.';
  var items=Object.keys(s.profiel).map(function(v){return {v:v,g:s.profiel[v].gem,
    w:s.profiel[v].winst,vt:s.profiel[v].verlies};});
  if(!items.length)return '';
  items.sort(function(a,b){return a.g-b.g;});
  var laagste=items[0],hoogste=items[items.length-1];
  var fmt=function(g){return (g>0?'+':'')+g.toLocaleString('nl-NL');};
  if(Math.abs(hoogste.g)<0.05&&Math.abs(laagste.g)<0.05)
   return 'De veranderingen verdelen zich gelijk over de waarden — geen nadrukverschuiving.';
  if(laagste.v===hoogste.v)
   {var nchg=hoogste.w+hoogste.vt;
    return 'De verandering zit volledig in <b>'+label(laagste.v)+'</b>: '+
    nchg+' buurt'+(nchg===1?'':'en')+' veranderen (gemiddeld '+
    fmt(hoogste.g)+' punten).';}
  return 'De nadruk verschuift van <b>'+label(laagste.v)+'</b> naar <b>'+
   label(hoogste.v)+'</b> (gemiddeld '+fmt(laagste.g)+' en '+
   fmt(hoogste.g)+' punten waar buurten veranderen).';}
 function chips(s){var uit='';
  D.waarden.forEach(function(w){var p=s.profiel[w.key];if(!p||(!p.winst&&!p.verlies))return;
   uit+='<span class="chip '+(p.winst>=p.verlies?'winst':'verlies')+'">'+w.label+
   ': '+p.winst+' winst, '+p.verlies+' verlies</span>';});
  return uit?'<div class="chips">'+uit+'</div>':'';}
 function movers(s){if(!s.movers.length)return '';
  var rijen=s.movers.slice(0,3).map(function(m){
   var delen=Object.keys(m.rangDelta).map(function(v){
     var d=m.rangDelta[v];return label(v)+' '+(d>0?'+':'')+d+' plek'+(Math.abs(d)===1?'':'en');});
   return '<div><b>'+(m.buurt||m.buurtcode)+'</b>: '+delen.join(', ')+'</div>';}).join('');
  return '<div class="movers"><b>Grootste verschuivers</b>'+rijen+
   '<span style="color:#6b7280;font-size:11.5px">+ = stijgt in de Breda-ranglijst</span></div>';}
 function kaartvraag(){
  return actModus==='onderling'
   ?'<div class="kaartvraag">De kaart kleurt per buurt de waarde die <b>ten opzichte van '+
    'de andere waarden</b> het sterkst verschuift (winst of verlies — '+
    'klik de buurt). Donker = sterke afwijking.</div>'
   :'<div class="kaartvraag">De kaart toont winst/verlies op <b>'+label(actVal)+
    '</b> t.o.v. het 0-scenario.</div>';}
 function ververs(){layer.setStyle(function(f){return{color:'#fff',weight:1,
    fillOpacity:0.85,fillColor:kleur(f)};});legend.upd();
  var s=D.scenarios.find(function(x){return x.id===actScen;}),u=document.getElementById('uitleg');
  if(!s){u.innerHTML='';return;}
  u.innerHTML='<div class="zin">'+nadruk(s)+'</div>'+chips(s)+movers(s)+kaartvraag();}
 var se=document.getElementById('scen');
 D.scenarios.forEach(function(s,i){var d=document.createElement('div');
  d.className='scen-kaart'+(i===0?' actief':'');
  d.innerHTML='<b>'+s.name+'</b><span class="soort">'+s.soort+'</span>'+
   '<div class="wat">'+s.wat+' — gevolg voor '+s.n+' van de '+D.geo.features.length+
   ' buurten</div>';
  d.onclick=function(){actScen=s.id;
   Array.prototype.forEach.call(se.children,function(c){c.classList.remove('actief');});
   d.classList.add('actief');ververs();};
  se.appendChild(d);if(i===0)actScen=s.id;});
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
        "# What-if-scenario's — Breda vijf-waardenscan",
        "",
        f"Verdict: **{report['validation']['verdict']}** · "
        f"{report['nAccepted']}/{report['nScenarios']} scenario's aangenomen · "
        f"control {'identiek aan baseline' if report['control']['identicalToBaseline'] else 'WIJKT AF'}.",
        "",
        "| scenario | basis | mutaties | buurten Δ | grootste verschuivers |",
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
    lines += ["", "## Rank-stabiliteit (top-5/onderste-5 over alle runs)", ""]
    for waarde, s in report.get("stability", {}).items():
        robuust = ", ".join(
            f"{r['buurt']} ({'top' if r['top'] == s['runs'] else 'bodem'} {r['top']}/{r['bodem']})"
            for r in s["robust"][:4]
        ) or "—"
        lines.append(f"- **{waarde}** ({s['runs']} runs): {robuust}")
    if report["rejected"]:
        lines += ["", "## Afgewezen (ledger)", ""]
        lines += [f"- {r.get('scenarioId') or '?'}: {r['reden']}" for r in report["rejected"]]
    return "\n".join(lines) + "\n"
