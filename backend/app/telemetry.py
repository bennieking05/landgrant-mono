"""OpenTelemetry configuration (Phase 3.4).

Exports traces via OTLP HTTP when ``ENABLE_OTLP`` is set.  Auto-instruments
FastAPI and SQLAlchemy so every request and DB query is traced without
per-route plumbing.  Silently becomes a no-op when optional dependencies
are missing so tests still import cleanly.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_configured = False


def configure_tracing() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    if not settings.enable_otlp:
        logger.info("OTLP disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except Exception as exc:  # pragma: no cover - optional dep missing
        logger.warning("OTLP dependencies missing: %s", exc)
        return

    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "service.namespace": "landgrant",
            "deployment.environment": settings.environment,
        }
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    logger.info("OTLP tracing configured")


def instrument_app(app) -> None:
    """Attach FastAPI + SQLAlchemy instrumentation to a running app.

    Called after the FastAPI instance and database engine exist so the
    instrumentation libraries can hook their middlewares cleanly.
    """

    if not settings.enable_otlp:
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:  # pragma: no cover
        logger.warning("FastAPI instrumentation skipped: %s", exc)

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from app.db.session import engine

        SQLAlchemyInstrumentor().instrument(engine=engine)
    except Exception as exc:  # pragma: no cover
        logger.warning("SQLAlchemy instrumentation skipped: %s", exc)
