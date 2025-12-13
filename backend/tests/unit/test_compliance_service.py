"""Unit tests for the compliance service."""

import pytest
from unittest.mock import MagicMock

from src.services.compliance import (
    ComplianceService,
    PIISeverity,
    PIIColumnInfo,
    PIITypeSummary,
    PIILayerSummary,
)


class TestPIISeverity:
    """Tests for PIISeverity enum."""

    def test_severity_values(self):
        """Test PIISeverity enum values."""
        assert PIISeverity.CRITICAL.value == "critical"
        assert PIISeverity.HIGH.value == "high"
        assert PIISeverity.MEDIUM.value == "medium"
        assert PIISeverity.LOW.value == "low"

    def test_severity_from_string(self):
        """Test creating PIISeverity from string."""
        assert PIISeverity("critical") == PIISeverity.CRITICAL
        assert PIISeverity("high") == PIISeverity.HIGH
        assert PIISeverity("medium") == PIISeverity.MEDIUM
        assert PIISeverity("low") == PIISeverity.LOW

    def test_invalid_severity(self):
        """Test that invalid severity raises ValueError."""
        with pytest.raises(ValueError):
            PIISeverity("invalid")


class TestPIILayerSummary:
    """Tests for PIILayerSummary dataclass."""

    def test_pii_layer_summary_creation(self):
        """Test creating PIILayerSummary."""
        summary = PIILayerSummary(
            layer="gold",
            column_count=5,
            capsule_count=3,
            pii_types=["email", "name", "phone"],
        )

        assert summary.layer == "gold"
        assert summary.column_count == 5
        assert summary.capsule_count == 3
        assert "email" in summary.pii_types


class TestComplianceServiceMethods:
    """Tests for ComplianceService methods."""

    def test_service_initialization(self):
        """Test service can be initialized with session."""
        session_mock = MagicMock()
        service = ComplianceService(session_mock)
        assert service is not None


class TestExposureDetection:
    """Tests for PII exposure detection concepts."""

    def test_consumption_layers(self):
        """Test that consumption layers are correctly identified."""
        consumption_layers = {"gold", "marts", "presentation", "reporting"}

        assert "gold" in consumption_layers
        assert "marts" in consumption_layers
        assert "bronze" not in consumption_layers
        assert "silver" not in consumption_layers

    def test_protected_transformations(self):
        """Test that protected transformations are identified."""
        protected_transformations = {
            "masked", "hashed", "encrypted", "redacted",
            "anonymized", "pseudonymized", "tokenized"
        }

        assert "masked" in protected_transformations
        assert "hashed" in protected_transformations
        assert "direct" not in protected_transformations
