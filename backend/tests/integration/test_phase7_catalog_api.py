"""Integration tests for Phase 7 Catalog API endpoints."""

import os

import pytest
from httpx import AsyncClient

# Catalog endpoints require PostgreSQL (materialized views not supported in SQLite)
pytestmark = pytest.mark.skipif(
    "sqlite" in os.environ.get("DATABASE_URL", "sqlite"),
    reason="Catalog materialized views require PostgreSQL"
)


@pytest.mark.asyncio
class TestCatalogAPI:
    """Integration tests for catalog endpoints."""

    async def test_list_capsule_catalog_empty(self, client: AsyncClient):
        """Test listing capsule catalog when database is empty."""
        response = await client.get("/api/v1/catalog/capsules")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_capsule_catalog_filter_by_layer(self, client: AsyncClient):
        """Test filtering capsule catalog by layer."""
        response = await client.get("/api/v1/catalog/capsules?layer=bronze")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_catalog_filter_by_type(self, client: AsyncClient):
        """Test filtering capsule catalog by capsule type."""
        response = await client.get("/api/v1/catalog/capsules?capsule_type=table")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_catalog_filter_by_contract_status(self, client: AsyncClient):
        """Test filtering capsule catalog by contract status."""
        response = await client.get("/api/v1/catalog/capsules?contract_status=active")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_catalog_filter_has_quality_rules(self, client: AsyncClient):
        """Test filtering capsule catalog by presence of quality rules."""
        response = await client.get("/api/v1/catalog/capsules?has_quality_rules=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_catalog_filter_has_masking_rules(self, client: AsyncClient):
        """Test filtering capsule catalog by presence of masking rules."""
        response = await client.get("/api/v1/catalog/capsules?has_masking_rules=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_catalog_pagination(self, client: AsyncClient):
        """Test capsule catalog pagination."""
        response = await client.get("/api/v1/catalog/capsules?offset=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 10

    async def test_list_capsule_catalog_response_structure(self, client: AsyncClient):
        """Test capsule catalog response structure."""
        response = await client.get("/api/v1/catalog/capsules")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data

        # If there are capsules, check structure
        if data["data"]:
            capsule = data["data"][0]
            assert "id" in capsule
            assert "urn" in capsule
            assert "name" in capsule
            assert "column_count" in capsule
            assert "quality_rule_count" in capsule
            assert "version_count" in capsule
            assert "upstream_count" in capsule
            assert "downstream_count" in capsule

    async def test_list_column_catalog_empty(self, client: AsyncClient):
        """Test listing column catalog when database is empty."""
        response = await client.get("/api/v1/catalog/columns")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_column_catalog_filter_by_capsule_id(self, client: AsyncClient):
        """Test filtering column catalog by capsule ID."""
        # Use a random UUID
        capsule_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/catalog/columns?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_column_catalog_filter_by_data_type(self, client: AsyncClient):
        """Test filtering column catalog by data type."""
        response = await client.get("/api/v1/catalog/columns?data_type=VARCHAR")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_column_catalog_filter_primary_keys(self, client: AsyncClient):
        """Test filtering column catalog for primary keys."""
        response = await client.get("/api/v1/catalog/columns?is_primary_key=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_column_catalog_filter_has_masking_rules(self, client: AsyncClient):
        """Test filtering column catalog by presence of masking rules."""
        response = await client.get("/api/v1/catalog/columns?has_masking_rules=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_column_catalog_pagination(self, client: AsyncClient):
        """Test column catalog pagination."""
        response = await client.get("/api/v1/catalog/columns?offset=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 10

    async def test_list_column_catalog_response_structure(self, client: AsyncClient):
        """Test column catalog response structure."""
        response = await client.get("/api/v1/catalog/columns")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data

        # If there are columns, check structure
        if data["data"]:
            column = data["data"][0]
            assert "id" in column
            assert "urn" in column
            assert "name" in column
            assert "data_type" in column
            assert "capsule_id" in column
            assert "capsule_urn" in column
            assert "capsule_name" in column
            assert "is_primary_key" in column
            assert "business_term_count" in column
            assert "masking_rule_count" in column

    async def test_refresh_catalog_views(self, client: AsyncClient):
        """Test refreshing catalog materialized views."""
        response = await client.post("/api/v1/catalog/refresh")

        assert response.status_code == 204

    async def test_catalog_endpoints_with_multiple_filters(self, client: AsyncClient):
        """Test catalog endpoints with multiple filters combined."""
        response = await client.get(
            "/api/v1/catalog/capsules?"
            "layer=bronze&"
            "has_quality_rules=true&"
            "has_masking_rules=false&"
            "offset=0&"
            "limit=20"
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["limit"] == 20
