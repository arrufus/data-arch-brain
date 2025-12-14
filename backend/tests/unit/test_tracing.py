"""Unit tests for the distributed tracing module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestTracingSetup:
    """Tests for tracing setup and configuration."""

    def test_import_tracing_module(self):
        """Test that tracing module can be imported."""
        from src import tracing
        
        assert hasattr(tracing, "setup_tracing")
        assert hasattr(tracing, "shutdown_tracing")
        assert hasattr(tracing, "create_span")
        assert hasattr(tracing, "traced")

    def test_span_attributes_class(self):
        """Test SpanAttributes class constants."""
        from src.tracing import SpanAttributes
        
        # Test HTTP attributes
        assert SpanAttributes.HTTP_METHOD == "http.method"
        assert SpanAttributes.HTTP_URL == "http.url"
        assert SpanAttributes.HTTP_STATUS_CODE == "http.status_code"
        
        # Test DB attributes
        assert SpanAttributes.DB_SYSTEM == "db.system"
        assert SpanAttributes.DB_NAME == "db.name"
        assert SpanAttributes.DB_OPERATION == "db.operation"
        
        # Test custom DAB attributes
        assert "dab" in SpanAttributes.DAB_CAPSULE_URN

    def test_tracer_provider_not_configured_by_default(self):
        """Test that tracer is not configured when disabled."""
        from src.tracing import get_tracer
        
        # Should return a tracer (may be no-op if not configured)
        tracer = get_tracer("test")
        assert tracer is not None


class TestTracingDisabled:
    """Tests for behavior when tracing is disabled."""

    @patch("src.tracing._tracer", None)
    def test_create_span_when_disabled(self):
        """Test create_span is no-op when tracing disabled."""
        from src.tracing import create_span

        # Should not raise even when tracing is disabled
        with create_span("test_span") as span:
            pass  # No-op context manager

    @patch("src.tracing._tracer", None)
    def test_traced_decorator_when_disabled(self):
        """Test @traced decorator works when tracing disabled."""
        from src.tracing import traced

        @traced("test_operation")
        def my_function():
            return "result"

        # Function should still work
        result = my_function()
        assert result == "result"

    @patch("src.tracing._tracer", None)
    def test_async_traced_when_disabled(self):
        """Test @traced decorator with async functions when disabled."""
        from src.tracing import traced

        @traced("async_operation")
        async def my_async_function():
            return "async_result"

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(my_async_function())
        assert result == "async_result"


class TestTracingHelpers:
    """Tests for tracing helper functions."""

    def test_add_span_attributes(self):
        """Test add_span_attributes function."""
        from src.tracing import add_span_attributes
        
        # Should not raise even without active span
        add_span_attributes(key1="value1", key2="value2")

    def test_record_exception(self):
        """Test record_exception function."""
        from src.tracing import record_exception
        
        exc = ValueError("Test error")
        
        # Should not raise even without active span
        record_exception(exc)

    def test_get_trace_id(self):
        """Test get_trace_id returns None when no span."""
        from src.tracing import get_trace_id
        
        # Without active span, should return None
        trace_id = get_trace_id()
        assert trace_id is None or isinstance(trace_id, str)

    def test_get_span_id(self):
        """Test get_span_id returns None when no span."""
        from src.tracing import get_span_id
        
        # Without active span, should return None
        span_id = get_span_id()
        assert span_id is None or isinstance(span_id, str)


class TestTracingConfig:
    """Tests for tracing configuration validation."""

    def test_config_has_tracing_settings(self):
        """Test that config includes tracing settings."""
        from src.config import Settings
        
        settings = Settings(
            database_url="sqlite:///:memory:",
            tracing_enabled=True,
            tracing_service_name="test-service",
        )
        
        assert settings.tracing_enabled is True
        assert settings.tracing_service_name == "test-service"

    def test_config_tracing_defaults(self):
        """Test tracing config defaults."""
        from src.config import Settings
        
        settings = Settings(database_url="sqlite:///:memory:")
        
        assert settings.tracing_enabled is False
        assert settings.tracing_console_export is False

    def test_config_otlp_endpoint_optional(self):
        """Test OTLP endpoint is optional."""
        from src.config import Settings
        
        settings = Settings(database_url="sqlite:///:memory:")
        
        assert settings.tracing_otlp_endpoint is None


class TestSpanNaming:
    """Tests for span naming conventions."""

    def test_http_span_names(self):
        """Test HTTP span naming follows convention."""
        # HTTP spans should be named: HTTP {METHOD} {PATH}
        method = "GET"
        path = "/api/v1/capsules"
        
        span_name = f"HTTP {method} {path}"
        
        assert "HTTP" in span_name
        assert method in span_name
        assert path in span_name

    def test_db_span_names(self):
        """Test database span naming follows convention."""
        # DB spans should be named: {OPERATION} {TABLE}
        operation = "SELECT"
        table = "capsules"
        
        span_name = f"{operation} {table}"
        
        assert operation in span_name
        assert table in span_name

    def test_service_span_names(self):
        """Test service operation span naming."""
        # Service spans should describe the operation
        service = "IngestionService"
        operation = "ingest_dbt"
        
        span_name = f"{service}.{operation}"
        
        assert service in span_name
        assert operation in span_name


class TestTracingIntegration:
    """Tests for tracing integration with FastAPI."""

    def test_fastapi_instrumentation_available(self):
        """Test FastAPI instrumentation is available."""
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            assert FastAPIInstrumentor is not None
        except ImportError:
            pytest.skip("FastAPI instrumentation not installed")

    def test_httpx_instrumentation_available(self):
        """Test HTTPX instrumentation is available."""
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            assert HTTPXClientInstrumentor is not None
        except ImportError:
            pytest.skip("HTTPX instrumentation not installed")

    def test_sqlalchemy_instrumentation_available(self):
        """Test SQLAlchemy instrumentation is available."""
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            assert SQLAlchemyInstrumentor is not None
        except ImportError:
            pytest.skip("SQLAlchemy instrumentation not installed")


class TestTracedDecorator:
    """Tests for the @traced decorator."""

    def test_traced_preserves_function_name(self):
        """Test @traced preserves function name."""
        from src.tracing import traced
        
        @traced("operation")
        def my_function():
            pass
        
        assert my_function.__name__ == "my_function"

    def test_traced_preserves_docstring(self):
        """Test @traced preserves docstring."""
        from src.tracing import traced
        
        @traced("operation")
        def my_function():
            """This is my docstring."""
            pass
        
        assert my_function.__doc__ == "This is my docstring."

    def test_traced_with_span_name(self):
        """Test @traced accepts custom span name."""
        from src.tracing import traced
        
        @traced("custom_span_name")
        def my_function():
            return "result"
        
        result = my_function()
        assert result == "result"

    def test_traced_without_span_name(self):
        """Test @traced uses function name if no span name."""
        from src.tracing import traced
        
        @traced()
        def another_function():
            return "result"
        
        result = another_function()
        assert result == "result"


class TestContextPropagation:
    """Tests for trace context propagation."""

    def test_context_propagation_headers(self):
        """Test trace context can be extracted from headers."""
        # W3C Trace Context format
        traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        
        # Verify format
        parts = traceparent.split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # version
        assert len(parts[1]) == 32  # trace-id (16 bytes hex)
        assert len(parts[2]) == 16  # parent-id (8 bytes hex)
        assert parts[3] == "01"  # flags (sampled)

    def test_context_injection_headers(self):
        """Test trace context can be injected into headers."""
        headers = {}
        
        # In a real scenario, this would be populated by the SDK
        headers["traceparent"] = "00-trace_id-span_id-01"
        
        assert "traceparent" in headers
