"""Single-file HTML report for the GWT twin run (vanilla HTML/CSS, offline).

Companion to the animated hex map: KPIs, per-day forecast + trigger
counts, scenario diff, backtest honesty numbers, command preview and the
provenance/caveat footer (Annex M governance: aggregate alerts only).
"""

from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Mapping, Optional

REPORT_VERSION = "poc-rijnland-gwt-report/0.1"

_CAVEAT = (
    "PROVENANCE — the depth series in this run are a deterministic seed "
    "(documented formula from open sensor metadata + open-meteo rain): no "
    "open Rijnland groundwater series resolves today (BRO / Lizard are "
    "credential-gated). Prediction numbers are relative (model vs "
    "persistence), thresholds are defaults — not board policy. See "
    "README + design doc.")


def _esc(v: Any) -> str:
    return _html.escape(str(v if v is not None else "—"))


def _fmt(v: Any, nd: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def _kpi(label: str, value: str, note: str = "") -> str:
    note_html = f'<div class="kpi-note">{_esc(note)}</div>' if note else ""
    return (f'<div class="kpi"><div class="kpi-value">{_esc(value)}</div>'
            f'<div class="kpi-label">{_esc(label)}</div>{note_html}</div>')


def _backtest_cells(bt: List[Mapping[str, Any]]) -> Dict[str, Any]:
    mses = sorted(b["mse"] for b in bt if b.get("available"))
    skills = [b["skillVsPersistence"] for b in bt if
              b.get("available") and b.get("skillVsPersistence") is not None]
    n_ok = len(mses)
    med_mse = mses[n_ok // 2] if mses else None
    med_skill = (sorted(skills)[len(skills) // 2] if skills else None)
    return {"nAvailable": n_ok, "medianMse": med_mse,
            "medianSkill": med_skill}


def render_report(run: Mapping[str, Any]) -> str:
    """run → standalone HTML string."""
    fc = run.get("forecastSummary") or {}
    days = fc.get("days") or []
    bt = _backtest_cells(run.get("backtests") or [])
    n_cmd = run.get("commandSummary", {}).get("totalCommands", 0)
    n_gaps = run.get("commandSummary", {}).get("totalGaps", 0)
    scenario = run.get("scenario")
    commands: List[Mapping[str, Any]] = (run.get("commands") or [])[:25]

    day_rows = "".join(
        f"<tr><td>{_esc(d['date'])}</td>"
        f"<td>{_fmt(d.get('meanDepth'))} m</td>"
        f'<td class="on">{d.get("WaterpumpON", 0)}</td>'
        f'<td class="off">{d.get("WaterpumpOFF", 0)}</td>'
        f"<td>{d.get('Monitor', 0)}</td>"
        f'<td class="gap">{d.get("gaps", 0)}</td></tr>'
        for d in days)

    scen_html = ""
    if scenario:
        srows = "".join(
            f"<tr><td>{_esc(d['date'])}</td>"
            f"<td>{_fmt(d.get('meanDepth'))} m</td>"
            f'<td class="on">{d.get("WaterpumpON", 0)}</td>'
            f'<td class="off">{d.get("WaterpumpOFF", 0)}</td>'
            f"<td>{d.get('gaps', 0)}</td></tr>"
            for d in (scenario.get("commandSummary", {}).get("days") or []))
        scen_html = f"""
<h2>Scenario — cloudburst {run.get('scenarioMm')} mm on day +1</h2>
<p>Same archive and models, forecast rain replaced by a flat cloudburst
(what-if, thesis “visualise the possible scenario”).</p>
<table><tr><th>date</th><th>mean depth</th><th>ON</th><th>OFF</th>
<th>gaps</th></tr>{srows}</table>"""

    cmd_rows = "".join(
        f"<tr><td>{_esc(c['date'])}</td>"
        f'<td class="{"on" if c["event"] == "WaterpumpON" else "off"}">'
        f'{_esc(c["event"])}</td>'
        f"<td>{_esc(c['loggerCode'])}</td><td>{_esc(c.get('polder'))}</td>"
        f"<td>{_fmt(c.get('depth'))} m</td>"
        f"<td>{_esc(c['gemaal']['code']) if c.get('gemaal') else ''} "
        f"({_fmt(c.get('distanceM'), 0)} m)</td>"
        f'<td class="gap">{"GAP" if c.get("gap") else ""}</td></tr>'
        for c in commands)

    map_link = (f'<p>Animated twin map (history → forecast, red = shallow/'
                f' ingress risk): <a href="{run.get("hexmapName")}">'
                f'{_esc(run.get("hexmapName"))}</a></p>' if run.get("hexmapName")
                else "<p>Hex map skipped (--no-h3).</p>")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Rijnland GWT twin — {run.get('runId')}</title>
<style>
 body{{font-family:-apple-system,'Segoe UI',sans-serif;margin:2rem auto;
      max-width:60rem;padding:0 1rem;color:#1a1a2e}}
 h1{{font-size:1.4rem}} h2{{font-size:1.1rem;margin-top:1.6rem}}
 table{{border-collapse:collapse;width:100%;font-size:.85rem}}
 th,td{{border:1px solid #d5d5de;padding:.25rem .5rem;text-align:left}}
 th{{background:#eef1f6}}
 .caveat{{background:#fff3cd;border:1px solid #e0c36a;border-radius:.4rem;
      padding:.6rem .9rem;font-size:.85rem}}
 .kpis{{display:flex;flex-wrap:wrap;gap:.8rem;margin:1rem 0}}
 .kpi{{border:1px solid #d5d5de;border-radius:.4rem;padding:.5rem .9rem;
      min-width:8rem}}
 .kpi-value{{font-size:1.3rem;font-weight:600}}
 .kpi-label{{font-size:.72rem;color:#555}}
 .kpi-note{{font-size:.68rem;color:#777}}
 td.on,th.on{{color:#a11212}} td.off{{color:#12508a}}
 td.gap{{color:#8a5a00;font-weight:600}}
 footer{{margin-top:2rem;font-size:.75rem;color:#666;border-top:1px solid
      #ddd;padding-top:.6rem}}
</style></head><body>
<h1>PoC-6 Rijnland GWT digital twin — {run.get('runId')}</h1>
<p><em>{_esc(run.get('mvpQuestion'))}</em></p>
<div class="caveat">{_CAVEAT}</div>
<div class="kpis">
{_kpi('Groundwater loggers', run.get('nLoggers', 0), 'Rijnland open ArcGIS')}
{_kpi('Forecast days', len(days), 'recursive day-ahead')}
{_kpi('Median holdout MSE', _fmt(bt['medianMse'], 4) + ' m²', f"n={bt['nAvailable']} loggers")}
{_kpi('Median skill vs persistence', _fmt(bt['medianSkill'], 2), '>0 beats persistence')}
{_kpi('Commands (5 d)', n_cmd, f'{n_gaps} without gemaal in reach')}
</div>
{map_link}
<h2>Forecast + trigger counts</h2>
<table><tr><th>date</th><th>mean depth</th><th class="on">WaterpumpON</th>
<th class="off">WaterpumpOFF</th><th>Monitor</th><th>gaps</th></tr>
{day_rows}</table>
{scen_html}
<h2>Command preview (first 25 of {n_cmd})</h2>
<table><tr><th>date</th><th>event</th><th>logger</th><th>polder</th>
<th>depth</th><th>nearest gemaal</th><th>gap</th></tr>
{cmd_rows or '<tr><td colspan="7">no triggers in this window</td></tr>'}
</table>
<footer>
Framework: Morales Ortega (2023), <i>A Digital Twin for Ground Water Table
Monitoring</i>, MSc thesis ITC Twente — translated to Rijnland on the nLDT
stack (design: docs/superpowers/specs/2026-10-13-rijnland-gwt-digital-twin-design.md).
Sensors: rijnland-meetlocatie-waterkwantiteit (open ArcGIS); rain: open-meteo;
pumps: rijnland-gemaal. Seed formula: {_esc(run.get('seedFormula'))}.<br>
Aggregate alerts only — no address-level detail (thesis Annex M governance).
</footer>
</body></html>"""
