"""Rijnland peilen what-if: scenario deltas → CDC lake batches → report."""

from __future__ import annotations

import copy
import importlib.util
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.cdc import bronze_cdc_dir, silver_peilen_path
from services.lake import DEFAULT_BUCKET, NLDT_ROOT

WORKSPACE = NLDT_ROOT.parent
POC_RIJNLAND = WORKSPACE / "poc-rijnland"
DEFAULT_ARCHIVE = POC_RIJNLAND / "data" / "peilen" / "peilen.json"


def load_archive(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_ARCHIVE
    return json.loads(p.read_text(encoding="utf-8"))


def apply_scenario_to_archive(
    archive: dict[str, Any],
    scenario: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (scenario_archive, cdc_change_rows) without mutating input."""
    delta = float(scenario["delta_m"])
    layer = (scenario.get("layer") or "all").lower()
    station_ids = set(scenario.get("stationIds") or [])
    limit = scenario.get("limit")

    out = copy.deepcopy(archive)
    stations = out.get("stations") or {}
    changes: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    touched = 0

    for sid, rec in stations.items():
        if station_ids and sid not in station_ids:
            continue
        rec_layer = (rec.get("layer") or "").lower()
        if layer != "all" and rec_layer != layer:
            continue
        latest = rec.get("latest") or {}
        if latest.get("value") is None:
            continue
        before = float(latest["value"])
        after = before + delta
        latest["value"] = after
        latest["fetchedAt"] = now
        latest["whatIf"] = {
            "before": before,
            "after": after,
            "delta_m": delta,
            "scenarioId": scenario.get("id"),
        }
        rec["latest"] = latest
        day = now[:10]
        days = rec.setdefault("days", {})
        days[day] = {
            "n": 1,
            "median": after,
            "min": after,
            "max": after,
            "whatIf": True,
        }
        touched += 1
        changes.append(
            {
                "cdc_lsn": touched,
                "op": "U",
                "peilgebied_id": sid,
                "waterstand_m": after,
                "measured_at": now,
                "source": f"whatif:{scenario.get('id') or 'scenario'}",
                "captured_at": now,
                "before_m": before,
                "delta_m": delta,
                "layer": rec_layer,
                "name": rec.get("name"),
            }
        )
        if limit is not None and touched >= int(limit):
            break

    out["whatIf"] = {
        "scenario": {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
            "description": scenario.get("description"),
            "delta_m": delta,
            "layer": layer,
            "stationIds": sorted(station_ids) if station_ids else None,
            "limit": limit,
        },
        "stationsTouched": touched,
        "appliedAt": now,
    }
    return out, changes


def write_cdc_batch(changes: list[dict[str, Any]], *, poc: str = "rijnland") -> Path | None:
    if not changes:
        return None
    rows = [
        {
            "cdc_lsn": c["cdc_lsn"],
            "op": c["op"],
            "peilgebied_id": c["peilgebied_id"],
            "waterstand_m": c["waterstand_m"],
            "measured_at": c["measured_at"],
            "source": c["source"],
            "captured_at": c["captured_at"],
        }
        for c in changes
    ]
    import duckdb

    out_dir = bronze_cdc_dir(poc)
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-whatif"
    dest = out_dir / f"{batch_id}.parquet"
    jl = out_dir / f"{batch_id}.jsonl"
    with jl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    con = duckdb.connect()
    con.execute(
        f"COPY (SELECT * FROM read_json_auto('{jl.as_posix()}')) "
        f"TO '{dest.as_posix()}' (FORMAT PARQUET)"
    )
    jl.unlink(missing_ok=True)
    return dest


def _load_apply_batches():
    path = NLDT_ROOT / "scripts" / "cdc_apply_peilen.py"
    spec = importlib.util.spec_from_file_location("cdc_apply_peilen", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cdc_apply_peilen"] = mod
    spec.loader.exec_module(mod)
    return mod.apply_batches


def write_diff_html(changes: list[dict[str, Any]], scenario: dict[str, Any], dest: Path) -> Path:
    rows = "".join(
        f"<tr><td>{c.get('name') or c['peilgebied_id']}</td>"
        f"<td>{c.get('layer')}</td>"
        f"<td>{c['before_m']:.3f}</td>"
        f"<td>{c['waterstand_m']:.3f}</td>"
        f"<td>{c['delta_m']:+.3f}</td></tr>"
        for c in changes[:200]
    )
    html = f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"/>
<title>Rijnland peilen what-if</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;background:#f6f7f9;color:#1a1a1a}}
table{{border-collapse:collapse;width:100%;background:#fff}}
th,td{{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}}
th{{background:#e8eef5}}
.meta{{margin-bottom:1.5rem}}
</style></head><body>
<h1>{scenario.get('title') or 'Rijnland peilen what-if'}</h1>
<div class="meta">
<p>{scenario.get('description') or ''}</p>
<p><strong>Δ</strong> {scenario.get('delta_m')} m ·
<strong>laag</strong> {scenario.get('layer') or 'all'} ·
<strong>stations</strong> {len(changes)}</p>
</div>
<table>
<thead><tr><th>Station</th><th>Laag</th><th>Voor</th><th>Na</th><th>Δ m</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p><em>AI proposes · pipeline disposes · human decides</em></p>
</body></html>
"""
    dest.write_text(html, encoding="utf-8")
    return dest


def build_whatif_report(
    *,
    scenario: dict[str, Any],
    changes: list[dict[str, Any]],
    cdc_batch: str | None,
    silver_uri: str | None,
    run_dir: str,
    conflict_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    deltas = [c["delta_m"] for c in changes]
    layers: dict[str, int] = {}
    for c in changes:
        layers[c.get("layer") or "unknown"] = layers.get(c.get("layer") or "unknown", 0) + 1
    return {
        "id": f"whatif-{scenario.get('id') or 'scenario'}",
        "artifactType": "rijnland-peil-whatif-report",
        "scenario": scenario,
        "stationsTouched": len(changes),
        "layersTouched": layers,
        "delta_m": scenario.get("delta_m"),
        "deltaStats": {
            "min": min(deltas) if deltas else None,
            "max": max(deltas) if deltas else None,
            "median": statistics.median(deltas) if deltas else None,
        },
        "cdcBatch": cdc_batch,
        "silverUri": silver_uri,
        "runDir": run_dir,
        "conflict": conflict_summary,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "doctrine": "AI proposes · pipeline disposes · human decides",
    }


def run_whatif(
    scenario: dict[str, Any],
    *,
    archive_path: Path | None = None,
    out_dir: Path | None = None,
    apply_to_lake: bool = True,
    attach_conflict_replay: bool = True,
) -> dict[str, Any]:
    archive = load_archive(archive_path)
    scenario_archive, changes = apply_scenario_to_archive(archive, scenario)
    if not changes:
        raise ValueError("scenario touched 0 stations — check layer/stationIds/limit")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir or (POC_RIJNLAND / "runs" / f"{ts}-peilen-whatif")
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "peilen-whatif.json").write_text(
        json.dumps(scenario_archive, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    (run_dir / "scenario.json").write_text(
        json.dumps(scenario, indent=2) + "\n", encoding="utf-8"
    )
    write_diff_html(changes, scenario, run_dir / "whatif-diff.html")

    cdc_path = None
    silver_uri = None
    if apply_to_lake:
        cdc_path = write_cdc_batch(changes)
        if cdc_path:
            apply_batches = _load_apply_batches()
            applied = apply_batches([cdc_path], silver_peilen_path("rijnland"))
            silver_uri = (
                f"lake://{DEFAULT_BUCKET}/silver/rijnland/peilen_latest/peilen_latest.parquet"
            )
            (run_dir / "cdc-apply.json").write_text(
                json.dumps(applied, indent=2) + "\n", encoding="utf-8"
            )

    conflict_summary = None
    if attach_conflict_replay:
        conflict_summary = _conflict_replay_summary()

    report = build_whatif_report(
        scenario=scenario,
        changes=changes,
        cdc_batch=str(cdc_path) if cdc_path else None,
        silver_uri=silver_uri,
        run_dir=str(run_dir),
        conflict_summary=conflict_summary,
    )
    (run_dir / "whatif-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "changes.json").write_text(
        json.dumps(changes[:500], indent=2) + "\n", encoding="utf-8"
    )

    return {
        "summary": {
            "mode": "whatif",
            "runDir": str(run_dir),
            "stationsTouched": len(changes),
            "delta_m": scenario.get("delta_m"),
            "layer": scenario.get("layer") or "all",
            "scenarioId": scenario.get("id"),
            "cdcBatch": str(cdc_path) if cdc_path else None,
            "silverUri": silver_uri,
            "diffHtml": str(run_dir / "whatif-diff.html"),
            "conflictVerdict": (conflict_summary or {}).get("verdict"),
            "reportPath": str(run_dir / "whatif-report.json"),
            "lakeUriHint": silver_uri,
        }
    }


def _conflict_replay_summary() -> dict[str, Any] | None:
    try:
        from services.process_adapter.poc_handlers import execute_rijnland_peil_conflict

        out = execute_rijnland_peil_conflict({"mode": "replay"})
        return out.get("summary")
    except Exception as exc:
        return {"error": str(exc), "mode": "replay_failed"}
