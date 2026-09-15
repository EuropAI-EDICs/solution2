# 17 — Source monitor (open-data continuity)

> Status: **MVP done** (2026-09-15).  
> Origin: [`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) “Watching the data sources”
> · slides *Next 2 — a source-monitor agent*.

Continuity of open data is a **monitored process**, not a snapshot. The monitor
catches silent registry drift (e.g. 117 012 trees collapsing to a page-cap of
1 000).

Doctrine: **AI proposes · pipeline disposes · human decides** — the monitor
**never** writes `sources.json`.

---

## What it does

1. **Deterministic probe** (ArcGIS REST FeatureServer/MapServer): layer metadata
   (`maxRecordCount`, fields, geometryType) + `returnCountOnly` feature count.
2. **Machine diff** vs registry snapshot → severity `ok` | `warn` | `critical`
   (critical includes page-cap collapse and probe HTTP errors).
3. **Artifacts:** `change-report.md`, `registry-patch-proposal.json`,
   `validation-report.json`, `prov.json` under
   `nldt/data/source-monitor/runs/<ts>-monitor/`.
4. **Human merge (V4):** operator applies accepted fields from the patch
   proposal; nothing is auto-applied.

Modes: `replay` (fixtures / CI) · `live` (HTTP).

---

## nLDT wiring

| Piece | Location |
|-------|----------|
| Engine | [`services/source_monitor/`](services/source_monitor/) |
| Process | `source-monitor-probe` |
| Recipe | `source-monitor-run` (`riskLevel: high`) |
| Watchlist | [`data/source-monitor-watchlist.json`](data/source-monitor-watchlist.json) |
| Fixtures | [`data/source-monitor/fixtures/`](data/source-monitor/fixtures/) |
| CLI | `python -m services.source_monitor.cli run --mode replay\|live` |

Scheduler note: Kestra (or any cron) can invoke the CLI/process; the job body
is this process — no scheduler YAML ships in this MVP.

---

## Quick start

```bash
cd nldt
NLDT_OFFLINE=1 PYTHONPATH=. python -m services.source_monitor.cli run --mode replay

# Via process
PYTHONPATH=. python -c "
from services.process_adapter.handlers import execute_local
print(execute_local('source-monitor-probe', {'mode': 'replay'})['summary']['worstSeverity'])
"

# Live (needs network)
PYTHONPATH=. python -m services.source_monitor.cli run --mode live
```

---

## Non-goals (follow-ups)

- Auto-updating `poc/data/sources.json`
- Full PDOK/CBS WFS XML filter suite
- LLM-authored change prose (reuse Q&A number-gate later)
