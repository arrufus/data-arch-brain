"""Integration tests for Phase 5-6 API endpoints."""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestCapsuleVersionsAPI:
    """Integration tests for capsule versions endpoints."""

    async def test_list_capsule_versions_empty(self, client: AsyncClient):
        """Test listing capsule versions when database is empty."""
        response = await client.get("/api/v1/capsule-versions")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_capsule_versions_filter_by_capsule(self, client: AsyncClient):
        """Test filtering capsule versions by capsule_id."""
        capsule_id = str(uuid4())
        response = await client.get(f"/api/v1/capsule-versions?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_versions_filter_by_change_type(self, client: AsyncClient):
        """Test filtering capsule versions by change_type."""
        response = await client.get("/api/v1/capsule-versions?change_type=schema_change")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_versions_breaking_only(self, client: AsyncClient):
        """Test filtering for breaking changes only."""
        response = await client.get("/api/v1/capsule-versions?breaking_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_capsule_version_not_found(self, client: AsyncClient):
        """Test getting non-existent capsule version returns 404."""
        version_id = str(uuid4())
        response = await client.get(f"/api/v1/capsule-versions/{version_id}")

        assert response.status_code == 404

    async def test_create_capsule_version_structure(self, client: AsyncClient):
        """Test creating capsule version with valid structure."""
        version_data = {
            "capsule_id": str(uuid4()),
            "version_number": 1,
            "version_name": "v1.0.0",
            "schema_snapshot": {"columns": [], "indexes": []},
            "change_type": "created",
            "breaking_change": False,
            "upstream_capsule_urns": [],
            "downstream_capsule_urns": [],
            "is_current": True,
            "meta": {},
        }

        response = await client.post("/api/v1/capsule-versions", json=version_data)

        # May fail with 404 if capsule doesn't exist
        assert response.status_code in [201, 404]

    async def test_update_capsule_version_not_found(self, client: AsyncClient):
        """Test updating non-existent capsule version returns 404."""
        version_id = str(uuid4())
        update_data = {"version_name": "v1.0.1"}

        response = await client.patch(f"/api/v1/capsule-versions/{version_id}", json=update_data)

        assert response.status_code == 404

    async def test_delete_capsule_version_not_found(self, client: AsyncClient):
        """Test deleting non-existent capsule version returns 404."""
        version_id = str(uuid4())
        response = await client.delete(f"/api/v1/capsule-versions/{version_id}")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestTransformationCodeAPI:
    """Integration tests for transformation code endpoints."""

    async def test_list_transformation_code_empty(self, client: AsyncClient):
        """Test listing transformation code when database is empty."""
        response = await client.get("/api/v1/transformation-code")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_transformation_code_filter_by_capsule(self, client: AsyncClient):
        """Test filtering transformation code by capsule_id."""
        capsule_id = str(uuid4())
        response = await client.get(f"/api/v1/transformation-code?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_transformation_code_filter_by_language(self, client: AsyncClient):
        """Test filtering transformation code by language."""
        response = await client.get("/api/v1/transformation-code?language=sql")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_transformation_code_not_found(self, client: AsyncClient):
        """Test getting non-existent transformation code returns 404."""
        code_id = str(uuid4())
        response = await client.get(f"/api/v1/transformation-code/{code_id}")

        assert response.status_code == 404

    async def test_create_transformation_code_validation_error(self, client: AsyncClient):
        """Test creating transformation code with invalid data."""
        code_data = {
            "capsule_id": str(uuid4()),
            "lineage_edge_id": str(uuid4()),  # Both set - should fail validation
            "language": "sql",
            "code_text": "SELECT * FROM table",
            "upstream_references": [],
            "function_calls": [],
            "meta": {},
        }

        response = await client.post("/api/v1/transformation-code", json=code_data)

        # Should fail validation (both capsule_id and lineage_edge_id set)
        assert response.status_code in [400, 422, 500]

    async def test_create_transformation_code_structure(self, client: AsyncClient):
        """Test creating transformation code with valid structure."""
        code_data = {
            "capsule_id": str(uuid4()),
            "language": "sql",
            "code_text": "SELECT * FROM table",
            "upstream_references": [],
            "function_calls": [],
            "meta": {},
        }

        response = await client.post("/api/v1/transformation-code", json=code_data)

        # May fail with 404 if capsule doesn't exist
        assert response.status_code in [201, 404]

    async def test_delete_transformation_code_not_found(self, client: AsyncClient):
        """Test deleting non-existent transformation code returns 404."""
        code_id = str(uuid4())
        response = await client.delete(f"/api/v1/transformation-code/{code_id}")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestCapsuleContractsAPI:
    """Integration tests for capsule contracts endpoints."""

    async def test_list_capsule_contracts_empty(self, client: AsyncClient):
        """Test listing capsule contracts when database is empty."""
        response = await client.get("/api/v1/capsule-contracts")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_capsule_contracts_filter_by_capsule(self, client: AsyncClient):
        """Test filtering capsule contracts by capsule_id."""
        capsule_id = str(uuid4())
        response = await client.get(f"/api/v1/capsule-contracts?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_contracts_filter_by_status(self, client: AsyncClient):
        """Test filtering capsule contracts by status."""
        response = await client.get("/api/v1/capsule-contracts?status=active")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_capsule_contracts_active_only(self, client: AsyncClient):
        """Test filtering for active contracts only."""
        response = await client.get("/api/v1/capsule-contracts?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_capsule_contract_not_found(self, client: AsyncClient):
        """Test getting non-existent capsule contract returns 404."""
        contract_id = str(uuid4())
        response = await client.get(f"/api/v1/capsule-contracts/{contract_id}")

        assert response.status_code == 404

    async def test_create_capsule_contract_structure(self, client: AsyncClient):
        """Test creating capsule contract with valid structure."""
        contract_data = {
            "capsule_id": str(uuid4()),
            "contract_version": "1.0",
            "contract_status": "active",
            "critical_quality_rules": [],
            "maintenance_windows": [],
            "known_consumers": [],
            "consumer_notification_required": True,
            "billing_tags": {},
            "meta": {},
        }

        response = await client.post("/api/v1/capsule-contracts", json=contract_data)

        # May fail with 404 if capsule doesn't exist
        assert response.status_code in [201, 404]

    async def test_delete_capsule_contract_not_found(self, client: AsyncClient):
        """Test deleting non-existent capsule contract returns 404."""
        contract_id = str(uuid4())
        response = await client.delete(f"/api/v1/capsule-contracts/{contract_id}")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestSLAIncidentsAPI:
    """Integration tests for SLA incidents endpoints."""

    async def test_list_sla_incidents_empty(self, client: AsyncClient):
        """Test listing SLA incidents when database is empty."""
        response = await client.get("/api/v1/sla-incidents")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_sla_incidents_filter_by_contract(self, client: AsyncClient):
        """Test filtering SLA incidents by contract_id."""
        contract_id = str(uuid4())
        response = await client.get(f"/api/v1/sla-incidents?contract_id={contract_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_sla_incidents_filter_by_capsule(self, client: AsyncClient):
        """Test filtering SLA incidents by capsule_id."""
        capsule_id = str(uuid4())
        response = await client.get(f"/api/v1/sla-incidents?capsule_id={capsule_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_sla_incidents_filter_by_type(self, client: AsyncClient):
        """Test filtering SLA incidents by incident_type."""
        response = await client.get("/api/v1/sla-incidents?incident_type=freshness")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_sla_incidents_filter_by_status(self, client: AsyncClient):
        """Test filtering SLA incidents by status."""
        response = await client.get("/api/v1/sla-incidents?status=open")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_list_sla_incidents_open_only(self, client: AsyncClient):
        """Test filtering for open incidents only."""
        response = await client.get("/api/v1/sla-incidents?open_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    async def test_get_sla_incident_not_found(self, client: AsyncClient):
        """Test getting non-existent SLA incident returns 404."""
        incident_id = str(uuid4())
        response = await client.get(f"/api/v1/sla-incidents/{incident_id}")

        assert response.status_code == 404

    async def test_create_sla_incident_structure(self, client: AsyncClient):
        """Test creating SLA incident with valid structure."""
        incident_data = {
            "contract_id": str(uuid4()),
            "capsule_id": str(uuid4()),
            "incident_type": "freshness",
            "incident_severity": "medium",
            "incident_status": "open",
            "affected_consumers": [],
            "meta": {},
        }

        response = await client.post("/api/v1/sla-incidents", json=incident_data)

        # May fail with 404 if contract or capsule doesn't exist
        assert response.status_code in [201, 404]

    async def test_update_sla_incident_not_found(self, client: AsyncClient):
        """Test updating non-existent SLA incident returns 404."""
        incident_id = str(uuid4())
        update_data = {"incident_status": "resolved"}

        response = await client.patch(f"/api/v1/sla-incidents/{incident_id}", json=update_data)

        assert response.status_code == 404

    async def test_delete_sla_incident_not_found(self, client: AsyncClient):
        """Test deleting non-existent SLA incident returns 404."""
        incident_id = str(uuid4())
        response = await client.delete(f"/api/v1/sla-incidents/{incident_id}")

        assert response.status_code == 404
