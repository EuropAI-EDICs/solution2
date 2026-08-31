#!/usr/bin/env python3
"""CLI orchestrator for the scenario sweep (Phase A of docs/GENAI_SEAMS.md).

Replays a canonical pipeline run (``poc/runs/<ts>-<use-case>``) offline —
same request, same FormalRules, same cached layers, same recorded tunings —
and executes a schema-validated scenario set against it:

    control (unmutated re-execution, the V3 reproduction check)
      + one deterministic mutation sweep per ScenarioSpec
      -> scenario-report.json / .md + per-scenario GeoJSON + validation.json
         + prov.json + run_summary.json

Every scenario carries its provenance basis (norm_variance / policy_variant /
hypothetical) so hypotheticals stay traceable to what they vary without
faking a legal citation. No LLM at runtime: the ScenarioSpec contract is the
exact seam where a Phase-B LLM ScenarioAuthor may later *propose* specs.

Usage (from the workspace root; the default path is fully offline):

    python3 poc/scenarios/run.py                     # wind, latest baseline run
    python3 poc/scenarios/run.py --use-case zon
    python3 poc/scenarios/run.py --use-case bos
    python3 poc/scenarios/run.py --baseline poc/runs/20260830T113234Z-wind
    python3 poc/scenarios/run.py --set path/to/set.json --out /tmp/demo-scen

GenAI seams (docs/GENAI_SEAMS.md Phase B — proposals only, gated):

    python3 poc/scenarios/run.py --author auto      # deterministic author from
                                                    # the baseline artifacts
    LDT_SCENARIO_LLM_ENDPOINT=http://localhost:8000/v1 \
        python3 poc/scenarios/run.py --author llm   # open-model endpoint
                                                    # (OpenAI-compatible, temp 0)
    python3 poc/scenarios/run.py --narrate          # seam S8: prose over the
                                                    # report, numeric-grounding gated
    LDT_SCENARIO_LLM_ENDPOINT=http://localhost:11434/v1 \
        python3 poc/scenarios/run.py --narrator llm   # the model narrates; the
                                                    # same gate decides (loud
                                                    # fallback on rejection)

Exit code 0 only when the scenario critic's verdict is ``pass`` (V4 human
review stays pending by design).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

POC_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = POC_ROOT.parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts, explainer, scenario_author, scenarios  # noqa: E402

RUN_VERSION = "poc-scenario-run/1.0"
SCENARIO_RUNS_DIR = POC_ROOT / "scenario-runs"
DEFAULT_SETS_DIR = POC_ROOT / "scenarios"


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump_json(path: Path, obj: Any, indent: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    return path


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class RunLog:
    """Collects PROV activities (stages) with wall-clock timestamps."""

    def __init__(self) -> None:
        self.activities: List[Dict[str, Any]] = []

    def stage(self, name: str, label: str, agent: str,
              used: Sequence[str] = (), generated: Sequence[str] = ()):
        log = self

        class _Ctx:
            def __enter__(self2):
                self2.started = time.time()
                self2.started_iso = utcnow()
                return self2

            def __exit__(self2, *exc):
                log.activities.append({
                    "id": name, "label": label, "type": name, "agent": agent,
                    "startedAt": self2.started_iso, "endedAt": utcnow(),
                    "durationS": round(time.time() - self2.started, 3),
                    "used": list(used), "generated": list(generated),
                })
                return False

        return _Ctx()


def latest_baseline_run(use_case: str) -> Path:
    runs = sorted((POC_ROOT / "runs").glob(f"*-{use_case}"))
    dirs = [p for p in runs if (p / "run_summary.json").is_file()]
    if not dirs:
        raise SystemExit(
            f"no pipeline run found for use case {use_case!r} under poc/runs/ — "
            f"run `python3 poc/run.py --use-case {use_case}` first"
        )
    return dirs[-1]


def load_scenario_set(path: Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    contracts.validate(data, "scenario-set")
    for spec in data["scenarios"]:
        contracts.validate(spec, "scenario-spec")
        if spec["basis"]["type"] == "baseline":
            raise SystemExit(
                f"scenario set {path}: spec {spec['id']} uses basis.type 'baseline', "
                f"which is reserved for the runner's control"
            )
    return data


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--use-case", default="wind",
                    help="track id (wind|zon|bos); selects the default baseline run "
                         "and scenario set (default: wind)")
    ap.add_argument("--baseline", default=None,
                    help="baseline pipeline run dir (default: latest poc/runs/*-<use-case>)")
    ap.add_argument("--set", default=None,
                    help="scenario set file for --author file "
                         "(default: poc/scenarios/<use-case>.json)")
    ap.add_argument("--author", choices=("file", "auto", "llm"), default="file",
                    help="who proposes the ScenarioSpecs: file = the shipped demo set; "
                         "auto = the deterministic author deriving proposals from the "
                         "baseline artifacts (offline); llm = the GenAI seam — an "
                         "OpenAI-compatible endpoint via LDT_SCENARIO_LLM_ENDPOINT "
                         "(local/open model, temperature 0, proposals gated on schema "
                         "+ grounding before execution)")
    ap.add_argument("--max-scenarios", type=int, default=10,
                    help="effort budget for the auto/llm authors (default 10)")
    ap.add_argument("--narrate", action="store_true",
                    help="write scenario-narrative.md (seam S8) and gate it: every "
                         "number and id in the prose must resolve to the report")
    ap.add_argument("--narrator", choices=("deterministic", "llm"), default="deterministic",
                    help="who narrates (implies --narrate): deterministic (grounded "
                         "by construction) or llm — the local open-model endpoint "
                         "narrates and the SAME numeric-grounding gate decides; a "
                         "rejected narration falls back loudly to the deterministic "
                         "one and the rejection is persisted (narrative-rejected.md)")
    ap.add_argument("--out", default=None,
                    help="output directory (default: poc/scenario-runs/<ts>-<use-case>)")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.time()
    run_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{run_ts}-{args.use_case}-scen"
    out_dir = Path(args.out) if args.out else SCENARIO_RUNS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log = RunLog()

    baseline_dir = Path(args.baseline) if args.baseline else latest_baseline_run(args.use_case)
    set_path = Path(args.set) if args.set else DEFAULT_SETS_DIR / f"{args.use_case}.json"
    if not set_path.is_file():
        raise SystemExit(f"scenario set not found: {set_path}")
    print(f"[scenario-run] {run_id} -> {out_dir}")
    print(f"[scenario-run] baseline: {baseline_dir}")

    # ---------------- 1. baseline + (set or author) -------------------------- #
    with log.stage("load-baseline", f"Load baseline run {baseline_dir.name}", RUN_VERSION,
                   used=[str(baseline_dir / n) for n in
                         ("request.json", "formalrules.json", "normcards.json",
                          "run_summary.json", "layers.json")],
                   generated=["scenario-report.json"]):
        baseline = scenarios.load_baseline(baseline_dir)
        if args.author == "file":
            if not set_path.is_file():
                raise SystemExit(f"scenario set not found: {set_path}")
            scenario_set = load_scenario_set(set_path)
            if scenario_set["useCase"] != args.use_case:
                raise SystemExit(f"scenario set {set_path} is for useCase "
                                 f"{scenario_set['useCase']!r}, not {args.use_case!r}")
            specs = list(scenario_set["scenarios"])
            scenario_set_id = str(scenario_set["id"])
        else:
            specs = None
            scenario_set_id = None

    # ---------------- 1b. scenario author (seam S7) -------------------------- #
    author_agent = {"id": "deterministic-scenario-author", "name": "file-based demo set",
                    "version": "poc-v0", "role": "shipped ScenarioSpec fixtures"}
    if args.author != "file":
        author_obj = (scenario_author.DeterministicScenarioAuthor()
                      if args.author == "auto" else scenario_author.LLMScenarioAuthor())
        with log.stage("author", f"Scenario author ({args.author}) proposes ScenarioSpecs",
                       scenario_author.DETERMINISTIC_AUTHOR_RUN if args.author == "auto"
                       else f"llm-proposal#{getattr(author_obj, 'model', '')}",
                       used=["formalrules.json", "normcards.json", "normcards-rejected.json",
                             "rule-stats.json"],
                       generated=["proposals.json", "proposals-rejected.json"]):
            try:
                specs, author_rejected = author_obj.propose(baseline, args.max_scenarios)
            except scenario_author.ScenarioAuthorError as exc:
                raise SystemExit(f"[author] {exc}")
            scenario_set_id = (f"SSET-auto-{args.use_case}" if args.author == "auto"
                               else f"SSET-llm-{getattr(author_obj, 'model', 'model')}")
            model_slug = re.sub(r"[^a-z0-9]+", "-",
                                str(getattr(author_obj, "model", "")).lower()).strip("-")
            dump_json(out_dir / "proposals.json", {
                "author": args.author,
                "authorModel": str(getattr(author_obj, "model", "")),
                "authorRun": (scenario_author.DETERMINISTIC_AUTHOR_RUN
                              if args.author == "auto"
                              else f"llm-proposal#{model_slug}"),
                "maxScenarios": args.max_scenarios,
                "accepted": len(specs), "specs": specs,
            }, indent=1)
            dump_json(out_dir / "proposals-rejected.json", {
                "author": args.author, "rejected": author_rejected,
                "note": "cite-or-abstain for authors: proposals failing the schema, "
                        "grounding or budget gates are recorded here and never executed",
            }, indent=1)
            author_agent = {
                "id": ("deterministic-scenario-author" if args.author == "auto"
                       else "llm-scenario-author"),
                "name": f"{args.author} scenario author (seam S7)",
                "version": (scenario_author.DETERMINISTIC_AUTHOR_RUN
                            if args.author == "auto"
                            else f"llm-proposal#{getattr(author_obj, 'model', '')}"),
                "role": "proposes ScenarioSpecs; schema+grounding gated before execution",
            }
            print(f"[author] {args.author}: {len(specs)} proposals accepted, "
                  f"{len(author_rejected)} rejected (see proposals-rejected.json)")
        if not specs:
            raise SystemExit(f"{args.author} author produced zero accepted proposals — "
                             f"nothing to sweep (see proposals-rejected.json)")

    want = baseline["request"].get("objectType")
    bad = [s["id"] for s in (specs or []) if s.get("objectType") != want]
    if bad:
        raise SystemExit(f"specs {bad} objectType does not match baseline request "
                         f"objectType {want!r}")

    with log.stage("load-layers", "Load cached zone layers (offline replay)",
                   "scenario-engine",
                   used=["layers.json"], generated=["scenarios/CONTROL.geojson"]):
        layers, layer_degrades = scenarios.load_layers(
            baseline["manifest"], simplify_m=baseline["inputSimplifyM"])
        if layer_degrades:
            print(f"[scenario-run] WARNING {len(layer_degrades)} layer degradation(s); "
                  f"affected rules will be dropped")

    # ---------------- 2. the sweep ------------------------------------------ #
    written_geojsons: Dict[str, str] = {}

    def _geojson_writer(scenario_id: str, rich_zones) -> str:
        rel = f"scenarios/{scenario_id}.geojson"
        scenarios.write_scenario_geojson(rich_zones, out_dir / rel)
        written_geojsons[scenario_id] = rel
        return rel

    sweep_generated = ["scenario-report.json"]
    narrate = args.narrate or args.narrator != "deterministic"
    if narrate:
        sweep_generated.append("scenario-narrative.md")

    narrator_fn = None
    narration_events: List[Dict[str, Any]] = []
    if narrate:
        if args.narrator == "llm":
            llm_narrator = scenario_author.LLMScenarioNarrator()
            if not llm_narrator.endpoint:
                raise SystemExit("[narrator] --narrator llm requires "
                                 "LDT_SCENARIO_LLM_ENDPOINT; refusing to guess")
            narrator_fn = scenario_author.make_fallback_narrator(
                llm_narrator, scenarios.deterministic_narrative, narration_events)
        else:
            narrator_fn = scenarios.deterministic_narrative

    with log.stage("sweep", f"Execute control + {len(specs)} scenarios",
                   "scenario-engine",
                   used=["formalrules.json", "layers.json"],
                   generated=sweep_generated):
        report = scenarios.run_scenario_set(
            baseline=baseline,
            layers=layers,
            specs=specs,
            scenario_set_id=scenario_set_id,
            report_id=f"SR-{baseline.get('runId')}-{run_ts}",
            degradations=layer_degrades,
            on_scenario_geojson=_geojson_writer,
            narrator=narrator_fn,
        )
        validation = report.pop("_validation")
        control_rich = report.pop("_control_rich")
        narrative = report.pop("_narrative", None)
        if narration_events:
            for ev in narration_events:
                validation["levels"]["V2"]["checks"].append({
                    "id": "v2-narrative-llm-rejected", "status": "skipped",
                    "detail": (f"{ev['kind']}: {ev['reason']} — deterministic "
                               f"narration published instead (see "
                               f"narrative-rejected.md)"),
                })
            lines = ["# Rejected LLM narration(s)", "",
                     "The numeric-grounding gate rejected the model's prose (or the",
                     "transport errored); the deterministic narration was published",
                     "instead — loud fallback, never silent.", ""]
            for i, ev in enumerate(narration_events, 1):
                lines += [f"## Event {i}: `{ev['kind']}`", "",
                          f"**Reason:** {ev['reason']}", "",
                          "**Rejected prose:**", "",
                          "```text", str(ev.get("prose") or "(transport error — no prose)"),
                          "```", ""]
            (out_dir / "narrative-rejected.md").write_text("\n".join(lines), encoding="utf-8")
            print(f"[narrator] LLM narration REJECTED ({len(narration_events)} "
                  f"event(s)); deterministic fallback published")
        if narrative is not None:
            (out_dir / "scenario-narrative.md").write_text(
                f"# Scenario narrative — {report['id']}\n\n{narrative}\n",
                encoding="utf-8")
        scenarios.write_scenario_geojson(control_rich, out_dir / "scenarios" / "CONTROL.geojson")
        written_geojsons["CONTROL"] = "scenarios/CONTROL.geojson"
        print(f"[sweep] control {report['control']['finalAreaKm2']:,.3f} km2 "
              f"(baseline {report['control']['baselineFinalAreaKm2']:,.3f}); "
              f"{len(report['scenarios'])} scenarios")
        for row in report["scenarios"]:
            print(f"[sweep] {row['scenarioId']:<24} {row['finalAreaKm2']:>12,.3f} km2 "
                  f"  delta {row['deltaVsControlKm2']:>+12,.3f} "
                  f"  IoU {row['iouVsControl']:.6f}  [{row['status']}]")

    # ---------------- 3. validation + artifacts ----------------------------- #
    with log.stage("validate", "Scenario critic: V0-V3 + V4 pending",
                   scenarios.SCENARIO_CRITIC_RUN,
                   used=["scenario-report.json"], generated=["validation.json"]):
        verdict = validation["verdict"]
        dump_json(out_dir / "scenario-report.json", report, indent=1)
        dump_json(out_dir / "validation.json", validation, indent=1)
        (out_dir / "scenario-report.md").write_text(
            scenarios.report_markdown(report), encoding="utf-8")
        print(f"[critic] scenario-run verdict: {verdict}")

    # ---------------- 4. PROV + summary -------------------------------------- #
    with log.stage("prov", "PROV bundle", "explainer",
                   used=["scenario-report.json"], generated=["prov.json"]):
        expl = explainer.Explainer()
        baseline_files = ["request.json", "formalrules.json", "normcards.json",
                          "run_summary.json", "layers.json"]
        entities = [explainer.entity_for(baseline_dir / n, f"baseline run artifact ({n})")
                    for n in baseline_files]
        if args.author == "file":
            entities.append(explainer.entity_for(set_path, "ScenarioSet (scenario-spec contracts)"))
        else:
            entities.append(explainer.entity_for(out_dir / "proposals.json",
                                                 "accepted ScenarioSpec proposals"))
            entities.append(explainer.entity_for(out_dir / "proposals-rejected.json",
                                                 "rejected-proposals ledger (author cite-or-abstain)"))
        entities.append(explainer.entity_for(out_dir / "scenario-report.json", "ScenarioReport"))
        entities.append(explainer.entity_for(out_dir / "validation.json", "ValidationReport"))
        entities.append(explainer.entity_for(out_dir / "scenario-report.md",
                                             "ScenarioReport (markdown)"))
        if narrative is not None:
            narrator_label = ("LLM scenario narrator (gated; "
                              + ("fallback used)" if narration_events else "accepted)"))
            entities.append(explainer.entity_for(
                out_dir / "scenario-narrative.md",
                f"scenario narrative (seam S8; {narrator_label})"))
            if narration_events:
                entities.append(explainer.entity_for(
                    out_dir / "narrative-rejected.md",
                    "rejected LLM narration ledger (loud fallback)"))
        for sid, rel in sorted(written_geojsons.items()):
            entities.append(explainer.entity_for(
                out_dir / rel, "per-scenario zones GeoJSON (WGS84)",
                {"scenarioId": sid}))
        agents_list = [
            {"id": "orchestrator", "name": "scenarios/run.py orchestrator",
             "version": RUN_VERSION,
             "role": "replay baseline, dispatch author+sweep, gate on verdict"},
            author_agent,
            {"id": "scenario-engine", "name": "Deterministic scenario engine",
             "version": scenarios.SCENARIOS_VERSION,
             "role": "mutations + zone re-execution (docs/GENAI_SEAMS.md Phase A/B)"},
            {"id": "scenario-critic", "name": "Scenario critic",
             "version": scenarios.SCENARIO_CRITIC_RUN,
             "role": "V0-V3 over the scenario artifacts; V4 pending"},
            {"id": "explainer", "name": "Explainer (PROV)",
             "version": explainer.EXPLAINER_VERSION,
             "role": "PROV bundle for the scenario run"},
        ]
        if narrative is not None:
            agents_list.append({
                "id": "scenario-narrator",
                "name": (f"{args.narrator} scenario narrator"
                         if args.narrator == "llm"
                         else "Deterministic scenario narrator"),
                "version": (f"{scenario_author.NARRATOR_LLM_RUN}#{getattr(llm_narrator, 'model', '')}"
                            if args.narrator == "llm" else "poc-v1"),
                "role": "seam S8: prose over the report; output gated by the "
                        "numeric-grounding check (v2-narrative-grounding)"})
        prov = expl.build_prov(
            run_id=run_id,
            generated_at=utcnow(),
            request_id=str(baseline["request"].get("id")),
            namespace="ldttoolbox:poc:scenarios:",
            agents=agents_list,
            activities=log.activities,
            entities=entities,
            derivations=[
                {"generatedEntity": "scenario-report.json",
                 "usedEntity": "formalrules.json",
                 "note": "mutations over the baseline rule set, executed per ScenarioSpec"},
                {"generatedEntity": "scenario-report.json",
                 "usedEntity": "layers.json",
                 "note": "cached layers replayed offline at the baseline tunings"},
                {"generatedEntity": "validation.json",
                 "usedEntity": "scenario-report.json",
                 "note": "V0-V3 checks; V4 pending"},
            ],
            sources=[
                {"zone": zone, "sourceId": entry.get("aliasSourceId"),
                 "service": f"{entry.get('serviceUrl')}/{entry.get('layerId')}",
                 "lastChecked": entry.get("lastChecked"),
                 "fetchedAt": entry.get("fetchedAt"),
                 "features": entry.get("featureCount"),
                 "aliasFor": (entry.get("geoBinding") or {}).get("gioJoinId")
                 or (entry.get("geoBinding") or {}).get("geometrySource"),
                 "authoritative": entry.get("authoritative")}
                for zone, entry in sorted(baseline["manifest"].items())
            ],
        )
        dump_json(out_dir / "prov.json", prov, indent=1)

    artifacts = sorted(p for p in out_dir.rglob("*") if p.is_file())
    summary = {
        "runId": run_id,
        "useCase": args.use_case,
        "baselineRun": str(baseline_dir),
        "author": args.author,
        "scenarioSet": (str(set_path) if args.author == "file" else scenario_set_id),
        "narrated": bool(narrative),
        "narrator": (f"{args.narrator}" + ("-rejected-fallback" if narration_events else "")
                     if narrative else None),
        "generatedAt": utcnow(),
        "durationS": round(time.time() - started, 1),
        "orchestrator": RUN_VERSION,
        "engine": scenarios.SCENARIOS_VERSION,
        "verdict": verdict,
        "levels": {k: v["status"] for k, v in validation["levels"].items()},
        "control": report["control"],
        "scenarios": [
            {"scenarioId": r["scenarioId"], "status": r["status"],
             "finalAreaKm2": r["finalAreaKm2"], "deltaVsControlKm2": r["deltaVsControlKm2"],
             "iouVsControl": r["iouVsControl"], "basis": r["basis"]["type"]}
            for r in report["scenarios"]
        ],
        "degradations": report["degradations"],
        "artifacts": [{"name": str(p.relative_to(out_dir)), "path": str(p),
                       "sha256": sha256_of(p), "bytes": p.stat().st_size}
                      for p in artifacts],
    }
    dump_json(out_dir / "run_summary.json", summary, indent=1)

    print()
    print("=" * 78)
    print(f"SCENARIO RUN {run_id} — verdict: {verdict.upper()}")
    print("=" * 78)
    print(f"  {'Baseline':<28} {baseline_dir.name}")
    print(f"  {'Control final zone':<28} {report['control']['finalAreaKm2']:,.3f} km2 "
          f"(reproduction rel delta {report['control']['reproductionRelDelta']:.6f})")
    for row in report["scenarios"]:
        print(f"  {row['scenarioId']:<28} {row['finalAreaKm2']:>12,.3f} km2   "
              f"delta {row['deltaVsControlKm2']:>+12,.3f} ({row['deltaVsControlPct']:>+7.2f}%)   "
              f"IoU {row['iouVsControl']:.6f}  [{row['basis']['type']}]")
    if report["degradations"]:
        print(f"  DEGRADATIONS ({len(report['degradations'])}):")
        for d in report["degradations"]:
            print(f"    - {json.dumps(d, ensure_ascii=False)[:150]}")
    print(f"  Duration {summary['durationS']}s; report: {out_dir / 'scenario-report.md'}")
    print("=" * 78)
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        traceback.print_exc()
        print(f"[scenario-run] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
