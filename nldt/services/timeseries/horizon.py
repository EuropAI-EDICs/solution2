"""Linear horizon projections from annual CBS (and similar) time series.

PoC-grade: ordinary least-squares on year→value, extrapolate to a target year
with optional clamps for percentages. Not a demographic model — cite-or-abstain
evidence for S7 authors.
"""

from __future__ import annotations

from typing import Any


def linear_fit(years: list[float], values: list[float]) -> tuple[float, float]:
    """Return (slope per year, intercept at year 0)."""
    n = len(years)
    if n < 2:
        raise ValueError("need at least two points")
    if n != len(values):
        raise ValueError("years/values length mismatch")
    mean_x = sum(years) / n
    mean_y = sum(values) / n
    var_x = sum((x - mean_x) ** 2 for x in years)
    if var_x == 0:
        return 0.0, mean_y
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(years, values))
    slope = cov / var_x
    intercept = mean_y - slope * mean_x
    return slope, intercept


def project_linear(
    points: list[tuple[int, float]],
    *,
    target_year: int = 2050,
    clamp: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Project a (year, value) series to target_year.

    ``clamp`` e.g. (0, 100) for percentages.
    """
    if len(points) < 2:
        raise ValueError("need at least two (year, value) points")
    years = [float(y) for y, _ in points]
    values = [float(v) for _, v in points]
    slope, intercept = linear_fit(years, values)
    raw = intercept + slope * float(target_year)
    projected = raw
    if clamp is not None:
        lo, hi = clamp
        projected = max(lo, min(hi, raw))
    last_year, last_val = max(points, key=lambda p: p[0])
    return {
        "targetYear": target_year,
        "projected": round(projected, 2),
        "uncapped": round(raw, 2),
        "slopePerYear": round(slope, 4),
        "lastObserved": {"year": last_year, "value": last_val},
        "nPoints": len(points),
        "clamped": clamp is not None and projected != raw,
    }


def projections_from_cbs_kwb_rows(
    rows: list[dict[str, Any]],
    *,
    target_year: int = 2050,
) -> list[dict[str, Any]]:
    """Group CBS KWB-like rows by (buurt, measure) and project each series."""
    series: dict[tuple[str, str, str], list[tuple[int, float]]] = {}
    meta: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        period = str(row.get("Perioden") or "")
        year = period[:4]
        if not year.isdigit():
            continue
        buurt = str(row.get("WijkenEnBuurten") or row.get("RegioS") or "").strip()
        measure = str(row.get("Measure") or row.get("variable") or "").strip()
        if not buurt or not measure or row.get("value") is None:
            continue
        try:
            val = float(row["value"])
        except (TypeError, ValueError):
            continue
        key = (buurt, measure, str(row.get("unit") or "1"))
        series.setdefault(key, []).append((int(year), val))
        meta[key] = {
            "buurtnaam": str(row.get("buurtnaam") or buurt),
            "unit": str(row.get("unit") or "1"),
        }

    out: list[dict[str, Any]] = []
    for (buurt, measure, unit), pts in sorted(series.items()):
        pts = sorted(pts, key=lambda p: p[0])
        if len(pts) < 2:
            continue
        clamp = (0.0, 100.0) if unit == "%" or "percentage" in measure.lower() else None
        try:
            proj = project_linear(pts, target_year=target_year, clamp=clamp)
        except ValueError:
            continue
        m = meta[(buurt, measure, unit)]
        out.append(
            {
                "seriesId": f"cbs-kwb-{measure}-{buurt}".lower().replace("_", "-"),
                # stable slug-ish id without full slugger dependency
                "buurtcode": buurt,
                "buurtnaam": m["buurtnaam"],
                "variable": measure,
                "unit": unit,
                "method": "linear_ols",
                "horizon": target_year,
                **proj,
                "observed": [{"year": y, "value": v} for y, v in pts],
            }
        )
    # Fix seriesId to match lake slug style (normalize)
    for item in out:
        var_slug = "".join(c if c.isalnum() else "-" for c in item["variable"].lower()).strip("-")
        buurt_slug = item["buurtcode"].lower()
        item["seriesId"] = f"cbs-kwb-{var_slug}-{buurt_slug}"
    return out


def format_projections_for_prompt(projections: list[dict[str, Any]], *, limit: int = 12) -> str:
    """Compact bullet list for S7 LLM system prompt."""
    lines = []
    for p in projections[:limit]:
        lines.append(
            f"- {p['seriesId']}: {p['buurtnaam']} {p['variable']} "
            f"{p['lastObserved']['year']}={p['lastObserved']['value']}{p['unit']} "
            f"→ {p['horizon']}≈{p['projected']}{p['unit']} "
            f"(slope {p['slopePerYear']}/yr"
            f"{', clamped' if p.get('clamped') else ''})"
        )
    return "\n".join(lines)
