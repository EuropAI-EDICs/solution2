"""Observation-extractors: lees de episodische laag, lever triggers (v1 automatische bronnen).

Pure functies met injecteerbare paden; afwezige bronnen leveren een lege
lijst (nooit een fout). De waardentabel per observationType is vast en
citeerbaar — geen LLM-tekstgeneratie (selection, not generation).
Bronpaden in observations worden repo-relatief genormaliseerd zodat
trailId's machine-onafhankelijk zijn.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
NLDT_ROOT = REPO_ROOT / "nldt"
POC_ROOT = REPO_ROOT / "poc"

DEFAULTS: dict[str, dict[str, str]] = {
    "journal_error": {
        "what": "Process-executie faalde met een fout (journal, process_result/error).",
        "why": "Onbekend — het proces faalde; oorzaak ligt in de procesimplementatie of de invoer.",
        "whatShouldChange": "Oorzaak analyseren; bij herhaling proces of invoer verbeteren.",
    },
    "hitl_needs_human": {
        "what": "Validatie-verdict needs_human: de keten wacht op een menselijk oordeel (V4/HITL).",
        "why": "RiskLevel hoog of het V4-verdict vraagt expliciete menselijke beoordeling.",
        "whatShouldChange": "Menselijk oordeel vastleggen; terugkerende redenen zijn kandidaat voor procedureverduidelijking.",
    },
    "ledger_reject": {
        "what": "Een LLM-proposal is afgewezen door een gate (cite-or-abstain ledger).",
        "why": "De proposal voldeed niet aan schema-, grounding- of budget-gate; hij is nooit uitgevoerd.",
        "whatShouldChange": "Patronen in afwijzingen reviewen; terugkerende afwijzingen wijzen op prompt- of schema-onderhoud.",
    },
    "golden_drift": {
        "what": "Golden-regressie wijst drift op: een of meer canonieke tracks diffen tegen de frozen goldens.",
        "why": "Een pipeline-, prompt- of modelwijziging veranderde de canonieke output.",
        "whatShouldChange": "Drift beoordelen: goldens vervangen bij intentionele wijziging, anders de wijziging terugdraaien.",
    },
}


def _rel(path: Path) -> str:
    """Repo-relatief als mogelijk — trailId blijft dan machine-onafhankelijk."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _obs(type_: str, source: str, detail: str, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    o: dict[str, Any] = {"type": type_, "source": source, "detail": detail}
    if provenance:
        clean = {k: v for k, v in provenance.items() if v}
        if clean:
            o["provenance"] = clean
    return o


def read_journal_errors(journal_path: Path | None = None) -> list[dict[str, Any]]:
    from services.process_adapter.journal import journal_path as default_journal_path

    path = journal_path or default_journal_path()
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and entry.get("kind") == "process_result" and entry.get("status") == "error":
            out.append(_obs(
                "journal_error",
                _rel(path),
                f"{entry.get('agent')}: {entry.get('summary')}",
                {"jobId": entry.get("jobId"), "agent": entry.get("agent")},
            ))
    return out


def read_hitl_observations(runs_root: Path | None = None) -> list[dict[str, Any]]:
    root = runs_root or NLDT_ROOT / "data" / "runs"
    out = []
    if not root.is_dir():
        return out
    for vfile in sorted(root.glob("*/validation.json")):
        try:
            report = json.loads(vfile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(report, dict) and report.get("verdict") == "needs_human":
            out.append(_obs(
                "hitl_needs_human",
                _rel(vfile),
                f"validation verdict needs_human (artifactId={report.get('artifactId')})",
                {"runId": vfile.parent.name},
            ))
    return out


def _ledger_entries(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    if isinstance(data, dict) and isinstance(data.get("rejected"), list):
        return [e for e in data["rejected"] if isinstance(e, dict)]
    return []


def read_ledger_observations(poc_root: Path | None = None) -> list[dict[str, Any]]:
    root = poc_root or POC_ROOT
    out = []
    patterns = [
        "scenario-runs/*/proposals-rejected.json",
        "runs/*/norm-llm-ledger.json",
        "llm-runs/*/norm-llm-ledger.json",
    ]
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            for entry in _ledger_entries(path):
                out.append(_obs("ledger_reject", _rel(path), json.dumps(entry, ensure_ascii=False)[:300]))
    return out


def read_golden_drift(diff_path: Path | None = None) -> list[dict[str, Any]]:
    path = diff_path or POC_ROOT / "eval" / "golden-diff.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for track, result in (data.get("tracks") or {}).items():
        if isinstance(result, dict) and result.get("pass") is False:
            out.append(_obs("golden_drift", _rel(path), f"track {track}: {json.dumps(result, ensure_ascii=False)[:200]}"))
    return out


def collect_observations() -> list[dict[str, Any]]:
    return read_journal_errors() + read_hitl_observations() + read_ledger_observations() + read_golden_drift()


def to_trail(observation: dict[str, Any]) -> dict[str, Any]:
    from services.memory.store import make_trail

    defaults = DEFAULTS.get(observation.get("type", ""), {})
    return make_trail(
        observation,
        what=defaults.get("what", observation.get("detail", "")),
        why=defaults.get("why", ""),
        what_should_change=defaults.get("whatShouldChange", ""),
    )
