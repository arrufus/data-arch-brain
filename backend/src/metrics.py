"""Prometheus metrics for Data Architecture Brain.

Provides application-level metrics for monitoring and observability.
Includes both standard HTTP metrics and custom business metrics.
"""

from typing import Any, Callable, Optional
from functools import wraps
import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Global metrics registry
_metrics: Optional["MetricsRegistry"] = None


class MetricsRegistry:
    """
    Simple metrics registry that works without prometheus_client.
    When prometheus_fastapi_instrumentator is available, it provides richer metrics.
    """

    def __init__(self, prefix: str = "dab"):
        self.prefix = prefix
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._instrumentator: Optional[Any] = None
        self._prom_counters: dict[str, Any] = {}
        self._prom_gauges: dict[str, Any] = {}
        self._prom_histograms: dict[str, Any] = {}

    def _init_prometheus(self) -> bool:
        """Try to initialize prometheus_client metrics."""
        try:
            from prometheus_client import Counter, Gauge, Histogram, REGISTRY
            
            # Business metrics
            self._prom_counters["ingestion_total"] = Counter(
                f"{self.prefix}_ingestion_total",
                "Total number of ingestion jobs",
                ["status", "source_type"],
            )
            self._prom_counters["capsules_ingested"] = Counter(
                f"{self.prefix}_capsules_ingested_total",
                "Total number of capsules ingested",
                ["capsule_type", "layer"],
            )
            self._prom_counters["conformance_evaluations"] = Counter(
                f"{self.prefix}_conformance_evaluations_total",
                "Total number of conformance evaluations",
                ["scope"],  # full, by_layer, single_capsule
            )
            self._prom_counters["pii_queries"] = Counter(
                f"{self.prefix}_pii_queries_total",
                "Total number of PII inventory queries",
            )
            self._prom_counters["cache_hits"] = Counter(
                f"{self.prefix}_cache_hits_total",
                "Total number of cache hits",
                ["cache_type"],
            )
            self._prom_counters["cache_misses"] = Counter(
                f"{self.prefix}_cache_misses_total",
                "Total number of cache misses",
                ["cache_type"],
            )
            
            # Gauges
            self._prom_gauges["capsule_count"] = Gauge(
                f"{self.prefix}_capsule_count",
                "Current number of capsules in the database",
                ["capsule_type"],
            )
            self._prom_gauges["pii_column_count"] = Gauge(
                f"{self.prefix}_pii_column_count",
                "Current number of PII columns",
                ["pii_type"],
            )
            self._prom_gauges["conformance_score"] = Gauge(
                f"{self.prefix}_conformance_score",
                "Current conformance score (0-100)",
                ["layer"],
            )
            self._prom_gauges["active_ingestion_jobs"] = Gauge(
                f"{self.prefix}_active_ingestion_jobs",
                "Number of currently running ingestion jobs",
            )
            
            # Histograms
            self._prom_histograms["ingestion_duration"] = Histogram(
                f"{self.prefix}_ingestion_duration_seconds",
                "Ingestion job duration in seconds",
                ["source_type"],
                buckets=[1, 5, 10, 30, 60, 120, 300, 600],
            )
            self._prom_histograms["conformance_evaluation_duration"] = Histogram(
                f"{self.prefix}_conformance_evaluation_duration_seconds",
                "Conformance evaluation duration in seconds",
                ["scope"],
                buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
            )
            self._prom_histograms["lineage_query_duration"] = Histogram(
                f"{self.prefix}_lineage_query_duration_seconds",
                "Lineage query duration in seconds",
                ["direction"],  # upstream, downstream
                buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5],
            )
            self._prom_histograms["db_query_duration"] = Histogram(
                f"{self.prefix}_db_query_duration_seconds",
                "Database query duration in seconds",
                ["operation"],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1],
            )
            
            logger.info("Prometheus metrics initialized")
            return True
        except ImportError:
            logger.warning("prometheus_client not installed, using basic metrics")
            return False

    # Counter methods
    def inc_counter(self, name: str, value: int = 1, **labels: str) -> None:
        """Increment a counter."""
        if name in self._prom_counters:
            if labels:
                self._prom_counters[name].labels(**labels).inc(value)
            else:
                self._prom_counters[name].inc(value)
        else:
            key = f"{name}:{labels}" if labels else name
            self._counters[key] = self._counters.get(key, 0) + value

    def get_counter(self, name: str, **labels: str) -> int:
        """Get counter value."""
        key = f"{name}:{labels}" if labels else name
        return self._counters.get(key, 0)

    # Gauge methods
    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        """Set a gauge value."""
        if name in self._prom_gauges:
            if labels:
                self._prom_gauges[name].labels(**labels).set(value)
            else:
                self._prom_gauges[name].set(value)
        else:
            key = f"{name}:{labels}" if labels else name
            self._gauges[key] = value

    def inc_gauge(self, name: str, value: float = 1, **labels: str) -> None:
        """Increment a gauge."""
        if name in self._prom_gauges:
            if labels:
                self._prom_gauges[name].labels(**labels).inc(value)
            else:
                self._prom_gauges[name].inc(value)
        else:
            key = f"{name}:{labels}" if labels else name
            self._gauges[key] = self._gauges.get(key, 0) + value

    def dec_gauge(self, name: str, value: float = 1, **labels: str) -> None:
        """Decrement a gauge."""
        if name in self._prom_gauges:
            if labels:
                self._prom_gauges[name].labels(**labels).dec(value)
            else:
                self._prom_gauges[name].dec(value)
        else:
            key = f"{name}:{labels}" if labels else name
            self._gauges[key] = self._gauges.get(key, 0) - value

    def get_gauge(self, name: str, **labels: str) -> float:
        """Get gauge value."""
        key = f"{name}:{labels}" if labels else name
        return self._gauges.get(key, 0.0)

    # Histogram methods
    def observe_histogram(self, name: str, value: float, **labels: str) -> None:
        """Record a histogram observation."""
        if name in self._prom_histograms:
            if labels:
                self._prom_histograms[name].labels(**labels).observe(value)
            else:
                self._prom_histograms[name].observe(value)
        else:
            key = f"{name}:{labels}" if labels else name
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def time_histogram(self, name: str, **labels: str):
        """Context manager to time a block and record in histogram."""
        outer_self = self
        
        class Timer:
            def __init__(self):
                self.start: float = 0.0

            def __enter__(self):
                self.start = time.perf_counter()
                return self

            def __exit__(self, *args):
                duration = time.perf_counter() - self.start
                outer_self.observe_histogram(name, duration, **labels)

        return Timer()

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary (for basic metrics endpoint)."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                }
                for k, v in self._histograms.items()
            },
        }


def get_metrics() -> MetricsRegistry:
    """Get the global metrics registry."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsRegistry(prefix=settings.metrics_prefix)
    return _metrics


def configure_prometheus_metrics(app: FastAPI) -> None:
    """
    Configure Prometheus metrics for the FastAPI application.
    
    Uses prometheus-fastapi-instrumentator if available for comprehensive
    HTTP metrics, with custom business metrics added.
    """
    if not settings.metrics_enabled:
        logger.info("Metrics disabled")
        return
    
    metrics = get_metrics()
    
    # Try to use prometheus-fastapi-instrumentator for comprehensive HTTP metrics
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        from prometheus_fastapi_instrumentator.metrics import Info
        
        # Initialize instrumentator
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health/live"],
            env_var_name="ENABLE_METRICS",
            inprogress_name=f"{settings.metrics_prefix}_http_requests_inprogress",
            inprogress_labels=True,
        )
        
        # Add default metrics
        instrumentator.add(
            request_size(metric_namespace=settings.metrics_prefix)
        ).add(
            response_size(metric_namespace=settings.metrics_prefix)
        ).add(
            latency_histogram(metric_namespace=settings.metrics_prefix)
        )
        
        # Instrument the app and expose /metrics endpoint
        instrumentator.instrument(app).expose(
            app, 
            include_in_schema=True,
            endpoint="/metrics",
            tags=["monitoring"],
        )
        
        metrics._instrumentator = instrumentator
        logger.info("Prometheus HTTP metrics enabled via instrumentator")
        
    except ImportError:
        logger.warning(
            "prometheus-fastapi-instrumentator not installed, "
            "using basic metrics endpoint"
        )
        # Add a basic metrics endpoint
        from fastapi.responses import PlainTextResponse
        
        @app.get("/metrics", tags=["monitoring"], include_in_schema=True)
        async def basic_metrics() -> PlainTextResponse:
            """Basic metrics endpoint (Prometheus format not available)."""
            all_metrics = metrics.get_all_metrics()
            lines = []
            
            for name, value in all_metrics["counters"].items():
                lines.append(f"{settings.metrics_prefix}_{name} {value}")
            for name, value in all_metrics["gauges"].items():
                lines.append(f"{settings.metrics_prefix}_{name} {value}")
            for name, hist in all_metrics["histograms"].items():
                lines.append(f"{settings.metrics_prefix}_{name}_count {hist['count']}")
                lines.append(f"{settings.metrics_prefix}_{name}_sum {hist['sum']}")
            
            return PlainTextResponse("\n".join(lines))
    
    # Initialize custom prometheus metrics
    metrics._init_prometheus()


# Metric helper functions for instrumentator
def request_size(metric_namespace: str = "dab"):
    """Request size metric."""
    def instrumentation(info: Any) -> None:
        pass  # Will be handled by instrumentator
    return instrumentation


def response_size(metric_namespace: str = "dab"):
    """Response size metric."""
    def instrumentation(info: Any) -> None:
        pass  # Will be handled by instrumentator
    return instrumentation


def latency_histogram(metric_namespace: str = "dab"):
    """Latency histogram metric."""
    def instrumentation(info: Any) -> None:
        pass  # Will be handled by instrumentator
    return instrumentation


# Decorators for tracking business metrics
def track_ingestion(source_type: str = "dbt"):
    """Decorator to track ingestion metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics()
            metrics.inc_gauge("active_ingestion_jobs")
            
            try:
                with metrics.time_histogram("ingestion_duration", source_type=source_type):
                    result = await func(*args, **kwargs)
                metrics.inc_counter("ingestion_total", status="success", source_type=source_type)
                return result
            except Exception as e:
                metrics.inc_counter("ingestion_total", status="error", source_type=source_type)
                raise
            finally:
                metrics.dec_gauge("active_ingestion_jobs")
        
        return wrapper
    return decorator


def track_conformance_evaluation(scope: str = "full"):
    """Decorator to track conformance evaluation metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics()
            
            with metrics.time_histogram("conformance_evaluation_duration", scope=scope):
                result = await func(*args, **kwargs)
            
            metrics.inc_counter("conformance_evaluations", scope=scope)
            return result
        
        return wrapper
    return decorator


def track_lineage_query(direction: str = "upstream"):
    """Decorator to track lineage query metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics()
            
            with metrics.time_histogram("lineage_query_duration", direction=direction):
                result = await func(*args, **kwargs)
            
            return result
        
        return wrapper
    return decorator


def track_db_query(operation: str = "select"):
    """Decorator to track database query metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics()
            
            with metrics.time_histogram("db_query_duration", operation=operation):
                result = await func(*args, **kwargs)
            
            return result
        
        return wrapper
    return decorator


# Utility functions for updating business metrics
def record_capsule_counts(counts_by_type: dict[str, int]) -> None:
    """Record capsule counts by type."""
    metrics = get_metrics()
    for capsule_type, count in counts_by_type.items():
        metrics.set_gauge("capsule_count", count, capsule_type=capsule_type)


def record_pii_counts(counts_by_type: dict[str, int]) -> None:
    """Record PII column counts by type."""
    metrics = get_metrics()
    for pii_type, count in counts_by_type.items():
        metrics.set_gauge("pii_column_count", count, pii_type=pii_type)


def record_conformance_scores(scores_by_layer: dict[str, float]) -> None:
    """Record conformance scores by layer."""
    metrics = get_metrics()
    for layer, score in scores_by_layer.items():
        metrics.set_gauge("conformance_score", score, layer=layer)


def record_cache_hit(cache_type: str = "general") -> None:
    """Record a cache hit."""
    get_metrics().inc_counter("cache_hits", cache_type=cache_type)


def record_cache_miss(cache_type: str = "general") -> None:
    """Record a cache miss."""
    get_metrics().inc_counter("cache_misses", cache_type=cache_type)
