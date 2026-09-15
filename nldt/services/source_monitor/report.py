"""Deterministic Markdown change report (every number cites probe/diff)."""

from __future__ import annotations

from typing import Any


def render_change_report(diff: dict[str, Any], probe: dict[str, Any]) -> str:
    lines = [
        "# Source monitor change report",
        "",
        f"- Registry: `{diff.get('registryPath')}`",
        f"- Mode: `{diff.get('mode')}`",
        f"- Probed at: `{diff.get('probedAt')}` (from probe.probedAt)",
        f"- Sources probed: **{probe.get('sourceCount')}** (probe.sourceCount)",
        f"- Worst severity: **{diff.get('worstSeverity')}** (diff.worstSeverity)",
        f"- Critical findings: **{diff.get('criticalCount')}** (diff.criticalCount)",
        f"- Warn findings: **{diff.get('warnCount')}** (diff.warnCount)",
        "",
        "## Findings",
        "",
    ]
    for f in diff.get("findings") or []:
        sid = f.get("sourceId")
        lines.append(f"### `{sid}` — {f.get('severity')}")
        lines.append("")
        lines.append(
            f"- Registered featureCount: **{f.get('registeredFeatureCount')}** "
            f"(registrySnapshot.{sid}.featureCount)"
        )
        lines.append(
            f"- Live featureCount: **{f.get('liveFeatureCount')}** "
            f"(probe.results[{sid}].featureCount)"
        )
        lines.append(
            f"- Registered maxRecordCount: **{f.get('registeredMaxRecordCount')}**"
        )
        lines.append(f"- Live maxRecordCount: **{f.get('liveMaxRecordCount')}**")
        if f.get("probeStatus") != "ok":
            lines.append(f"- Probe status: `{f.get('probeStatus')}`")
        for ch in f.get("changes") or []:
            lines.append(f"- Change: `{ch}`")
        lines.append("")

    lines.extend(
        [
            "## Human action required",
            "",
            "This report and `registry-patch-proposal.json` are **proposals only**.",
            "A human must merge accepted updates into the authoritative `sources.json` (V4).",
            "The monitor never writes the registry itself.",
            "",
        ]
    )
    return "\n".join(lines)
