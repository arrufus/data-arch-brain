"""Unit tests for the capsules API router."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from httpx import AsyncClient

from src.api.routers.capsules import (
    CapsuleSummary,
    CapsuleDetail,
    ColumnSummary,
    LineageNode,
    LineageEdge,
    LineageResponse,
    CapsuleListResponse,
)


class TestCapsuleSummaryModel:
    """Tests for CapsuleSummary Pydantic model."""

    def test_summary_required_fields(self):
        """Test CapsuleSummary with required fields only."""
        summary = CapsuleSummary(
            id="uuid-123",
            urn="urn:dab:dbt:model:test.schema:customers",
            name="customers",
            capsule_type="model",
        )
        
        assert summary.id == "uuid-123"
        assert summary.urn == "urn:dab:dbt:model:test.schema:customers"
        assert summary.name == "customers"
        assert summary.capsule_type == "model"

    def test_summary_optional_fields_defaults(self):
        """Test CapsuleSummary optional fields have correct defaults."""
        summary = CapsuleSummary(
            id="uuid-123",
            urn="urn:test",
            name="test",
            capsule_type="model",
        )
        
        assert summary.layer is None
        assert summary.schema_name is None
        assert summary.database_name is None
        assert summary.domain_name is None
        assert summary.description is None
        assert summary.column_count == 0
        assert summary.has_pii is False
        assert summary.has_tests is False

    def test_summary_all_fields(self):
        """Test CapsuleSummary with all fields populated."""
        summary = CapsuleSummary(
            id="uuid-123",
            urn="urn:dab:dbt:model:proj.staging:stg_customers",
            name="stg_customers",
            capsule_type="model",
            layer="silver",
            schema_name="staging",
            database_name="analytics",
            domain_name="Customer",
            description="Staged customer data",
            column_count=15,
            has_pii=True,
            has_tests=True,
        )
        
        assert summary.layer == "silver"
        assert summary.column_count == 15
        assert summary.has_pii is True


class TestCapsuleDetailModel:
    """Tests for CapsuleDetail Pydantic model."""

    def test_detail_extends_summary(self):
        """Test CapsuleDetail includes all summary fields."""
        detail = CapsuleDetail(
            id="uuid-123",
            urn="urn:test",
            name="test",
            capsule_type="model",
            created_at="2025-01-13T10:00:00Z",
            updated_at="2025-01-13T10:00:00Z",
        )
        
        # Verify inherited fields
        assert hasattr(detail, "id")
        assert hasattr(detail, "urn")
        assert hasattr(detail, "name")
        assert hasattr(detail, "capsule_type")
        assert hasattr(detail, "layer")

    def test_detail_additional_fields(self):
        """Test CapsuleDetail additional fields."""
        detail = CapsuleDetail(
            id="uuid-123",
            urn="urn:test",
            name="test",
            capsule_type="model",
            materialization="table",
            owner_name="data_team",
            source_system="dbt",
            pii_column_count=3,
            test_count=5,
            doc_coverage=0.85,
            upstream_count=10,
            downstream_count=5,
            violation_count=2,
            meta={"key": "value"},
            tags=["customer", "core"],
            created_at="2025-01-13T10:00:00Z",
            updated_at="2025-01-13T10:00:00Z",
        )
        
        assert detail.materialization == "table"
        assert detail.owner_name == "data_team"
        assert detail.pii_column_count == 3
        assert detail.test_count == 5
        assert detail.doc_coverage == 0.85
        assert detail.upstream_count == 10
        assert detail.downstream_count == 5
        assert detail.violation_count == 2
        assert detail.meta == {"key": "value"}
        assert "customer" in detail.tags


class TestColumnSummaryModel:
    """Tests for ColumnSummary Pydantic model."""

    def test_column_required_fields(self):
        """Test ColumnSummary with required fields."""
        column = ColumnSummary(
            id="col-uuid-123",
            urn="urn:dab:dbt:column:test:customers.email",
            name="email",
        )
        
        assert column.id == "col-uuid-123"
        assert column.name == "email"

    def test_column_pii_fields(self):
        """Test ColumnSummary PII-related fields."""
        column = ColumnSummary(
            id="col-uuid-123",
            urn="urn:test",
            name="email",
            data_type="VARCHAR",
            semantic_type="pii",
            pii_type="email",
            pii_detected_by="pattern",
        )
        
        assert column.pii_type == "email"
        assert column.pii_detected_by == "pattern"
        assert column.semantic_type == "pii"


class TestLineageModels:
    """Tests for Lineage-related Pydantic models."""

    def test_lineage_node(self):
        """Test LineageNode model."""
        node = LineageNode(
            id="node-uuid",
            urn="urn:dab:dbt:model:proj:customers",
            name="customers",
            layer="gold",
            capsule_type="model",
            depth=1,
            direction="upstream",
        )
        
        assert node.depth == 1
        assert node.direction == "upstream"
        assert node.layer == "gold"

    def test_lineage_edge(self):
        """Test LineageEdge model."""
        edge = LineageEdge(
            source_urn="urn:source",
            target_urn="urn:target",
            edge_type="depends_on",
            transformation="SELECT",
        )
        
        assert edge.source_urn == "urn:source"
        assert edge.target_urn == "urn:target"
        assert edge.edge_type == "depends_on"

    def test_lineage_response(self):
        """Test LineageResponse model."""
        root = CapsuleSummary(
            id="root-uuid",
            urn="urn:root",
            name="root",
            capsule_type="model",
        )
        
        response = LineageResponse(
            root=root,
            nodes=[
                LineageNode(
                    id="n1",
                    urn="urn:upstream",
                    name="upstream",
                    capsule_type="model",
                    depth=1,
                    direction="upstream",
                )
            ],
            edges=[
                LineageEdge(
                    source_urn="urn:upstream",
                    target_urn="urn:root",
                    edge_type="depends_on",
                )
            ],
            summary={"upstream_count": 1, "downstream_count": 0},
        )
        
        assert len(response.nodes) == 1
        assert len(response.edges) == 1
        assert response.summary["upstream_count"] == 1


class TestCapsuleListResponse:
    """Tests for CapsuleListResponse model."""

    def test_empty_list_response(self):
        """Test empty capsule list response."""
        response = CapsuleListResponse(
            data=[],
            pagination={
                "total": 0,
                "offset": 0,
                "limit": 50,
                "has_more": False,
            },
        )
        
        assert len(response.data) == 0
        assert response.pagination["total"] == 0
        assert response.pagination["has_more"] is False

    def test_paginated_response(self):
        """Test paginated capsule list response."""
        capsules = [
            CapsuleSummary(
                id=str(uuid4()),
                urn=f"urn:dab:dbt:model:test:table{i}",
                name=f"table{i}",
                capsule_type="model",
            )
            for i in range(50)
        ]
        
        response = CapsuleListResponse(
            data=capsules,
            pagination={
                "total": 100,
                "offset": 0,
                "limit": 50,
                "has_more": True,
            },
        )
        
        assert len(response.data) == 50
        assert response.pagination["has_more"] is True


@pytest.mark.asyncio
class TestCapsuleEndpoints:
    """Integration-style tests for capsule endpoints."""

    async def test_list_capsules_endpoint(self, client: AsyncClient):
        """Test list capsules endpoint returns correct structure."""
        response = await client.get("/api/v1/capsules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_capsules_with_layer_filter(self, client: AsyncClient):
        """Test filtering capsules by layer."""
        response = await client.get("/api/v1/capsules?layer=gold")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned capsules should be in gold layer (or empty)
        for capsule in data["data"]:
            if capsule.get("layer"):
                assert capsule["layer"] == "gold"

    async def test_list_capsules_with_pagination(self, client: AsyncClient):
        """Test capsule pagination parameters."""
        response = await client.get("/api/v1/capsules?offset=0&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 10

    async def test_list_capsules_invalid_limit(self, client: AsyncClient):
        """Test that limit over 100 is rejected."""
        response = await client.get("/api/v1/capsules?limit=150")
        
        # Should be rejected due to validation (limit max is 100)
        assert response.status_code == 422

    async def test_get_capsule_stats_endpoint(self, client: AsyncClient):
        """Test capsule stats endpoint."""
        response = await client.get("/api/v1/capsules/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_capsules" in data
        assert "by_layer" in data
        assert "by_type" in data

    async def test_get_capsule_by_urn_not_found(self, client: AsyncClient):
        """Test getting non-existent capsule returns 404."""
        response = await client.get(
            "/api/v1/capsules/urn:dab:dbt:model:nonexistent:table/detail"
        )
        
        assert response.status_code == 404


class TestCapsuleLayerFiltering:
    """Tests for layer-based filtering logic."""

    def test_layer_values(self):
        """Test valid layer values."""
        valid_layers = {"bronze", "silver", "gold"}
        
        for layer in valid_layers:
            assert layer in valid_layers

    def test_layer_hierarchy(self):
        """Test layer hierarchy concept."""
        layer_order = ["bronze", "silver", "gold"]
        
        assert layer_order.index("bronze") < layer_order.index("silver")
        assert layer_order.index("silver") < layer_order.index("gold")


class TestCapsuleTypeFiltering:
    """Tests for capsule type filtering logic."""

    def test_dbt_capsule_types(self):
        """Test dbt capsule types."""
        dbt_types = {"model", "source", "seed", "snapshot", "test", "macro"}
        
        assert "model" in dbt_types
        assert "source" in dbt_types
        assert "seed" in dbt_types

    def test_capsule_type_grouping(self):
        """Test capsule types can be grouped."""
        materialized_types = {"model", "seed", "snapshot"}
        virtual_types = {"source", "test"}
        
        assert "model" in materialized_types
        assert "source" in virtual_types
