"""Unit tests for column lineage parsing."""

import pytest
from pathlib import Path

from src.parsers.base import RawColumnEdge, ParseResult
from src.parsers.dbt_parser import DbtParser


class TestColumnLineageParsing:
    """Tests for column-level lineage extraction."""

    @pytest.fixture
    def parser(self):
        """Create a DbtParser instance."""
        return DbtParser()

    def test_raw_column_edge_creation(self):
        """Test creating a RawColumnEdge."""
        edge = RawColumnEdge(
            source_column_urn="urn:dab:column:project.schema:source_table.col1",
            target_column_urn="urn:dab:column:project.schema:target_table.col2",
            transformation_type="transform",
            transformation_expr="UPPER(col1)",
            meta={"test": "value"},
        )
        
        assert edge.source_column_urn == "urn:dab:column:project.schema:source_table.col1"
        assert edge.target_column_urn == "urn:dab:column:project.schema:target_table.col2"
        assert edge.transformation_type == "transform"
        assert edge.transformation_expr == "UPPER(col1)"

    def test_parse_result_includes_column_edges(self):
        """Test that ParseResult includes column_edges field."""
        result = ParseResult()
        
        assert hasattr(result, "column_edges")
        assert result.column_edges == []

    def test_parse_result_summary_includes_column_edges(self):
        """Test that ParseResult summary includes column_edges count."""
        result = ParseResult()
        result.column_edges.append(
            RawColumnEdge(
                source_column_urn="urn:source:col",
                target_column_urn="urn:target:col",
            )
        )
        
        summary = result.summary()
        assert "column_edges" in summary
        assert summary["column_edges"] == 1

    @pytest.mark.asyncio
    async def test_build_column_lineage_empty_manifest(self, parser):
        """Test column lineage building with no column depends."""
        # Create a minimal ParseResult
        result = ParseResult(source_type="dbt")
        
        # Empty manifest
        manifest = {"nodes": {}}
        urn_lookup = {}
        column_urn_lookup = {}
        
        # This shouldn't raise an error
        parser._build_column_lineage(manifest, result, urn_lookup, column_urn_lookup)
        
        assert result.column_edges == []

    def test_resolve_column_ref_valid(self, parser):
        """Test resolving a valid column reference."""
        urn_lookup = {
            "model.project.table": "urn:dab:model:project.schema:table"
        }
        column_urn_lookup = {
            "model.project.table.column_a": "urn:dab:column:project.schema:table.column_a"
        }
        
        resolved = parser._resolve_column_ref(
            "model.project.table.column_a",
            urn_lookup,
            column_urn_lookup,
        )
        
        assert resolved == "urn:dab:column:project.schema:table.column_a"

    def test_resolve_column_ref_invalid_format(self, parser):
        """Test resolving an invalid column reference."""
        urn_lookup = {}
        column_urn_lookup = {}
        
        # Missing column name (only one dot)
        resolved = parser._resolve_column_ref(
            "invalid_ref",
            urn_lookup,
            column_urn_lookup,
        )
        
        assert resolved is None

    def test_resolve_column_ref_not_found(self, parser):
        """Test resolving a column reference that doesn't exist."""
        urn_lookup = {}
        column_urn_lookup = {}
        
        resolved = parser._resolve_column_ref(
            "model.project.table.nonexistent",
            urn_lookup,
            column_urn_lookup,
        )
        
        assert resolved is None


class TestIngestionStats:
    """Tests for IngestionStats with delta reporting."""

    def test_stats_includes_deleted_fields(self):
        """Test that IngestionStats includes deleted fields."""
        from src.services.ingestion import IngestionStats
        
        stats = IngestionStats()
        
        assert hasattr(stats, "capsules_deleted")
        assert hasattr(stats, "columns_deleted")
        assert hasattr(stats, "edges_deleted")
        assert hasattr(stats, "column_edges_deleted")

    def test_stats_to_dict_includes_deleted(self):
        """Test that to_dict includes deleted counts."""
        from src.services.ingestion import IngestionStats
        
        stats = IngestionStats(
            capsules_created=5,
            capsules_updated=3,
            capsules_deleted=2,
        )
        
        d = stats.to_dict()
        
        assert d["capsules_deleted"] == 2

    def test_total_changes(self):
        """Test total_changes property."""
        from src.services.ingestion import IngestionStats
        
        stats = IngestionStats(
            capsules_created=5,
            capsules_updated=3,
            capsules_deleted=2,
            columns_created=10,
            columns_updated=5,
            columns_deleted=1,
            edges_created=20,
            edges_updated=10,
            edges_deleted=5,
        )
        
        # 5+3+2 + 10+5+1 + 20+10+5 + 0+0+0 = 61
        assert stats.total_changes == 61

    def test_delta_summary(self):
        """Test delta_summary method."""
        from src.services.ingestion import IngestionStats
        
        stats = IngestionStats(
            capsules_created=5,
            capsules_updated=3,
            capsules_deleted=2,
        )
        
        summary = stats.delta_summary()
        
        assert summary["capsules"]["created"] == 5
        assert summary["capsules"]["updated"] == 3
        assert summary["capsules"]["deleted"] == 2


class TestProcessedUrns:
    """Tests for ProcessedUrns tracking."""

    def test_processed_urns_initialization(self):
        """Test ProcessedUrns default initialization."""
        from src.services.ingestion import ProcessedUrns
        
        processed = ProcessedUrns()
        
        assert processed.capsule_urns == set()
        assert processed.column_urns == set()
        assert processed.edge_keys == set()
        assert processed.column_edge_keys == set()

    def test_processed_urns_tracking(self):
        """Test adding URNs to ProcessedUrns."""
        from src.services.ingestion import ProcessedUrns
        
        processed = ProcessedUrns()
        
        processed.capsule_urns.add("urn:dab:model:project:table1")
        processed.capsule_urns.add("urn:dab:model:project:table2")
        processed.column_urns.add("urn:dab:column:project:table1.col1")
        processed.edge_keys.add(("urn:source", "urn:target"))
        
        assert len(processed.capsule_urns) == 2
        assert "urn:dab:model:project:table1" in processed.capsule_urns
        assert "urn:dab:column:project:table1.col1" in processed.column_urns
        assert ("urn:source", "urn:target") in processed.edge_keys
