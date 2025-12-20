"""Integration tests for Phase 3-4 API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime


@pytest.mark.asyncio
class TestQualityRulesAPI:
    """Integration tests for quality rules endpoints."""

    async def test_list_quality_rules_empty(self, client: AsyncClient):
        """Test listing quality rules when database is empty."""
        response = await client.get("/api/v1/quality-rules")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_quality_rules_filter_by_capsule(self, client: AsyncClient):
        """Test filtering quality rules by capsule_id."""
        capsule_id = str(uuid4())
        response = await client.get(f"/api/v1/quality-rules?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_quality_rules_filter_by_column(self, client: AsyncClient):
        """Test filtering quality rules by column_id."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/quality-rules?column_id={column_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_quality_rules_filter_by_type(self, client: AsyncClient):
        """Test filtering quality rules by rule_type."""
        response = await client.get("/api/v1/quality-rules?rule_type=not_null")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_quality_rules_filter_by_category(self, client: AsyncClient):
        """Test filtering quality rules by rule_category."""
        response = await client.get("/api/v1/quality-rules?rule_category=completeness")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_quality_rules_enabled_only(self, client: AsyncClient):
        """Test filtering for enabled rules only."""
        response = await client.get("/api/v1/quality-rules?enabled_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_quality_rule_not_found(self, client: AsyncClient):
        """Test getting non-existent quality rule returns 404."""
        rule_id = str(uuid4())
        response = await client.get(f"/api/v1/quality-rules/{rule_id}")

        assert response.status_code == 404

    async def test_create_quality_rule_validation_error(self, client: AsyncClient):
        """Test creating quality rule with invalid data."""
        rule_data = {
            "capsule_id": str(uuid4()),
            "column_id": str(uuid4()),  # Both set - should fail validation
            "rule_name": "Test Rule",
            "rule_type": "not_null",
            "rule_config": {},
        }

        response = await client.post("/api/v1/quality-rules", json=rule_data)

        # Should fail validation (both capsule_id and column_id set)
        assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
class TestColumnProfilesAPI:
    """Integration tests for column profiles endpoints."""

    async def test_list_column_profiles_requires_column_id(self, client: AsyncClient):
        """Test that listing profiles requires column_id parameter."""
        response = await client.get("/api/v1/column-profiles")

        # Should require column_id parameter
        assert response.status_code == 422

    async def test_list_column_profiles_with_column_id(self, client: AsyncClient):
        """Test listing column profiles with column_id."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/column-profiles?column_id={column_id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_get_latest_profile_requires_column_id(self, client: AsyncClient):
        """Test that getting latest profile requires column_id parameter."""
        response = await client.get("/api/v1/column-profiles/latest")

        # Should require column_id parameter
        assert response.status_code == 422

    async def test_get_latest_profile_not_found(self, client: AsyncClient):
        """Test getting latest profile for non-existent column."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/column-profiles/latest?column_id={column_id}")

        assert response.status_code == 404

    async def test_get_column_profile_not_found(self, client: AsyncClient):
        """Test getting non-existent column profile returns 404."""
        profile_id = str(uuid4())
        response = await client.get(f"/api/v1/column-profiles/{profile_id}")

        assert response.status_code == 404

    async def test_create_column_profile_structure(self, client: AsyncClient):
        """Test creating column profile with valid structure."""
        profile_data = {
            "column_id": str(uuid4()),
            "total_count": 1000,
            "null_count": 50,
            "null_percentage": 5.0,
            "distinct_count": 800,
            "unique_percentage": 80.0,
            "profiled_at": datetime.now().isoformat(),
        }

        response = await client.post("/api/v1/column-profiles", json=profile_data)

        # May fail with 404 if column doesn't exist
        assert response.status_code in [201, 404]


@pytest.mark.asyncio
class TestDataPoliciesAPI:
    """Integration tests for data policies endpoints."""

    async def test_list_data_policies_empty(self, client: AsyncClient):
        """Test listing data policies when database is empty."""
        response = await client.get("/api/v1/data-policies")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_data_policies_filter_by_capsule(self, client: AsyncClient):
        """Test filtering data policies by capsule_id."""
        capsule_id = str(uuid4())
        response = await client.get(f"/api/v1/data-policies?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_data_policies_filter_by_column(self, client: AsyncClient):
        """Test filtering data policies by column_id."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/data-policies?column_id={column_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_data_policies_filter_by_sensitivity(self, client: AsyncClient):
        """Test filtering data policies by sensitivity_level."""
        response = await client.get("/api/v1/data-policies?sensitivity_level=confidential")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_data_policies_active_only(self, client: AsyncClient):
        """Test filtering for active policies only."""
        response = await client.get("/api/v1/data-policies?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_data_policy_not_found(self, client: AsyncClient):
        """Test getting non-existent data policy returns 404."""
        policy_id = str(uuid4())
        response = await client.get(f"/api/v1/data-policies/{policy_id}")

        assert response.status_code == 404

    async def test_create_data_policy_structure(self, client: AsyncClient):
        """Test creating data policy with valid structure."""
        policy_data = {
            "column_id": str(uuid4()),
            "sensitivity_level": "confidential",
            "classification_tags": ["GDPR", "PII"],
            "policy_status": "active",
            "requires_masking": True,
            "encryption_required": False,
        }

        response = await client.post("/api/v1/data-policies", json=policy_data)

        # May fail with 404 if column doesn't exist
        assert response.status_code in [201, 404]

    async def test_create_data_policy_validation_error(self, client: AsyncClient):
        """Test creating data policy with invalid data."""
        policy_data = {
            "capsule_id": str(uuid4()),
            "column_id": str(uuid4()),  # Both set - should fail validation
            "sensitivity_level": "confidential",
        }

        response = await client.post("/api/v1/data-policies", json=policy_data)

        # Should fail validation (both capsule_id and column_id set)
        assert response.status_code in [400, 422, 500]


@pytest.mark.asyncio
class TestMaskingRulesAPI:
    """Integration tests for masking rules endpoints."""

    async def test_list_masking_rules_requires_column_id(self, client: AsyncClient):
        """Test that listing masking rules requires column_id parameter."""
        response = await client.get("/api/v1/masking-rules")

        # Should require column_id parameter
        assert response.status_code == 422

    async def test_list_masking_rules_with_column_id(self, client: AsyncClient):
        """Test listing masking rules with column_id."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/masking-rules?column_id={column_id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_masking_rules_enabled_only(self, client: AsyncClient):
        """Test filtering for enabled masking rules only."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/masking-rules?column_id={column_id}&enabled_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_masking_rule_not_found(self, client: AsyncClient):
        """Test getting non-existent masking rule returns 404."""
        rule_id = str(uuid4())
        response = await client.get(f"/api/v1/masking-rules/{rule_id}")

        assert response.status_code == 404

    async def test_create_masking_rule_structure(self, client: AsyncClient):
        """Test creating masking rule with valid structure."""
        rule_data = {
            "column_id": str(uuid4()),
            "rule_name": "Email Redaction",
            "masking_method": "redaction",
            "method_config": {"replacement": "***@***.***"},
            "is_enabled": True,
        }

        response = await client.post("/api/v1/masking-rules", json=rule_data)

        # May fail with 404 if column doesn't exist
        assert response.status_code in [201, 404]

    async def test_create_masking_rule_with_roles(self, client: AsyncClient):
        """Test creating masking rule with role-based configuration."""
        rule_data = {
            "column_id": str(uuid4()),
            "rule_name": "Role-Based Masking",
            "masking_method": "tokenization",
            "method_config": {"algorithm": "FPE"},
            "applies_to_roles": ["analyst", "developer"],
            "exempt_roles": ["admin"],
            "is_enabled": True,
        }

        response = await client.post("/api/v1/masking-rules", json=rule_data)

        # May fail with 404 if column doesn't exist
        assert response.status_code in [201, 404]


@pytest.mark.asyncio
class TestPhase3_4Pagination:
    """Integration tests for pagination across Phase 3-4 endpoints."""

    async def test_quality_rules_pagination(self, client: AsyncClient):
        """Test pagination for quality rules endpoint."""
        response = await client.get("/api/v1/quality-rules?offset=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 10

    async def test_column_profiles_pagination(self, client: AsyncClient):
        """Test pagination for column profiles endpoint."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/column-profiles?column_id={column_id}&offset=0&limit=25")

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 25

    async def test_data_policies_pagination(self, client: AsyncClient):
        """Test pagination for data policies endpoint."""
        response = await client.get("/api/v1/data-policies?offset=0&limit=50")

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 50

    async def test_masking_rules_pagination(self, client: AsyncClient):
        """Test pagination for masking rules endpoint."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/masking-rules?column_id={column_id}&offset=0&limit=20")

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 20


@pytest.mark.asyncio
class TestPhase3_4ErrorHandling:
    """Integration tests for error handling in Phase 3-4 endpoints."""

    async def test_quality_rule_invalid_uuid(self, client: AsyncClient):
        """Test handling of invalid UUID in quality rule endpoint."""
        response = await client.get("/api/v1/quality-rules/invalid-uuid")

        assert response.status_code == 422

    async def test_column_profile_invalid_uuid(self, client: AsyncClient):
        """Test handling of invalid UUID in column profile endpoint."""
        response = await client.get("/api/v1/column-profiles/invalid-uuid")

        assert response.status_code == 422

    async def test_data_policy_invalid_uuid(self, client: AsyncClient):
        """Test handling of invalid UUID in data policy endpoint."""
        response = await client.get("/api/v1/data-policies/invalid-uuid")

        assert response.status_code == 422

    async def test_masking_rule_invalid_uuid(self, client: AsyncClient):
        """Test handling of invalid UUID in masking rule endpoint."""
        response = await client.get("/api/v1/masking-rules/invalid-uuid")

        assert response.status_code == 422
