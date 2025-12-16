"""Unit tests for ingestion API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.api.routers.ingest import AirflowIngestRequest, ingest_airflow
from src.services.ingestion import IngestionResult, IngestionStats
from src.models.ingestion import IngestionStatus


class TestAirflowIngestRequest:
    """Tests for AirflowIngestRequest model."""

    def test_minimal_request(self):
        """Test creating request with minimal fields."""
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com"
        )

        assert request.base_url == "https://airflow.example.com"
        assert request.instance_name is None
        assert request.auth_mode == "none"
        assert request.cleanup_orphans is False

    def test_full_request(self):
        """Test creating request with all fields."""
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
            instance_name="prod-airflow",
            auth_mode="bearer_env",
            token_env="MY_TOKEN",
            dag_id_regex="customer_.*",
            include_paused=True,
            page_limit=50,
            timeout_seconds=60.0,
            cleanup_orphans=True,
        )

        assert request.base_url == "https://airflow.example.com"
        assert request.instance_name == "prod-airflow"
        assert request.auth_mode == "bearer_env"
        assert request.token_env == "MY_TOKEN"
        assert request.dag_id_regex == "customer_.*"
        assert request.include_paused is True
        assert request.page_limit == 50
        assert request.timeout_seconds == 60.0
        assert request.cleanup_orphans is True

    def test_defaults(self):
        """Test default values."""
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com"
        )

        assert request.auth_mode == "none"
        assert request.token_env == "AIRFLOW_TOKEN"
        assert request.username_env == "AIRFLOW_USERNAME"
        assert request.password_env == "AIRFLOW_PASSWORD"
        assert request.include_paused is False
        assert request.include_inactive is False
        assert request.page_limit == 100
        assert request.timeout_seconds == 30.0
        assert request.domain_tag_prefix == "domain:"
        assert request.cleanup_orphans is False


class TestAirflowIngestEndpoint:
    """Tests for ingest_airflow endpoint function."""

    @pytest.mark.asyncio
    async def test_ingest_airflow_minimal_config(self):
        """Test Airflow ingestion with minimal configuration."""
        # Mock database session
        mock_db = MagicMock()

        # Create request
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com"
        )

        # Mock ingestion result
        job_id = uuid4()
        mock_result = IngestionResult(
            job_id=job_id,
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="test-airflow",
            stats=IngestionStats(
                capsules_created=5,
                edges_created=10,
            ),
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response
            assert response.job_id == job_id
            assert response.status == "completed"
            assert response.source_type == "airflow"
            assert response.source_name == "test-airflow"
            assert response.stats.capsules_created == 5
            assert response.stats.edges_created == 10

            # Verify service was called correctly
            mock_service.ingest_airflow.assert_called_once()
            call_kwargs = mock_service.ingest_airflow.call_args.kwargs
            assert call_kwargs["base_url"] == "https://airflow.example.com"

    @pytest.mark.asyncio
    async def test_ingest_airflow_full_config(self):
        """Test Airflow ingestion with full configuration."""
        # Mock database session
        mock_db = MagicMock()

        # Create request with all parameters
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
            instance_name="prod-airflow",
            auth_mode="bearer_env",
            token_env="AIRFLOW_TOKEN",
            dag_id_regex="customer_.*",
            include_paused=True,
            include_inactive=False,
            page_limit=50,
            timeout_seconds=60.0,
            domain_tag_prefix="domain:",
            cleanup_orphans=True,
        )

        # Mock ingestion result
        job_id = uuid4()
        mock_result = IngestionResult(
            job_id=job_id,
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="prod-airflow",
            stats=IngestionStats(
                capsules_created=10,
                capsules_updated=2,
                edges_created=15,
                warnings=1,
            ),
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response
            assert response.job_id == job_id
            assert response.status == "completed"
            assert response.source_type == "airflow"
            assert response.source_name == "prod-airflow"
            assert response.stats.capsules_created == 10
            assert response.stats.capsules_updated == 2
            assert response.stats.edges_created == 15
            assert response.stats.warnings == 1

            # Verify service was called with correct parameters
            mock_service.ingest_airflow.assert_called_once()
            call_kwargs = mock_service.ingest_airflow.call_args.kwargs
            assert call_kwargs["base_url"] == "https://airflow.example.com"
            assert call_kwargs["instance_name"] == "prod-airflow"
            assert call_kwargs["auth_mode"] == "bearer_env"
            assert call_kwargs["dag_id_regex"] == "customer_.*"
            assert call_kwargs["cleanup_orphans"] is True

    @pytest.mark.asyncio
    async def test_ingest_airflow_with_dag_allowlist(self):
        """Test Airflow ingestion with DAG allowlist."""
        # Mock database session
        mock_db = MagicMock()

        # Create request with allowlist
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
            dag_id_allowlist=["dag1", "dag2", "dag3"],
        )

        # Mock ingestion result
        mock_result = IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="test-airflow",
            stats=IngestionStats(),
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response
            assert response.status == "completed"

            # Verify allowlist was passed to service
            call_kwargs = mock_service.ingest_airflow.call_args.kwargs
            assert call_kwargs["dag_id_allowlist"] == ["dag1", "dag2", "dag3"]

    @pytest.mark.asyncio
    async def test_ingest_airflow_with_dag_denylist(self):
        """Test Airflow ingestion with DAG denylist."""
        # Mock database session
        mock_db = MagicMock()

        # Create request with denylist
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
            dag_id_denylist=["old_dag", "deprecated_dag"],
        )

        # Mock ingestion result
        mock_result = IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="test-airflow",
            stats=IngestionStats(),
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response
            assert response.status == "completed"

            # Verify denylist was passed to service
            call_kwargs = mock_service.ingest_airflow.call_args.kwargs
            assert call_kwargs["dag_id_denylist"] == ["old_dag", "deprecated_dag"]

    @pytest.mark.asyncio
    async def test_ingest_airflow_failed_ingestion(self):
        """Test Airflow ingestion that fails."""
        # Mock database session
        mock_db = MagicMock()

        # Create request
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
            auth_mode="bearer_env",
        )

        # Mock ingestion result with error
        mock_result = IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.FAILED,
            source_type="airflow",
            source_name="test-airflow",
            stats=IngestionStats(),
            error_message="Connection failed: Invalid credentials",
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response
            assert response.status == "failed"
            assert response.message == "Connection failed: Invalid credentials"

    @pytest.mark.asyncio
    async def test_ingest_airflow_defaults(self):
        """Test that Airflow ingestion uses correct defaults."""
        # Mock database session
        mock_db = MagicMock()

        # Create request with only base_url
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
        )

        # Mock ingestion result
        mock_result = IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="test-airflow",
            stats=IngestionStats(),
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response
            assert response.status == "completed"

            # Verify defaults were used
            call_kwargs = mock_service.ingest_airflow.call_args.kwargs
            assert call_kwargs["auth_mode"] == "none"
            assert call_kwargs["include_paused"] is False
            assert call_kwargs["include_inactive"] is False
            assert call_kwargs["page_limit"] == 100
            assert call_kwargs["timeout_seconds"] == 30.0
            assert call_kwargs["cleanup_orphans"] is False

    @pytest.mark.asyncio
    async def test_ingest_airflow_returns_job_id(self):
        """Test that Airflow ingestion returns a job ID."""
        # Mock database session
        mock_db = MagicMock()

        # Create request
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
        )

        # Mock ingestion result with specific job_id
        job_id = uuid4()
        mock_result = IngestionResult(
            job_id=job_id,
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="test-airflow",
            stats=IngestionStats(),
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response has correct job_id
            assert response.job_id == job_id

    @pytest.mark.asyncio
    async def test_ingest_airflow_returns_stats(self):
        """Test that Airflow ingestion returns detailed stats."""
        # Mock database session
        mock_db = MagicMock()

        # Create request
        request = AirflowIngestRequest(
            base_url="https://airflow.example.com",
        )

        # Mock ingestion result with detailed stats
        mock_result = IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="test-airflow",
            stats=IngestionStats(
                capsules_created=15,
                capsules_updated=3,
                capsules_unchanged=2,
                edges_created=25,
                edges_updated=5,
                domains_created=2,
                warnings=1,
                errors=0,
            ),
        )

        # Mock ingestion service
        mock_service = MagicMock()
        mock_service.ingest_airflow = AsyncMock(return_value=mock_result)

        # Patch IngestionService
        with patch("src.api.routers.ingest.IngestionService", return_value=mock_service):
            response = await ingest_airflow(request, mock_db)

            # Verify response has detailed stats
            assert response.stats.capsules_created == 15
            assert response.stats.capsules_updated == 3
            assert response.stats.capsules_unchanged == 2
            assert response.stats.edges_created == 25
            assert response.stats.edges_updated == 5
            assert response.stats.domains_created == 2
            assert response.stats.warnings == 1
            assert response.stats.errors == 0
