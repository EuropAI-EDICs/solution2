"""ZN-2 — optelbaarheid: dezelfde indicatordefinities over ≥2 gebieden.

MVP: offline fixtures met twee synthetische gemeenten; identieke
``DEFAULT_PARAMS``; gewogen combined mean (gewicht = aantal land-buurten
met score). Geen LLM; geen live tweede stad.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import indicators

ROOT = Path(__file__).resolve().parent.parent
REPORT_SCHEMA_PATH = ROOT / "schemas" / "optelbaarheid-report.schema.json"

SCORE_WAARDEN = ("democratic", "spatial", "economic", "social")


def load_report_schema() -> dict:
    return json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))


def formula_fingerprint() -> str:
    """Stabiele hash van formules + default params (citeerbaar in rapport)."""
    payload = {
        "accessFields": [f for f, _ in indicators.ACCESS_FIELDS],
        "accessMinPresent": indicators.ACCESS_MIN_PRESENT,
        "defaultParams": indicators.DEFAULT_PARAMS,
        "bedrijvenFields": indicators.BEDRIJVEN_FIELDS,
        "values": list(SCORE_WAARDEN),
        "scale": "percentile-0-100-within-area",
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def params_fingerprint(params: dict | None = None) -> str:
    p = params if params is not None else indicators.DEFAULT_PARAMS
    raw = json.dumps(p, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def area_means(scan_buurten: list[dict]) -> tuple[dict, dict, int, dict]:
    """Per waarde: percentile-mean + absolute input-means; gewichten = n scored.

    Within-area percentiles middelen vaak ~50; optelbaarheid over gebieden
    steunt daarom ook op ``absoluteMeans`` (ruwe deelindicatoren).
    """
    means: dict[str, float | None] = {}
    weights: dict[str, int] = {}
    absolute: dict[str, float | None] = {}
    n_land = sum(1 for b in scan_buurten if b.get("water") == "NEE")
    for v in SCORE_WAARDEN:
        vals = [
            b["scores"][v]["score"]
            for b in scan_buurten
            if b.get("water") == "NEE" and b["scores"][v]["score"] is not None
        ]
        weights[v] = len(vals)
        means[v] = round(sum(vals) / len(vals), 2) if vals else None

    # Absolute, cross-area vergelijkbare middelen (citeerbaar)
    abs_specs = {
        "onbenut_dakpotentieel": ("economic", "onbenut_dakpotentieel"),
        "groendekking_share": ("spatial", "groendekking_share"),
        "verharding_pct": ("social", "verharding_pct"),
        "ouderen_pct": ("social", "ouderen_pct"),
    }
    for key, (value, input_key) in abs_specs.items():
        vals = []
        for b in scan_buurten:
            if b.get("water") != "NEE":
                continue
            raw = (b.get("scores") or {}).get(value, {}).get("inputs", {}).get(input_key)
            if isinstance(raw, (int, float)):
                vals.append(float(raw))
        absolute[key] = round(sum(vals) / len(vals), 4) if vals else None

    return means, weights, n_land, absolute


def weighted_combined(areas: list[dict]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for v in SCORE_WAARDEN:
        num = 0.0
        den = 0
        for a in areas:
            m = a["means"].get(v)
            w = int((a.get("weights") or {}).get(v) or 0)
            if m is not None and w > 0:
                num += float(m) * w
                den += w
        out[v] = round(num / den, 2) if den else None
    return out


def _weighted_absolute(areas: list[dict]) -> dict[str, float | None]:
    keys = (
        "onbenut_dakpotentieel",
        "groendekking_share",
        "verharding_pct",
        "ouderen_pct",
    )
    out: dict[str, float | None] = {}
    for key in keys:
        num = 0.0
        den = 0
        for a in areas:
            m = (a.get("absoluteMeans") or {}).get(key)
            w = int(a.get("nLandBuurten") or 0)
            if m is not None and w > 0:
                num += float(m) * w
                den += w
        out[key] = round(num / den, 4) if den else None
    return out


def second_city_layers(base_layers: dict, *, gemeente: str, code: str, gm: str) -> dict:
    """Kloon fixture-lagen naar een tweede gemeente (andere codes/namen)."""
    import copy

    layers = copy.deepcopy(base_layers)
    buurten = layers["buurten"]
    for i, f in enumerate(buurten["features"]):
        p = f["properties"]
        # hernummer buurtcodes stabiel onder nieuwe GM
        old = p.get("buurtcode") or f"BU0000{i:04d}"
        suffix = old[-4:] if len(old) >= 4 else f"{i:04d}"
        p["buurtcode"] = f"BU{gm[2:]}{suffix}"
        p["wijkcode"] = f"WK{gm[2:]}{(i // 12):02d}"
        p["gemeentecode"] = gm
        p["gemeentenaam"] = gemeente
        # lichte score-shift zodat gebieden niet bit-identiek zijn
        if p.get("water") != "JA":
            for key in (
                "percentageWoningenMetZonnestroom",
                "percentagePersonen65JaarEnOuder",
                "percentageEengezinswoning",
            ):
                if isinstance(p.get(key), (int, float)) and p[key] > -90000:
                    p[key] = round(float(p[key]) * 0.92 + 1.5, 3)
    return {
        "layers": layers,
        "meta": {"areaId": code, "gemeente": gemeente, "gemeenteCode": gm},
    }


def run_optelbaarheid(
    area_specs: list[tuple[str, dict, dict]],
    *,
    params: dict | None = None,
    generated_at: str | None = None,
) -> dict:
    """``area_specs``: list of (areaId, layers, meta{gemeente,gemeenteCode})."""
    import datetime as _dt

    checks: list[dict] = []
    fp = formula_fingerprint()
    pp = params_fingerprint(params)
    areas_out = []

    for area_id, layers, meta in area_specs:
        scan = indicators.compute_scan(layers, params)
        means, weights, n_land, absolute = area_means(scan["buurten"])
        areas_out.append(
            {
                "areaId": area_id,
                "gemeente": meta["gemeente"],
                "gemeenteCode": meta["gemeenteCode"],
                "nLandBuurten": n_land,
                "means": means,
                "absoluteMeans": absolute,
                "weights": weights,
                "formulaFingerprint": fp,
                "paramsFingerprint": pp,
            }
        )

    identical = (
        len({a["formulaFingerprint"] for a in areas_out}) == 1
        and len({a["paramsFingerprint"] for a in areas_out}) == 1
        and len(areas_out) >= 2
    )
    checks.append(
        {
            "id": "definitions-identical",
            "ok": identical,
            "detail": (
                f"formula={fp} params={pp} over {len(areas_out)} gebieden"
                if identical
                else "fingerprints divergeren"
            ),
        }
    )

    combined_means = weighted_combined(areas_out)
    # Algebra-check: combined moet tussen min/max van area means liggen
    algebra_ok = True
    for v in SCORE_WAARDEN:
        vals = [a["means"][v] for a in areas_out if a["means"][v] is not None]
        c = combined_means[v]
        if not vals or c is None:
            continue
        if c < min(vals) - 0.05 or c > max(vals) + 0.05:
            algebra_ok = False
    checks.append(
        {
            "id": "combined-within-range",
            "ok": algebra_ok,
            "detail": "gewogen mean ligt binnen min/max van deelgebieden"
            if algebra_ok
            else "combined buiten bereik van deel-means",
        }
    )

    # Reconstructie: weighted mean handmatig
    recon_ok = True
    for v in SCORE_WAARDEN:
        num = sum(
            float(a["means"][v]) * a["weights"][v]
            for a in areas_out
            if a["means"][v] is not None and a["weights"][v] > 0
        )
        den = sum(
            a["weights"][v]
            for a in areas_out
            if a["means"][v] is not None and a["weights"][v] > 0
        )
        expected = round(num / den, 2) if den else None
        if expected != combined_means[v]:
            recon_ok = False
    checks.append(
        {
            "id": "weighted-mean-reconstructible",
            "ok": recon_ok,
            "detail": "combined = Σ(mean×n)/Σ(n)" if recon_ok else "reconstructie faalt",
        }
    )

    verdict = "pass" if all(c["ok"] for c in checks) else "fail"
    generated = generated_at or _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    report = {
        "reportId": "zn2-optelbaarheid",
        "generatedAt": generated,
        "znTrack": "ZN-2",
        "definitions": {
            "identical": identical,
            "formulaFingerprint": fp,
            "paramsFingerprint": pp,
            "scoreScale": "0-100 percentile within each area (then comparable means)",
            "values": list(SCORE_WAARDEN),
        },
        "areas": [
            {
                "areaId": a["areaId"],
                "gemeente": a["gemeente"],
                "gemeenteCode": a["gemeenteCode"],
                "nLandBuurten": a["nLandBuurten"],
                "means": a["means"],
                "absoluteMeans": a["absoluteMeans"],
                "weights": a["weights"],
            }
            for a in areas_out
        ],
        "combined": {
            "method": "weighted_mean_by_scored_land_buurten",
            "nAreas": len(areas_out),
            "means": combined_means,
            "absoluteMeans": _weighted_absolute(areas_out),
        },
        "validation": {"verdict": verdict, "checks": checks},
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
        "# ZN-2 — Optelbaarheid",
        "",
        f"Gegenereerd: {report['generatedAt']}",
        f"Verdict: **{report['validation']['verdict']}**",
        f"Definitions identical: **{report['definitions']['identical']}**",
        f"Fingerprint: `{report['definitions']['formulaFingerprint']}` / "
        f"`{report['definitions']['paramsFingerprint']}`",
        "",
        "## Gebieden",
        "",
        "| Gebied | GM | n land | dem | spa | eco | soc |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for a in report["areas"]:
        m = a["means"]
        lines.append(
            f"| {a['gemeente']} | {a['gemeenteCode']} | {a['nLandBuurten']} | "
            f"{m['democratic']} | {m['spatial']} | {m['economic']} | {m['social']} |"
        )
    c = report["combined"]["means"]
    lines += [
        "",
        "## Combined (gewogen)",
        "",
        f"Methode: `{report['combined']['method']}`",
        "",
        f"- democratic: {c['democratic']}",
        f"- spatial: {c['spatial']}",
        f"- economic: {c['economic']}",
        f"- social: {c['social']}",
        "",
        "## Absolute (cross-area)",
        "",
    ]
    abs_c = report["combined"].get("absoluteMeans") or {}
    for k, v in abs_c.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Checks"]
    for ch in report["validation"]["checks"]:
        mark = "OK" if ch["ok"] else "FAIL"
        lines.append(f"- [{mark}] `{ch['id']}` — {ch['detail']}")
    return "\n".join(lines) + "\n"
