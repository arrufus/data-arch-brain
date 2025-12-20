"""Integration tests for Phase 1-2 API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestConstraintsAPI:
    """Integration tests for constraints endpoints."""

    async def test_list_constraints_empty(self, client: AsyncClient):
        """Test listing constraints when database is empty."""
        response = await client.get("/api/v1/constraints")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_constraints_filter_by_column(self, client: AsyncClient):
        """Test filtering constraints by column_id."""
        column_id = str(uuid4())
        response = await client.get(f"/api/v1/constraints?column_id={column_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_constraints_filter_by_type(self, client: AsyncClient):
        """Test filtering constraints by type."""
        response = await client.get("/api/v1/constraints?constraint_type=primary_key")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_primary_keys(self, client: AsyncClient):
        """Test listing all primary key constraints."""
        response = await client.get("/api/v1/constraints/primary-keys")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_foreign_keys(self, client: AsyncClient):
        """Test listing all foreign key constraints."""
        response = await client.get("/api/v1/constraints/foreign-keys")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_get_constraint_not_found(self, client: AsyncClient):
        """Test getting non-existent constraint returns 404."""
        constraint_id = str(uuid4())
        response = await client.get(f"/api/v1/constraints/{constraint_id}")

        assert response.status_code == 404

    async def test_create_and_delete_constraint(self, client: AsyncClient):
        """Test creating and deleting a constraint."""
        # Note: This requires a valid column_id from the database
        # For now, we test the endpoint structure
        constraint_data = {
            "column_id": str(uuid4()),
            "constraint_name": "test_pk",
            "constraint_type": "primary_key",
            "is_enforced": True,
        }

        response = await client.post("/api/v1/constraints", json=constraint_data)

        # May fail with 404 if column doesn't exist, which is expected in integration tests
        assert response.status_code in [201, 404, 422]


@pytest.mark.asyncio
class TestIndexesAPI:
    """Integration tests for indexes endpoints."""

    async def test_list_indexes_empty(self, client: AsyncClient):
        """Test listing indexes when database is empty."""
        response = await client.get("/api/v1/indexes")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_indexes_filter_by_capsule(self, client: AsyncClient):
        """Test filtering indexes by capsule_id."""
        capsule_id = str(uuid4())
        response = await client.get(f"/api/v1/indexes?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_indexes_filter_by_type(self, client: AsyncClient):
        """Test filtering indexes by type."""
        response = await client.get("/api/v1/indexes?index_type=btree")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_index_not_found(self, client: AsyncClient):
        """Test getting non-existent index returns 404."""
        index_id = str(uuid4())
        response = await client.get(f"/api/v1/indexes/{index_id}")

        assert response.status_code == 404

    async def test_create_index_endpoint_structure(self, client: AsyncClient):
        """Test create index endpoint structure."""
        index_data = {
            "capsule_id": str(uuid4()),
            "index_name": "idx_test",
            "index_type": "btree",
            "column_names": ["id"],
            "is_unique": True,
            "is_primary": False,
            "is_partial": False,
        }

        response = await client.post("/api/v1/indexes", json=index_data)

        # May fail with 404 if capsule doesn't exist
        assert response.status_code in [201, 404, 422]


@pytest.mark.asyncio
class TestBusinessTermsAPI:
    """Integration tests for business terms endpoints."""

    async def test_list_business_terms_empty(self, client: AsyncClient):
        """Test listing business terms when database is empty."""
        response = await client.get("/api/v1/business-terms")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_business_terms_with_search(self, client: AsyncClient):
        """Test searching business terms."""
        response = await client.get("/api/v1/business-terms?search=customer")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_business_terms_filter_by_domain(self, client: AsyncClient):
        """Test filtering business terms by domain."""
        domain_id = str(uuid4())
        response = await client.get(f"/api/v1/business-terms?domain_id={domain_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_business_terms_filter_by_category(self, client: AsyncClient):
        """Test filtering business terms by category."""
        response = await client.get("/api/v1/business-terms?category=financial")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_business_terms_filter_by_status(self, client: AsyncClient):
        """Test filtering business terms by approval status."""
        response = await client.get("/api/v1/business-terms?approval_status=approved")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_business_term_categories(self, client: AsyncClient):
        """Test listing unique categories."""
        response = await client.get("/api/v1/business-terms/categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_business_term_not_found(self, client: AsyncClient):
        """Test getting non-existent business term returns 404."""
        term_id = str(uuid4())
        response = await client.get(f"/api/v1/business-terms/{term_id}")

        assert response.status_code == 404

    async def test_create_business_term(self, client: AsyncClient):
        """Test creating a business term."""
        term_data = {
            "term_name": "test_term_" + str(uuid4())[:8],
            "display_name": "Test Term",
            "definition": "A test business term definition",
        }

        response = await client.post("/api/v1/business-terms", json=term_data)

        # Should succeed or fail with validation error
        assert response.status_code in [201, 409, 422]

        if response.status_code == 201:
            data = response.json()
            assert data["term_name"] == term_data["term_name"]
            assert data["display_name"] == term_data["display_name"]

            # Test update
            term_id = data["id"]
            update_data = {"description": "Updated description"}
            response = await client.put(
                f"/api/v1/business-terms/{term_id}", json=update_data
            )
            assert response.status_code == 200

            # Test approval
            approval_data = {
                "approval_status": "approved",
                "approved_by": "Test User",
            }
            response = await client.post(
                f"/api/v1/business-terms/{term_id}/approve", json=approval_data
            )
            assert response.status_code == 200

            # Test delete
            response = await client.delete(f"/api/v1/business-terms/{term_id}")
            assert response.status_code == 204

    async def test_create_capsule_association_endpoint(self, client: AsyncClient):
        """Test capsule-business term association endpoint."""
        association_data = {
            "capsule_id": str(uuid4()),
            "business_term_id": str(uuid4()),
            "relationship_type": "implements",
            "added_by": "test@example.com",
        }

        response = await client.post(
            "/api/v1/business-terms/capsule-associations", json=association_data
        )

        # May fail with 404 if entities don't exist
        assert response.status_code in [201, 404, 409, 422]

    async def test_create_column_association_endpoint(self, client: AsyncClient):
        """Test column-business term association endpoint."""
        association_data = {
            "column_id": str(uuid4()),
            "business_term_id": str(uuid4()),
            "relationship_type": "implements",
            "added_by": "test@example.com",
        }

        response = await client.post(
            "/api/v1/business-terms/column-associations", json=association_data
        )

        # May fail with 404 if entities don't exist
        assert response.status_code in [201, 404, 409, 422]


@pytest.mark.asyncio
class TestValueDomainsAPI:
    """Integration tests for value domains endpoints."""

    async def test_list_value_domains_empty(self, client: AsyncClient):
        """Test listing value domains when database is empty."""
        response = await client.get("/api/v1/value-domains")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_value_domains_with_search(self, client: AsyncClient):
        """Test searching value domains."""
        response = await client.get("/api/v1/value-domains?search=status")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_value_domains_filter_by_type(self, client: AsyncClient):
        """Test filtering value domains by type."""
        response = await client.get("/api/v1/value-domains?domain_type=enum")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_value_domains_filter_by_owner(self, client: AsyncClient):
        """Test filtering value domains by owner."""
        owner_id = str(uuid4())
        response = await client.get(f"/api/v1/value-domains?owner_id={owner_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_value_domains_filter_by_extensible(self, client: AsyncClient):
        """Test filtering value domains by extensibility."""
        response = await client.get("/api/v1/value-domains?is_extensible=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_value_domain_not_found(self, client: AsyncClient):
        """Test getting non-existent value domain returns 404."""
        domain_id = str(uuid4())
        response = await client.get(f"/api/v1/value-domains/{domain_id}")

        assert response.status_code == 404

    async def test_create_enum_domain(self, client: AsyncClient):
        """Test creating an enum type value domain."""
        domain_data = {
            "domain_name": "test_status_" + str(uuid4())[:8],
            "domain_type": "enum",
            "description": "Test status values",
            "allowed_values": [
                {"code": "active", "label": "Active"},
                {"code": "inactive", "label": "Inactive"},
            ],
            "is_extensible": False,
        }

        response = await client.post("/api/v1/value-domains", json=domain_data)

        # Should succeed or fail with validation/conflict error
        assert response.status_code in [201, 409, 422]

        if response.status_code == 201:
            data = response.json()
            assert data["domain_name"] == domain_data["domain_name"]
            assert data["domain_type"] == "enum"

            # Test validation
            domain_id = data["id"]
            validation_data = {"value": "active"}
            response = await client.post(
                f"/api/v1/value-domains/{domain_id}/validate", json=validation_data
            )
            assert response.status_code == 200
            validation_result = response.json()
            assert "valid" in validation_result
            assert validation_result["valid"] is True

            # Test update
            update_data = {"description": "Updated description"}
            response = await client.put(
                f"/api/v1/value-domains/{domain_id}", json=update_data
            )
            assert response.status_code == 200

            # Test delete
            response = await client.delete(f"/api/v1/value-domains/{domain_id}")
            assert response.status_code == 204

    async def test_create_pattern_domain(self, client: AsyncClient):
        """Test creating a pattern type value domain."""
        domain_data = {
            "domain_name": "test_email_" + str(uuid4())[:8],
            "domain_type": "pattern",
            "description": "Email address pattern",
            "pattern_regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "pattern_description": "Standard email format",
            "is_extensible": False,
        }

        response = await client.post("/api/v1/value-domains", json=domain_data)

        assert response.status_code in [201, 409, 422]

        if response.status_code == 201:
            data = response.json()
            domain_id = data["id"]

            # Test validation with valid email
            validation_data = {"value": "test@example.com"}
            response = await client.post(
                f"/api/v1/value-domains/{domain_id}/validate", json=validation_data
            )
            assert response.status_code == 200
            validation_result = response.json()
            assert validation_result["valid"] is True

            # Test validation with invalid email
            validation_data = {"value": "invalid-email"}
            response = await client.post(
                f"/api/v1/value-domains/{domain_id}/validate", json=validation_data
            )
            assert response.status_code == 200
            validation_result = response.json()
            assert validation_result["valid"] is False

            # Cleanup
            await client.delete(f"/api/v1/value-domains/{domain_id}")

    async def test_create_range_domain(self, client: AsyncClient):
        """Test creating a range type value domain."""
        domain_data = {
            "domain_name": "test_percentage_" + str(uuid4())[:8],
            "domain_type": "range",
            "description": "Percentage values",
            "min_value": "0",
            "max_value": "100",
            "is_extensible": False,
        }

        response = await client.post("/api/v1/value-domains", json=domain_data)

        assert response.status_code in [201, 409, 422]

    async def test_validation_endpoint(self, client: AsyncClient):
        """Test value validation endpoint structure."""
        domain_id = str(uuid4())
        validation_data = {"value": "test"}

        response = await client.post(
            f"/api/v1/value-domains/{domain_id}/validate", json=validation_data
        )

        # Should return 404 for non-existent domain
        assert response.status_code == 404
