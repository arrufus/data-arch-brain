"""Unit tests for Snowflake performance optimizations."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from src.parsers.snowflake_parser import SnowflakeParser
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers.base import ParseResult


class TestSnowflakeParallelExecution:
    """Tests for parallel database extraction."""

    @pytest.mark.asyncio
    async def test_parallel_execution_enabled(self):
        """Test parallel execution processes databases concurrently."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["DB1", "DB2", "DB3"],
            "parallel_execution": True,
        }

        # Mock connection and extraction
        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["DB1", "DB2", "DB3"]):
                    # Track extraction calls
                    extraction_calls = []

                    async def track_extraction(database, cfg, res):
                        extraction_calls.append(database)

                    with patch.object(parser, "_extract_database_metadata", side_effect=track_extraction):
                        result = await parser.parse(config)

        # Verify all databases were extracted
        assert len(extraction_calls) == 3
        assert "DB1" in extraction_calls
        assert "DB2" in extraction_calls
        assert "DB3" in extraction_calls

        # Verify metadata indicates parallel execution
        assert result.metadata["performance"]["parallel_execution"] is True

    @pytest.mark.asyncio
    async def test_parallel_execution_disabled(self):
        """Test sequential execution when parallel is disabled."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["DB1", "DB2"],
            "parallel_execution": False,
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["DB1", "DB2"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        result = await parser.parse(config)

        # Verify metadata indicates sequential execution
        assert result.metadata["performance"]["parallel_execution"] is False

    @pytest.mark.asyncio
    async def test_single_database_sequential(self):
        """Test single database uses sequential execution."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["DB1"],
            "parallel_execution": True,  # Even if enabled, single DB is sequential
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["DB1"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        result = await parser.parse(config)

        # Single database, so sequential even with parallel enabled
        assert result.metadata["performance"]["databases_processed"] == 1


class TestSnowflakeQueryCache:
    """Tests for query result caching."""

    @pytest.mark.asyncio
    async def test_cache_enabled(self):
        """Test query cache is enabled by default."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "enable_query_cache": True,
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=[]):
                    result = await parser.parse(config)

        assert result.metadata["performance"]["cache_enabled"] is True

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test query cache can be disabled."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "enable_query_cache": False,
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=[]):
                    result = await parser.parse(config)

        assert result.metadata["performance"]["cache_enabled"] is False

    @pytest.mark.asyncio
    async def test_database_list_cached(self):
        """Test database list is cached on repeated calls."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()
        parser._cache_enabled = True

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock cursor to return databases
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("DB1",), ("DB2",)]
        parser.connector.cursor.return_value = mock_cursor

        result = ParseResult(source_type="snowflake")

        # First call - should query
        databases1 = await parser._get_databases(config, result)
        assert databases1 == ["DB1", "DB2"]
        assert mock_cursor.execute.call_count == 1

        # Second call - should use cache
        databases2 = await parser._get_databases(config, result)
        assert databases2 == ["DB1", "DB2"]
        assert mock_cursor.execute.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_cache_bypassed_when_disabled(self):
        """Test cache is bypassed when disabled."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()
        parser._cache_enabled = False

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("DB1",)]
        parser.connector.cursor.return_value = mock_cursor

        result = ParseResult(source_type="snowflake")

        # First call
        await parser._get_databases(config, result)
        assert mock_cursor.execute.call_count == 1

        # Second call - should query again (no cache)
        await parser._get_databases(config, result)
        assert mock_cursor.execute.call_count == 2


class TestSnowflakeLineageOptimization:
    """Tests for ACCESS_HISTORY query optimization."""

    @pytest.mark.asyncio
    async def test_lineage_row_limit_applied(self):
        """Test ACCESS_HISTORY query uses row limit."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            max_lineage_rows=1000,
        )

        mock_cursor = MagicMock()
        mock_cursor.description = [("source_object",), ("target_object",), ("query_count",), ("last_query_time",)]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        await parser._query_lineage(config, ["TEST_DB"])

        # Verify query includes LIMIT
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        assert "LIMIT 1000" in query

    @pytest.mark.asyncio
    async def test_lineage_no_limit_when_disabled(self):
        """Test ACCESS_HISTORY query without limit when None."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            max_lineage_rows=None,
        )

        mock_cursor = MagicMock()
        mock_cursor.description = [("source_object",), ("target_object",), ("query_count",), ("last_query_time",)]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        await parser._query_lineage(config, ["TEST_DB"])

        # Verify query does not include LIMIT
        execute_call = mock_cursor.execute.call_args
        query = execute_call[0][0]
        assert "LIMIT" not in query


class TestSnowflakePerformanceMetrics:
    """Tests for performance metrics tracking."""

    @pytest.mark.asyncio
    async def test_performance_metrics_captured(self):
        """Test performance metrics are captured in metadata."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["DB1"],
            "parallel_execution": True,
            "enable_query_cache": True,
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["DB1"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        result = await parser.parse(config)

        # Verify performance metrics exist
        assert "performance" in result.metadata
        perf = result.metadata["performance"]

        # Verify required metrics
        assert "total_duration_seconds" in perf
        assert "databases_processed" in perf
        assert "capsules_extracted" in perf
        assert "columns_extracted" in perf
        assert "edges_extracted" in perf
        assert "errors_count" in perf
        assert "parallel_execution" in perf
        assert "cache_enabled" in perf

        # Verify types
        assert isinstance(perf["total_duration_seconds"], (int, float))
        assert isinstance(perf["databases_processed"], int)
        assert isinstance(perf["capsules_extracted"], int)
        assert isinstance(perf["columns_extracted"], int)
        assert isinstance(perf["edges_extracted"], int)
        assert isinstance(perf["errors_count"], int)
        assert isinstance(perf["parallel_execution"], bool)
        assert isinstance(perf["cache_enabled"], bool)

    @pytest.mark.asyncio
    async def test_sync_timing_metadata(self):
        """Test sync start and end times are captured."""
        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=[]):
                    result = await parser.parse(config)

        # Verify timing metadata
        assert "sync_start_time" in result.metadata
        assert "sync_end_time" in result.metadata

        # Verify timestamps are valid ISO format
        start_time = datetime.fromisoformat(result.metadata["sync_start_time"])
        end_time = datetime.fromisoformat(result.metadata["sync_end_time"])

        # End should be after start
        assert end_time >= start_time

    @pytest.mark.asyncio
    async def test_extraction_timing_logged(self, caplog):
        """Test extraction timing is logged."""
        import logging
        caplog.set_level(logging.INFO)

        parser = SnowflakeParser()

        config = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "databases": ["DB1"],
            "enable_lineage": True,
            "use_account_usage": True,
            "enable_tag_extraction": True,
        }

        with patch.object(parser, "_connect", new_callable=AsyncMock):
            with patch.object(parser, "_disconnect", new_callable=AsyncMock):
                with patch.object(parser, "_get_databases", return_value=["DB1"]):
                    with patch.object(parser, "_extract_database_metadata", new_callable=AsyncMock):
                        with patch.object(parser, "_extract_lineage", new_callable=AsyncMock):
                            with patch.object(parser, "_extract_tags", new_callable=AsyncMock):
                                await parser.parse(config)

        # Check logs contain timing information
        logs = [record.message for record in caplog.records]

        # Check for duration logs
        timing_logs = [log for log in logs if "in" in log.lower() and "s" in log.lower()]
        assert len(timing_logs) > 0

        # Check for completion log with metrics
        completion_logs = [log for log in logs if "complete" in log.lower()]
        assert len(completion_logs) > 0


class TestSnowflakeConfigPerformanceOptions:
    """Tests for performance-related configuration options."""

    def test_config_default_parallel_enabled(self):
        """Test parallel execution is enabled by default."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        assert config.parallel_execution is True

    def test_config_parallel_can_be_disabled(self):
        """Test parallel execution can be disabled."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            parallel_execution=False,
        )

        assert config.parallel_execution is False

    def test_config_default_cache_enabled(self):
        """Test query cache is enabled by default."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        assert config.enable_query_cache is True

    def test_config_cache_can_be_disabled(self):
        """Test query cache can be disabled."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            enable_query_cache=False,
        )

        assert config.enable_query_cache is False

    def test_config_default_lineage_limit(self):
        """Test default lineage row limit."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        assert config.max_lineage_rows == 10000

    def test_config_lineage_limit_can_be_changed(self):
        """Test lineage row limit can be customized."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            max_lineage_rows=5000,
        )

        assert config.max_lineage_rows == 5000

    def test_config_lineage_limit_can_be_disabled(self):
        """Test lineage row limit can be disabled."""
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
            max_lineage_rows=None,
        )

        assert config.max_lineage_rows is None

    def test_config_from_dict_with_performance_options(self):
        """Test config creation from dict with performance options."""
        config_dict = {
            "account": "test-account",
            "user": "test-user",
            "password": "test-password",
            "parallel_execution": False,
            "enable_query_cache": False,
            "max_lineage_rows": 500,
        }

        config = SnowflakeParserConfig.from_dict(config_dict)

        assert config.parallel_execution is False
        assert config.enable_query_cache is False
        assert config.max_lineage_rows == 500
