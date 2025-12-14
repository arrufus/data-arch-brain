"""Unit tests for Products API endpoints."""

import pytest
from uuid import uuid4


@pytest.mark.asyncio
class TestProductsListEndpoint:
    """Tests for GET /api/v1/products endpoint."""

    async def test_list_products_empty(self, client):
        """Test listing products when none exist."""
        response = await client.get("/api/v1/products")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["pagination"]["total"] == 0

    async def test_list_products_pagination(self, client):
        """Test products list pagination parameters."""
        response = await client.get("/api/v1/products?offset=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 10


@pytest.mark.asyncio
class TestProductsCreateEndpoint:
    """Tests for POST /api/v1/products endpoint."""

    async def test_create_product_minimal(self, client):
        """Test creating a product with minimal fields."""
        payload = {
            "name": "Test Product",
        }

        response = await client.post("/api/v1/products", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Product"
        assert data["status"] == "draft"
        assert "id" in data

    async def test_create_product_with_slos(self, client):
        """Test creating a product with SLO definitions."""
        payload = {
            "name": "Analytics Product",
            "description": "Main analytics data product",
            "version": "1.0.0",
            "slo": {
                "freshness_hours": 24,
                "availability_percent": 99.9,
                "quality_threshold": 0.95,
            },
        }

        response = await client.post("/api/v1/products", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Analytics Product"
        assert data["slo"]["freshness_hours"] == 24
        assert data["slo"]["availability_percent"] == 99.9
        assert data["slo"]["quality_threshold"] == 0.95

    async def test_create_product_with_tags(self, client):
        """Test creating a product with tags."""
        payload = {
            "name": "Tagged Product",
            "tags": ["critical", "tier-1", "gdpr"],
            "meta": {"team": "analytics"},
        }

        response = await client.post("/api/v1/products", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "critical" in data["tags"]
        assert data["meta"]["team"] == "analytics"

    async def test_create_product_duplicate_name(self, client):
        """Test creating a product with duplicate name fails."""
        payload = {"name": "Duplicate Product"}

        # First create should succeed
        response1 = await client.post("/api/v1/products", json=payload)
        assert response1.status_code == 201

        # Second create should fail
        response2 = await client.post("/api/v1/products", json=payload)
        assert response2.status_code == 409

    async def test_create_product_invalid_name(self, client):
        """Test creating a product with empty name fails."""
        payload = {"name": ""}

        response = await client.post("/api/v1/products", json=payload)

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestProductsGetEndpoint:
    """Tests for GET /api/v1/products/{id} endpoint."""

    async def test_get_product_not_found(self, client):
        """Test getting a non-existent product."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/products/{fake_id}")

        assert response.status_code == 404

    async def test_get_product_success(self, client):
        """Test getting an existing product."""
        # Create a product first
        create_response = await client.post(
            "/api/v1/products",
            json={"name": "Test Product for Get"},
        )
        product_id = create_response.json()["id"]

        # Get the product
        response = await client.get(f"/api/v1/products/{product_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        assert data["name"] == "Test Product for Get"

    async def test_get_product_invalid_uuid(self, client):
        """Test getting a product with invalid UUID format."""
        response = await client.get("/api/v1/products/not-a-uuid")

        assert response.status_code == 422


@pytest.mark.asyncio
class TestProductsUpdateEndpoint:
    """Tests for PUT /api/v1/products/{id} endpoint."""

    async def test_update_product_success(self, client):
        """Test updating a product."""
        # Create a product first
        create_response = await client.post(
            "/api/v1/products",
            json={"name": "Original Name"},
        )
        product_id = create_response.json()["id"]

        # Update the product
        response = await client.put(
            f"/api/v1/products/{product_id}",
            json={
                "name": "Updated Name",
                "description": "New description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    async def test_update_product_slos(self, client):
        """Test updating product SLOs."""
        # Create a product
        create_response = await client.post(
            "/api/v1/products",
            json={"name": "SLO Product"},
        )
        product_id = create_response.json()["id"]

        # Update SLOs
        response = await client.put(
            f"/api/v1/products/{product_id}",
            json={
                "slo": {
                    "freshness_hours": 12,
                    "quality_threshold": 0.99,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["slo"]["freshness_hours"] == 12
        assert data["slo"]["quality_threshold"] == 0.99

    async def test_update_product_not_found(self, client):
        """Test updating a non-existent product."""
        fake_id = str(uuid4())
        response = await client.put(
            f"/api/v1/products/{fake_id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestProductsDeleteEndpoint:
    """Tests for DELETE /api/v1/products/{id} endpoint."""

    async def test_delete_product_success(self, client):
        """Test deleting a product."""
        # Create a product
        create_response = await client.post(
            "/api/v1/products",
            json={"name": "To Delete"},
        )
        product_id = create_response.json()["id"]

        # Delete the product
        response = await client.delete(f"/api/v1/products/{product_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(f"/api/v1/products/{product_id}")
        assert get_response.status_code == 404

    async def test_delete_product_not_found(self, client):
        """Test deleting a non-existent product."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/products/{fake_id}")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestProductsStatsEndpoint:
    """Tests for GET /api/v1/products/stats endpoint."""

    async def test_get_stats_empty(self, client):
        """Test getting stats when no products exist."""
        response = await client.get("/api/v1/products/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_products"] == 0
        assert data["by_status"] == {}

    async def test_get_stats_with_products(self, client):
        """Test getting stats with products."""
        # Create some products
        await client.post("/api/v1/products", json={"name": "Product 1"})
        await client.post(
            "/api/v1/products",
            json={"name": "Product 2", "status": "active"},
        )

        response = await client.get("/api/v1/products/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_products"] == 2


@pytest.mark.asyncio
class TestProductsSLOStatusEndpoint:
    """Tests for GET /api/v1/products/{id}/slo-status endpoint."""

    async def test_slo_status_not_configured(self, client):
        """Test SLO status when no SLOs configured."""
        # Create product without SLOs
        create_response = await client.post(
            "/api/v1/products",
            json={"name": "No SLO Product"},
        )
        product_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/products/{product_id}/slo-status")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "not_configured"

    async def test_slo_status_not_found(self, client):
        """Test SLO status for non-existent product."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/products/{fake_id}/slo-status")

        assert response.status_code == 404
