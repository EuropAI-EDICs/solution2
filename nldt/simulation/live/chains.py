"""Chain-registry: zes PoC-chains, elke stap één MCP-toolcall.

Vervangt fetch_script.py. Stap-model: label, server, tool, args,
samenvatting(raw)->str, optioneel laag; nieuw: optioneel args_uit_vorige
(prev_raw:str)->dict — resolved vlak vóór de call, zodat een runDir uit het
vorige pipeline-resultaat expliciet doorvoert naar run_artifact. Geen
condities, geen LLM — "no invented numbers".
"""

from __future__ import annotations

import json
from typing import Any


def _count_top_level(raw: str) -> str:
    data = json.loads(raw)
    if isinstance(data, list):
        return f"{len(data)} items"
    if isinstance(data, dict):
        return f"{len(data)} sleutels"
    return "ok"


def _sum_poc_tool(raw: str) -> str:
    payload = json.loads(raw)
    s = (payload.get("outputs") or {}).get("summary") or {}
    return f"{s.get('featureCount')} features · {s.get('title')}"


def _sum_entities(raw: str) -> str:
    ents = json.loads(raw)
    mock = any(isinstance(e, dict) and e.get("mock") for e in ents)
    return f"{len(ents)} entities{' (mock)' if mock else ''}"


def _sum_fc(raw: str) -> str:
    fc = json.loads(raw)
    return f"{len(fc.get('features') or [])} features"


def _sum_pipeline(raw: str) -> str:
    payload = json.loads(raw)
    s = (payload.get("outputs") or {}).get("summary") or {}
    run = (s.get("runDir") or "").replace("\\", "/").rsplit("/", 1)[-1] or "-"
    detail = s.get("verdict") or s.get("uitkomst") or s.get("outcome") or s.get("indicatorCount") or ""
    return f"{s.get('mode', 'execute')} · {run}" + (f" · {detail}" if detail != "" else "")


def _sum_artifact(raw: str) -> str:
    payload = json.loads(raw)
    a = (payload.get("outputs") or {}).get("artifact") or {}
    return f"{a.get('name')} · {a.get('kind')} · {a.get('bytes')}B"


def _run_dir_uit_vorige(artifact: str):
    def resolve(raw: str) -> dict:
        payload = json.loads(raw)
        s = (payload.get("outputs") or {}).get("summary") or {}
        run_dir = s.get("runDir")
        if not run_dir:
            raise ValueError("vorige stap gaf geen runDir — artifact niet te resolven")
        return {"run_dir": run_dir, "artifact": artifact}

    return resolve


NGSI_LAAG = {"source_id": "ngsi-ld-dpl-airquality", "laagtype": "punten", "inline": True}

CHAINS: dict[str, dict[str, Any]] = {
    "utrecht": {
        "id": "utrecht",
        "label": "PoC-1 · Utrecht (wind)",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Regels-instrumenten in het gebied", "server": "dso", "tool": "dso_kb_overview",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Inclusion-zone wind (agrest)", "server": "poc", "tool": "fetch_geo_layer",
             "args": {"source_id": "agrest-ov-gebied-windenergie"},
             "laag": {"source_id": "agrest-ov-gebied-windenergie", "laagtype": "zone"},
             "samenvatting": _sum_poc_tool},
            {"label": "Kaartlaag wind (ArcGIS Online)", "server": "poc", "tool": "fetch_geo_layer",
             "args": {"source_id": "arcgis-et-wind-gebieden"},
             "laag": {"source_id": "arcgis-et-wind-gebieden", "laagtype": "zone"},
             "samenvatting": _sum_poc_tool},
            {"label": "NGSI-LD entities (lucht)", "server": "data", "tool": "list_entities",
             "args": {"entity_type": "AirQualityObserved"}, "samenvatting": _sum_entities},
            {"label": "NGSI-LD → GeoJSON", "server": "data", "tool": "entities_to_geojson",
             "args": {"entity_type": "AirQualityObserved"}, "laag": NGSI_LAAG, "samenvatting": _sum_fc},
            {"label": "Opportunity-map engine (wind)", "server": "poc", "tool": "run_opportunity_map",
             "args": {"mode": "execute", "useCase": "wind"}, "samenvatting": _sum_pipeline},
            {"label": "Zonelaag uit de engine-run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("zones.geojson"),
             "laag": {"source_id": "utrecht-zones", "laagtype": "zone", "inline": True,
                      "inline_uit": "artifact_content"},
             "samenvatting": _sum_artifact},
        ],
    },
    "eindhoven": {
        "id": "eindhoven",
        "label": "PoC-2 · BP→OP Eindhoven",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Regels-instrumenten in het gebied", "server": "dso", "tool": "dso_kb_overview",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "BP→OP-omzetting (engine)", "server": "poc", "tool": "run_bp2op_transform",
             "args": {"mode": "execute", "useCase": "eindhoven"}, "samenvatting": _sum_pipeline},
            {"label": "Omzettabel uit de run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("omzettabel.json"), "samenvatting": _sum_artifact},
        ],
    },
    "breda": {
        "id": "breda",
        "label": "PoC-4 · Breda vijf-waarden",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Vijf-waardenscan (engine)", "server": "poc", "tool": "run_value_scan",
             "args": {"mode": "execute"}, "samenvatting": _sum_pipeline},
            {"label": "Buurtkaart uit de scan", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("geo-buurten.wgs84.geojson"),
             "laag": {"source_id": "breda-buurten", "laagtype": "zone", "inline": True,
                      "inline_uit": "artifact_content"},
             "samenvatting": _sum_artifact},
        ],
    },
    "gent": {
        "id": "gent",
        "label": "Gent · EUROPAI-piloot",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Levensgebeurtenis-replay (fase 1+2+3)", "server": "poc",
             "tool": "gent_life_event_run",
             "args": {"mode": "execute", "package": "gent-mobiliteit-ondernemer", "persona": "sanne"},
             "samenvatting": _sum_pipeline},
            {"label": "Run-registratie uit de run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("run.json"), "samenvatting": _sum_artifact},
        ],
    },
    "veenendaal": {
        "id": "veenendaal",
        "label": "Veenendaal · Spoorzone",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "74-item gebiedscheck (engine)", "server": "poc",
             "tool": "veenendaal_gebiedscheck_run", "args": {"mode": "execute"},
             "samenvatting": _sum_pipeline},
            {"label": "Indicatoren uit de run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("indicators.json"), "samenvatting": _sum_artifact},
        ],
    },
    "dsorr": {
        "id": "dsorr",
        "label": "DSO ↔ RegelRecht",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Regels-instrumenten in het gebied", "server": "dso", "tool": "dso_kb_overview",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Annotaties Utrecht Domplein", "server": "dso", "tool": "dso_kb_annotations",
             "args": {"instrument": "utrecht-domplein"}, "samenvatting": _count_top_level},
            {"label": "TPOD-profiel Utrecht Domplein", "server": "dso", "tool": "dso_kb_tpod",
             "args": {"instrument": "utrecht-domplein"}, "samenvatting": _count_top_level},
        ],
    },
}

_PIPELINE_TOOLS = {
    "run_opportunity_map",
    "run_bp2op_transform",
    "run_value_scan",
    "gent_life_event_run",
    "veenendaal_gebiedscheck_run",
}


def chain_met_mode(chain_id: str, mode: str) -> list[dict[str, Any]]:
    """Test-hulp: diepe kopie van de stappen met pipeline-stappen op `mode`."""
    uit = []
    for stap in CHAINS[chain_id]["stappen"]:
        s = dict(stap)
        if s.get("tool") in _PIPELINE_TOOLS:
            s["args"] = {**s["args"], "mode": mode}
        uit.append(s)
    return uit
