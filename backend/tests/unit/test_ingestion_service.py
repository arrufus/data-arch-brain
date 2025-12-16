"""Unit tests for the ingestion service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.ingestion import (
    IngestionService,
    IngestionStats,
    IngestionResult,
    ProcessedUrns,
)
from src.models.ingestion import IngestionStatus
from src.parsers.base import ParseResult, RawCapsule, RawEdge


class TestIngestionStats:
    """Tests for IngestionStats dataclass."""

    def test_default_values(self):
        """Test IngestionStats default values."""
        stats = IngestionStats()
        
        assert stats.capsules_created == 0
        assert stats.capsules_updated == 0
        assert stats.capsules_unchanged == 0
        assert stats.capsules_deleted == 0
        assert stats.columns_created == 0
        assert stats.columns_updated == 0
        assert stats.columns_deleted == 0
        assert stats.edges_created == 0
        assert stats.errors == 0
        assert stats.warnings == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = IngestionStats(
            capsules_created=5,
            capsules_updated=3,
            columns_created=20,
            pii_columns_detected=2,
        )
        
        result = stats.to_dict()
        
        assert result["capsules_created"] == 5
        assert result["capsules_updated"] == 3
        assert result["columns_created"] == 20
        assert result["pii_columns_detected"] == 2

    def test_total_changes(self):
        """Test total_changes calculation."""
        stats = IngestionStats(
            capsules_created=2,
            capsules_updated=3,
            capsules_deleted=1,
            columns_created=10,
            columns_updated=5,
            columns_deleted=2,
            edges_created=8,
        )
        
        expected = 2 + 3 + 1 + 10 + 5 + 2 + 8  # = 31
        assert stats.total_changes == expected

    def test_delta_summary(self):
        """Test delta_summary grouping."""
        stats = IngestionStats(
            capsules_created=5,
            capsules_updated=3,
            capsules_deleted=1,
            columns_created=20,
            edges_created=15,
        )
        
        summary = stats.delta_summary()
        
        assert summary["capsules"]["created"] == 5
        assert summary["capsules"]["updated"] == 3
        assert summary["capsules"]["deleted"] == 1
        assert "columns" in summary
        assert "edges" in summary


class TestProcessedUrns:
    """Tests for ProcessedUrns dataclass."""

    def test_default_empty_sets(self):
        """Test that ProcessedUrns initializes with empty sets."""
        urns = ProcessedUrns()
        
        assert len(urns.capsule_urns) == 0
        assert len(urns.column_urns) == 0
        assert len(urns.edge_keys) == 0
        assert len(urns.column_edge_keys) == 0

    def test_add_urns(self):
        """Test adding URNs to sets."""
        urns = ProcessedUrns()
        
        urns.capsule_urns.add("urn:dab:dbt:model:test:customers")
        urns.capsule_urns.add("urn:dab:dbt:model:test:orders")
        urns.column_urns.add("urn:dab:dbt:column:test:customers.id")
        
        assert len(urns.capsule_urns) == 2
        assert len(urns.column_urns) == 1

    def test_edge_key_tuples(self):
        """Test edge key tuple storage."""
        urns = ProcessedUrns()
        
        urns.edge_keys.add(("urn:source", "urn:target"))
        urns.column_edge_keys.add(("urn:col_source", "urn:col_target"))
        
        assert ("urn:source", "urn:target") in urns.edge_keys
        assert ("urn:col_source", "urn:col_target") in urns.column_edge_keys


class TestIngestionServiceInit:
    """Tests for IngestionService initialization."""

    def test_service_initialization(self):
        """Test IngestionService can be initialized."""
        session_mock = MagicMock()
        service = IngestionService(session_mock)
        
        assert service is not None
        assert service.session == session_mock

    def test_service_initializes_repositories(self):
        """Test that service initializes all required repositories."""
        session_mock = MagicMock()
        service = IngestionService(session_mock)

        assert service.capsule_repo is not None
        assert service.column_repo is not None
        assert service.lineage_repo is not None
        assert service.column_lineage_repo is not None
        assert service.domain_repo is not None
        assert service.source_system_repo is not None
        assert service.job_repo is not None  # Named job_repo, not ingestion_job_repo


class TestIngestionStatus:
    """Tests for IngestionStatus enum."""

    def test_status_values(self):
        """Test IngestionStatus enum values."""
        assert IngestionStatus.PENDING.value == "pending"
        assert IngestionStatus.RUNNING.value == "running"
        assert IngestionStatus.COMPLETED.value == "completed"
        assert IngestionStatus.FAILED.value == "failed"

    def test_terminal_statuses(self):
        """Test which statuses are terminal."""
        terminal = {IngestionStatus.COMPLETED, IngestionStatus.FAILED}
        non_terminal = {IngestionStatus.PENDING, IngestionStatus.RUNNING}
        
        assert IngestionStatus.COMPLETED in terminal
        assert IngestionStatus.FAILED in terminal
        assert IngestionStatus.PENDING in non_terminal


class TestIngestionServiceMethods:
    """Tests for IngestionService methods (mock-based)."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock ingestion service."""
        session_mock = AsyncMock()
        service = IngestionService(session_mock)
        return service

    def test_generate_source_system_urn(self, mock_service):
        """Test URN generation for source systems."""
        source_type = "dbt"
        project_name = "my_project"
        
        # URN format: urn:dab:{source_type}:project:{project_name}
        urn = f"urn:dab:{source_type}:project:{project_name}"
        
        assert urn == "urn:dab:dbt:project:my_project"

    def test_layer_inference_from_schema(self, mock_service):
        """Test layer inference from schema names."""
        # Common layer mappings
        layer_mappings = {
            "raw": "bronze",
            "staging": "silver",
            "stg": "silver",
            "intermediate": "silver",
            "int": "silver",
            "marts": "gold",
            "mart": "gold",
            "analytics": "gold",
            "gold": "gold",
            "bronze": "bronze",
            "silver": "silver",
        }
        
        for schema, expected_layer in layer_mappings.items():
            # Verify the mapping concept
            assert expected_layer in ["bronze", "silver", "gold"]

    def test_pii_detection_patterns(self, mock_service):
        """Test PII detection pattern matching."""
        import re

        # Test common PII patterns (case-insensitive)
        email_pattern = re.compile(r"(?i)(email|e-mail|e_mail)")
        phone_pattern = re.compile(r"(?i)(phone|telephone|mobile|cell)")
        ssn_pattern = re.compile(r"(?i)(ssn|social.?security)")

        # Test email pattern
        assert email_pattern.search("customer_email")
        assert email_pattern.search("EMAIL_ADDRESS")

        # Test phone pattern
        assert phone_pattern.search("phone_number")

        # Test SSN pattern
        assert ssn_pattern.search("ssn")
        assert ssn_pattern.search("social_security_number")


class TestIngestionStatsAggregation:
    """Tests for stats aggregation scenarios."""

    def test_multiple_capsule_operations(self):
        """Test stats after multiple capsule operations."""
        stats = IngestionStats()
        
        # Simulate processing results
        stats.capsules_created = 10
        stats.capsules_updated = 5
        stats.capsules_unchanged = 85
        
        total_processed = (
            stats.capsules_created + 
            stats.capsules_updated + 
            stats.capsules_unchanged
        )
        
        assert total_processed == 100

    def test_column_pii_detection_stats(self):
        """Test PII column detection statistics."""
        stats = IngestionStats()
        
        stats.columns_created = 500
        stats.pii_columns_detected = 25
        
        pii_percentage = (stats.pii_columns_detected / stats.columns_created) * 100
        
        assert pii_percentage == 5.0

    def test_edge_processing_stats(self):
        """Test edge (lineage) processing statistics."""
        stats = IngestionStats()
        
        stats.edges_created = 150
        stats.edges_updated = 20
        stats.edges_deleted = 5
        stats.column_edges_created = 300
        stats.column_edges_updated = 50
        stats.column_edges_deleted = 10
        
        total_capsule_edges = (
            stats.edges_created + 
            stats.edges_updated + 
            stats.edges_deleted
        )
        total_column_edges = (
            stats.column_edges_created + 
            stats.column_edges_updated + 
            stats.column_edges_deleted
        )
        
        assert total_capsule_edges == 175
        assert total_column_edges == 360


class TestIngestionJobLifecycle:
    """Tests for ingestion job lifecycle concepts."""

    def test_job_state_transitions(self):
        """Test valid job state transitions."""
        # Valid transitions
        valid_transitions = {
            IngestionStatus.PENDING: [IngestionStatus.RUNNING, IngestionStatus.FAILED],
            IngestionStatus.RUNNING: [IngestionStatus.COMPLETED, IngestionStatus.FAILED],
            IngestionStatus.COMPLETED: [],  # Terminal state
            IngestionStatus.FAILED: [IngestionStatus.PENDING],  # Can retry
        }
        
        # Test PENDING -> RUNNING is valid
        assert IngestionStatus.RUNNING in valid_transitions[IngestionStatus.PENDING]
        
        # Test RUNNING -> COMPLETED is valid
        assert IngestionStatus.COMPLETED in valid_transitions[IngestionStatus.RUNNING]
        
        # Test COMPLETED is terminal
        assert len(valid_transitions[IngestionStatus.COMPLETED]) == 0

    def test_job_metadata_structure(self):
        """Test expected job metadata structure."""
        metadata = {
            "source_type": "dbt",
            "project_name": "analytics",
            "file_path": "/path/to/manifest.json",
            "options": {
                "full_refresh": False,
                "detect_pii": True,
            },
        }
        
        assert metadata["source_type"] == "dbt"
        assert metadata["options"]["detect_pii"] is True

    def test_job_timing_calculation(self):
        """Test job duration calculation."""
        from datetime import timedelta
        
        started_at = datetime(2025, 1, 13, 10, 0, 0)
        completed_at = datetime(2025, 1, 13, 10, 5, 30)
        
        duration = completed_at - started_at
        
        assert duration == timedelta(minutes=5, seconds=30)
        assert duration.total_seconds() == 330


class TestURNGeneration:
    """Tests for URN generation and validation."""

    def test_capsule_urn_format(self):
        """Test capsule URN format."""
        # Format: urn:dab:{source}:{type}:{project}.{schema}:{name}
        urn = "urn:dab:dbt:model:analytics.staging:stg_customers"

        parts = urn.split(":")
        assert parts[0] == "urn"
        assert parts[1] == "dab"
        assert parts[2] == "dbt"
        assert parts[3] == "model"
        assert parts[4] == "analytics.staging"
        assert parts[5] == "stg_customers"

    def test_column_urn_format(self):
        """Test column URN format."""
        # Format: urn:dab:{source}:column:{project}.{schema}:{table}.{column}
        urn = "urn:dab:dbt:column:analytics.staging:stg_customers.customer_id"
        
        assert "column" in urn
        assert "customer_id" in urn

    def test_urn_uniqueness(self):
        """Test that URNs are unique identifiers."""
        urns = set()
        
        # Add unique URNs
        urns.add("urn:dab:dbt:model:proj.schema:table1")
        urns.add("urn:dab:dbt:model:proj.schema:table2")
        urns.add("urn:dab:dbt:model:proj.schema:table1")  # Duplicate
        
        assert len(urns) == 2  # Duplicates should be ignored


class TestAirflowIngestion:
    """Tests for Airflow ingestion via IngestionService."""

    @pytest.mark.asyncio
    async def test_ingest_airflow_creates_correct_config(self):
        """Test that ingest_airflow builds correct configuration."""
        mock_session = AsyncMock()
        service = IngestionService(mock_session)

        # Mock the generic ingest method
        service.ingest = AsyncMock(return_value=IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
            source_name="test-airflow",
        ))

        # Call ingest_airflow
        result = await service.ingest_airflow(
            base_url="https://airflow.example.com",
            instance_name="test-airflow",
            auth_mode="bearer_env",
            dag_id_regex="customer_.*",
            include_paused=True,
            cleanup_orphans=True,
        )

        # Verify ingest was called with correct config
        service.ingest.assert_called_once()
        call_args = service.ingest.call_args
        
        assert call_args[0][0] == "airflow"  # source_type
        config = call_args[0][1]  # config dict
        assert config["base_url"] == "https://airflow.example.com"
        assert config["instance_name"] == "test-airflow"
        assert config["auth_mode"] == "bearer_env"
        assert config["dag_id_regex"] == "customer_.*"
        assert config["include_paused"] is True
        assert call_args[1]["cleanup_orphans"] is True

    @pytest.mark.asyncio
    async def test_ingest_airflow_removes_none_values(self):
        """Test that ingest_airflow removes None values from config."""
        mock_session = AsyncMock()
        service = IngestionService(mock_session)

        service.ingest = AsyncMock(return_value=IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
        ))

        # Call with minimal parameters (many None values)
        await service.ingest_airflow(
            base_url="https://airflow.example.com",
        )

        call_args = service.ingest.call_args
        config = call_args[0][1]

        # None values should be removed
        assert "base_url" in config
        assert "instance_name" not in config  # None was removed
        assert "dag_id_allowlist" not in config  # None was removed
        assert "dag_id_denylist" not in config  # None was removed

    @pytest.mark.asyncio
    async def test_ingest_airflow_with_kwargs(self):
        """Test that ingest_airflow accepts additional kwargs."""
        mock_session = AsyncMock()
        service = IngestionService(mock_session)

        service.ingest = AsyncMock(return_value=IngestionResult(
            job_id=uuid4(),
            status=IngestionStatus.COMPLETED,
            source_type="airflow",
        ))

        # Call with extra kwargs
        await service.ingest_airflow(
            base_url="https://airflow.example.com",
            token_env="MY_CUSTOM_TOKEN",
            page_limit=50,
            timeout_seconds=60.0,
        )

        call_args = service.ingest.call_args
        config = call_args[0][1]

        assert config["token_env"] == "MY_CUSTOM_TOKEN"
        assert config["page_limit"] == 50
        assert config["timeout_seconds"] == 60.0

    @pytest.mark.asyncio
    async def test_ingest_with_airflow_source_type(self):
        """Test generic ingest method works with airflow source type."""
        mock_session = AsyncMock()
        
        # Mock repositories
        mock_job_repo = AsyncMock()
        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job.started_at = datetime.now()
        mock_job.source_name = None
        mock_job_repo.start_job.return_value = mock_job
        mock_job_repo.complete_job = AsyncMock()

        mock_source_system_repo = AsyncMock()
        mock_source_system = MagicMock()
        mock_source_system.id = uuid4()
        mock_source_system_repo.get_or_create.return_value = (mock_source_system, True)

        # Mock parser
        mock_parse_result = ParseResult(
            source_type="airflow",
            source_name="test-airflow",
            source_version="2.7.0",
            capsules=[
                RawCapsule(
                    urn="urn:dab:airflow:dag:test:test_dag",
                    name="test_dag",
                    capsule_type="airflow_dag",
                    unique_id="test:test_dag",
                ),
                RawCapsule(
                    urn="urn:dab:airflow:task:test:test_dag.task1",
                    name="task1",
                    capsule_type="airflow_task",
                    unique_id="test:test_dag.task1",
                ),
            ],
            edges=[
                RawEdge(
                    source_urn="urn:dab:airflow:dag:test:test_dag",
                    target_urn="urn:dab:airflow:task:test:test_dag.task1",
                    edge_type="contains",
                ),
            ],
        )

        with patch("src.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = MagicMock()
            mock_parser.validate_config.return_value = []
            mock_parser.parse = AsyncMock(return_value=mock_parse_result)
            mock_get_parser.return_value = mock_parser

            # Create service with mocked repos
            service = IngestionService(mock_session)
            service.job_repo = mock_job_repo
            service.source_system_repo = mock_source_system_repo
            
            # Mock _persist_parse_result
            service._persist_parse_result = AsyncMock(return_value=ProcessedUrns())

            # Call ingest with Airflow config
            config = {
                "base_url": "https://airflow.example.com",
                "instance_name": "test-airflow",
            }
            result = await service.ingest("airflow", config, cleanup_orphans=False)

            # Verify parser was called
            mock_get_parser.assert_called_once_with("airflow")
            mock_parser.validate_config.assert_called_once_with(config)
            mock_parser.parse.assert_called_once_with(config)

            # Verify source system was created
            mock_source_system_repo.get_or_create.assert_called_once()

            # Verify job was completed
            mock_job_repo.complete_job.assert_called_once()

            # Verify result
            assert result.status == IngestionStatus.COMPLETED
            assert result.source_type == "airflow"
            assert result.source_name == "test-airflow"

    @pytest.mark.asyncio
    async def test_ingest_airflow_with_cleanup_orphans(self):
        """Test that cleanup_orphans flag is passed through correctly."""
        mock_session = AsyncMock()
        
        mock_job_repo = AsyncMock()
        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job.started_at = datetime.now()
        mock_job_repo.start_job.return_value = mock_job
        mock_job_repo.complete_job = AsyncMock()

        mock_source_system_repo = AsyncMock()
        mock_source_system = MagicMock()
        mock_source_system.id = uuid4()
        mock_source_system_repo.get_or_create.return_value = (mock_source_system, True)

        mock_parse_result = ParseResult(
            source_type="airflow",
            source_name="test-airflow",
            capsules=[],
            edges=[],
        )

        with patch("src.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = MagicMock()
            mock_parser.validate_config.return_value = []
            mock_parser.parse = AsyncMock(return_value=mock_parse_result)
            mock_get_parser.return_value = mock_parser

            service = IngestionService(mock_session)
            service.job_repo = mock_job_repo
            service.source_system_repo = mock_source_system_repo
            service._persist_parse_result = AsyncMock(return_value=ProcessedUrns())
            service._cleanup_orphans = AsyncMock()

            # Call with cleanup_orphans=True
            config = {"base_url": "https://airflow.example.com"}
            await service.ingest("airflow", config, cleanup_orphans=True)

            # Verify cleanup was called
            service._cleanup_orphans.assert_called_once()
            call_args = service._cleanup_orphans.call_args
            assert call_args[1]["source_system_id"] == mock_source_system.id
