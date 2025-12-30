"""Integration tests for Phase 4 Orchestration API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPipelineEndpoints:
    """Integration tests for pipeline API endpoints."""

    async def test_list_pipelines_empty(self, client: AsyncClient):
        """Test listing pipelines when database is empty."""
        response = await client.get("/api/v1/pipelines")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    async def test_list_pipelines_pagination(self, client: AsyncClient):
        """Test pipeline pagination parameters."""
        response = await client.get("/api/v1/pipelines?offset=0&limit=20")

        assert response.status_code == 200
        data = response.json()

        pagination = data["pagination"]
        assert pagination["offset"] == 0
        assert pagination["limit"] == 20

    async def test_list_pipelines_filter_by_type(self, client: AsyncClient):
        """Test filtering pipelines by type."""
        response = await client.get("/api/v1/pipelines?pipeline_type=airflow_dag")

        assert response.status_code == 200
        data = response.json()

        # All returned pipelines should have airflow_dag type
        for pipeline in data["data"]:
            if pipeline.get("pipeline_type"):
                assert pipeline["pipeline_type"] == "airflow_dag"

    async def test_list_pipelines_filter_by_active(self, client: AsyncClient):
        """Test filtering pipelines by active status."""
        response = await client.get("/api/v1/pipelines?is_active=true")

        assert response.status_code == 200
        data = response.json()

        for pipeline in data["data"]:
            assert pipeline["is_active"] is True

    async def test_list_pipelines_filter_by_paused(self, client: AsyncClient):
        """Test filtering pipelines by paused status."""
        response = await client.get("/api/v1/pipelines?is_paused=false")

        assert response.status_code == 200
        data = response.json()

        for pipeline in data["data"]:
            assert pipeline["is_paused"] is False

    async def test_list_pipelines_search(self, client: AsyncClient):
        """Test searching pipelines by name."""
        response = await client.get("/api/v1/pipelines?search=finance")

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        # Search should return results if finance pipelines exist
        # or empty list if they don't

    async def test_pipeline_stats(self, client: AsyncClient):
        """Test pipeline statistics endpoint."""
        response = await client.get("/api/v1/pipelines/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_pipelines" in data
        assert "by_type" in data
        assert "by_source_system" in data
        assert isinstance(data["total_pipelines"], int)
        assert isinstance(data["by_type"], dict)

    async def test_get_pipeline_not_found(self, client: AsyncClient):
        """Test getting non-existent pipeline."""
        response = await client.get(
            "/api/v1/pipelines/urn:dcs:pipeline:airflow:prod:nonexistent"
        )

        assert response.status_code == 404

    async def test_get_pipeline_tasks_not_found(self, client: AsyncClient):
        """Test getting tasks for non-existent pipeline."""
        response = await client.get(
            "/api/v1/pipelines/urn:dcs:pipeline:airflow:prod:nonexistent/tasks"
        )

        assert response.status_code == 404

    async def test_get_pipeline_data_footprint_not_found(self, client: AsyncClient):
        """Test getting data footprint for non-existent pipeline."""
        response = await client.get(
            "/api/v1/pipelines/urn:dcs:pipeline:airflow:prod:nonexistent/data-footprint"
        )

        assert response.status_code == 404

    async def test_get_pipeline_dependencies_not_found(self, client: AsyncClient):
        """Test getting dependencies for non-existent pipeline."""
        response = await client.get(
            "/api/v1/pipelines/urn:dcs:pipeline:airflow:prod:nonexistent/dependencies"
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestCapsuleOrchestrationEndpoints:
    """Integration tests for capsule-to-pipeline endpoints."""

    async def test_get_capsule_producers_not_found(self, client: AsyncClient):
        """Test getting producers for non-existent capsule."""
        response = await client.get(
            "/api/v1/capsules/urn:dcs:postgres:table:test:nonexistent/producers"
        )

        assert response.status_code == 404

    async def test_get_capsule_consumers_not_found(self, client: AsyncClient):
        """Test getting consumers for non-existent capsule."""
        response = await client.get(
            "/api/v1/capsules/urn:dcs:postgres:table:test:nonexistent/consumers"
        )

        assert response.status_code == 404

    async def test_get_capsule_producers_pagination(self, client: AsyncClient):
        """Test pagination for capsule producers."""
        # Create a valid URN from existing data (this will 404 or return empty)
        response = await client.get(
            "/api/v1/capsules/urn:dcs:postgres:table:test:sample/producers?offset=0&limit=10"
        )

        # Should either 404 (no capsule) or 200 with pagination
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "pagination" in data
            assert data["pagination"]["offset"] == 0
            assert data["pagination"]["limit"] == 10

    async def test_get_capsule_consumers_pagination(self, client: AsyncClient):
        """Test pagination for capsule consumers."""
        response = await client.get(
            "/api/v1/capsules/urn:dcs:postgres:table:test:sample/consumers?offset=0&limit=10"
        )

        # Should either 404 (no capsule) or 200 with pagination
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "pagination" in data
            assert data["pagination"]["offset"] == 0
            assert data["pagination"]["limit"] == 10


@pytest.mark.asyncio
class TestIntegratedLineageEndpoint:
    """Integration tests for integrated lineage endpoint."""

    async def test_integrated_lineage_not_found(self, client: AsyncClient):
        """Test integrated lineage for non-existent URN."""
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:nonexistent"
        )

        assert response.status_code == 404

    async def test_integrated_lineage_direction_upstream(self, client: AsyncClient):
        """Test integrated lineage with upstream direction."""
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?direction=upstream"
        )

        # Should either 404 (no capsule) or 200 with structure
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "nodes" in data
            assert "edges" in data
            assert "summary" in data
            assert isinstance(data["nodes"], list)
            assert isinstance(data["edges"], list)

    async def test_integrated_lineage_direction_downstream(self, client: AsyncClient):
        """Test integrated lineage with downstream direction."""
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?direction=downstream"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "nodes" in data
            assert "edges" in data
            assert "summary" in data

    async def test_integrated_lineage_direction_both(self, client: AsyncClient):
        """Test integrated lineage with both directions."""
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?direction=both"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "nodes" in data
            assert "edges" in data
            assert "summary" in data
            assert "capsule_count" in data["summary"]
            assert "task_count" in data["summary"]
            assert "data_edges" in data["summary"]
            assert "orchestration_edges" in data["summary"]

    async def test_integrated_lineage_depth(self, client: AsyncClient):
        """Test integrated lineage depth parameter."""
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?depth=2"
        )

        assert response.status_code in [200, 404]

    async def test_integrated_lineage_depth_validation(self, client: AsyncClient):
        """Test integrated lineage depth validation."""
        # Depth too high
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?depth=10"
        )

        assert response.status_code == 422  # Validation error

        # Depth too low
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?depth=0"
        )

        assert response.status_code == 422

    async def test_integrated_lineage_without_orchestration(
        self, client: AsyncClient
    ):
        """Test integrated lineage without orchestration edges."""
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?include_orchestration=false"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should have 0 orchestration edges when include_orchestration=false
            assert data["summary"]["orchestration_edges"] == 0

    async def test_integrated_lineage_invalid_direction(self, client: AsyncClient):
        """Test integrated lineage with invalid direction."""
        response = await client.get(
            "/api/v1/graph/lineage/integrated/urn:dcs:postgres:table:test:sample?direction=invalid"
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestImpactAnalysisEndpoint:
    """Integration tests for pipeline impact analysis endpoint."""

    async def test_impact_analysis_not_found(self, client: AsyncClient):
        """Test impact analysis for non-existent pipeline."""
        response = await client.get(
            "/api/v1/graph/impact-analysis/urn:dcs:pipeline:airflow:prod:nonexistent"
        )

        assert response.status_code == 404

    async def test_impact_analysis_modify_scenario(self, client: AsyncClient):
        """Test impact analysis with modify scenario."""
        response = await client.get(
            "/api/v1/graph/impact-analysis/urn:dcs:pipeline:airflow:prod:test?scenario=modify"
        )

        # Should either 404 (no pipeline) or 200 with structure
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "pipeline_urn" in data
            assert "scenario" in data
            assert data["scenario"] == "modify"
            assert "risk_level" in data
            assert "directly_affected_capsules" in data
            assert "impact_details" in data
            assert "recommendations" in data
            assert isinstance(data["recommendations"], list)

    async def test_impact_analysis_disable_scenario(self, client: AsyncClient):
        """Test impact analysis with disable scenario."""
        response = await client.get(
            "/api/v1/graph/impact-analysis/urn:dcs:pipeline:airflow:prod:test?scenario=disable"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["scenario"] == "disable"
            assert data["risk_level"] in ["low", "medium", "high", "critical"]

    async def test_impact_analysis_delete_scenario(self, client: AsyncClient):
        """Test impact analysis with delete scenario."""
        response = await client.get(
            "/api/v1/graph/impact-analysis/urn:dcs:pipeline:airflow:prod:test?scenario=delete"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["scenario"] == "delete"
            # Delete should have critical or high risk
            assert data["risk_level"] in ["high", "critical"]

    async def test_impact_analysis_invalid_scenario(self, client: AsyncClient):
        """Test impact analysis with invalid scenario."""
        response = await client.get(
            "/api/v1/graph/impact-analysis/urn:dcs:pipeline:airflow:prod:test?scenario=invalid"
        )

        assert response.status_code == 422  # Validation error

    async def test_impact_analysis_with_task_urn(self, client: AsyncClient):
        """Test impact analysis with specific task URN."""
        response = await client.get(
            "/api/v1/graph/impact-analysis/urn:dcs:pipeline:airflow:prod:test"
            "?scenario=modify&task_urn=urn:dcs:task:airflow:prod:test.task1"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "impact_details" in data
