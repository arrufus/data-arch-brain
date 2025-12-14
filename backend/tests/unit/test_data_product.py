"""Unit tests for DataProduct models."""

import pytest
from datetime import datetime, timezone

from src.models.data_product import (
    CapsuleDataProduct,
    CapsuleRole,
    DataProduct,
    DataProductStatus,
)


class TestDataProductModel:
    """Tests for the DataProduct model."""

    def test_create_data_product_minimal(self):
        """Test creating a data product with minimal fields."""
        product = DataProduct(name="Test Product")

        assert product.name == "Test Product"
        assert product.description is None
        # Note: server_default only applies in DB, not Python object creation
        # Status will be None until inserted into DB
        assert product.version is None
        assert product.slo_freshness_hours is None
        assert product.slo_availability_percent is None
        assert product.slo_quality_threshold is None

    def test_create_data_product_with_slos(self):
        """Test creating a data product with SLO definitions."""
        product = DataProduct(
            name="Analytics Product",
            description="Main analytics data product",
            version="1.0.0",
            status=DataProductStatus.ACTIVE,
            slo_freshness_hours=24,
            slo_availability_percent=99.9,
            slo_quality_threshold=0.95,
        )

        assert product.name == "Analytics Product"
        assert product.status == DataProductStatus.ACTIVE
        assert product.slo_freshness_hours == 24
        assert product.slo_availability_percent == 99.9
        assert product.slo_quality_threshold == 0.95

    def test_create_data_product_with_contract(self):
        """Test creating a data product with contract definitions."""
        output_schema = {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "order_total": {"type": "number"},
            },
        }
        input_sources = [
            "urn:dab:model:raw.customers",
            "urn:dab:model:raw.orders",
        ]

        product = DataProduct(
            name="Customer Orders Product",
            output_port_schema=output_schema,
            input_sources=input_sources,
        )

        assert product.output_port_schema == output_schema
        assert product.input_sources == input_sources
        assert len(product.input_sources) == 2

    def test_data_product_metadata(self):
        """Test data product metadata and tags."""
        product = DataProduct(
            name="Tagged Product",
            meta={"team": "analytics", "cost_center": "12345"},
            tags=["critical", "gdpr", "tier-1"],
        )

        assert product.meta["team"] == "analytics"
        assert "gdpr" in product.tags
        assert len(product.tags) == 3


class TestCapsuleDataProductModel:
    """Tests for the CapsuleDataProduct association model."""

    def test_create_association_default_role(self):
        """Test creating a capsule-product association with default role."""
        # Note: In actual DB tests, we'd need real capsule and product IDs
        from uuid import uuid4

        capsule_id = uuid4()
        product_id = uuid4()

        association = CapsuleDataProduct(
            capsule_id=capsule_id,
            data_product_id=product_id,
        )

        assert association.capsule_id == capsule_id
        assert association.data_product_id == product_id
        # Note: server_default only applies in DB, not Python object creation
        # role will be None until inserted into DB or explicitly set

    def test_create_association_with_role(self):
        """Test creating association with specific role."""
        from uuid import uuid4

        association = CapsuleDataProduct(
            capsule_id=uuid4(),
            data_product_id=uuid4(),
            role=CapsuleRole.OUTPUT,
        )

        assert association.role == CapsuleRole.OUTPUT

    def test_association_with_metadata(self):
        """Test association with additional metadata."""
        from uuid import uuid4

        association = CapsuleDataProduct(
            capsule_id=uuid4(),
            data_product_id=uuid4(),
            role=CapsuleRole.INPUT,
            meta={"added_reason": "Primary data source"},
        )

        assert association.meta["added_reason"] == "Primary data source"


class TestDataProductEnums:
    """Tests for DataProduct related enums."""

    def test_data_product_status_values(self):
        """Test DataProductStatus enum values."""
        assert DataProductStatus.DRAFT == "draft"
        assert DataProductStatus.ACTIVE == "active"
        assert DataProductStatus.DEPRECATED == "deprecated"

    def test_capsule_role_values(self):
        """Test CapsuleRole enum values."""
        assert CapsuleRole.MEMBER == "member"
        assert CapsuleRole.OUTPUT == "output"
        assert CapsuleRole.INPUT == "input"

    def test_status_enum_members(self):
        """Test all status enum members are strings."""
        for status in DataProductStatus:
            assert isinstance(status.value, str)

    def test_role_enum_members(self):
        """Test all role enum members are strings."""
        for role in CapsuleRole:
            assert isinstance(role.value, str)
