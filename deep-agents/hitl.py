"""HITL-support: configuratie, duurzaam verdict-ledger en resume-mapping.

De journal (runs/live/steps.jsonl) wordt per run gereset; alles wat de
leerstaat voedt gaat daarom in dit append-only ledger.
"""

import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "runs" / "live" / "hitl-verdicts.jsonl"
PENDING = "__hitl_pending__"   # sentinel: run_streamed retourneert dit bij een interrupt-einde
PENDING_EXIT_CODE = 2

MC6_TOELICHTING = (
    "MC-6 (VNG-methode): niets wordt door AI gekoppeld; de jurist beslist. "
    "De bp2op-transform schrijft het omgevingsplan-dossier."
)

HITL_TOOLS: dict[str, dict] = {
    "run_bp2op_transform": {
        "allowed_decisions": ["approve", "reject"],
        "description": MC6_TOELICHTING,
    }
}


def ledger_append(record: dict) -> None:
    """Append-only: één record per regel, met tijdstempel."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    line = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def ledger_read() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def pending_from_ledger() -> dict | None:
    """Eerste request zonder bijbehorend verdict (op interruptId), of None."""
    verdicts = {r["interruptId"] for r in ledger_read() if r.get("kind") == "verdict"}
    for r in ledger_read():
        if r.get("kind") == "request" and r.get("interruptId") not in verdicts:
            return r
    return None


def verdict_to_decisions(approved: bool, comment: str) -> dict:
    """Mapt het dashboard-verdict op het deepagents-resume-contract."""
    if approved:
        return {"decisions": [{"type": "approve"}]}
    return {"decisions": [{"type": "reject", "message": comment}]}


def args_summary(args: dict) -> str:
    """Deterministische, afgekorte samenvatting voor journal/UI/ledger."""
    if not isinstance(args, dict):
        return str(args)[:120]
    flat = ", ".join(f"{k}={str(v)[:40]}" for k, v in sorted(args.items()))
    return flat[:120]
