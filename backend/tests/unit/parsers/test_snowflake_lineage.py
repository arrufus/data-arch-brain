"""Unit tests for Snowflake lineage extraction."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.parsers.snowflake_parser import SnowflakeParser
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers.base import ParseResult, RawCapsule


class TestSnowflakeLineageExtraction:
    """Tests for Snowflake lineage extraction."""

    def test_build_urn_from_fqn(self):
        """Test building URN from fully qualified name."""
        parser = SnowflakeParser()

        # Standard FQN
        urn = parser._build_urn_from_fqn("PROD.RAW_DATA.CUSTOMERS")
        assert urn == "urn:dcs:snowflake:table:PROD.RAW_DATA:CUSTOMERS"

        # Different case
        urn = parser._build_urn_from_fqn("analytics.marts.customer_summary")
        assert urn == "urn:dcs:snowflake:table:analytics.marts:customer_summary"

    def test_build_urn_from_fqn_malformed(self):
        """Test building URN from malformed FQN."""
        parser = SnowflakeParser()

        # Only two parts
        urn = parser._build_urn_from_fqn("PROD.CUSTOMERS")
        assert "urn:dcs:snowflake:table:::" in urn
        assert "PROD.CUSTOMERS" in urn

        # Only one part
        urn = parser._build_urn_from_fqn("CUSTOMERS")
        assert "urn:dcs:snowflake:table:::" in urn

    @pytest.mark.asyncio
    async def test_extract_lineage_basic(self):
        """Test basic lineage extraction."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_lineage=True,
            use_account_usage=True,
        )

        # Create parse result with some capsules
        result = ParseResult(source_type="snowflake")
        result.capsules.extend([
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.RAW:SOURCE",
                name="SOURCE",
                capsule_type="table",
                unique_id="PROD.RAW.SOURCE",
                database_name="PROD",
                schema_name="RAW",
            ),
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.STAGING:TARGET",
                name="TARGET",
                capsule_type="table",
                unique_id="PROD.STAGING.TARGET",
                database_name="PROD",
                schema_name="STAGING",
            ),
        ])

        # Mock lineage query results
        lineage_data = [
            {
                "source_object": "PROD.RAW.SOURCE",
                "target_object": "PROD.STAGING.TARGET",
                "query_count": 10,
                "last_query_time": datetime(2024, 12, 1, 10, 0, 0),
            }
        ]

        with patch.object(parser, "_query_lineage", return_value=lineage_data):
            await parser._extract_lineage(config, result, ["PROD"])

        # Verify edge was created
        assert len(result.edges) == 1
        edge = result.edges[0]
        assert edge.source_urn == "urn:dcs:snowflake:table:PROD.RAW:SOURCE"
        assert edge.target_urn == "urn:dcs:snowflake:table:PROD.STAGING:TARGET"
        assert edge.edge_type == "flows_to"
        assert edge.transformation == "query"
        assert edge.meta["query_count"] == 10
        assert edge.meta["source"] == "snowflake_access_history"

    @pytest.mark.asyncio
    async def test_extract_lineage_deduplication(self):
        """Test lineage de-duplication aggregates query counts."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_lineage=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")
        result.capsules.extend([
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.RAW:SOURCE",
                name="SOURCE",
                capsule_type="table",
                unique_id="PROD.RAW.SOURCE",
                database_name="PROD",
                schema_name="RAW",
            ),
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.STAGING:TARGET",
                name="TARGET",
                capsule_type="table",
                unique_id="PROD.STAGING.TARGET",
                database_name="PROD",
                schema_name="STAGING",
            ),
        ])

        # Mock duplicate lineage relationships (should be de-duplicated)
        lineage_data = [
            {
                "source_object": "PROD.RAW.SOURCE",
                "target_object": "PROD.STAGING.TARGET",
                "query_count": 10,
                "last_query_time": datetime(2024, 12, 1, 10, 0, 0),
            },
            {
                "source_object": "PROD.RAW.SOURCE",
                "target_object": "PROD.STAGING.TARGET",
                "query_count": 5,
                "last_query_time": datetime(2024, 12, 2, 10, 0, 0),
            },
        ]

        with patch.object(parser, "_query_lineage", return_value=lineage_data):
            await parser._extract_lineage(config, result, ["PROD"])

        # Should have only 1 edge with aggregated query count
        assert len(result.edges) == 1
        edge = result.edges[0]
        assert edge.meta["query_count"] == 15  # 10 + 5
        assert "2024-12-02" in edge.meta["last_query_time"]  # Should use latest timestamp

    @pytest.mark.asyncio
    async def test_extract_lineage_skip_missing_objects(self):
        """Test lineage skips edges where objects are not in capsules."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_lineage=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")
        # Only add one capsule
        result.capsules.append(
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.RAW:SOURCE",
                name="SOURCE",
                capsule_type="table",
                unique_id="PROD.RAW.SOURCE",
                database_name="PROD",
                schema_name="RAW",
            )
        )

        # Lineage references a target that doesn't exist
        lineage_data = [
            {
                "source_object": "PROD.RAW.SOURCE",
                "target_object": "PROD.STAGING.MISSING",  # Not in capsules
                "query_count": 10,
                "last_query_time": datetime(2024, 12, 1, 10, 0, 0),
            }
        ]

        with patch.object(parser, "_query_lineage", return_value=lineage_data):
            await parser._extract_lineage(config, result, ["PROD"])

        # Should have no edges (missing target)
        assert len(result.edges) == 0

    @pytest.mark.asyncio
    async def test_extract_lineage_skip_self_references(self):
        """Test lineage skips self-referencing edges."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_lineage=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")
        result.capsules.append(
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.RAW:TABLE1",
                name="TABLE1",
                capsule_type="table",
                unique_id="PROD.RAW.TABLE1",
                database_name="PROD",
                schema_name="RAW",
            )
        )

        # Self-referencing lineage
        lineage_data = [
            {
                "source_object": "PROD.RAW.TABLE1",
                "target_object": "PROD.RAW.TABLE1",  # Same table
                "query_count": 1,
                "last_query_time": datetime(2024, 12, 1, 10, 0, 0),
            }
        ]

        with patch.object(parser, "_query_lineage", return_value=lineage_data):
            await parser._extract_lineage(config, result, ["PROD"])

        # Should have no edges (self-reference)
        assert len(result.edges) == 0

    @pytest.mark.asyncio
    async def test_extract_lineage_multiple_edges(self):
        """Test extracting multiple lineage edges."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_lineage=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")
        result.capsules.extend([
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.RAW:SOURCE1",
                name="SOURCE1",
                capsule_type="table",
                unique_id="PROD.RAW.SOURCE1",
                database_name="PROD",
                schema_name="RAW",
            ),
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.RAW:SOURCE2",
                name="SOURCE2",
                capsule_type="table",
                unique_id="PROD.RAW.SOURCE2",
                database_name="PROD",
                schema_name="RAW",
            ),
            RawCapsule(
                urn="urn:dcs:snowflake:table:PROD.STAGING:TARGET",
                name="TARGET",
                capsule_type="table",
                unique_id="PROD.STAGING.TARGET",
                database_name="PROD",
                schema_name="STAGING",
            ),
        ])

        # Multiple lineage relationships
        lineage_data = [
            {
                "source_object": "PROD.RAW.SOURCE1",
                "target_object": "PROD.STAGING.TARGET",
                "query_count": 10,
                "last_query_time": datetime(2024, 12, 1, 10, 0, 0),
            },
            {
                "source_object": "PROD.RAW.SOURCE2",
                "target_object": "PROD.STAGING.TARGET",
                "query_count": 5,
                "last_query_time": datetime(2024, 12, 1, 11, 0, 0),
            },
        ]

        with patch.object(parser, "_query_lineage", return_value=lineage_data):
            await parser._extract_lineage(config, result, ["PROD"])

        # Should have 2 distinct edges
        assert len(result.edges) == 2
        source_urns = {edge.source_urn for edge in result.edges}
        assert "urn:dcs:snowflake:table:PROD.RAW:SOURCE1" in source_urns
        assert "urn:dcs:snowflake:table:PROD.RAW:SOURCE2" in source_urns

    @pytest.mark.asyncio
    async def test_extract_lineage_error_handling(self):
        """Test lineage extraction handles errors gracefully."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            enable_lineage=True,
            use_account_usage=True,
        )

        result = ParseResult(source_type="snowflake")

        # Mock query failure
        with patch.object(parser, "_query_lineage", side_effect=Exception("Query failed")):
            await parser._extract_lineage(config, result, ["PROD"])

        # Should add error to result
        assert len(result.errors) > 0
        assert any("lineage" in str(e).lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_query_lineage_with_database_filter(self):
        """Test lineage query builds correct database filter."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            lineage_lookback_days=14,
        )

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [("source_object",), ("target_object",), ("query_count",)]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        await parser._query_lineage(config, ["PROD", "ANALYTICS"])

        # Verify execute was called with database filter
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        assert "'PROD'" in query
        assert "'ANALYTICS'" in query
        assert "SPLIT_PART" in query

        # Verify lookback days parameter
        params = execute_call[0][1]
        assert params["lookback_days"] == 14

    @pytest.mark.asyncio
    async def test_query_lineage_no_database_filter(self):
        """Test lineage query without database filter."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test",
            user="test",
            password="test",
            lineage_lookback_days=7,
        )

        mock_cursor = MagicMock()
        mock_cursor.description = [("source_object",), ("target_object",), ("query_count",)]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        await parser._query_lineage(config, [])

        # Verify execute was called without database filter
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        # Database filter placeholder should be empty
        assert "AND SPLIT_PART" not in query or "IN ()" not in query
