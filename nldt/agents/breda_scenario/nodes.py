"""LangGraph nodes for the Breda scenario plane (stubs + live hooks)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4


def _ensure_breda_path() -> Path:
    """Put poc-breda (+ poc) on sys.path so ``import breda`` works from nLDT."""
    repo = Path(__file__).resolve().parents[3]
    breda_root = repo / "poc-breda"
    poc_root = repo / "poc"
    for p in (str(poc_root), str(breda_root)):
        if p not in sys.path:
            sys.path.insert(0, p)
    return breda_root


def deep_research(state: dict[str, Any]) -> dict[str, Any]:
    """S10 — optional Deep Research brief before S7 authors."""
    if not state.get("enable_deep_research"):
        return {}
    from agents.seams.deep_research import propose_research_brief

    topic = state.get("research_topic") or (
        f"Breda five-value horizon {state.get('horizon_year') or 2050}"
    )
    force_stub = state.get("mode", "stub") == "stub"
    brief, rejected = propose_research_brief(
        topic,
        lake_series_hints=state.get("lake_hints") or [],
        force_stub=force_stub,
    )
    out: dict[str, Any] = {"research_rejected": rejected}
    if brief:
        out["research_brief"] = brief
        extra = [
            {"seriesId": sid, "source": "s10-research"}
            for sid in (brief.get("suggestedSeriesIds") or [])
            if sid
        ]
        if extra:
            out["lake_hints"] = list(state.get("lake_hints") or []) + extra
    return out


def horizon_inputs(state: dict[str, Any]) -> dict[str, Any]:
    """Load / stub CBS-KNMI projections + lake hints for the horizon year."""
    if state.get("mode", "stub") == "live":
        try:
            _ensure_breda_path()
            from breda import scenarios as breda_scen  # type: ignore

            year = int(state.get("horizon_year") or 2050)
            projections = breda_scen.breda_horizon_projections(year)
            hints = breda_scen.enrich_hints_with_projections(
                breda_scen.breda_lake_series_hints(), projections
            )
            return {"projections": projections, "lake_hints": hints, "horizon_year": year}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"horizon_inputs live failed: {exc}"}

    year = int(state.get("horizon_year") or 2050)
    return {
        "horizon_year": year,
        "projections": state.get("projections") or [
            {
                "variable": "percentagePersonen65JaarEnOuder",
                "buurtcode": "BU07580202",
                "buurtnaam": "Heusdenhout",
                "projected": 45.0,
                "horizon": year,
            }
        ],
        "lake_hints": state.get("lake_hints") or [],
    }


def author_floor(state: dict[str, Any]) -> dict[str, Any]:
    """Deterministic 2050 floor proposals (S7 floor)."""
    if state.get("error"):
        return {}
    if state.get("mode", "stub") == "live":
        try:
            _ensure_breda_path()
            from breda import scenarios as breda_scen  # type: ignore

            floor, rej = breda_scen.deterministic_scenarios_2050(
                state.get("projections") or [],
                max_scenarios=3,
            )
            return {
                "floor_specs": floor,
                "rejected_authoring": list(state.get("rejected_authoring") or []) + rej,
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": f"author_floor live failed: {exc}"}

    thr = 45
    for p in state.get("projections") or []:
        if p.get("variable") == "percentagePersonen65JaarEnOuder":
            thr = int(round(float(p.get("projected") or 45)))
            break
    return {
        "floor_specs": [
            {
                "scenarioId": "VS-2050-SOC-GATE",
                "name": f"Extra heat focus where over {thr}% are aged 65+",
                "mutations": [
                    {
                        "action": "set_social_rule",
                        "rule": "ouderen_gated",
                        "thresholdPct": thr,
                    }
                ],
                "proposedBy": "auto-horizon-2050",
            }
        ]
    }


def author_llm(state: dict[str, Any]) -> dict[str, Any]:
    """S7 LLM explorer — propose-only; live hook optional."""
    if state.get("error"):
        return {}
    if state.get("mode", "stub") == "live":
        try:
            _ensure_breda_path()
            from breda import scenarios as breda_scen  # type: ignore

            budget = max(
                1, int(state.get("max_scenarios") or 6) - len(state.get("floor_specs") or [])
            )
            specs, rej = breda_scen.LLMScenarioAuthor().propose(
                budget,
                lake_series_hints=state.get("lake_hints") or [],
                horizon_projections=state.get("projections") or None,
            )
            return {
                "llm_specs": specs,
                "rejected_authoring": list(state.get("rejected_authoring") or []) + rej,
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": f"author_llm live failed: {exc}"}

    hints = (state.get("research_brief") or {}).get("suggestedMutationHints") or []
    aspect = (hints[0].get("aspect") if hints else None) or "spatial_weights"
    if aspect == "social_rule":
        mut = {"action": "set_social_rule", "rule": "ouderen_gated", "thresholdPct": 28}
        name = "Extra heat focus where over 28% are aged 65+"
    elif aspect == "economic_weights":
        mut = {"action": "set_economic_weights", "dak": 7, "bedrijven": 3}
        name = "Roof solar potential dominates the economy score (7×)"
    else:
        mut = {"action": "set_spatial_weights", "groen": 6, "afstand": 5, "bomen": 2}
        name = "More weight on green cover and park distance (trees stay lighter)"
    return {
        "llm_specs": [
            {
                "scenarioId": "VS-STUB-01",
                "name": name,
                "mutations": [mut],
                "proposedBy": "llm-proposal#stub",
                "basis": {"type": "hypothetical", "variedAspect": aspect, "rationale": "stub"},
            }
        ]
    }


def merge_and_gate(state: dict[str, Any]) -> dict[str, Any]:
    """Hybrid merge: floor first; LLM only if mutation fingerprint novel."""
    if state.get("error"):
        return {}
    floor = list(state.get("floor_specs") or [])
    llm = list(state.get("llm_specs") or [])
    if state.get("mode", "stub") == "live":
        try:
            _ensure_breda_path()
            from breda import scenarios as breda_scen  # type: ignore

            specs, rej = breda_scen.merge_horizon_floor_and_llm(
                floor, llm, max_scenarios=int(state.get("max_scenarios") or 6)
            )
            return {
                "specs": specs,
                "rejected_authoring": list(state.get("rejected_authoring") or []) + rej,
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": f"merge_and_gate live failed: {exc}"}

    def _fp(spec: dict) -> str:
        parts = []
        for m in spec.get("mutations") or []:
            parts.append(str(sorted(m.items())))
        return "|".join(parts)

    accepted = list(floor)
    keys = {_fp(s) for s in accepted}
    rejected = list(state.get("rejected_authoring") or [])
    budget = int(state.get("max_scenarios") or 6)
    for spec in llm:
        fp = _fp(spec)
        if fp in keys:
            rejected.append({
                "scenarioId": spec.get("scenarioId"),
                "reden": "superseded by 2050 horizon floor (same mutation)",
            })
            continue
        if len(accepted) >= budget:
            rejected.append({
                "scenarioId": spec.get("scenarioId"),
                "reden": f"budget: max_scenarios={budget}",
            })
            continue
        accepted.append(spec)
        keys.add(fp)
    return {"specs": accepted, "rejected_authoring": rejected}


def run_scenarios_node(state: dict[str, Any]) -> dict[str, Any]:
    """Dispose: control + variants. Live calls poc-breda ``run_scenarios``."""
    if state.get("error"):
        return {}
    specs = state.get("specs") or []
    if state.get("mode", "stub") == "live":
        baseline = state.get("baseline_scan")
        layers = state.get("layers")
        if not baseline or not layers:
            return {
                "error": "live run_scenarios needs baseline_scan + layers in state "
                "(see agents.breda_scenario.run)"
            }
        try:
            _ensure_breda_path()
            from breda import scenarios as breda_scen  # type: ignore

            report = breda_scen.run_scenarios(baseline, layers, specs)
            report["rejectedAuthoring"] = list(state.get("rejected_authoring") or [])
            report["author"] = "hybrid"
            report["horizonYear"] = state.get("horizon_year")
            report["researchBrief"] = state.get("research_brief")
            report["researchRejected"] = state.get("research_rejected") or []
            if state.get("lake_hints"):
                report["lakeSeriesHints"] = state["lake_hints"]
            if state.get("projections"):
                report["horizonProjections"] = [
                    {
                        "seriesId": p.get("seriesId"),
                        "buurtnaam": p.get("buurtnaam"),
                        "variable": p.get("variable"),
                        "unit": p.get("unit"),
                        "horizon": p.get("horizon"),
                        "projected": p.get("projected"),
                        "slopePerYear": p.get("slopePerYear"),
                        "lastObserved": p.get("lastObserved"),
                        "method": p.get("method"),
                    }
                    for p in state["projections"]
                ]
            return {"report": report}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"run_scenarios live failed: {exc}"}

    variants = []
    for spec in specs:
        by = spec.get("proposedBy") or "file"
        variants.append({
            "scenarioId": spec.get("scenarioId"),
            "name": spec.get("name"),
            "mutations": spec.get("mutations") or [],
            "proposedBy": by,
            "nBuurtenVeranderd": 0,
            "deltas": {},
            "profiel": {},
            "grootsteVerschuivers": [],
            "basis": spec.get("basis") or {"type": "hypothetical"},
        })
    report = {
        "author": "hybrid",
        "nAccepted": len(variants),
        "nScenarios": len(variants) + len(state.get("rejected_authoring") or []),
        "variants": variants,
        "rejectedAuthoring": state.get("rejected_authoring") or [],
        "researchBrief": state.get("research_brief"),
        "researchRejected": state.get("research_rejected") or [],
        "horizonYear": state.get("horizon_year"),
        "validation": {"verdict": "stub-pass"},
        "control": {"identicalToBaseline": True},
    }
    return {"report": report}


def pathways_node(state: dict[str, Any]) -> dict[str, Any]:
    """Per-AI pathways (+ optional CBS horizon pathway in live mode)."""
    if state.get("error"):
        return {}
    report = dict(state.get("report") or {})
    llm_variants = [
        v for v in report.get("variants") or []
        if str(v.get("proposedBy") or "").lower().startswith("llm")
    ]
    llm_ids = [v["scenarioId"] for v in llm_variants if v.get("scenarioId")]
    hz = int(state.get("horizon_year") or 2050)

    if state.get("mode", "stub") == "live":
        baseline = state.get("baseline_scan")
        layers = state.get("layers")
        if not baseline or not layers:
            return {"error": "live pathways need baseline_scan + layers"}
        try:
            _ensure_breda_path()
            from breda import scenarios as breda_scen  # type: ignore

            if state.get("projections"):
                report["horizonPathway"] = breda_scen.build_horizon_pathway_frames(
                    layers,
                    baseline,
                    state["projections"],
                    start_year=2026,
                    end_year=hz,
                    step=4,
                )
            if llm_variants:
                paths = breda_scen.build_llm_scenario_pathways(
                    layers,
                    baseline,
                    llm_variants,
                    start_year=2026,
                    end_year=hz,
                    step=4,
                )
                report["llmScenarioPathways"] = paths
                llm_ids = list(paths.keys())
            report.pop("llmHorizonPathway", None)
            return {"report": report, "llm_pathway_ids": llm_ids}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"pathways live failed: {exc}"}

    report["llmScenarioPathways"] = {
        sid: {
            "scenarioId": sid,
            "bron": "llm",
            "startYear": 2026,
            "endYear": hz,
            "step": 4,
            "keyframes": {},
            "method": "stub-placeholder",
        }
        for sid in llm_ids
    }
    report.pop("llmHorizonPathway", None)
    return {"report": report, "llm_pathway_ids": llm_ids}


def assemble(state: dict[str, Any]) -> dict[str, Any]:
    """Final bookkeeping (+ optional what-if.html write in live mode)."""
    if state.get("error"):
        return {}
    report = dict(state.get("report") or {})
    report["runId"] = state.get("run_id") or str(uuid4())[:8]
    report["graph"] = "breda_scenario"
    out: dict[str, Any] = {"report": report}

    if (
        state.get("mode") == "live"
        and state.get("build_whatif")
        and state.get("layers")
        and state.get("out_dir")
    ):
        try:
            _ensure_breda_path()
            from breda import scenarios as breda_scen  # type: ignore

            out_dir = Path(state["out_dir"])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "scenario-report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            (out_dir / "scenario-report.md").write_text(
                breda_scen.build_report_md(report), encoding="utf-8"
            )
            html_path = out_dir / "what-if.html"
            html_path.write_text(
                breda_scen.build_whatif_html(report, state["layers"]),
                encoding="utf-8",
            )
            out["whatif_html_path"] = str(html_path)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"assemble what-if failed: {exc}", "report": report}
    return out
