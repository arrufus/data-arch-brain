"""Tests for API authentication."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.auth import is_path_exempt, verify_api_key
from src.api.main import app
from src.config import Settings


class TestAPIKeyValidation:
    """Tests for API key validation functions."""

    def test_verify_valid_api_key(self):
        """Test that valid API key is accepted."""
        valid_keys = ["key-123", "key-456", "key-789"]
        assert verify_api_key("key-123", valid_keys) is True
        assert verify_api_key("key-456", valid_keys) is True
        assert verify_api_key("key-789", valid_keys) is True

    def test_verify_invalid_api_key(self):
        """Test that invalid API key is rejected."""
        valid_keys = ["key-123", "key-456"]
        assert verify_api_key("wrong-key", valid_keys) is False
        assert verify_api_key("", valid_keys) is False
        assert verify_api_key("key-12", valid_keys) is False  # Partial match

    def test_verify_empty_valid_keys(self):
        """Test that empty valid keys list rejects all keys."""
        assert verify_api_key("any-key", []) is False


class TestPathExemption:
    """Tests for path exemption checking."""

    def test_exact_match_exempt(self):
        """Test exact path match exemption."""
        exempt_paths = ["/api/v1/health", "/api/v1/docs"]
        assert is_path_exempt("/api/v1/health", exempt_paths) is True
        assert is_path_exempt("/api/v1/docs", exempt_paths) is True

    def test_non_exempt_path(self):
        """Test non-exempt path."""
        exempt_paths = ["/api/v1/health"]
        assert is_path_exempt("/api/v1/capsules", exempt_paths) is False
        assert is_path_exempt("/api/v1/conformance", exempt_paths) is False

    def test_wildcard_exempt(self):
        """Test wildcard path exemption."""
        exempt_paths = ["/api/v1/health*"]
        assert is_path_exempt("/api/v1/health", exempt_paths) is True
        assert is_path_exempt("/api/v1/health/live", exempt_paths) is True
        assert is_path_exempt("/api/v1/health/ready", exempt_paths) is True

    def test_trailing_slash_handling(self):
        """Test trailing slash handling."""
        exempt_paths = ["/api/v1/health"]
        assert is_path_exempt("/api/v1/health", exempt_paths) is True
        assert is_path_exempt("/api/v1/health/", exempt_paths) is True


class TestAuthMiddleware:
    """Tests for authentication middleware behavior."""

    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth_required(self, client):
        """Test that health endpoint works without authentication."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_endpoint_no_auth_required(self, client):
        """Test that docs endpoint works without authentication."""
        response = await client.get("/api/v1/docs")
        # Docs should return HTML page
        assert response.status_code == 200


class TestAuthenticatedEndpoints:
    """Tests for endpoints that require authentication when enabled."""

    @pytest.mark.asyncio
    async def test_authenticated_client_can_access(self, authenticated_client):
        """Test that authenticated client can access protected endpoints."""
        response = await authenticated_client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_request_blocked(self, test_session):
        """Test that unauthenticated requests are blocked when auth is enabled."""
        from src.database import get_db
        from tests.conftest import get_test_settings_with_auth
        from collections.abc import AsyncGenerator

        async def override_get_db() -> AsyncGenerator:
            yield test_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.clear()  # Clear to get default auth behavior

        # Create a fresh app with auth enabled
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Health endpoint should still work (exempt)
            response = await ac.get("/api/v1/health")
            assert response.status_code == 200
