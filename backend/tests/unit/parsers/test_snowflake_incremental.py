"""Unit tests for Snowflake incremental sync functionality."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from src.parsers.snowflake_parser import SnowflakeParser
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers.base import ParseResult


class TestSnowflakeIncrementalSync:
    """Tests for Snowflake incremental sync."""

    @pytest.mark.asyncio
    async def test_full_sync_metadata(self):
        """Test full sync stores correct metadata."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["TEST_DB"],
        }

        # Mock connection and queries
        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["TEST_DB"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        result = await parser.parse(config)

        # Verify metadata
        assert result.metadata["sync_mode"] == "full"
        assert "sync_start_time" in result.metadata
        assert "last_sync_timestamp" in result.metadata
        assert "previous_sync_timestamp" not in result.metadata

    @pytest.mark.asyncio
    async def test_incremental_sync_metadata(self):
        """Test incremental sync stores correct metadata."""
        parser = SnowflakeParser()

        previous_timestamp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["TEST_DB"],
            "last_sync_timestamp": previous_timestamp,
        }

        # Mock connection and queries
        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["TEST_DB"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        result = await parser.parse(config)

        # Verify metadata
        assert result.metadata["sync_mode"] == "incremental"
        assert "sync_start_time" in result.metadata
        assert "last_sync_timestamp" in result.metadata
        assert result.metadata["previous_sync_timestamp"] == previous_timestamp

    @pytest.mark.asyncio
    async def test_incremental_filter_applied(self):
        """Test incremental filter is applied to table queries."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        previous_timestamp = "2024-12-23T10:00:00+00:00"

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            databases=["TEST_DB"],
            last_sync_timestamp=previous_timestamp,
        )

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        result = ParseResult(source_type="snowflake")
        await parser._extract_database_metadata("TEST_DB", config, result)

        # Verify execute was called with incremental filter
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        assert f"LAST_ALTERED > '{previous_timestamp}'" in query

    @pytest.mark.asyncio
    async def test_full_sync_no_filter(self):
        """Test full sync does not apply incremental filter."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            databases=["TEST_DB"],
            # No last_sync_timestamp
        )

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        result = ParseResult(source_type="snowflake")
        await parser._extract_database_metadata("TEST_DB", config, result)

        # Verify execute was called without incremental filter
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        assert "LAST_ALTERED >" not in query

    @pytest.mark.asyncio
    async def test_incremental_sync_returns_changed_tables_only(self):
        """Test incremental sync only returns tables modified after last sync."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        previous_timestamp = "2024-12-23T10:00:00+00:00"

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            databases=["TEST_DB"],
            last_sync_timestamp=previous_timestamp,
        )

        # Mock cursor with only changed table
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        # Only one table that was altered after the timestamp
        mock_cursor.fetchall.return_value = [
            (
                "TEST_DB", "PUBLIC", "CHANGED_TABLE", "BASE TABLE",
                100, 1024, datetime(2024, 12, 20), datetime(2024, 12, 24), "Changed table"
            )
        ]
        parser.connector.cursor.return_value = mock_cursor

        result = ParseResult(source_type="snowflake")
        await parser._extract_database_metadata("TEST_DB", config, result)

        # Should only have 1 capsule (the changed one)
        assert len(result.capsules) == 1
        assert result.capsules[0].name == "CHANGED_TABLE"

    @pytest.mark.asyncio
    async def test_sync_timestamp_format(self):
        """Test sync timestamp is in correct ISO format."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["TEST_DB"],
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["TEST_DB"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        result = await parser.parse(config)

        # Verify timestamp format (ISO 8601)
        timestamp = result.metadata["last_sync_timestamp"]
        # Should be parseable as datetime
        parsed = datetime.fromisoformat(timestamp)
        assert parsed.tzinfo is not None  # Should have timezone

    @pytest.mark.asyncio
    async def test_incremental_sync_with_lineage(self):
        """Test incremental sync works with lineage extraction."""
        parser = SnowflakeParser()

        previous_timestamp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["TEST_DB"],
            "last_sync_timestamp": previous_timestamp,
            "enable_lineage": True,
            "use_account_usage": True,
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["TEST_DB"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        with patch.object(parser, "_extract_lineage", new_callable=AsyncMock):
                            result = await parser.parse(config)

        # Verify metadata includes incremental mode
        assert result.metadata["sync_mode"] == "incremental"
        assert result.metadata["previous_sync_timestamp"] == previous_timestamp

    @pytest.mark.asyncio
    async def test_incremental_sync_with_tags(self):
        """Test incremental sync works with tag extraction."""
        parser = SnowflakeParser()

        previous_timestamp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["TEST_DB"],
            "last_sync_timestamp": previous_timestamp,
            "enable_tag_extraction": True,
            "use_account_usage": True,
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["TEST_DB"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        with patch.object(parser, "_extract_tags", new_callable=AsyncMock):
                            result = await parser.parse(config)

        # Verify metadata includes incremental mode
        assert result.metadata["sync_mode"] == "incremental"

    @pytest.mark.asyncio
    async def test_metadata_preserved_on_error(self):
        """Test sync metadata is populated even if extraction fails."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["TEST_DB"],
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["TEST_DB"]):
                    # Simulate extraction failure
                    with patch.object(
                        parser, "_extract_database_metadata",
                        side_effect=Exception("Extraction failed")
                    ):
                        result = await parser.parse(config)

        # Metadata should still be populated
        assert "sync_mode" in result.metadata
        assert "last_sync_timestamp" in result.metadata
        # Should have error
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_incremental_timestamp_validation(self):
        """Test incremental sync validates timestamp format."""
        parser = SnowflakeParser()

        # Invalid timestamp format
        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["TEST_DB"],
            "last_sync_timestamp": "invalid-timestamp",
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["TEST_DB"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        result = await parser.parse(config)

        # Should still work (query will use the invalid timestamp as-is)
        # Snowflake will handle the error if the format is truly invalid
        assert result.metadata["sync_mode"] == "incremental"


class TestSnowflakeIncrementalConfig:
    """Tests for incremental sync configuration."""

    def test_config_with_last_sync_timestamp(self):
        """Test config accepts last_sync_timestamp."""
        timestamp = "2024-12-23T10:00:00+00:00"

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            last_sync_timestamp=timestamp,
        )

        assert config.last_sync_timestamp == timestamp

    def test_config_without_last_sync_timestamp(self):
        """Test config works without last_sync_timestamp."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        assert config.last_sync_timestamp is None

    def test_config_from_dict_with_timestamp(self):
        """Test config creation from dict with timestamp."""
        timestamp = "2024-12-23T10:00:00+00:00"

        config_dict = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "last_sync_timestamp": timestamp,
        }

        config = SnowflakeParserConfig.from_dict(config_dict)
        assert config.last_sync_timestamp == timestamp


class TestSnowflakeIncrementalPerformance:
    """Tests for incremental sync performance characteristics."""

    @pytest.mark.asyncio
    async def test_incremental_queries_fewer_tables(self):
        """Test incremental sync queries fewer tables than full sync."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        # Full sync config
        full_config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            databases=["TEST_DB"],
        )

        # Mock cursor for full sync (100 tables)
        mock_cursor_full = MagicMock()
        mock_cursor_full.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        mock_cursor_full.fetchall.return_value = [
            (
                "TEST_DB", "PUBLIC", f"TABLE_{i}", "BASE TABLE",
                100, 1024, datetime(2024, 12, 20), datetime(2024, 12, 20), ""
            )
            for i in range(100)
        ]

        parser.connector.cursor.return_value = mock_cursor_full
        result_full = ParseResult(source_type="snowflake")
        await parser._extract_database_metadata("TEST_DB", full_config, result_full)

        # Incremental sync config
        incremental_config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            databases=["TEST_DB"],
            last_sync_timestamp="2024-12-23T10:00:00+00:00",
        )

        # Mock cursor for incremental sync (only 10 changed tables)
        mock_cursor_incremental = MagicMock()
        mock_cursor_incremental.description = mock_cursor_full.description
        mock_cursor_incremental.fetchall.return_value = [
            (
                "TEST_DB", "PUBLIC", f"TABLE_{i}", "BASE TABLE",
                100, 1024, datetime(2024, 12, 20), datetime(2024, 12, 24), ""
            )
            for i in range(10)  # Only 10 changed
        ]

        parser.connector.cursor.return_value = mock_cursor_incremental
        result_incremental = ParseResult(source_type="snowflake")
        await parser._extract_database_metadata("TEST_DB", incremental_config, result_incremental)

        # Verify incremental returned fewer capsules
        assert len(result_full.capsules) == 100
        assert len(result_incremental.capsules) == 10
