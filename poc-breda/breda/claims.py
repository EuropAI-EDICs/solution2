"""Plane D — deterministische ruimtelijke claims op de Breda vijf-waardenscan.

Een claim is een **contract** (``schemas/spatial-claim.schema.json``): kind,
doelbuurten, magnitude, bewijsklasse. De runner herhaalt eerst een ongemuteerde
control (V3) en past daarna gedocumenteerde impactregels toe. Geen LLM in de
cijferlijn; geen single winner-score (V4 = human / pending).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import indicators

ROOT = Path(__file__).resolve().parent.parent
CLAIM_SCHEMA_PATH = ROOT / "schemas" / "spatial-claim.schema.json"
REPORT_SCHEMA_PATH = ROOT / "schemas" / "gebiedsafweging-report.schema.json"

WAARDEN = ("democratic", "spatial", "economic", "social", "autonomous")
SCORE_WAARDEN = ("democratic", "spatial", "economic", "social")


class ClaimError(RuntimeError):
    """Contract- of gate-fout (nooit stil hersteld)."""


def load_claim_schema() -> dict:
    return json.loads(CLAIM_SCHEMA_PATH.read_text(encoding="utf-8"))


def load_report_schema() -> dict:
    return json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_claim(spec: dict) -> list[str]:
    """V0 (schema) + lichte V2-checks. Lege lijst = ok."""
    import jsonschema

    try:
        jsonschema.validate(spec, load_claim_schema())
    except jsonschema.ValidationError as exc:
        return [f"schema: {exc.message}"]

    schendingen: list[str] = []
    basis = spec["basis"]
    if basis["type"] == "hypothetical" and not (basis.get("rationale") or "").strip():
        schendingen.append("hypothetical vereist rationale")
    if not spec.get("buurtcodes"):
        schendingen.append("buurtcodes mag niet leeg zijn")
    return schendingen


def _clamp(score: float | None, lo: float = 0.0, hi: float = 100.0) -> float | None:
    if score is None:
        return None
    return round(max(lo, min(hi, float(score))), 1)


def _score_map(buurt: dict) -> dict:
    scores = buurt.get("scores") or {}
    out = {v: (scores.get(v) or {}).get("score") for v in SCORE_WAARDEN}
    out["autonomous"] = None  # manifest, geen buurtscore
    return out


def _delta_map(baseline: dict, scenario: dict) -> dict:
    out = {}
    for v in WAARDEN:
        b, s = baseline.get(v), scenario.get(v)
        if b is None or s is None:
            out[v] = None
        else:
            out[v] = round(float(s) - float(b), 1)
    return out


def _inputs(buurt: dict, value: str) -> dict:
    return dict(((buurt.get("scores") or {}).get(value) or {}).get("inputs") or {})


# --------------------------------------------------------------------------- #
# Impactregels (unit-tested, citeerbaar)
# --------------------------------------------------------------------------- #


RULES = {
    "R-PV-ECO": (
        "dak_pv_maximalisatie: economic += magnitude × (3 + 20 × onbenut_dakpotentieel); "
        "waarde van het realiseren van dakpotentieel"
    ),
    "R-PV-SPA": (
        "dak_pv_maximalisatie: spatial −= magnitude × 4 × groendekking_share "
        "wanneer groendekking_share ≥ 0.25 (druk op groene ruggegraat)"
    ),
    "R-WON-CAP": (
        "woningverdichting: capacityPressure = magnitude × 10 "
        "(herleidbare drukindicator, geen zesde congreswaarde)"
    ),
    "R-WON-SPA": (
        "woningverdichting: spatial −= magnitude × (2 + 8 × groendekking_share)"
    ),
    "R-WON-SOC": (
        "woningverdichting: social += magnitude × (2 + 0.04 × verharding_pct × "
        "ouderen_pct / 100) — meer hitte-aandacht bij verdichting"
    ),
    "R-WON-ECO": (
        "woningverdichting: economic += magnitude × 1.5 (lichte capaciteitswinst)"
    ),
}


def apply_claim_to_buurt(buurt: dict, kind: str, magnitude: int) -> tuple[dict, list[str], float | None]:
    """Pas één claim toe op één buurt. Geeft (scenario_scores, flags, capacityPressure)."""
    base = _score_map(buurt)
    scenario = dict(base)
    flags: list[str] = []
    capacity: float | None = None
    mag = int(magnitude)

    if kind == "dak_pv_maximalisatie":
        eco_in = _inputs(buurt, "economic")
        onbenut = eco_in.get("onbenut_dakpotentieel")
        onbenut_f = float(onbenut) if isinstance(onbenut, (int, float)) else 0.0
        eco_delta = mag * (3.0 + 20.0 * onbenut_f)
        scenario["economic"] = _clamp(
            None if base["economic"] is None else base["economic"] + eco_delta
        )
        flags.append("economic_up")
        spa_in = _inputs(buurt, "spatial")
        share = spa_in.get("groendekking_share")
        share_f = float(share) if isinstance(share, (int, float)) else 0.0
        if share_f >= 0.25 and base["spatial"] is not None:
            spa_delta = mag * 4.0 * share_f
            scenario["spatial"] = _clamp(base["spatial"] - spa_delta)
            flags.append("spatial_down_green_pressure")
    elif kind == "woningverdichting":
        capacity = float(mag * 10)
        flags.append("capacity_pressure")
        spa_in = _inputs(buurt, "spatial")
        share = spa_in.get("groendekking_share")
        share_f = float(share) if isinstance(share, (int, float)) else 0.0
        if base["spatial"] is not None:
            scenario["spatial"] = _clamp(base["spatial"] - mag * (2.0 + 8.0 * share_f))
            flags.append("spatial_down")
        soc_in = _inputs(buurt, "social")
        verh = soc_in.get("verharding_pct")
        oud = soc_in.get("ouderen_pct")
        verh_f = float(verh) if isinstance(verh, (int, float)) else 0.0
        oud_f = float(oud) if isinstance(oud, (int, float)) else 0.0
        if base["social"] is not None:
            scenario["social"] = _clamp(
                base["social"] + mag * (2.0 + 0.04 * verh_f * oud_f / 100.0)
            )
            flags.append("social_up_heat_attention")
        if base["economic"] is not None:
            scenario["economic"] = _clamp(base["economic"] + mag * 1.5)
            flags.append("economic_up_capacity")
    else:
        raise ClaimError(f"onbekend claim-kind: {kind!r}")

    return scenario, flags, capacity


def rules_for_kind(kind: str) -> list[dict]:
    if kind == "dak_pv_maximalisatie":
        ids = ["R-PV-ECO", "R-PV-SPA"]
    elif kind == "woningverdichting":
        ids = ["R-WON-CAP", "R-WON-SPA", "R-WON-SOC", "R-WON-ECO"]
    else:
        ids = []
    return [{"ruleId": rid, "description": RULES[rid]} for rid in ids]


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


def _buurten_by_code(scan: dict) -> dict:
    return {b["buurtcode"]: b for b in scan.get("buurten") or []}


def _control_ok(baseline_scan: dict, layers: dict) -> tuple[bool, str]:
    control = indicators.compute_scan(layers)
    base = {
        b["buurtcode"]: {v: b["scores"][v]["score"] for v in SCORE_WAARDEN}
        for b in baseline_scan.get("buurten") or []
    }
    ctrl = {
        b["buurtcode"]: {v: b["scores"][v]["score"] for v in SCORE_WAARDEN}
        for b in control.get("buurten") or []
    }
    diffs = [
        f"{code}/{v}"
        for code in base
        for v in SCORE_WAARDEN
        if base[code][v] != ctrl.get(code, {}).get(v)
    ]
    if diffs:
        return False, f"{len(diffs)} scoreverschillen, o.a. {diffs[:5]}"
    return True, "control reproduceert de baseline exact"


def run_afweging(
    baseline_scan: dict,
    layers: dict,
    claim_specs: list[dict],
    *,
    baseline_source: str = "value-scan",
    generated_at: str | None = None,
) -> dict:
    """Control + claims → gebiedsafweging-report."""
    import datetime as _dt

    checks: list[dict] = []
    errors: list[str] = []

    def check(cid: str, ok: bool, detail: str) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            errors.append(f"{cid}: {detail}")

    gevalideerd, afgewezen = [], []
    for spec in claim_specs:
        schendingen = validate_claim(spec)
        if schendingen:
            afgewezen.append(
                {
                    "claimId": spec.get("claimId"),
                    "name": spec.get("name"),
                    "kind": spec.get("kind"),
                    "magnitude": spec.get("magnitude"),
                    "basis": spec.get("basis") or {},
                    "rulesApplied": [],
                    "buurten": [],
                    "tradeOffFlags": [],
                    "rejected": True,
                    "rejectReason": "; ".join(schendingen),
                }
            )
        else:
            gevalideerd.append(spec)
    check(
        "V0-V2-claimcontracten",
        not afgewezen,
        f"{len(gevalideerd)} aangenomen, {len(afgewezen)} afgewezen",
    )

    ok_ctrl, detail_ctrl = _control_ok(baseline_scan, layers)
    check("V3-control-identiteit", ok_ctrl, detail_ctrl)

    by_code = _buurten_by_code(baseline_scan)
    claim_rows: list[dict] = list(afgewezen)

    if ok_ctrl:
        for spec in gevalideerd:
            unknown = [c for c in spec["buurtcodes"] if c not in by_code]
            if unknown:
                claim_rows.append(
                    {
                        "claimId": spec["claimId"],
                        "name": spec["name"],
                        "kind": spec["kind"],
                        "magnitude": spec["magnitude"],
                        "basis": spec["basis"],
                        "rulesApplied": rules_for_kind(spec["kind"]),
                        "buurten": [],
                        "tradeOffFlags": [],
                        "rejected": True,
                        "rejectReason": f"onbekende buurtcodes: {unknown}",
                    }
                )
                continue

            buurt_rows = []
            trade_flags: set[str] = set()
            for code in spec["buurtcodes"]:
                buurt = by_code[code]
                if buurt.get("water") != "NEE":
                    buurt_rows.append(
                        {
                            "buurtcode": code,
                            "buurtnaam": buurt.get("buurtnaam"),
                            "capacityPressure": None,
                            "baseline": _score_map(buurt),
                            "scenario": _score_map(buurt),
                            "delta": {v: None for v in WAARDEN},
                            "flags": ["skipped_water"],
                        }
                    )
                    continue
                scenario, flags, capacity = apply_claim_to_buurt(
                    buurt, spec["kind"], spec["magnitude"]
                )
                baseline_scores = _score_map(buurt)
                delta = _delta_map(baseline_scores, scenario)
                for f in flags:
                    trade_flags.add(f)
                buurt_rows.append(
                    {
                        "buurtcode": code,
                        "buurtnaam": buurt.get("buurtnaam"),
                        "capacityPressure": capacity,
                        "baseline": baseline_scores,
                        "scenario": scenario,
                        "delta": delta,
                        "flags": flags,
                    }
                )

            claim_rows.append(
                {
                    "claimId": spec["claimId"],
                    "name": spec["name"],
                    "kind": spec["kind"],
                    "magnitude": spec["magnitude"],
                    "basis": spec["basis"],
                    "provenanceNote": spec.get("provenanceNote"),
                    "proposedBy": spec.get("proposedBy") or "file",
                    "rulesApplied": rules_for_kind(spec["kind"]),
                    "buurten": buurt_rows,
                    "tradeOffFlags": sorted(trade_flags),
                    "rejected": False,
                    "rejectReason": None,
                }
            )

    accepted = [c for c in claim_rows if not c.get("rejected")]
    if errors and not ok_ctrl:
        verdict = "fail"
    elif afgewezen and not accepted:
        verdict = "fail"
    elif accepted:
        verdict = "needs_human"  # V4 always pending for Plane D
    else:
        verdict = "fail"

    generated = generated_at or _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    report = {
        "reportId": "breda-gebiedsafweging",
        "generatedAt": generated,
        "plane": "D",
        "baseline": {
            "source": baseline_source,
            "nBuurten": len(baseline_scan.get("buurten") or []),
            "scanId": (baseline_scan.get("scan") or {}).get("scanId"),
        },
        "checks": checks,
        "claims": claim_rows,
        "validation": {
            "verdict": verdict,
            "levels": {
                "V0": "pass" if not afgewezen else "fail",
                "V2": "pass" if not afgewezen else "fail",
                "V3": "pass" if ok_ctrl else "fail",
                "V4": "pending",
            },
        },
        "decision": {
            "mode": "human",
            "winnerClaimId": None,
            "note": (
                "Plane D kwantificeert trade-offs; kiest geen winnaar. "
                "Bestuurlijke afweging blijft bij de mens (V4)."
            ),
        },
    }
    return report


def validate_report(report: dict) -> list[str]:
    import jsonschema

    try:
        jsonschema.validate(report, load_report_schema())
    except jsonschema.ValidationError as exc:
        return [exc.message]
    return []


def build_report_md(report: dict) -> str:
    lines = [
        "# Plane D — Integrale gebiedsafweging (Breda)",
        "",
        f"Gegenereerd: {report.get('generatedAt')}",
        f"Verdict: **{report['validation']['verdict']}** (V4={report['validation']['levels']['V4']})",
        "",
        report["decision"]["note"],
        "",
        "## Checks",
    ]
    for c in report.get("checks") or []:
        mark = "OK" if c["ok"] else "FAIL"
        lines.append(f"- [{mark}] `{c['id']}` — {c['detail']}")
    lines.append("")
    lines.append("## Claims")
    for claim in report.get("claims") or []:
        lines.append(f"### {claim['claimId']} — {claim['name']}")
        if claim.get("rejected"):
            lines.append(f"**Afgewezen:** {claim.get('rejectReason')}")
            lines.append("")
            continue
        lines.append(f"- Kind: `{claim['kind']}` · magnitude {claim['magnitude']}")
        lines.append(f"- Basis: `{claim['basis'].get('type')}`")
        if claim["basis"].get("rationale"):
            lines.append(f"- Rationale: {claim['basis']['rationale']}")
        lines.append(f"- Trade-off flags: {', '.join(claim.get('tradeOffFlags') or []) or '—'}")
        lines.append("")
        lines.append("| Buurt | Δ dem | Δ spa | Δ eco | Δ soc | flags |")
        lines.append("|---|---:|---:|---:|---:|---|")
        for b in claim.get("buurten") or []:
            d = b["delta"]
            lines.append(
                f"| {b.get('buurtnaam') or b['buurtcode']} | "
                f"{d['democratic']} | {d['spatial']} | {d['economic']} | "
                f"{d['social']} | {', '.join(b.get('flags') or [])} |"
            )
        lines.append("")
        lines.append("Regels:")
        for r in claim.get("rulesApplied") or []:
            lines.append(f"- `{r['ruleId']}`: {r['description']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_report_html(report: dict) -> str:
    """Compacte offline HTML-trade-offkaart (geen externe deps)."""
    rows = []
    for claim in report.get("claims") or []:
        if claim.get("rejected"):
            rows.append(
                f"<section><h2>{_esc(claim.get('claimId'))} (afgewezen)</h2>"
                f"<p>{_esc(claim.get('rejectReason'))}</p></section>"
            )
            continue
        body = [
            f"<h2>{_esc(claim['claimId'])} — {_esc(claim['name'])}</h2>",
            f"<p><code>{_esc(claim['kind'])}</code> · magnitude {claim['magnitude']} · "
            f"basis {_esc(claim['basis'].get('type'))}</p>",
        ]
        if claim["basis"].get("rationale"):
            body.append(f"<p class='rationale'>{_esc(claim['basis']['rationale'])}</p>")
        body.append(
            "<table><thead><tr><th>Buurt</th><th>baseline eco/spa/soc</th>"
            "<th>scenario eco/spa/soc</th><th>Δ eco/spa/soc</th><th>flags</th></tr></thead><tbody>"
        )
        for b in claim.get("buurten") or []:
            bl, sc, d = b["baseline"], b["scenario"], b["delta"]
            body.append(
                "<tr>"
                f"<td>{_esc(b.get('buurtnaam') or b['buurtcode'])}</td>"
                f"<td>{bl['economic']} / {bl['spatial']} / {bl['social']}</td>"
                f"<td>{sc['economic']} / {sc['spatial']} / {sc['social']}</td>"
                f"<td class='delta'>{d['economic']} / {d['spatial']} / {d['social']}</td>"
                f"<td>{_esc(', '.join(b.get('flags') or []))}</td>"
                "</tr>"
            )
        body.append("</tbody></table>")
        body.append("<ul class='rules'>")
        for r in claim.get("rulesApplied") or []:
            body.append(f"<li><code>{_esc(r['ruleId'])}</code> — {_esc(r['description'])}</li>")
        body.append("</ul>")
        rows.append("<section>" + "".join(body) + "</section>")

    checks_html = "".join(
        f"<li class='{'ok' if c['ok'] else 'fail'}'>"
        f"<code>{_esc(c['id'])}</code> — {_esc(c['detail'])}</li>"
        for c in report.get("checks") or []
    )
    return f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"/>
<title>Plane D — gebiedsafweging Breda</title>
<style>
 body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 24px; color: #1e293b; }}
 h1 {{ font-size: 1.35rem; }} h2 {{ font-size: 1.1rem; margin-top: 1.4rem; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin: 8px 0 16px; }}
 th, td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; }}
 th {{ background: #f1f5f9; }}
 .delta {{ font-weight: 600; }}
 .rationale {{ color: #475569; font-size: 13px; }}
 .ok {{ color: #15803d; }} .fail {{ color: #b91c1c; }}
 .note {{ background: #fff7ed; border: 1px solid #fdba74; padding: 10px 12px; border-radius: 6px; }}
 code {{ font-size: 12px; }}
</style></head><body>
<h1>Plane D — Integrale gebiedsafweging (Breda)</h1>
<p>Gegenereerd: {_esc(report.get('generatedAt'))} · verdict
<strong>{_esc(report['validation']['verdict'])}</strong>
(V4={_esc(report['validation']['levels']['V4'])})</p>
<p class="note">{_esc(report['decision']['note'])}</p>
<h2>Checks</h2><ul>{checks_html}</ul>
{''.join(rows)}
</body></html>
"""


def _esc(value) -> str:
    s = "" if value is None else str(value)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_claims_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("claims"), list):
        return data["claims"]
    raise ClaimError(f"geen claims[] in {path}")
