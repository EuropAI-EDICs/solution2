from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.common import telemetry


@pytest.fixture
def fresh_telemetry(tmp_path: Path, monkeypatch) -> Path:
    """Reset de module-global zodat init opnieuw loopt; stuur exporter naar tmp."""
    monkeypatch.setenv("NLDT_OTEL_ENABLED", "1")
    monkeypatch.setenv("NLDT_TRACES_DIR", str(tmp_path / "traces"))
    monkeypatch.setattr(telemetry, "_initialized", False)
    monkeypatch.setattr(telemetry, "_tracer", None)
    return tmp_path / "traces"


def test_span_writes_jsonl_with_and_without_job_id(fresh_telemetry: Path) -> None:
    """Één test voor beide gevallen: opentelemetry's set_tracer_provider is
    maar één keer per proces aanroepbaar, dus geen tweede init in een tweede test."""
    telemetry.set_current_job_id("job-7")
    with telemetry.span("unit.test", {"k": "v"}):
        pass
    telemetry.set_current_job_id(None)
    with telemetry.span("unit.clean"):
        pass
    from opentelemetry import trace as otel_trace

    otel_trace.get_tracer_provider().force_flush()
    files = list(fresh_telemetry.glob("*-spans.jsonl"))
    assert files, "geen spans-bestand geschreven"
    entries = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines() if line]
    with_job = next(e for e in entries if e["name"] == "unit.test")
    without = next(e for e in entries if e["name"] == "unit.clean")
    assert with_job["attributes"]["job.id"] == "job-7"
    assert with_job["attributes"]["k"] == "v"
    assert "job.id" not in without["attributes"]
