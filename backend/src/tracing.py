"""Distributed tracing with OpenTelemetry.

This module provides OpenTelemetry instrumentation for the Data Capsule Server
application, enabling distributed tracing across service boundaries.

Features:
- OTLP export to APM backends (Jaeger, Zipkin, Azure Monitor, etc.)
- Automatic HTTP request tracing
- Database query tracing
- Custom span creation for business operations
- Context propagation across async boundaries

Usage:
    from src.tracing import setup_tracing, create_span, get_tracer

    # In app startup
    setup_tracing(app)

    # In business code
    with create_span("process_ingestion") as span:
        span.set_attribute("capsule_count", len(capsules))
        # ... processing code
"""

import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])

# Module-level tracer instance
_tracer: Optional[Tracer] = None


def get_tracer(name: str = "dab") -> Tracer:
    """Get or create the OpenTelemetry tracer.

    Args:
        name: Name for the tracer (default: 'dab')

    Returns:
        OpenTelemetry Tracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(name)
    return _tracer


def setup_tracing(
    app: Any,
    service_name: str = "data-architecture-brain",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
    engine: Optional[Any] = None,
) -> None:
    """Configure OpenTelemetry tracing for the application.

    Args:
        app: FastAPI application instance
        service_name: Service name for trace identification
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        enable_console_export: Enable console span export for debugging
        engine: SQLAlchemy engine for database tracing
    """
    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "data-architecture",
            "service.version": "1.0.0",
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint is configured
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # Use insecure=False with TLS in production
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP tracing enabled, exporting to {otlp_endpoint}")

    # Add console exporter for debugging
    if enable_console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console tracing enabled")

    # Set the tracer provider
    trace.set_tracer_provider(provider)

    # Set up context propagation (W3C Trace Context + B3 for compatibility)
    propagator = TraceContextTextMapPropagator()
    set_global_textmap(propagator)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI tracing instrumented")

    # Instrument HTTPX for outgoing HTTP calls
    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX tracing instrumented")

    # Instrument SQLAlchemy if engine provided
    if engine:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,
            enable_commenter=True,
        )
        logger.info("SQLAlchemy tracing instrumented")

    # Update module tracer
    global _tracer
    _tracer = trace.get_tracer(service_name)


def shutdown_tracing() -> None:
    """Shutdown tracing and flush remaining spans."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
        logger.info("Tracing shutdown complete")


@contextmanager
def create_span(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
):
    """Create a traced span context manager.

    Args:
        name: Span name
        kind: Span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)
        attributes: Initial span attributes

    Yields:
        The active span

    Example:
        with create_span("process_capsule", attributes={"capsule_urn": urn}) as span:
            result = process(capsule)
            span.set_attribute("result_status", result.status)
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def traced(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Decorator for tracing function execution.

    Args:
        name: Span name (defaults to function name)
        kind: Span kind
        attributes: Static span attributes

    Returns:
        Decorated function

    Example:
        @traced("ingest_capsule", attributes={"operation": "ingest"})
        async def ingest_capsule(urn: str) -> Capsule:
            ...
    """

    def decorator(func: F) -> F:
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with create_span(span_name, kind=kind, attributes=attributes) as span:
                # Add function arguments as span attributes
                if args:
                    span.set_attribute("args_count", len(args))
                if kwargs:
                    span.set_attribute("kwargs_keys", list(kwargs.keys()))
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with create_span(span_name, kind=kind, attributes=attributes) as span:
                if args:
                    span.set_attribute("args_count", len(args))
                if kwargs:
                    span.set_attribute("kwargs_keys", list(kwargs.keys()))
                return func(*args, **kwargs)

        # Check if function is async
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def add_span_attributes(attributes: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
    """Add attributes to the current span.

    Args:
        attributes: Dictionary of attributes to add (optional)
        **kwargs: Key-value pairs to add as attributes

    Example:
        add_span_attributes({"capsule_count": 10, "layer": "silver"})
        add_span_attributes(capsule_count=10, layer="silver")
    """
    span = trace.get_current_span()
    if span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        for key, value in kwargs.items():
            span.set_attribute(key, value)


def record_exception(exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Record an exception in the current span.

    Args:
        exception: The exception to record
        attributes: Additional attributes for context
    """
    span = trace.get_current_span()
    if span:
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID as a hex string.

    Returns:
        Trace ID hex string or None if no active trace
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_span_id() -> Optional[str]:
    """Get the current span ID as a hex string.

    Returns:
        Span ID hex string or None if no active span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return None


# Pre-defined span attributes for common operations
class SpanAttributes:
    """Common span attribute names for consistency."""

    # HTTP (OpenTelemetry semantic conventions)
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_TARGET = "http.target"
    HTTP_HOST = "http.host"
    HTTP_SCHEME = "http.scheme"
    HTTP_ROUTE = "http.route"
    HTTP_USER_AGENT = "http.user_agent"
    HTTP_REQUEST_CONTENT_LENGTH = "http.request_content_length"
    HTTP_RESPONSE_CONTENT_LENGTH = "http.response_content_length"

    # Database (OpenTelemetry semantic conventions)
    DB_SYSTEM = "db.system"
    DB_NAME = "db.name"
    DB_OPERATION = "db.operation"
    DB_STATEMENT = "db.statement"
    DB_TABLE = "db.sql.table"
    DB_ROW_COUNT = "db.row_count"

    # Custom DAB attributes - Ingestion
    DAB_CAPSULE_URN = "dab.capsule.urn"
    INGESTION_JOB_ID = "dab.ingestion.job_id"
    INGESTION_SOURCE_TYPE = "dab.ingestion.source_type"
    INGESTION_CAPSULE_COUNT = "dab.ingestion.capsule_count"
    INGESTION_COLUMN_COUNT = "dab.ingestion.column_count"
    INGESTION_EDGE_COUNT = "dab.ingestion.edge_count"

    # Custom DAB attributes - Conformance
    CONFORMANCE_SCOPE = "dab.conformance.scope"
    CONFORMANCE_RULE_COUNT = "dab.conformance.rule_count"
    CONFORMANCE_VIOLATION_COUNT = "dab.conformance.violation_count"
    CONFORMANCE_SCORE = "dab.conformance.score"

    # Custom DAB attributes - Lineage
    LINEAGE_CAPSULE_URN = "dab.lineage.capsule_urn"
    LINEAGE_DIRECTION = "dab.lineage.direction"
    LINEAGE_DEPTH = "dab.lineage.depth"
    LINEAGE_NODE_COUNT = "dab.lineage.node_count"

    # Custom DAB attributes - Capsule
    CAPSULE_URN = "dab.capsule.urn"
    CAPSULE_TYPE = "dab.capsule.type"
    CAPSULE_LAYER = "dab.capsule.layer"
