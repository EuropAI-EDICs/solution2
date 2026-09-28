"""Tests for linear horizon projections (2050 PoC)."""

from __future__ import annotations

import json
from pathlib import Path

from services.timeseries.horizon import (
    format_projections_for_prompt,
    linear_fit,
    project_linear,
    projections_from_cbs_kwb_rows,
)

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "timeseries"
    / "cbs_kwb_breda_sample.json"
)


def test_linear_fit_known_line():
    slope, intercept = linear_fit([2020.0, 2021.0, 2022.0], [10.0, 12.0, 14.0])
    assert slope == 2.0
    assert intercept == 10.0 - 2.0 * 2020.0


def test_project_linear_clamps_percent():
    pts = [(2020, 90.0), (2022, 95.0), (2024, 99.0)]
    out = project_linear(pts, target_year=2050, clamp=(0.0, 100.0))
    assert out["projected"] == 100.0
    assert out["clamped"] is True
    assert out["uncapped"] > 100.0


def test_cbs_kwb_projections_heusdenhout_65():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    projs = projections_from_cbs_kwb_rows(data["rows"], target_year=2050)
    assert len(projs) >= 4
    h = next(
        p
        for p in projs
        if p["buurtcode"] == "BU07580202"
        and p["variable"] == "percentagePersonen65JaarEnOuder"
    )
    # 22.0 → 25.1 over 2020–2024 ≈ +0.775/yr → 2050 well above 25
    assert h["projected"] > 25.0
    assert h["projected"] <= 100.0
    assert "2050" in format_projections_for_prompt([h])
