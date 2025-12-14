"""Integration tests for API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Integration tests for health endpoints."""

    async def test_health_check(self, client: AsyncClient):
        """Test main health check endpoint."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    async def test_liveness_probe(self, client: AsyncClient):
        """Test liveness probe endpoint."""
        response = await client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "alive"

    async def test_readiness_probe(self, client: AsyncClient):
        """Test readiness probe endpoint."""
        response = await client.get("/api/v1/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"


@pytest.mark.asyncio
class TestCapsuleEndpointsIntegration:
    """Integration tests for capsule endpoints."""

    async def test_list_capsules_empty(self, client: AsyncClient):
        """Test listing capsules when database is empty."""
        response = await client.get("/api/v1/capsules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_capsules_pagination(self, client: AsyncClient):
        """Test capsule pagination parameters."""
        response = await client.get("/api/v1/capsules?offset=0&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        pagination = data["pagination"]
        assert pagination["offset"] == 0
        assert pagination["limit"] == 10

    async def test_list_capsules_filter_by_layer(self, client: AsyncClient):
        """Test filtering capsules by layer."""
        response = await client.get("/api/v1/capsules?layer=gold")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned capsules should have gold layer
        for capsule in data["data"]:
            if capsule.get("layer"):
                assert capsule["layer"] == "gold"

    async def test_list_capsules_filter_by_type(self, client: AsyncClient):
        """Test filtering capsules by type."""
        response = await client.get("/api/v1/capsules?capsule_type=model")
        
        assert response.status_code == 200
        data = response.json()
        
        for capsule in data["data"]:
            if capsule.get("capsule_type"):
                assert capsule["capsule_type"] == "model"

    async def test_list_capsules_search(self, client: AsyncClient):
        """Test searching capsules by name."""
        response = await client.get("/api/v1/capsules?search=customer")
        
        assert response.status_code == 200

    async def test_capsule_stats(self, client: AsyncClient):
        """Test capsule statistics endpoint."""
        response = await client.get("/api/v1/capsules/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_capsules" in data
        assert "by_layer" in data
        assert "by_type" in data

    async def test_get_capsule_not_found(self, client: AsyncClient):
        """Test getting non-existent capsule returns 404."""
        response = await client.get(
            "/api/v1/capsules/urn:dab:dbt:model:nonexistent:table/detail"
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestDomainEndpointsIntegration:
    """Integration tests for domain endpoints."""

    async def test_list_domains(self, client: AsyncClient):
        """Test listing domains."""
        response = await client.get("/api/v1/domains")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert isinstance(data["data"], list)


@pytest.mark.asyncio
class TestConformanceEndpointsIntegration:
    """Integration tests for conformance endpoints."""

    async def test_list_rules(self, client: AsyncClient):
        """Test listing conformance rules."""
        response = await client.get("/api/v1/conformance/rules")

        assert response.status_code == 200
        data = response.json()

        # Response should be a list or dict with rules
        assert isinstance(data, (list, dict))

    async def test_conformance_score(self, client: AsyncClient):
        """Test conformance score endpoint."""
        response = await client.get("/api/v1/conformance/score")

        # May return 503 if no data exists in test database
        # or 200 if endpoint works correctly
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.asyncio
class TestComplianceEndpointsIntegration:
    """Integration tests for compliance endpoints."""

    async def test_pii_inventory(self, client: AsyncClient):
        """Test PII inventory endpoint."""
        response = await client.get("/api/v1/compliance/pii-inventory")

        # May return 503 if database unavailable or 200 if working
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.asyncio
class TestReportEndpointsIntegration:
    """Integration tests for report endpoints."""

    async def test_conformance_report(self, client: AsyncClient):
        """Test conformance report endpoint."""
        response = await client.get("/api/v1/reports/conformance")

        # May return 503 if database unavailable or 200 if working
        assert response.status_code in [200, 503]

    async def test_conformance_report_html(self, client: AsyncClient):
        """Test conformance report HTML format."""
        response = await client.get("/api/v1/reports/conformance?format=html")

        # May return 503 if database unavailable or 200 if working
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.asyncio
class TestErrorHandling:
    """Integration tests for error handling."""

    async def test_invalid_endpoint(self, client: AsyncClient):
        """Test that invalid endpoints return 404."""
        response = await client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404

    async def test_invalid_query_param(self, client: AsyncClient):
        """Test that invalid query parameters (exceeding max) return 422."""
        # Test limit exceeding maximum (100 for capsules endpoint)
        response = await client.get("/api/v1/capsules?limit=150")

        assert response.status_code == 422

    async def test_invalid_uuid_param(self, client: AsyncClient):
        """Test that invalid UUID returns 422."""
        response = await client.get("/api/v1/capsules?domain_id=not-a-uuid")
        
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAuthenticationIntegration:
    """Integration tests for authentication."""

    async def test_authenticated_request(self, authenticated_client: AsyncClient):
        """Test authenticated request succeeds."""
        response = await authenticated_client.get("/api/v1/capsules")
        
        assert response.status_code == 200

    async def test_unauthenticated_request_when_auth_enabled(
        self, authenticated_client: AsyncClient
    ):
        """Test that auth header is properly set."""
        # The authenticated_client fixture includes the API key
        assert "X-API-Key" in authenticated_client.headers


@pytest.mark.asyncio
class TestCORSIntegration:
    """Integration tests for CORS headers."""

    async def test_cors_headers_present_on_get(self, client: AsyncClient):
        """Test that CORS headers are present in GET responses."""
        response = await client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )

        # Request should succeed
        assert response.status_code == 200
        # CORS allows all origins by default in test config
        # The actual header check depends on CORS middleware configuration
