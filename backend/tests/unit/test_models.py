"""Tests for database models."""

import pytest
from uuid import uuid4

from src.models import (
    Capsule,
    CapsuleType,
    Column,
    SemanticType,
    PIIType,
    ArchitectureLayer,
)


class TestCapsuleModel:
    """Tests for Capsule model."""

    def test_capsule_type_enum(self) -> None:
        """Test CapsuleType enum values."""
        assert CapsuleType.MODEL.value == "model"
        assert CapsuleType.SOURCE.value == "source"
        assert CapsuleType.SEED.value == "seed"
        assert CapsuleType.SNAPSHOT.value == "snapshot"

    def test_architecture_layer_enum(self) -> None:
        """Test ArchitectureLayer enum values."""
        assert ArchitectureLayer.BRONZE.value == "bronze"
        assert ArchitectureLayer.SILVER.value == "silver"
        assert ArchitectureLayer.GOLD.value == "gold"


class TestColumnModel:
    """Tests for Column model."""

    def test_semantic_type_enum(self) -> None:
        """Test SemanticType enum values."""
        assert SemanticType.PII.value == "pii"
        assert SemanticType.BUSINESS_KEY.value == "business_key"
        assert SemanticType.TIMESTAMP.value == "timestamp"

    def test_pii_type_enum(self) -> None:
        """Test PIIType enum values."""
        assert PIIType.EMAIL.value == "email"
        assert PIIType.SSN.value == "ssn"
        assert PIIType.PHONE.value == "phone"
        assert PIIType.CREDIT_CARD.value == "credit_card"
