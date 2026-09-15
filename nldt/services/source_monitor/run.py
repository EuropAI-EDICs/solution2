"""Orchestrate probe → diff → report → patch → ValidationReport."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.common.prov import utc_now
from services.source_monitor.diff import diff_probe
from services.source_monitor.donl_probe import diff_donl_probe
from services.source_monitor.patch import build_patch_proposal
from services.source_monitor.paths import DEFAULT_FIXTURES, DEFAULT_RUNS, DEFAULT_WATCHLIST, NLDT_ROOT
from services.source_monitor.probe import probe_registry
from services.source_monitor.report import render_change_report


def _load_watchlist(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_registry(entry: dict[str, Any], *, fixture_dir: Path) -> Path:
    raw = entry.get("registryPath") or ""
    candidates = [
        Path(raw),
        NLDT_ROOT / raw,
        NLDT_ROOT.parent / raw,
        fixture_dir / Path(raw).name,
    ]
    for path in candidates:
        if path.is_file():
            return path.resolve()
    return (NLDT_ROOT.parent / raw).resolve()


def build_validation_report(diff: dict[str, Any], run_id: str) -> dict[str, Any]:
    critical = int(diff.get("criticalCount") or 0)
    worst = diff.get("worstSeverity") or "ok"
    checks = [
        {"id": "diff-present", "status": "pass"},
        {
            "id": "critical-findings",
            "status": "fail" if critical else "pass",
            "detail": f"criticalCount={critical}",
        },
    ]
    if worst == "critical" or critical:
        verdict = "needs_human"
        v4 = {"status": "pending", "checks": [{"id": "hitl-merge", "status": "fail", "detail": "merge patch"}]}
    elif worst == "warn":
        verdict = "needs_human"
        v4 = {"status": "pending", "checks": [{"id": "hitl-review", "status": "fail"}]}
        checks[1] = {"id": "critical-findings", "status": "pass", "detail": "warn only"}
    else:
        verdict = "pass"
        v4 = {"status": "not_applicable"}

    return {
        "id": f"VR-{run_id}-monitor",
        "artifactId": f"monitor-{run_id}",
        "artifactType": "process-output",
        "levels": {
            "V0": {"status": "pass", "checks": [{"id": "artifacts", "status": "pass"}]},
            "V1": {"status": "not_applicable"},
            "V2": {
                "status": "pass" if verdict != "fail" else "fail",
                "checks": checks,
            },
            "V3": {"status": "not_applicable"},
            "V4": v4,
        },
        "verdict": verdict,
        "evaluatorRun": "source-monitor#continuity",
        "evaluatedAt": utc_now(),
        "evidence": [
            {"ref": "diff.criticalCount", "note": str(critical)},
            {"ref": "diff.worstSeverity", "note": str(worst)},
        ],
    }


def run_monitor(
    *,
    mode: str = "replay",
    watchlist_path: Path | None = None,
    fixture_dir: Path | None = None,
    out_dir: Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    watchlist_path = watchlist_path or DEFAULT_WATCHLIST
    fixture_dir = fixture_dir or DEFAULT_FIXTURES
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{ts}-{uuid4().hex[:6]}"
    out = out_dir or (DEFAULT_RUNS / f"{run_id}-monitor")
    out.mkdir(parents=True, exist_ok=True)

    watchlist = _load_watchlist(watchlist_path)
    all_probes: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []
    registry_paths: list[str] = []

    for entry in watchlist.get("registries") or []:
        reg_path = _resolve_registry(entry, fixture_dir=fixture_dir)
        registry_paths.append(str(reg_path))
        if not reg_path.is_file():
            raise FileNotFoundError(f"registry not found for {entry.get('id')}: {reg_path}")
        allow = entry.get("sourceIds")
        entry_fixture = entry.get("fixtureDir")
        resolved_fixture = fixture_dir
        if mode == "replay" and entry_fixture:
            candidates = [
                Path(entry_fixture),
                NLDT_ROOT / entry_fixture,
                NLDT_ROOT.parent / entry_fixture,
            ]
            for cand in candidates:
                if cand.is_dir():
                    resolved_fixture = cand
                    break
        probe = probe_registry(
            reg_path,
            mode=mode,
            fixture_dir=resolved_fixture if mode == "replay" else None,
            allowlist=allow,
            timeout=timeout,
            registry_type=entry.get("type"),
        )
        if entry.get("type") == "donl" or probe.get("registryType") == "donl":
            diff = diff_donl_probe(probe)
        else:
            diff = diff_probe(probe)
        all_probes.append(probe)
        all_findings.extend(diff.get("findings") or [])

    # Aggregate
    worst = "ok"
    order = {"ok": 0, "warn": 1, "critical": 2}
    for f in all_findings:
        if order.get(f.get("severity"), 0) > order.get(worst, 0):
            worst = f["severity"]

    aggregated_probe = {
        "mode": mode,
        "probedAt": utc_now(),
        "sourceCount": sum(p.get("sourceCount") or 0 for p in all_probes),
        "results": [r for p in all_probes for r in (p.get("results") or [])],
        "registrySnapshot": {
            k: v for p in all_probes for k, v in (p.get("registrySnapshot") or {}).items()
        },
        "registryPath": ";".join(registry_paths),
        "watchlistPath": str(watchlist_path),
        "registries": all_probes,
    }
    aggregated_diff = {
        "worstSeverity": worst,
        "findingCount": len(all_findings),
        "criticalCount": sum(1 for f in all_findings if f.get("severity") == "critical"),
        "warnCount": sum(1 for f in all_findings if f.get("severity") == "warn"),
        "findings": all_findings,
        "probedAt": aggregated_probe["probedAt"],
        "registryPath": aggregated_probe["registryPath"],
        "mode": mode,
    }
    report_md = render_change_report(aggregated_diff, aggregated_probe)
    patch = build_patch_proposal(aggregated_diff, aggregated_probe)
    validation = build_validation_report(aggregated_diff, run_id)
    prov = {
        "runId": run_id,
        "activity": "nldt:SourceMonitor",
        "startedAtTime": aggregated_probe["probedAt"],
        "endedAtTime": utc_now(),
        "used": [str(watchlist_path), *registry_paths],
        "generated": [
            "probe.json",
            "diff.json",
            "change-report.md",
            "registry-patch-proposal.json",
            "validation-report.json",
        ],
        "autoApply": False,
    }

    (out / "probe.json").write_text(json.dumps(aggregated_probe, indent=2), encoding="utf-8")
    (out / "diff.json").write_text(json.dumps(aggregated_diff, indent=2), encoding="utf-8")
    (out / "change-report.md").write_text(report_md, encoding="utf-8")
    (out / "registry-patch-proposal.json").write_text(
        json.dumps(patch, indent=2), encoding="utf-8"
    )
    (out / "validation-report.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    (out / "prov.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "runId": run_id,
        "runDir": str(out),
        "mode": mode,
        "worstSeverity": worst,
        "criticalCount": aggregated_diff["criticalCount"],
        "warnCount": aggregated_diff["warnCount"],
        "validationReport": validation,
        "patchProposalPath": str(out / "registry-patch-proposal.json"),
        "changeReportPath": str(out / "change-report.md"),
        "autoApply": False,
    }
