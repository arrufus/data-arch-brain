"""Integration tests for Snowflake ingestion CLI command."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typer.testing import CliRunner

from src.cli.main import app
from src.services.ingestion import IngestionResult, IngestionStats, IngestionStatus


runner = CliRunner()


@pytest.fixture
def mock_ingestion_service():
    """Fixture to mock IngestionService."""
    with patch("src.cli.main.IngestionService") as mock_service_class:
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Create a mock async method
        async def mock_ingest_snowflake(**kwargs):
            return IngestionResult(
                job_id="12345678-1234-1234-1234-123456789abc",
                status=IngestionStatus.COMPLETED,
                source_type="snowflake",
                source_name="PROD",
                stats=IngestionStats(
                    capsules_created=10,
                    capsules_updated=5,
                    columns_created=100,
                    edges_created=15,
                ),
            )

        mock_service.ingest_snowflake = mock_ingest_snowflake
        yield mock_service


def test_snowflake_ingest_with_password(mock_ingestion_service):
    """Test Snowflake CLI ingestion with password authentication."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--databases",
            "PROD,ANALYTICS",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout
    assert "PROD" in result.stdout or "snowflake" in result.stdout


def test_snowflake_ingest_missing_password():
    """Test Snowflake CLI ingestion fails when password is missing."""
    # Remove password from environment
    if "SNOWFLAKE_PASSWORD" in os.environ:
        del os.environ["SNOWFLAKE_PASSWORD"]

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
        ],
    )

    assert result.exit_code == 1
    assert "Password not found" in result.stdout or "Error" in result.stdout


def test_snowflake_ingest_with_key_pair(mock_ingestion_service, tmp_path):
    """Test Snowflake CLI ingestion with key-pair authentication."""
    # Create a temporary key file
    key_file = tmp_path / "test_key.p8"
    key_file.write_text("fake-key-content")

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--private-key",
            str(key_file),
            "--databases",
            "PROD",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout


def test_snowflake_ingest_with_lineage_options(mock_ingestion_service):
    """Test Snowflake CLI ingestion with lineage options."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--databases",
            "PROD",
            "--enable-lineage",
            "--lineage-lookback-days",
            "14",
            "--use-account-usage",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout


def test_snowflake_ingest_with_filters(mock_ingestion_service):
    """Test Snowflake CLI ingestion with database and schema filters."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--databases",
            "PROD,ANALYTICS",
            "--schemas",
            "RAW_*,STAGING_*",
            "--no-views",
            "--no-materialized-views",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout


def test_snowflake_ingest_with_tag_extraction(mock_ingestion_service):
    """Test Snowflake CLI ingestion with tag extraction enabled."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--databases",
            "PROD",
            "--enable-tag-extraction",
            "--use-account-usage",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout


def test_snowflake_ingest_with_cleanup_orphans(mock_ingestion_service):
    """Test Snowflake CLI ingestion with cleanup orphans flag."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--databases",
            "PROD",
            "--cleanup-orphans",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout


def test_snowflake_ingest_custom_warehouse_and_role(mock_ingestion_service):
    """Test Snowflake CLI ingestion with custom warehouse and role."""
    os.environ["SNOWFLAKE_PASSWORD"] = "test-password"

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--warehouse",
            "METADATA_WH",
            "--role",
            "METADATA_READER",
            "--databases",
            "PROD",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout


def test_snowflake_ingest_custom_password_env(mock_ingestion_service):
    """Test Snowflake CLI ingestion with custom password environment variable."""
    # Set custom env var
    os.environ["CUSTOM_SF_PASSWORD"] = "test-password"

    result = runner.invoke(
        app,
        [
            "ingest",
            "snowflake",
            "--account",
            "test-account",
            "--user",
            "test-user",
            "--password-env",
            "CUSTOM_SF_PASSWORD",
            "--databases",
            "PROD",
        ],
    )

    assert result.exit_code == 0
    assert "Ingestion completed successfully" in result.stdout

    # Clean up
    del os.environ["CUSTOM_SF_PASSWORD"]


def test_snowflake_ingest_help():
    """Test Snowflake CLI ingestion help text."""
    result = runner.invoke(app, ["ingest", "snowflake", "--help"])

    assert result.exit_code == 0
    assert "Snowflake" in result.stdout
    assert "--account" in result.stdout
    assert "--user" in result.stdout
    assert "--databases" in result.stdout
    assert "INFORMATION_SCHEMA" in result.stdout or "metadata" in result.stdout
