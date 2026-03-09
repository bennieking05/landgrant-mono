import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def configure_tracing() -> None:
    if not settings.enable_otlp:
        logger.info("OTLP disabled")
        return

    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    logger.info("OTLP tracing configured")
