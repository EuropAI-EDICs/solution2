"""Run-artefact: hcs-run-vorm + transaction-blok, weggeschreven onder runs/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def new_run_id(persona: str) -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-gent-transactional-{persona}"


def canonical(run: dict) -> dict:
    out = json.loads(json.dumps(run))
    out.pop("runId", None)
    out.pop("generatedAt", None)
    return out


def validate(run: dict, poc_root: Path) -> None:
    import jsonschema  # beschikbaar onder nldt/.venv; caller mag ImportError opvangen
    schema = json.loads((poc_root / "schemas" / "gent-run.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(run, schema)


def write_run(poc_root: Path, run: dict, events: list) -> Path:
    run_dir = poc_root / "runs" / run["runId"]
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (run_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return run_dir
