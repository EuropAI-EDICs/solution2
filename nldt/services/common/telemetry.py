from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("nldt.telemetry")

_tracer: Any = None
_initialized = False


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
    with tracer.start_as_current_span(name) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, str(v))
        yield
