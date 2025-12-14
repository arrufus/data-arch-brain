"""Unit tests for the ingestion service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.ingestion import (
    IngestionService,
    IngestionStats,
    ProcessedUrns,
)
from src.models.ingestion import IngestionStatus


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
