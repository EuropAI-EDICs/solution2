"""Thin OGC Process wrappers over PoC entrypoints (Fase 5.1).

PoC engines stay authoritative; this module only adapts inputs/outputs to the
nLDT process adapter contract. See ``nldt/12-governed-agent-layer.md``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

NLDT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = NLDT_ROOT.parent
POC_ROOT = WORKSPACE / "poc"
POC_BREDA = WORKSPACE / "poc-breda"
POC_RIJNLAND = WORKSPACE / "poc-rijnland"
POC_BP2OP = WORKSPACE / "poc-bp2op"
POC_MINIGIM = WORKSPACE / "poc-minigim"

POC_PROCESS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "breda-scan-query": {
        "id": "breda-scan-query",
        "title": "Breda five-value scan Q&A (S4)",
        "description": (
            "Grounded Q&A over a canonical Breda value-scan run. Deterministic "
            "ScanQuery parse + runner; optional LLM asker/narrator stay behind "
            "the number gate (cite-or-abstain)."
        ),
        "version": "1.0.0",
        "keywords": ["poc-breda", "qa", "s4", "scan"],
        "inputs": {
            "runDir": {
                "title": "Breda scan run directory",
                "schema": {"type": "string"},
            },
            "question": {
                "title": "Natural-language question",
                "schema": {"type": "string"},
            },
            "asker": {
                "title": "Asker mode (auto|llm)",
                "schema": {"type": "string", "default": "auto"},
            },
        },
        "outputs": {
            "result": {"title": "Q&A result bundle", "schema": {"type": "object"}},
        },
    },
    "scenario-author-propose": {
        "id": "scenario-author-propose",
        "title": "Scenario author proposals (S7)",
        "description": (
            "Propose ScenarioSpecs from a baseline opportunity-map run "
            "(author=auto|llm|hybrid). Writes nothing to the zone engine — "
            "proposals (+ reject ledger) only. Hybrid = det floor + LLM explorer."
        ),
        "version": "1.0.0",
        "keywords": ["poc-utrecht", "scenario", "s7"],
        "inputs": {
            "baselineRunDir": {
                "title": "Baseline poc/runs/<ts>-<track> directory",
                "schema": {"type": "string"},
            },
            "author": {
                "title": "Author mode (auto|llm|hybrid)",
                "schema": {"type": "string", "default": "hybrid"},
            },
            "maxScenarios": {
                "title": "Effort budget",
                "schema": {"type": "integer", "default": 10},
            },
        },
        "outputs": {
            "proposals": {"title": "Accepted ScenarioSpecs", "schema": {"type": "object"}},
        },
    },
    "scenario-sweep": {
        "id": "scenario-sweep",
        "title": "Scenario sweep (Plane B)",
        "description": (
            "Offline replay of a baseline run + scenario set (file|auto author). "
            "Control reproduction + per-scenario Δ/IoU; Critic V0–V3."
        ),
        "version": "1.0.0",
        "keywords": ["poc-utrecht", "scenario", "plane-b"],
        "inputs": {
            "useCase": {
                "title": "Track id (wind|zon|bos)",
                "schema": {"type": "string", "default": "wind"},
            },
            "baselineRunDir": {
                "title": "Optional baseline run dir",
                "schema": {"type": "string"},
            },
            "author": {
                "title": "file|auto",
                "schema": {"type": "string", "default": "file"},
            },
            "scenarioSetPath": {
                "title": "Scenario set JSON (author=file)",
                "schema": {"type": "string"},
            },
            "outDir": {
                "title": "Output directory",
                "schema": {"type": "string"},
            },
            "noH3": {
                "title": "Skip H3 metrics",
                "schema": {"type": "boolean", "default": True},
            },
        },
        "outputs": {
            "summary": {"title": "Sweep summary", "schema": {"type": "object"}},
        },
    },
    "opportunity-map-run": {
        "id": "opportunity-map-run",
        "title": "Opportunity-map run (Plane A)",
        "description": (
            "mode=replay: return summary of an existing poc/runs dir. "
            "mode=execute: invoke poc/run.py cache-first for a use case."
        ),
        "version": "1.0.0",
        "keywords": ["poc-utrecht", "opportunity-map", "plane-a"],
        "inputs": {
            "mode": {
                "title": "replay|execute",
                "schema": {"type": "string", "default": "replay"},
            },
            "useCase": {
                "title": "wind|zon|bos",
                "schema": {"type": "string"},
            },
            "runDir": {
                "title": "Existing run dir (replay)",
                "schema": {"type": "string"},
            },
        },
        "outputs": {
            "summary": {"title": "Run summary", "schema": {"type": "object"}},
        },
    },
    "crosstrack-overlay": {
        "id": "crosstrack-overlay",
        "title": "Crosstrack overlay (Plane C)",
        "description": "Pairwise track conflict overlay; V2 N/A; V4 pending.",
        "version": "1.0.0",
        "keywords": ["poc-utrecht", "crosstrack", "plane-c"],
        "inputs": {
            "mode": {
                "title": "replay|execute",
                "schema": {"type": "string", "default": "replay"},
            },
            "runDir": {
                "title": "Existing crosstrack-runs dir (replay)",
                "schema": {"type": "string"},
            },
            "outDir": {
                "title": "Output dir (execute)",
                "schema": {"type": "string"},
            },
        },
        "outputs": {
            "summary": {"title": "Crosstrack summary", "schema": {"type": "object"}},
        },
    },
    "breda-scan-run": {
        "id": "breda-scan-run",
        "title": "Breda five-value scan run",
        "description": (
            "mode=replay: summary of existing poc-breda/runs dir. "
            "mode=execute: invoke poc-breda/run.py."
        ),
        "version": "1.0.0",
        "keywords": ["poc-breda", "scan"],
        "inputs": {
            "mode": {
                "title": "replay|execute",
                "schema": {"type": "string", "default": "replay"},
            },
            "runDir": {
                "title": "Existing breda-scan run dir",
                "schema": {"type": "string"},
            },
        },
        "outputs": {
            "summary": {"title": "Scan summary", "schema": {"type": "object"}},
        },
    },
    "rijnland-peil-conflict": {
        "id": "rijnland-peil-conflict",
        "title": "Rijnland peil conflict (H3)",
        "description": (
            "Peilgebied (vigerend) × peilafwijking (praktijk). "
            "mode=replay: summary of existing peil-conflict-report. "
            "mode=execute: invoke poc-rijnland/run.py (default demo bbox; "
            "optional --no-h3 for polygon-only)."
        ),
        "version": "1.0.0",
        "keywords": ["poc-rijnland", "peil", "h3", "conflict"],
        "inputs": {
            "mode": {
                "title": "replay|execute",
                "schema": {"type": "string", "default": "replay"},
            },
            "runDir": {
                "title": "Existing *-rijnland-peil run dir (replay)",
                "schema": {"type": "string"},
            },
            "outDir": {
                "title": "Output dir (execute)",
                "schema": {"type": "string"},
            },
            "bbox": {
                "title": "xmin,ymin,xmax,ymax EPSG:28992 (execute)",
                "schema": {"type": "string"},
            },
            "full": {
                "title": "Fetch entire Rijnland (no bbox)",
                "schema": {"type": "boolean", "default": False},
            },
            "noH3": {
                "title": "Skip H3 overlay",
                "schema": {"type": "boolean", "default": False},
            },
            "noKrw": {
                "title": "Skip KRW monitoring overlay",
                "schema": {"type": "boolean", "default": False},
            },
            "noWq": {
                "title": "Skip waterkwaliteit overlay",
                "schema": {"type": "boolean", "default": False},
            },
            "h3Resolution": {
                "title": "H3 resolution",
                "schema": {"type": "integer", "default": 8},
            },
        },
        "outputs": {
            "summary": {"title": "Peil-conflict summary", "schema": {"type": "object"}},
        },
    },
    "rijnland-peil-whatif": {
        "id": "rijnland-peil-whatif",
        "title": "Rijnland peilen what-if (CDC lake)",
        "description": (
            "Apply a peilen delta scenario (layer/stations), write CDC bronze batch, "
            "merge to silver, emit whatif-report + diff HTML, optionally attach "
            "peil-conflict replay summary."
        ),
        "version": "1.0.0",
        "keywords": ["poc-rijnland", "peil", "whatif", "cdc", "scenario"],
        "inputs": {
            "delta_m": {
                "title": "Waterstand delta in metres (mNAP)",
                "schema": {"type": "number"},
            },
            "layer": {
                "title": "polders|boezem|all",
                "schema": {"type": "string", "default": "boezem"},
            },
            "limit": {
                "title": "Max stations to touch",
                "schema": {"type": "integer"},
            },
            "scenarioId": {
                "title": "Scenario id",
                "schema": {"type": "string", "default": "whatif"},
            },
            "scenarioPath": {
                "title": "Optional path to scenario JSON",
                "schema": {"type": "string"},
            },
            "archivePath": {
                "title": "Optional peilen.json archive",
                "schema": {"type": "string"},
            },
            "outDir": {
                "title": "Output run directory",
                "schema": {"type": "string"},
            },
            "applyToLake": {
                "title": "Write CDC batch + apply silver",
                "schema": {"type": "boolean", "default": True},
            },
            "attachConflictReplay": {
                "title": "Attach peil-conflict replay summary",
                "schema": {"type": "boolean", "default": True},
            },
        },
        "outputs": {
            "summary": {"title": "What-if summary", "schema": {"type": "object"}},
        },
    },
    "bp2op-transform": {
        "id": "bp2op-transform",
        "title": "Eindhoven bp2op transform",
        "description": (
            "Bestemmingsplan → omgevingsplan conversion (Eindhoven use case). "
            "mode=replay: summary of existing run. mode=execute: invoke poc-bp2op/run.py."
        ),
        "version": "1.0.0",
        "keywords": ["poc-eindhoven", "bp2op", "legal", "plane-a"],
        "inputs": {
            "mode": {
                "title": "replay|execute",
                "schema": {"type": "string", "default": "replay"},
            },
            "useCase": {
                "title": "Use case id (eindhoven)",
                "schema": {"type": "string", "default": "eindhoven"},
            },
            "runDir": {
                "title": "Existing bp2op run dir (replay)",
                "schema": {"type": "string"},
            },
            "outDir": {
                "title": "Output root (execute)",
                "schema": {"type": "string"},
            },
        },
        "outputs": {
            "summary": {"title": "bp2op run summary", "schema": {"type": "object"}},
        },
    },
    "minigim-gebiedscheck-run": {
        "id": "minigim-gebiedscheck-run",
        "title": "MiniGIM gebiedscheck run (Lijst + ILS draft)",
        "description": (
            "MiniGIM omgevingsanalyse voor een plangrens: 74 Lijst-v0.91 items "
            "auto-invullen uit keyless open data + ILS-v0.8 draft-gebiedsindeling. "
            "mode=replay: summary van bestaande poc-minigim/runs dir. "
            "mode=execute: invoke poc-minigim/run.py --aoi <geojson>."
        ),
        "version": "1.0.0",
        "keywords": ["poc-minigim", "minigim", "gebiedsontwikkeling", "checklist", "ils"],
        "inputs": {
            "mode": {
                "title": "replay|execute",
                "schema": {"type": "string", "default": "replay"},
            },
            "aoiPath": {
                "title": "Plangrens-GeoJSON (execute; default: pilot Breda-Teteringen)",
                "schema": {"type": "string"},
            },
            "label": {
                "title": "Run-label (execute)",
                "schema": {"type": "string", "default": "gebiedscheck"},
            },
            "runDir": {
                "title": "Existing minigim-gebiedscheck run dir (replay)",
                "schema": {"type": "string"},
            },
        },
        "outputs": {
            "summary": {"title": "Gebiedscheck summary", "schema": {"type": "object"}},
        },
    },
}


def _resolve_dir(raw: str | None, *, default: Path | None = None) -> Path:
    if raw is None or raw == "":
        if default is None:
            raise ValueError("directory path required")
        return default
    p = Path(str(raw))
    if not p.is_absolute():
        p = (WORKSPACE / p).resolve()
    return p


def _ensure_poc_on_path() -> None:
    for root in (str(POC_ROOT), str(POC_BREDA)):
        if root not in sys.path:
            sys.path.insert(0, root)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_dir(parent: Path, pattern: str) -> Path:
    dirs = sorted(
        p for p in parent.glob(pattern)
        if p.is_dir() and (
            (p / "run_summary.json").is_file()
            or (p / "value-scan.json").is_file()
            or (p / "crosstrack-report.json").is_file()
            or (p / "peil-conflict-report.json").is_file()
            or (p / "omzettabel.json").is_file()
        )
    )
    if not dirs:
        raise FileNotFoundError(f"no runs matching {pattern!r} under {parent}")
    return dirs[-1]


def execute_breda_scan_query(inputs: dict[str, Any]) -> dict[str, Any]:
    _ensure_poc_on_path()
    from breda import qa  # type: ignore

    run_dir = _resolve_dir(
        inputs.get("runDir"),
        default=_latest_dir(POC_BREDA / "runs", "*-breda-scan"),
    )
    question = (inputs.get("question") or "").strip()
    if not question:
        raise ValueError("question is required")
    asker = inputs.get("asker") or "auto"
    if asker not in ("auto", "llm"):
        raise ValueError("asker must be auto|llm")

    scan_path = run_dir / "value-scan.json"
    if not scan_path.is_file():
        raise FileNotFoundError(f"geen value-scan.json in {run_dir}")
    scan = _load_json(scan_path)

    rejection = None
    query = None
    if asker == "llm":
        query, rejection = qa.LLMAsker(scan).propose(question)
    else:
        query = qa.parse_question(question, scan)

    if query is None:
        return {
            "result": {
                "status": "abstained",
                "runDir": str(run_dir),
                "question": question,
                "rejection": rejection or {
                    "reason": "deterministische parser kan de vraag niet mappen (cite-or-abstain)",
                },
            }
        }

    exec_result = qa.execute_query(query, scan)
    answer = qa.deterministic_answer(exec_result, scan)
    grounding_fails = qa.check_answer_grounding(answer, exec_result, scan)
    return {
        "result": {
            "status": "answered" if not grounding_fails else "grounding_failed",
            "runDir": str(run_dir),
            "question": question,
            "query": query,
            "execution": exec_result,
            "answer": answer,
            "groundingFails": grounding_fails,
        }
    }


def execute_scenario_author_propose(inputs: dict[str, Any]) -> dict[str, Any]:
    _ensure_poc_on_path()
    from pipeline import scenario_author, scenarios  # type: ignore
    from scenarios import run as scen_run  # type: ignore

    author_mode = str(inputs.get("author") or "auto")
    if author_mode not in ("auto", "llm", "hybrid"):
        raise ValueError("author must be auto|llm|hybrid")

    use_case = inputs.get("useCase") or "wind"
    baseline_dir = _resolve_dir(
        inputs.get("baselineRunDir"),
        default=scen_run.latest_baseline_run(use_case),
    )
    max_n = int(inputs.get("maxScenarios") or 10)
    baseline = scenarios.load_baseline(baseline_dir)

    if author_mode == "auto":
        author_obj = scenario_author.DeterministicScenarioAuthor()
    elif author_mode == "llm":
        author_obj = scenario_author.LLMScenarioAuthor()
        if not author_obj.endpoint:
            raise ValueError(
                "author=llm requires LDT_SCENARIO_LLM_ENDPOINT "
                "(use author=hybrid for det fallback)"
            )
    else:
        author_obj = scenario_author.HybridScenarioAuthor()

    try:
        specs, rejected = author_obj.propose(baseline, max_scenarios=max_n)
    except scenario_author.ScenarioAuthorError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "proposals": {
            "baselineRunDir": str(baseline_dir),
            "author": author_mode,
            "authorModel": str(getattr(author_obj, "model", "") or ""),
            "accepted": specs,
            "acceptedCount": len(specs),
            "rejected": rejected,
            "rejectedCount": len(rejected),
        }
    }


def execute_scenario_sweep(inputs: dict[str, Any]) -> dict[str, Any]:
    _ensure_poc_on_path()
    from scenarios import run as scen_run  # type: ignore

    use_case = inputs.get("useCase") or "wind"
    author = inputs.get("author") or "file"
    if author not in ("file", "auto"):
        raise ValueError("scenario-sweep local process supports author=file|auto")

    argv = ["--use-case", use_case, "--author", author]
    if inputs.get("baselineRunDir"):
        argv += ["--baseline", str(_resolve_dir(inputs["baselineRunDir"]))]
    if inputs.get("scenarioSetPath"):
        argv += ["--set", str(_resolve_dir(inputs["scenarioSetPath"]))]
    if inputs.get("outDir"):
        argv += ["--out", str(_resolve_dir(inputs["outDir"]))]
    if inputs.get("noH3", True):
        argv.append("--no-h3")

    code = scen_run.main(argv)
    out_dir = (
        _resolve_dir(inputs["outDir"])
        if inputs.get("outDir")
        else _latest_dir(POC_ROOT / "scenario-runs", f"*-{use_case}-scen")
    )
    report_path = out_dir / "scenario-report.json"
    validation_path = out_dir / "validation.json"
    summary: dict[str, Any] = {
        "exitCode": code,
        "outDir": str(out_dir),
        "useCase": use_case,
        "author": author,
    }
    if report_path.is_file():
        report = _load_json(report_path)
        summary["reportId"] = report.get("id")
        summary["verdict"] = report.get("verdict")
        summary["controlAreaKm2"] = (report.get("control") or {}).get("finalAreaKm2")
        summary["scenarioCount"] = len(report.get("scenarios") or [])
    if validation_path.is_file():
        summary["validationVerdict"] = _load_json(validation_path).get("verdict")
    return {"summary": summary}


def execute_opportunity_map_run(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = inputs.get("mode") or "replay"
    use_case = inputs.get("useCase") or "wind"
    if mode == "replay":
        run_dir = _resolve_dir(
            inputs.get("runDir"),
            default=_latest_dir(POC_ROOT / "runs", f"*-{use_case}"),
        )
        summary = _load_json(run_dir / "run_summary.json")
        return {
            "summary": {
                "mode": "replay",
                "runDir": str(run_dir),
                "useCase": use_case,
                "runId": summary.get("runId") or run_dir.name,
                "verdict": summary.get("verdict"),
                "headline": summary.get("headline"),
                "artifactCount": len(summary.get("artifacts") or {}),
            }
        }
    if mode != "execute":
        raise ValueError("mode must be replay|execute")

    cmd = [sys.executable, str(POC_ROOT / "run.py"), "--use-case", use_case]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(POC_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), env=env, capture_output=True, text=True)
    run_dir = _latest_dir(POC_ROOT / "runs", f"*-{use_case}")
    summary = _load_json(run_dir / "run_summary.json") if (run_dir / "run_summary.json").is_file() else {}
    return {
        "summary": {
            "mode": "execute",
            "exitCode": proc.returncode,
            "runDir": str(run_dir),
            "useCase": use_case,
            "verdict": summary.get("verdict"),
            "stderrTail": (proc.stderr or "")[-2000:],
        }
    }


def execute_crosstrack_overlay(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = inputs.get("mode") or "replay"
    xdir = POC_ROOT / "crosstrack-runs"
    if mode == "replay":
        run_dir = _resolve_dir(
            inputs.get("runDir"),
            default=_latest_dir(xdir, "*-xtrack"),
        )
        report = _load_json(run_dir / "crosstrack-report.json")
        validation = (
            _load_json(run_dir / "validation.json")
            if (run_dir / "validation.json").is_file()
            else {}
        )
        return {
            "summary": {
                "mode": "replay",
                "runDir": str(run_dir),
                "reportId": report.get("id"),
                "verdict": validation.get("verdict") or report.get("verdict"),
                "pairCount": len(report.get("pairs") or report.get("conflicts") or []),
            }
        }
    if mode != "execute":
        raise ValueError("mode must be replay|execute")

    cmd = [sys.executable, str(POC_ROOT / "crosstrack" / "run.py")]
    if inputs.get("outDir"):
        cmd += ["--out", str(_resolve_dir(inputs["outDir"]))]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(POC_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), env=env, capture_output=True, text=True)
    run_dir = _latest_dir(xdir, "*-xtrack")
    report = _load_json(run_dir / "crosstrack-report.json") if (run_dir / "crosstrack-report.json").is_file() else {}
    return {
        "summary": {
            "mode": "execute",
            "exitCode": proc.returncode,
            "runDir": str(run_dir),
            "reportId": report.get("id"),
            "stderrTail": (proc.stderr or "")[-2000:],
        }
    }


def execute_breda_scan_run(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = inputs.get("mode") or "replay"
    if mode == "replay":
        run_dir = _resolve_dir(
            inputs.get("runDir"),
            default=_latest_dir(POC_BREDA / "runs", "*-breda-scan"),
        )
        summary_path = run_dir / "run_summary.json"
        scan_path = run_dir / "value-scan.json"
        payload: dict[str, Any] = {
            "mode": "replay",
            "runDir": str(run_dir),
            "hasValueScan": scan_path.is_file(),
        }
        if summary_path.is_file():
            s = _load_json(summary_path)
            payload["verdict"] = s.get("verdict")
            payload["runId"] = s.get("runId") or run_dir.name
        elif scan_path.is_file():
            scan = _load_json(scan_path)
            payload["buurtCount"] = len(scan.get("buurten") or scan.get("neighbourhoods") or [])
            payload["runId"] = run_dir.name
        return {"summary": payload}
    if mode != "execute":
        raise ValueError("mode must be replay|execute")

    cmd = [sys.executable, str(POC_BREDA / "run.py")]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(POC_BREDA) + os.pathsep + str(POC_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), env=env, capture_output=True, text=True)
    run_dir = _latest_dir(POC_BREDA / "runs", "*-breda-scan")
    return {
        "summary": {
            "mode": "execute",
            "exitCode": proc.returncode,
            "runDir": str(run_dir),
            "stderrTail": (proc.stderr or "")[-2000:],
        }
    }


def execute_rijnland_peil_conflict(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = inputs.get("mode") or "replay"
    if mode == "replay":
        run_dir = _resolve_dir(
            inputs.get("runDir"),
            default=_latest_dir(POC_RIJNLAND / "runs", "*rijnland-peil*"),
        )
        report_path = run_dir / "peil-conflict-report.json"
        if not report_path.is_file():
            raise FileNotFoundError(f"geen peil-conflict-report.json in {run_dir}")
        report = _load_json(report_path)
        peil = report.get("peil") or {}
        h3 = report.get("h3Overlay") or {}
        return {
            "summary": {
                "mode": "replay",
                "runDir": str(run_dir),
                "runId": report.get("id") or run_dir.name,
                "verdict": report.get("verdict"),
                "bbox": report.get("bbox"),
                "peilgebiedAreaKm2": peil.get("peilgebiedAreaKm2"),
                "peilafwijkingAreaKm2": peil.get("peilafwijkingAreaKm2"),
                "overlapAreaKm2": peil.get("overlapAreaKm2"),
                "overlapShareOfPeilPct": peil.get("overlapShareOfPeilPct"),
                "h3ConflictCells": h3.get("conflictCells"),
                "h3Cells": h3.get("cells"),
                "hasH3Map": (run_dir / "h3-peil-conflict.html").is_file(),
                "lakeUriHint": "lake://nldt-poc-lake/bronze/rijnland/arcgis/",
            }
        }
    if mode != "execute":
        raise ValueError("mode must be replay|execute")

    cmd = [sys.executable, str(POC_RIJNLAND / "run.py")]
    if inputs.get("outDir"):
        cmd += ["--out", str(_resolve_dir(inputs["outDir"]))]
    if inputs.get("full"):
        cmd.append("--full")
    elif inputs.get("bbox"):
        cmd += ["--bbox", str(inputs["bbox"])]
    if inputs.get("noH3"):
        cmd.append("--no-h3")
    if inputs.get("noKrw"):
        cmd.append("--no-krw")
    if inputs.get("noWq"):
        cmd.append("--no-wq")
    if inputs.get("h3Resolution") is not None:
        cmd += ["--h3-resolution", str(int(inputs["h3Resolution"]))]

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(POC_RIJNLAND)
        + os.pathsep
        + str(POC_ROOT)
        + os.pathsep
        + env.get("PYTHONPATH", "")
    )
    # Prefer offline H3 cache for process adapter demos unless refresh requested.
    env.setdefault("POC_H3_OFFLINE", "1")
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), env=env, capture_output=True, text=True)
    if inputs.get("outDir"):
        run_dir = _resolve_dir(inputs["outDir"])
    else:
        run_dir = _latest_dir(POC_RIJNLAND / "runs", "*rijnland-peil*")
    report_path = run_dir / "peil-conflict-report.json"
    report = _load_json(report_path) if report_path.is_file() else {}
    return {
        "summary": {
            "mode": "execute",
            "exitCode": proc.returncode,
            "runDir": str(run_dir),
            "runId": report.get("id") or run_dir.name,
            "verdict": report.get("verdict"),
            "stderrTail": (proc.stderr or "")[-2000:],
            "stdoutTail": (proc.stdout or "")[-1000:],
        }
    }


def execute_bp2op_transform(inputs: dict[str, Any]) -> dict[str, Any]:
    mode = (inputs.get("mode") or "replay").lower()
    if mode == "replay":
        run_dir = _resolve_dir(
            inputs.get("runDir"),
            default=_latest_dir(POC_BP2OP / "runs", "*-eindhoven"),
        )
        summary_path = run_dir / "run_summary.json"
        if not summary_path.is_file():
            raise FileNotFoundError(f"geen run_summary.json in {run_dir}")
        summary = _load_json(summary_path)
        return {
            "summary": {
                "mode": "replay",
                "runDir": str(run_dir),
                "verdict": summary.get("verdict"),
                "useCase": summary.get("useCase") or inputs.get("useCase", "eindhoven"),
                "lakeUriHint": "lake://nldt-poc-lake/silver/eindhoven/corpus/",
            }
        }
    if mode != "execute":
        raise ValueError("mode must be replay|execute")

    use_case = inputs.get("useCase") or "eindhoven"
    out_root = _resolve_dir(inputs.get("outDir"), default=POC_BP2OP / "runs")
    cmd = [
        sys.executable,
        str(POC_BP2OP / "run.py"),
        "--use-case",
        str(use_case),
        "--out",
        str(out_root),
    ]
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True)
    run_dir = _latest_dir(out_root, f"*-{use_case}")
    summary_path = run_dir / "run_summary.json"
    summary = _load_json(summary_path) if summary_path.is_file() else {}
    return {
        "summary": {
            "mode": "execute",
            "exitCode": proc.returncode,
            "runDir": str(run_dir),
            "verdict": summary.get("verdict"),
            "useCase": use_case,
            "stderrTail": (proc.stderr or "")[-2000:],
        }
    }


def execute_minigim_gebiedscheck_run(inputs: dict[str, Any]) -> dict[str, Any]:
    """PoC-5 MiniGIM: replay/execute wrapper rond poc-minigim/run.py."""
    mode = inputs.get("mode") or "replay"
    if mode == "replay":
        run_dir = _resolve_dir(
            inputs.get("runDir"),
            default=_latest_dir(POC_MINIGIM / "runs", "*-minigim-gebiedscheck"),
        )
        payload: dict[str, Any] = {"mode": "replay", "runDir": str(run_dir)}
        summary_path = run_dir / "run_summary.json"
        if summary_path.is_file():
            s = _load_json(summary_path)
            inner = s.get("summary") or {}
            payload.update({
                "verdict": s.get("verdict"),
                "runId": s.get("runId") or run_dir.name,
                "items": inner.get("itemCount"),
                "delivered": (inner.get("deliveredStatus") or {}).get("delivered"),
            })
        else:
            raise FileNotFoundError(f"geen run_summary.json in {run_dir}")
        # detail uit het checklist-artefact (samenvatting per status)
        oa_path = run_dir / "omgevingsanalyse.json"
        if oa_path.is_file():
            oa = _load_json(oa_path)
            payload["summary"] = oa.get("summary", {})
        return {"summary": payload}
    if mode != "execute":
        raise ValueError("mode must be replay|execute")

    aoi = _resolve_dir(
        inputs.get("aoiPath"),
        default=POC_MINIGIM / "examples" / "plangrens-breda-teteringen.28992.geojson",
    )
    cmd = [
        sys.executable,
        str(POC_MINIGIM / "run.py"),
        "--aoi", str(aoi),
        "--label", str(inputs.get("label") or "gebiedscheck"),
    ]
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True)
    run_dir = _latest_dir(POC_MINIGIM / "runs", "*-minigim-gebiedscheck")
    summary_path = run_dir / "run_summary.json"
    summary = _load_json(summary_path) if summary_path.is_file() else {}
    inner = summary.get("summary") or {}
    return {
        "summary": {
            "mode": "execute",
            "exitCode": proc.returncode,
            "runDir": str(run_dir),
            "verdict": summary.get("verdict"),
            "items": inner.get("itemCount"),
            "delivered": (inner.get("deliveredStatus") or {}).get("delivered"),
            "stderrTail": (proc.stderr or "")[-2000:],
        }
    }


def execute_rijnland_peil_whatif(inputs: dict[str, Any]) -> dict[str, Any]:
    from services.rijnland_whatif import run_whatif

    scenario: dict[str, Any]
    if inputs.get("scenarioPath"):
        p = Path(str(inputs["scenarioPath"]))
        if not p.is_absolute():
            p = (WORKSPACE / p).resolve()
        scenario = json.loads(p.read_text(encoding="utf-8"))
    else:
        if inputs.get("delta_m") is None:
            raise ValueError("delta_m or scenarioPath required")
        scenario = {
            "id": inputs.get("scenarioId") or "whatif",
            "title": inputs.get("title") or f"What-if Δ{inputs['delta_m']} m",
            "description": inputs.get("description")
            or "Rijnland peilen what-if via CDC lake pipeline",
            "delta_m": float(inputs["delta_m"]),
            "layer": inputs.get("layer") or "boezem",
            "limit": inputs.get("limit"),
            "stationIds": inputs.get("stationIds"),
        }

    archive = None
    if inputs.get("archivePath"):
        archive = Path(str(inputs["archivePath"]))
        if not archive.is_absolute():
            archive = (WORKSPACE / archive).resolve()

    out_dir = None
    if inputs.get("outDir"):
        out_dir = _resolve_dir(inputs["outDir"])

    apply_lake = inputs.get("applyToLake")
    if apply_lake is None:
        apply_lake = True
    attach = inputs.get("attachConflictReplay")
    if attach is None:
        attach = True

    return run_whatif(
        scenario,
        archive_path=archive,
        out_dir=out_dir,
        apply_to_lake=bool(apply_lake),
        attach_conflict_replay=bool(attach),
    )


EXECUTORS = {
    "breda-scan-query": execute_breda_scan_query,
    "scenario-author-propose": execute_scenario_author_propose,
    "scenario-sweep": execute_scenario_sweep,
    "opportunity-map-run": execute_opportunity_map_run,
    "crosstrack-overlay": execute_crosstrack_overlay,
    "breda-scan-run": execute_breda_scan_run,
    "rijnland-peil-conflict": execute_rijnland_peil_conflict,
    "rijnland-peil-whatif": execute_rijnland_peil_whatif,
    "bp2op-transform": execute_bp2op_transform,
    "minigim-gebiedscheck-run": execute_minigim_gebiedscheck_run,
}


def execute_poc_process(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    fn = EXECUTORS.get(process_id)
    if fn is None:
        raise KeyError(process_id)
    return fn(inputs)
