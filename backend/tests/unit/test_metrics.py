"""Tests for the metrics module."""

import pytest
from src.metrics import (
    MetricsRegistry,
    get_metrics,
    record_capsule_counts,
    record_pii_counts,
    record_conformance_scores,
    record_cache_hit,
    record_cache_miss,
)


class TestMetricsRegistry:
    """Tests for the MetricsRegistry class."""

    def test_counter_increment(self):
        """Test incrementing a counter."""
        registry = MetricsRegistry(prefix="test")
        registry.inc_counter("test_counter")
        assert registry.get_counter("test_counter") == 1
        
        registry.inc_counter("test_counter", 5)
        assert registry.get_counter("test_counter") == 6

    def test_counter_with_labels(self):
        """Test counter with labels."""
        registry = MetricsRegistry(prefix="test")
        registry.inc_counter("test_counter", status="success")
        registry.inc_counter("test_counter", status="error")
        
        assert registry.get_counter("test_counter", status="success") == 1
        assert registry.get_counter("test_counter", status="error") == 1

    def test_gauge_set(self):
        """Test setting a gauge value."""
        registry = MetricsRegistry(prefix="test")
        registry.set_gauge("test_gauge", 42.5)
        assert registry.get_gauge("test_gauge") == 42.5

    def test_gauge_increment_decrement(self):
        """Test incrementing and decrementing a gauge."""
        registry = MetricsRegistry(prefix="test")
        registry.set_gauge("test_gauge", 10.0)
        
        registry.inc_gauge("test_gauge", 5)
        assert registry.get_gauge("test_gauge") == 15.0
        
        registry.dec_gauge("test_gauge", 3)
        assert registry.get_gauge("test_gauge") == 12.0

    def test_histogram_observation(self):
        """Test histogram observations."""
        registry = MetricsRegistry(prefix="test")
        registry.observe_histogram("test_hist", 0.5)
        registry.observe_histogram("test_hist", 1.0)
        registry.observe_histogram("test_hist", 1.5)
        
        metrics = registry.get_all_metrics()
        # Key includes label dict representation
        hist_key = [k for k in metrics["histograms"].keys() if "test_hist" in k][0]
        hist_data = metrics["histograms"][hist_key]
        
        assert hist_data["count"] == 3
        assert hist_data["sum"] == 3.0
        assert hist_data["min"] == 0.5
        assert hist_data["max"] == 1.5

    def test_time_histogram_context_manager(self):
        """Test timing with histogram context manager."""
        registry = MetricsRegistry(prefix="test")
        
        with registry.time_histogram("test_timer"):
            # Simulate some work
            pass
        
        metrics = registry.get_all_metrics()
        # Check that some timer key exists
        assert any("test_timer" in k for k in metrics["histograms"])

    def test_get_all_metrics(self):
        """Test getting all metrics as dict."""
        registry = MetricsRegistry(prefix="test")
        registry.inc_counter("counter1")
        registry.set_gauge("gauge1", 100)
        registry.observe_histogram("hist1", 0.1)
        
        metrics = registry.get_all_metrics()
        
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics


class TestMetricHelpers:
    """Tests for metric helper functions."""

    def test_record_capsule_counts(self):
        """Test recording capsule counts."""
        # This should not raise
        record_capsule_counts({"model": 10, "source": 5})

    def test_record_pii_counts(self):
        """Test recording PII counts."""
        record_pii_counts({"email": 3, "phone": 2})

    def test_record_conformance_scores(self):
        """Test recording conformance scores."""
        record_conformance_scores({"bronze": 85.0, "silver": 90.0, "gold": 95.0})

    def test_record_cache_hit(self):
        """Test recording cache hit."""
        record_cache_hit("conformance")

    def test_record_cache_miss(self):
        """Test recording cache miss."""
        record_cache_miss("pii_inventory")


class TestGetMetrics:
    """Tests for global metrics getter."""

    def test_get_metrics_returns_singleton(self):
        """Test that get_metrics returns a singleton."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        assert metrics1 is metrics2

    def test_metrics_prefix(self):
        """Test that metrics have correct prefix."""
        metrics = get_metrics()
        assert metrics.prefix == "dab"  # From settings
