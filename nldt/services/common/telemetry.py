from __future__ import annotations

import contextvars
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("nldt.telemetry")

_tracer: Any = None
_initialized = False

_job_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("nldt_job_id", default=None)


def set_current_job_id(job_id: str | None) -> None:
    _job_id_var.set(job_id)


def init_telemetry(service_name: str = "nldt") -> bool:
    """Initialize OpenTelemetry if SDK is available and NLDT_OTEL_ENABLED=1."""
    global _tracer, _initialized
    import os

    if _initialized:
        return _tracer is not None
    _initialized = True

    if os.environ.get("NLDT_OTEL_ENABLED", "").lower() not in ("1", "true", "yes"):
        logger.debug("OpenTelemetry disabled (set NLDT_OTEL_ENABLED=1)")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:
        logger.warning("opentelemetry packages not installed; telemetry no-op")
        return False

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    traces_dir = Path(os.environ.get("NLDT_TRACES_DIR", Path(__file__).resolve().parents[2] / "data" / "traces"))
    provider.add_span_processor(BatchSpanProcessor(_JsonlSpanExporter(traces_dir)))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    logger.info("OpenTelemetry initialized for %s", service_name)
    return True


def get_tracer() -> Any:
    init_telemetry()
    return _tracer


@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[None]:
    tracer = get_tracer()
    if tracer is None:
        yield
        return
    merged = dict(attributes or {})
    job_id = _job_id_var.get()
    if job_id:
        merged.setdefault("job.id", job_id)
    with tracer.start_as_current_span(name) as s:
        for k, v in merged.items():
            s.set_attribute(k, str(v))
        yield


class _JsonlSpanExporter:
    """Schrijft gesloten spans als JSONL (één object per regel) — bestandsbasis
    vervangt de console-only observability (roadmap 08: OTLP i.p.v. console)."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def export(self, spans):
        path = self.directory / f"{datetime.now(timezone.utc):%Y%m%d}-spans.jsonl"
        lines = []
        for span in spans:
            lines.append(json.dumps({
                "name": span.name,
                "traceId": f"{span.context.trace_id:032x}",
                "spanId": f"{span.context.span_id:016x}",
                "startTimeUnixNano": span.start_time,
                "endTimeUnixNano": span.end_time,
                "attributes": {k: span.attributes[k] for k in span.attributes.keys()},
            }, ensure_ascii=False, default=str))
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + ("\n" if lines else ""))
        from opentelemetry.sdk.trace.export import SpanExportResult

        return SpanExportResult.SUCCESS

    def shutdown(self):
        return None

    def force_flush(self, timeout_millis: int = 30000):
        return True
