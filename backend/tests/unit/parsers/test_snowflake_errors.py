"""Unit tests for Snowflake error handling and resilience."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from src.parsers.snowflake_parser import SnowflakeParser
from src.parsers.snowflake_config import SnowflakeParserConfig
from src.parsers.base import ParseResult, ParseErrorSeverity
from src.utils.retry import is_retryable_snowflake_error, is_permission_error


class TestSnowflakeRetryLogic:
    """Tests for connection retry logic."""

    @pytest.mark.asyncio
    async def test_connection_retry_on_transient_error(self):
        """Test connection retries on transient errors."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock connector to fail twice then succeed
        call_count = 0

        def connect_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Connection timeout")
            return MagicMock()

        with patch("snowflake.connector.connect", side_effect=connect_side_effect):
            # Should succeed on third attempt
            await parser._connect(config)
            assert parser.connector is not None
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_connection_fails_after_max_retries(self):
        """Test connection fails after max retries."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock connector to always fail
        with patch(
            "snowflake.connector.connect",
            side_effect=Exception("Connection timeout")
        ):
            with pytest.raises(Exception) as exc_info:
                await parser._connect(config)
            assert "Connection timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_error_message_formatting(self):
        """Test connection error messages are formatted helpfully."""
        parser = SnowflakeParser()
        config = SnowflakeParserConfig(
            account="invalid-account",
            user="test-user",
            password="test-password",
        )

        # Mock account not found error
        with patch(
            "snowflake.connector.connect",
            side_effect=Exception("Account 'invalid-account' not found")
        ):
            with pytest.raises(Exception) as exc_info:
                await parser._connect(config)

            error_msg = str(exc_info.value)
            assert "account identifier is correct" in error_msg.lower()


class TestSnowflakeErrorDetection:
    """Tests for Snowflake error detection utilities."""

    def test_is_retryable_connection_reset(self):
        """Test connection reset is detected as retryable."""
        error = Exception("Connection reset by peer")
        assert is_retryable_snowflake_error(error) is True

    def test_is_retryable_timeout(self):
        """Test timeout errors are retryable."""
        error = Exception("Connection timed out")
        assert is_retryable_snowflake_error(error) is True

    def test_is_retryable_network_error(self):
        """Test network errors are retryable."""
        error = Exception("Network error occurred")
        assert is_retryable_snowflake_error(error) is True

    def test_is_retryable_rate_limit(self):
        """Test rate limit errors are retryable."""
        error = Exception("Too many requests, rate limit exceeded")
        assert is_retryable_snowflake_error(error) is True

    def test_is_not_retryable_syntax_error(self):
        """Test syntax errors are not retryable."""
        error = Exception("SQL compilation error: syntax error")
        assert is_retryable_snowflake_error(error) is False

    def test_is_permission_error_access_denied(self):
        """Test access denied is detected as permission error."""
        error = Exception("Access denied for user 'test'")
        assert is_permission_error(error) is True

    def test_is_permission_error_insufficient_privileges(self):
        """Test insufficient privileges detected."""
        error = Exception("Insufficient privileges to operate on database 'TEST'")
        assert is_permission_error(error) is True

    def test_is_not_permission_error(self):
        """Test non-permission errors not detected as permission."""
        error = Exception("Connection timeout")
        assert is_permission_error(error) is False


class TestSnowflakePartialSuccess:
    """Tests for partial success handling."""

    @pytest.mark.asyncio
    async def test_continues_on_table_error(self):
        """Test extraction continues when individual table fails."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock tables query - 3 tables
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        mock_cursor.fetchall.return_value = [
            ("TEST_DB", "PUBLIC", "TABLE1", "BASE TABLE", 100, 1024,
             datetime(2024, 12, 20), datetime(2024, 12, 20), "Table 1"),
            ("TEST_DB", "PUBLIC", "TABLE2", "BASE TABLE", 100, 1024,
             datetime(2024, 12, 20), datetime(2024, 12, 20), "Table 2"),
            ("TEST_DB", "PUBLIC", "TABLE3", "BASE TABLE", 100, 1024,
             datetime(2024, 12, 20), datetime(2024, 12, 20), "Table 3"),
        ]
        parser.connector.cursor.return_value = mock_cursor

        # Mock column query to fail for TABLE2
        async def mock_query_columns(db, schema, table):
            if table == "TABLE2":
                raise Exception("Permission denied on TABLE2")
            # Return empty list for successful tables
            return []

        with patch.object(parser, "_query_columns", side_effect=mock_query_columns):
            result = ParseResult(source_type="snowflake")
            await parser._extract_database_metadata("TEST_DB", config, result)

        # Should have 3 capsules (all tables are created, but TABLE2 has no columns)
        assert len(result.capsules) == 3
        capsule_names = {c.name for c in result.capsules}
        assert "TABLE1" in capsule_names
        assert "TABLE2" in capsule_names  # Capsule created, but column query failed
        assert "TABLE3" in capsule_names

        # Should have 1 warning for TABLE2 column extraction
        assert len(result.errors) == 1
        assert result.errors[0].severity == ParseErrorSeverity.WARNING
        assert "TABLE2" in result.errors[0].message
        assert "Permission denied" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_continues_on_column_error(self):
        """Test extraction continues when column extraction fails."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock tables query - 1 table
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        mock_cursor.fetchall.return_value = [
            ("TEST_DB", "PUBLIC", "TABLE1", "BASE TABLE", 100, 1024,
             datetime(2024, 12, 20), datetime(2024, 12, 20), "Table 1"),
        ]
        parser.connector.cursor.return_value = mock_cursor

        # Mock column query to fail
        with patch.object(
            parser,
            "_query_columns",
            side_effect=Exception("Column query failed")
        ):
            result = ParseResult(source_type="snowflake")
            await parser._extract_database_metadata("TEST_DB", config, result)

        # Should still have the table capsule
        assert len(result.capsules) == 1
        # Should have error
        assert len(result.errors) == 1


class TestSnowflakeErrorMessages:
    """Tests for error message quality."""

    def test_format_account_not_found_error(self):
        """Test account not found error is formatted."""
        parser = SnowflakeParser()
        error = Exception("Account 'test-account' not found")
        formatted = parser._format_connection_error(error)
        assert "account identifier is correct" in formatted
        assert "orgname-accountname" in formatted

    def test_format_authentication_error(self):
        """Test authentication error is formatted."""
        parser = SnowflakeParser()
        error = Exception("Authentication failed")
        formatted = parser._format_connection_error(error)
        assert "credentials" in formatted.lower()

    def test_format_warehouse_error(self):
        """Test warehouse error is formatted."""
        parser = SnowflakeParser()
        error = Exception("Warehouse 'UNKNOWN_WH' does not exist")
        formatted = parser._format_connection_error(error)
        assert "warehouse" in formatted.lower()

    def test_format_role_error(self):
        """Test role error is formatted."""
        parser = SnowflakeParser()
        error = Exception("Role 'UNKNOWN_ROLE' does not exist")
        formatted = parser._format_connection_error(error)
        assert "role" in formatted.lower()

    def test_format_generic_error(self):
        """Test generic error is returned as-is."""
        parser = SnowflakeParser()
        error = Exception("Some other error")
        formatted = parser._format_connection_error(error)
        assert formatted == "Some other error"


class TestSnowflakePerformanceLogging:
    """Tests for performance logging."""

    @pytest.mark.asyncio
    async def test_logs_extraction_duration(self, caplog):
        """Test extraction duration is logged."""
        import logging
        caplog.set_level(logging.INFO)

        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock tables query - 2 tables
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        mock_cursor.fetchall.return_value = [
            ("TEST_DB", "PUBLIC", "TABLE1", "BASE TABLE", 100, 1024,
             datetime(2024, 12, 20), datetime(2024, 12, 20), "Table 1"),
            ("TEST_DB", "PUBLIC", "TABLE2", "BASE TABLE", 100, 1024,
             datetime(2024, 12, 20), datetime(2024, 12, 20), "Table 2"),
        ]
        parser.connector.cursor.return_value = mock_cursor

        # Mock column query
        with patch.object(parser, "_query_columns", return_value=[]):
            result = ParseResult(source_type="snowflake")
            await parser._extract_database_metadata("TEST_DB", config, result)

        # Check performance log
        logs = [record.message for record in caplog.records]
        performance_logs = [log for log in logs if "extraction complete" in log.lower()]
        assert len(performance_logs) > 0

        perf_log = performance_logs[0]
        assert "2 tables" in perf_log
        assert "in" in perf_log  # Duration
        assert "s" in perf_log  # Seconds

    @pytest.mark.asyncio
    async def test_logs_warning_for_no_tables(self, caplog):
        """Test warning logged when no tables found."""
        import logging
        caplog.set_level(logging.WARNING)

        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock tables query - no tables
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
        ]
        mock_cursor.fetchall.return_value = []
        parser.connector.cursor.return_value = mock_cursor

        result = ParseResult(source_type="snowflake")
        await parser._extract_database_metadata("TEST_DB", config, result)

        # Check warning log
        logs = [record.message for record in caplog.records]
        warning_logs = [log for log in logs if "no tables found" in log.lower()]
        assert len(warning_logs) > 0


class TestSnowflakeErrorContext:
    """Tests for error context information."""

    @pytest.mark.asyncio
    async def test_error_includes_context(self):
        """Test errors include context information."""
        parser = SnowflakeParser()
        parser.connector = MagicMock()

        config = SnowflakeParserConfig(
            account="test-account",
            user="test-user",
            password="test-password",
        )

        # Mock tables query with one table
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("database_name",), ("schema_name",), ("table_name",),
            ("table_type",), ("row_count",), ("bytes",),
            ("created",), ("last_altered",), ("description",)
        ]
        mock_cursor.fetchall.return_value = [
            ("TEST_DB", "SCHEMA1", "TABLE1", "BASE TABLE", 100, 1024,
             datetime(2024, 12, 20), datetime(2024, 12, 20), "Table 1"),
        ]
        parser.connector.cursor.return_value = mock_cursor

        # Mock column query to fail
        with patch.object(
            parser,
            "_query_columns",
            side_effect=Exception("Column error")
        ):
            result = ParseResult(source_type="snowflake")
            await parser._extract_database_metadata("TEST_DB", config, result)

        # Check error has context
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.context is not None
        assert error.context.get("database") == "TEST_DB"
        assert error.context.get("schema") == "SCHEMA1"
        assert error.context.get("table") == "TABLE1"
